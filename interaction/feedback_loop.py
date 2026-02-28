class FeedbackLoop:
    """
    Handles human confirmation and correction flow.
    """

    def ask_confirmation(self, label: str) -> str:
        """
        Ask human to confirm prediction.
        """
        print(f"I think this is '{label}'. Am I right?")
        print("Please say YES or NO.")

        # Backend will capture voice again
        return "AWAIT_CONFIRMATION"

    def handle_feedback(self, intent: str):
        """
        Process confirmation response.
        """
        if intent == "CONFIRM_YES":
            return "CONFIRMED"

        if intent == "CONFIRM_NO":
            return "CORRECTION_REQUIRED"

        return "UNKNOWN"
