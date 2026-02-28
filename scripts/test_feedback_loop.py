from interaction.feedback_loop import FeedbackLoop

feedback = FeedbackLoop()

state = feedback.ask_confirmation("Paracetamol")
print("State:", state)

result = feedback.handle_feedback("CONFIRM_YES")
print("Result:", result)
