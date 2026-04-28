# coding: utf-8
"""
test_gpio.py - Full state-machine verification for IntelShareAI hardware feedback.

Run on the Raspberry Pi 5 (or any host for mock-mode log verification):
    python -m scripts.test_gpio

Expected sequence (watch LEDs and listen for buzzer):
    1. BOOT      - Both LEDs ON (solid)              ~2 s
    2. READY     - Red solid ON + 1 long beep        ~2 s
    3. INFER     - Red LED breathing (pulse)          ~4 s
    4. AWAIT     - Green LED blinking + 2 short beeps ~3 s (then advance)
    5. LEARN     - Green LED solid + 1 short beep     ~2 s
    6. SUCCESS   - Red breathing + 1 medium beep      ~4 s
    7. TIMEOUT   - Green blink, no feedback, timeout fires automatically
                   Red blinks rapidly + 3 beeps, reverts to Red breathing
"""

import sys
import os
import time

# Allow running as `python scripts/test_gpio.py` from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interaction.gpio_controller import hw

STEP_DELAY = 2.5  # seconds between demonstration steps


def pause(label, duration=STEP_DELAY):
    print("  >> Holding '%s' state for %.1fs ..." % (label, duration))
    time.sleep(duration)


def run_tests():
    print("\n" + "=" * 60)
    print("  IntelShareAI - GPIO State Machine Verification")
    print("=" * 60 + "\n")

    # --- 1. Boot ---
    print("[TEST 1/7] BOOT - Both LEDs solid ON")
    hw.boot()
    pause("boot")

    # --- 2. Ready ---
    print("[TEST 2/7] READY - Red solid + 1 long beep")
    hw.ready()
    pause("ready")

    # --- 3. Infer Mode ---
    print("[TEST 3/7] INFER MODE - Red breathing (pulse)")
    hw.set_infer_mode()
    pause("infer_mode", 4.0)

    # --- 4. Awaiting Feedback (manually cancel before timeout) ---
    print("[TEST 4/7] AWAITING FEEDBACK - Green blink + 2 beeps")
    print("           (watchdog set to 15 s; we will cancel manually in 3 s)")
    hw.set_awaiting_feedback(timeout_sec=15.0)
    pause("awaiting_feedback", 3.0)

    # --- 5. Learn Mode (cancels the watchdog above) ---
    print("[TEST 5/7] LEARN MODE - Green solid + 1 short beep (cancels watchdog)")
    hw.set_learn_mode()
    pause("learn_mode")

    # --- 6. Success ---
    print("[TEST 6/7] SUCCESS - Red breathing + 1 medium beep")
    hw.set_success()
    pause("success", 4.0)

    # --- 7. Timeout (let watchdog fire naturally) ---
    print("[TEST 7/7] TIMEOUT - Green blink, then 10-second watchdog fires")
    print("           Watch for: Red blinks fast + 3 rapid beeps -> Red breathing")
    hw.set_awaiting_feedback(timeout_sec=10.0)
    # Wait long enough: 10 s (timeout) + 2 s (error display) + 1 s (buffer)
    pause("awaiting_feedback -> timeout auto-revert", 14.0)

    # --- Done ---
    print("\n" + "=" * 60)
    print("  All 7 tests complete. Cleaning up GPIO resources.")
    print("=" * 60 + "\n")
    hw.cleanup()


if __name__ == "__main__":
    run_tests()
