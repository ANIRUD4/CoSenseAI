"""
gpio_controller.py — Hardware status feedback for IntelShareAI (Raspberry Pi 5)

Pin mapping (BCM numbering):
    Red  LED  → GPIO 5
    Green LED → GPIO 6
    Buzzer    → GPIO 12

States:
    boot()               → Both LEDs solid ON  (system starting up)
    ready()              → Red solid ON  +  1 long beep
    set_infer_mode()     → Red LED breathing (PWMLED.pulse)
    set_awaiting_feedback() → Green LED blinking  +  2 short beeps
                              Starts 10-second timeout watchdog.
                              If not cancelled, calls set_timeout_error().
    set_learn_mode()     → Green LED solid  +  1 short beep
                           Cancels any active timeout watchdog.
    set_success()        → Returns to Red breathing  +  1 medium beep
    set_timeout_error()  → Red blinking  +  3 rapid beeps
                           Reverts to set_infer_mode() after 2 s.

Non-Pi environments (laptop / CI):
    gpiozero is unavailable → falls through to a console-only mock so the
    rest of the system can run without modification.
"""

import threading
import time

# ── gpiozero import (graceful fallback for non-Pi environments) ──────────────
_HW_AVAILABLE = False
_LGPIO_OK     = False   # True only when LGPIOFactory.init() actually succeeded
_INIT_LOG = []

try:
    # Essential for Pi 5 — must set pin_factory BEFORE importing devices
    from gpiozero.pins.lgpio import LGPIOFactory
    from gpiozero import Device
    Device.pin_factory = LGPIOFactory()
    _LGPIO_OK = True
    _INIT_LOG.append("lgpio factory loaded")
except Exception as e:
    _INIT_LOG.append(f"lgpio factory fail: {e}")

# Independent imports to prevent one failure from killing everything
try:
    # LED is a subclass of DigitalOutputDevice that adds .blink().
    # CRITICAL: DigitalOutputDevice does NOT have .blink() — using it for LEDs
    # causes a silent AttributeError on every animated state transition.
    from gpiozero import LED
    _INIT_LOG.append("LED available")
except ImportError:
    LED = None
    _INIT_LOG.append("LED missing")

try:
    # Buzzer only uses .on()/.off() so DigitalOutputDevice is correct here.
    from gpiozero import DigitalOutputDevice
    _INIT_LOG.append("DigitalOutputDevice available")
except ImportError:
    DigitalOutputDevice = None
    _INIT_LOG.append("DigitalOutputDevice missing")

# Hardware is only truly available when BOTH lgpio initialised AND the LED
# class was imported.  Importing LED is not enough — if LGPIOFactory failed
# (e.g. /dev/gpiochip0 is locked or wrong user), every pin.on() call will
# throw at runtime, giving a false "HARDWARE mode" impression.
_HW_AVAILABLE = _LGPIO_OK and (LED is not None)
_INIT_ERROR = " | ".join(_INIT_LOG)

# -- Buzzer helper ────────────────────────────────────────────────────────────
_BUZZER_PIN = 12
_RED_PIN    = 5
_GREEN_PIN  = 6

class _BuzzerHelper:
    def __init__(self, pin):
        self._lock = threading.Lock()
        self._hw_pin = None
        if DigitalOutputDevice:
            try:
                self._hw_pin = DigitalOutputDevice(pin)
            except:
                pass

    def _beep_once(self, duration: float):
        if not self._hw_pin:
            time.sleep(duration)
            return
        try:
            self._hw_pin.on()
            time.sleep(duration)
            self._hw_pin.off()
        except Exception:
            pass

    def beep(self, count: int = 1, duration: float = 0.12, gap: float = 0.08):
        """Fire `count` beeps non-blocking in a daemon thread."""
        def _run():
            with self._lock:
                for i in range(count):
                    self._beep_once(duration)
                    if i < count - 1:
                        time.sleep(gap)
        t = threading.Thread(target=_run, daemon=True)
        t.start()


# ── GPIOController ────────────────────────────────────────────────────────────

class GPIOController:
    """
    Singleton-friendly hardware controller.

    Usage (from any backend module):
        from interaction.gpio_controller import hw
        hw.set_infer_mode()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._timeout_timer: threading.Timer | None = None

        # LEDs — use gpiozero.LED (NOT DigitalOutputDevice).
        # LED is a subclass that adds .blink(); DigitalOutputDevice lacks it,
        # causing a silent AttributeError on every animated state call.
        if _HW_AVAILABLE:
            try:
                self._red   = LED(_RED_PIN)
                self._green = LED(_GREEN_PIN)
                _INIT_LOG.append("LED pins opened OK")
            except Exception as e:
                print(f"[GPIO] Hardware init failed: {e} — running in mock mode.")
                self._red   = None
                self._green = None
        else:
            self._red   = None
            self._green = None

        # Buzzer — only uses .on()/.off(), so DigitalOutputDevice is fine
        self._buzzer = _BuzzerHelper(_BUZZER_PIN)

        # Initial state: everything off
        self.stop()

        print(
            "[GPIO] Controller initialised -- "
            "%(mode)s mode | "
            "Red=GPIO%(r)d Green=GPIO%(g)d Buzzer=GPIO%(b)d" % {
                "mode": "HARDWARE" if _HW_AVAILABLE and self._red else "MOCK",
                "r": _RED_PIN, "g": _GREEN_PIN, "b": _BUZZER_PIN,
            }
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _cancel_timeout(self):
        """Cancel any running feedback-timeout watchdog."""
        if self._timeout_timer and self._timeout_timer.is_alive():
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _stop_leds(self):
        """Stop all LED animations (blink / pulse)."""
        if self._red:
            try:
                self._red.off()
            except Exception:
                pass
        if self._green:
            try:
                self._green.off()
            except Exception:
                pass

    # ── Public state methods ─────────────────────────────────────────────────

    def boot(self):
        """Boot state: both LEDs solid ON (system initialising)."""
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.on()   # LED.on() — was incorrectly using .value=1.0 (PWMLED style)
            if self._green:
                self._green.on()
            print("[GPIO] STATE -> boot (both LEDs ON)")

    def ready(self):
        """Ready state: Red LED solid ON + 1 long beep."""
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.on()
            if self._green:
                self._green.off()
            print("[GPIO] STATE -> ready (Red solid, 1 long beep)")
        self._buzzer.beep(count=1, duration=0.50, gap=0)

    def blink_test(self):
        """Diagnostic: Blink both LEDs to test for inversion/brightness."""
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.blink(n=5, on_time=0.2, off_time=0.2)
            if self._green:
                self._green.blink(n=5, on_time=0.2, off_time=0.2)
            print("[GPIO] Diagnostic: Blinking LEDs...")
        self._buzzer.beep(count=3, duration=0.1, gap=0.1)

    def set_infer_mode(self):
        """Inference mode: Red LED slow-blinks (1 s on / 1 s off), Green OFF."""
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.blink(on_time=1.0, off_time=1.0)  # LED.blink() — works correctly
            if self._green:
                self._green.off()
            print("[GPIO] STATE -> infer_mode (Red blinking)")

    def set_awaiting_feedback(self, timeout_sec: float = 10.0):
        """
        Awaiting-feedback state:
        - Green LED blinks rapidly.
        - 2 short beeps to alert the user.
        - Watchdog timer: if not cancelled within `timeout_sec`, triggers set_timeout_error().
        """
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.off()
            if self._green:
                self._green.blink(on_time=0.25, off_time=0.25)
            # Watchdog
            self._timeout_timer = threading.Timer(timeout_sec, self._on_feedback_timeout)
            self._timeout_timer.daemon = True
            self._timeout_timer.start()
            print(f"[GPIO] STATE -> awaiting_feedback (Green blinking, timeout={timeout_sec}s)")
        self._buzzer.beep(count=2, duration=0.10, gap=0.07)

    def set_learn_mode(self):
        """
        Learning mode:
        - Green LED solid ON.
        - 1 short beep.
        - Cancels any active timeout watchdog.
        """
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                self._red.off()
            if self._green:
                self._green.on()
            print("[GPIO] STATE -> learn_mode (Green solid, 1 short beep)")
        self._buzzer.beep(count=1, duration=0.12, gap=0)

    def set_success(self):
        """
        Success state:
        - Red LED slow-blinks (pulse not available on DigitalOutputDevice).
        - Green OFF.
        - 1 medium beep.
        """
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
            if self._red:
                # DigitalOutputDevice has no .pulse() — use slow blink instead.
                # If PWMLED is ever wired, swap this for self._red.pulse(...)
                self._red.blink(on_time=1.0, off_time=1.0)
            if self._green:
                self._green.off()
            print("[GPIO] STATE -> success (Red slow-blink, 1 medium beep)")
        self._buzzer.beep(count=1, duration=0.25, gap=0)

    def set_timeout_error(self):
        """
        Timeout / error state:
        - Red LED blinks rapidly.
        - 3 rapid beeps.
        - Auto-reverts to infer_mode after 2 s.
        """
        with self._lock:
            self._stop_leds()
            if self._red:
                self._red.blink(on_time=0.15, off_time=0.15)
            if self._green:
                self._green.off()
            print("[GPIO] STATE -> timeout_error (Red blinking fast, 3 beeps)")
        self._buzzer.beep(count=3, duration=0.08, gap=0.06)
        # Revert to infer mode after 2 seconds
        revert = threading.Timer(2.0, self.set_infer_mode)
        revert.daemon = True
        revert.start()

    # ── Internal callback ────────────────────────────────────────────────────

    def _on_feedback_timeout(self):
        """Called by the watchdog timer when feedback is not received in time."""
        print("[GPIO] Feedback timeout -- triggering error state.")
        self.set_timeout_error()

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def cleanup(self):
        """Release all GPIO resources. Call on application shutdown."""
        with self._lock:
            self._cancel_timeout()
            self._stop_leds()
        if _HW_AVAILABLE:
            try:
                from gpiozero import Device
                Device.close()
            except Exception:
                pass
        print("[GPIO] Cleanup complete.")

    # ── Legacy compatibility stubs ───────────────────────────────────────────
    # Keep old method names so nothing elsewhere breaks.

    def learning_on(self):
        self.set_learn_mode()

    def waiting_confirmation(self):
        self.set_awaiting_feedback()

    def success(self):
        self.set_success()

    def reset(self):
        self.cleanup()

    def blink(self, times=1):
        print(f"[GPIO] Blink ×{times}")

    def beep(self, times=1):
        self._buzzer.beep(count=times)

    def stop(self):
        self._stop_leds()


# ── Module-level singleton ───────────────────────────────────────────────────
# Import this anywhere with: from interaction.gpio_controller import hw
hw = GPIOController()
