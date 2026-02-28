class IntentParser:
    """
    Converts raw speech text into high-level intent.
    Supports:
    - System commands (learn, infer, confirm, correct)
    - Action commands (highlight, alert, stop)
    """

    # Action intent keywords
    ACTION_INTENTS = {
        "highlight": ["show", "mark", "highlight", "focus"],
        "alert": ["warn", "alert", "danger", "notify"],
        "stop": ["stop", "halt", "freeze", "pause"]
    }

    def parse(self, text: str) -> str:
        """
        Main entry point.
        Returns standardized intent string.
        """

        if not text:
            return "UNKNOWN"

        t = text.lower().strip()

        # =============================
        # System intents
        # =============================

        if "learn" in t or "teach" in t:
            return "LEARN"

        if "what is this" in t or "identify" in t or "detect" in t:
            return "INFER"

        if t in ["yes", "correct", "right", "yeah", "yup"]:
            return "CONFIRM_YES"

        if t in ["no", "wrong", "nope", "incorrect"]:
            return "CONFIRM_NO"

        # =============================
        # Action intents
        # =============================

        for intent, keywords in self.ACTION_INTENTS.items():

            for word in keywords:
                if word in t:
                    return intent.upper()

        # =============================
        # Fallback
        # =============================

        return "UNKNOWN"
