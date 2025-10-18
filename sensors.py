import RPi.GPIO as GPIO
import time

class Ultrasonic:
    def __init__(self, trig_pin=23, echo_pin=24):
        self.TRIG = trig_pin
        self.ECHO = echo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.output(self.TRIG, False)
        time.sleep(0.1)

    def distance_cm(self):
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)
        start = time.time()
        timeout = start + 0.04
        while GPIO.input(self.ECHO) == 0 and time.time() < timeout:
            start = time.time()
        stop = time.time()
        timeout2 = stop + 0.04
        while GPIO.input(self.ECHO) == 1 and time.time() < timeout2:
            stop = time.time()
        elapsed = stop - start
        distance = (elapsed * 34300) / 2
        return distance

    def cleanup(self):
        GPIO.cleanup()
