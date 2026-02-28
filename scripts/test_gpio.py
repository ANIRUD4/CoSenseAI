from interaction.gpio_controller import GPIOController

gpio = GPIOController()

print("Learning ON")
gpio.learning_on()

print("Waiting confirmation")
gpio.waiting_confirmation()

print("Success")
gpio.success()

gpio.reset()
print("Done")
