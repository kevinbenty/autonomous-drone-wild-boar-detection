import RPi.GPIO as GPIO
import time

DETERRENT_PIN = 18

class Deterrent:
    def __init__(self, pin=DETERRENT_PIN):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)

    def activate(self, duration=5):
        print("[deterrent] activating for", duration, "s")
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.pin, GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()
