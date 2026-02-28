"""
Hardware-agnostic actions
"""

from interaction.gpio_controller import GPIOController


gpio = GPIOController()


def highlight(label: str):

    gpio.blink(times=2)

    return f"{label} highlighted"


def alert(label: str):

    gpio.beep(times=3)

    return f"Alert for {label}"


def stop_device(label: str):

    gpio.stop_all()

    return f"Device stopped for {label}"
