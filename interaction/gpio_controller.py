try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # Allows testing on laptop


class GPIOController:
    """
    Controls LEDs / relays for physical feedback.
    """

    LEARNING_LED = 17
    CONFIRM_LED = 27
    SUCCESS_LED = 22

    def __init__(self):
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.LEARNING_LED, GPIO.OUT)
            GPIO.setup(self.CONFIRM_LED, GPIO.OUT)
            GPIO.setup(self.SUCCESS_LED, GPIO.OUT)

    def learning_on(self):
        if GPIO:
            GPIO.output(self.LEARNING_LED, True)

    def waiting_confirmation(self):
        if GPIO:
            GPIO.output(self.CONFIRM_LED, True)

    def success(self):
        if GPIO:
            GPIO.output(self.SUCCESS_LED, True)

    def reset(self):
        if GPIO:
            GPIO.cleanup()

    """
    Mock + Hardware controller
    """

    def blink(self, times=1):
        print(f"[GPIO] Blink x{times}")

    def beep(self, times=1):
        print(f"[GPIO] Beep x{times}")

    def stop_all(self):
        print("[GPIO] STOP ALL")
