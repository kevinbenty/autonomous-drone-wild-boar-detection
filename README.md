# Autonomous Drone for Wild Boar Detection and Deterrence

An autonomous drone that patrols farmland, detects wild boar with an onboard vision model, and scares them away with an ultrasonic deterrent, built to reduce crop damage without harming the animals.

## How it works

| Step | What happens |
|------|--------------|
| **Patrol** | The drone takes off and flies a list of GPS waypoints (`mission.json`). |
| **Detect** | A TensorFlow Lite model runs on the camera feed onboard. A detection must be confirmed in 2 consecutive frames to avoid false alarms. |
| **Deter** | On a confirmed detection the drone hovers, activates the ultrasonic deterrent for 6 seconds, and yaws in place. |
| **Stay safe** | An ultrasonic distance sensor checks for obstacles; anything closer than 1.5 m makes the drone climb 5 m. Any error triggers Return-to-Launch. |
| **Return** | After the last waypoint, the drone returns home. |

## Hardware

| Component | Role |
|-----------|------|
| Raspberry Pi | Onboard computer running detection and mission logic |
| ArduPilot flight controller | Flight control, connected over MAVLink (`/dev/serial0`) |
| Camera (USB/CSI) | Video feed for detection, read via OpenCV |
| Ultrasonic distance sensor | Obstacle detection (TRIG: GPIO 23, ECHO: GPIO 24) |
| Ultrasonic deterrent | Switched on GPIO 18 |

## Code structure

| File | Purpose |
|------|---------|
| `main.py` | Mission loop: takeoff, waypoints, detection/deterrence, failsafes |
| `detection.py` | TFLite detector running on the camera feed |
| `deterrent.py` | Switches the deterrent on/off via GPIO |
| `sensors.py` | Ultrasonic distance sensor for obstacle checks |
| `camera.py`, `model.py` | Camera and model helpers |
| `mission.json` | Waypoints as `{"lat", "lon", "alt"}` |

## Setup

On the Raspberry Pi, install dependencies:

```bash
bash setup_pi.sh
```

Place your trained model at `wild_boar_model.tflite`, then run:

```bash
python3 main.py --connect /dev/serial0 --mission mission.json
```

## Team

Kevin Benty, Athul Joe Palliparambil, Alan Cherian, Aswin Anilkumar, Amal Roy (Government Engineering College, Idukki)
