import json
import time
import threading
from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
from pymavlink import mavutil
import argparse
import sys

from detection import TFLiteDetector
from sensors import Ultrasonic
from deterrent import Deterrent

MODEL_PATH = "wild_boar_model.tflite"
LABEL_MAP = {0: "wild_boar"}
DETECTION_THRESHOLD = 0.5
CAMERA_INDEX = 0
ULTRASONIC_TRIG = 23
ULTRASONIC_ECHO = 24
MIN_OBSTACLE_DIST_CM = 150
DETECTION_CONFIRMATIONS = 2
RTL_ON_DETECTION = False

CONNECTION_STRING = "/dev/serial0"

def load_mission(filename):
    with open(filename, 'r') as f:
        waypoints = json.load(f)
    return waypoints

def arm_and_takeoff(vehicle, target_alt):
    print("[flight] Arming motors")
    while not vehicle.is_armable:
        print("[flight] Waiting for vehicle to become armable...")
        time.sleep(1)
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        print("[flight] Waiting to arm...")
        time.sleep(1)
    print("[flight] Taking off to altitude", target_alt)
    vehicle.simple_takeoff(target_alt)
    while True:
        alt = vehicle.location.global_relative_frame.alt
        print("[flight] Altitude:", alt)
        if alt >= target_alt * 0.95:
            print("[flight] Reached target altitude")
            break
        time.sleep(1)

def goto_waypoint(vehicle, lat, lon, alt, acceptance_m=3):
    loc = LocationGlobalRelative(lat, lon, alt)
    print(f"[flight] Going to {lat},{lon} @ {alt}m")
    vehicle.simple_goto(loc)
    while True:
        cur = vehicle.location.global_frame
        dlat = (cur.lat - lat) * 1.113195e5
        dlon = (cur.lon - lon) * 1.113195e5
        dist = (dlat**2 + dlon**2) ** 0.5
        print(f"[flight] distance to wp (m): {dist:.1f}")
        if dist <= acceptance_m:
            print("[flight] reached waypoint")
            break
        time.sleep(1)

def circle_in_place(vehicle, radius=3, duration=8):
    print("[flight] circle/hold maneuver start")
    start = time.time()
    while time.time() - start < duration:
        msg = vehicle.message_factory.command_long_encode(
                0, 0,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                30,
                1,
                1,
                False,
                0,0,0)
        vehicle.send_mavlink(msg)
        time.sleep(1)
    print("[flight] circle/hold maneuver end")

class DetectorThread(threading.Thread):
    def __init__(self, detector, confirm_frames=2):
        super().__init__()
        self.detector = detector
        self.confirm_frames = confirm_frames
        self.running = True
        self.detection_event = threading.Event()
        self.lock = threading.Lock()
        self.latest_detections = []
        self.confirm_count = 0

    def run(self):
        while self.running:
            frame, detections = self.detector.detect_frame()
            if detections:
                found = any(d['label'] == 'wild_boar' for d in detections)
                if found:
                    self.confirm_count += 1
                else:
                    self.confirm_count = 0
            else:
                self.confirm_count = 0
            if self.confirm_count >= self.confirm_frames:
                print("[detector] CONFIRMED detection!")
                self.detection_event.set()
            time.sleep(0.15)

    def stop(self):
        self.running = False
        self.detector.close()

class UltrasonicThread(threading.Thread):
    def __init__(self, ultrasonic):
        super().__init__()
        self.ultrasonic = ultrasonic
        self.running = True
        self.last_distance = None
        self.obstacle_event = threading.Event()

    def run(self):
        while self.running:
            try:
                d = self.ultrasonic.distance_cm()
                self.last_distance = d
                if d < MIN_OBSTACLE_DIST_CM:
                    print("[ultra] obstacle within", d, "cm")
                    self.obstacle_event.set()
                else:
                    self.obstacle_event.clear()
            except Exception as e:
                print("[ultra] read error:", e)
            time.sleep(0.5)

    def stop(self):
        self.running = False
        self.ultrasonic.cleanup()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--connect', help='vehicle connection string', default=CONNECTION_STRING)
    parser.add_argument('--mission', help='mission json file', default='mission.json')
    args = parser.parse_args()

    waypoints = load_mission(args.mission)
    if not waypoints:
        print("No waypoints found, exiting")
        sys.exit(1)

    print("[main] connecting to vehicle on:", args.connect)
    vehicle = connect(args.connect, wait_ready=True, heartbeat_timeout=60)

    vehicle.parameters['WPNAV_SPEED'] = 200
    vehicle.wait_ready('autopilot_version')

    detector = TFLiteDetector(MODEL_PATH, label_map=LABEL_MAP, threshold=DETECTION_THRESHOLD, camera_index=CAMERA_INDEX)
    detect_thread = DetectorThread(detector, confirm_frames=DETECTION_CONFIRMATIONS)
    ultrasonic = Ultrasonic(ULTRASONIC_TRIG, ULTRASONIC_ECHO)
    ultra_thread = UltrasonicThread(ultrasonic)
    deterrent = Deterrent()

    detect_thread.start()
    ultra_thread.start()

    try:
        target_alt = waypoints[0]['alt']
        arm_and_takeoff(vehicle, target_alt)

        for wp in waypoints:
            lat, lon, alt = wp['lat'], wp['lon'], wp['alt']
            goto_waypoint(vehicle, lat, lon, alt, acceptance_m=3)

            start_wait = time.time()
            while True:
                if detect_thread.detection_event.is_set():
                    print("[main] detection event triggered")
                    if RTL_ON_DETECTION:
                        print("[main] RTL on detection enabled - returning to launch")
                        vehicle.mode = VehicleMode("RTL")
                        raise SystemExit("RTL triggered")
                    else:
                        vehicle.mode = VehicleMode("LOITER")
                        time.sleep(1)
                        deterrent.activate(duration=6)
                        circle_in_place(vehicle, radius=3, duration=6)
                        detect_thread.detection_event.clear()
                        break

                if ultra_thread.obstacle_event.is_set():
                    print("[main] obstacle detected - stopping and hovering")
                    vehicle.mode = VehicleMode("LOITER")
                    current_alt = vehicle.location.global_relative_frame.alt
                    new_alt = current_alt + 5
                    print("[main] ascending to", new_alt)
                    vehicle.simple_goto(LocationGlobalRelative(vehicle.location.global_frame.lat,
                                                                 vehicle.location.global_frame.lon,
                                                                 new_alt))
                    time.sleep(4)
                    ultra_thread.obstacle_event.clear()
                    break

                time.sleep(0.5)

        print("[main] mission complete - returning to launch")
        vehicle.mode = VehicleMode("RTL")
        time.sleep(5)

    except Exception as e:
        print("[main] Exception:", e)
        print("[main] switching to RTL and exiting")
        try:
            vehicle.mode = VehicleMode("RTL")
        except:
            pass

    finally:
        print("[main] cleaning up threads")
        detect_thread.stop()
        ultra_thread.stop()
        deterrent.cleanup()
        vehicle.close()
        print("[main] done")

if __name__ == "__main__":
    main()
