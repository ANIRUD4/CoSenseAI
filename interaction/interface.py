from interaction.voice_listener import VoiceListener
from interaction.intent_parser import IntentParser
from interaction.feedback_loop import FeedbackLoop
from interaction.intent_parser import IntentParser

_listener = VoiceListener(model_path="models/vosk-model-small-en-us-0.15")
_parser = IntentParser()
_feedback = FeedbackLoop()



def get_action_intent():

    text = _listener.listen_once()

    return _parser.parse(text)

def get_label() -> str:
    """
    Listens once and returns a high-level human intent.

    Returns:
        "label"    → the spoken label for the object
    """
    text = _listener.listen_once()
    intent = _parser.parse(text)

    return intent.lower()

def get_intent() -> str:
    """
    Listens once and returns a high-level human intent.

    Returns:
        "learn"    → start teaching mode
        "infer"    → identify current object
        "confirm"  → human agrees with system
        "correct"  → human disagrees / will correct
        "unknown"  → unclear input
    """
    text = _listener.listen_once()
    intent = _parser.parse(text)

    return intent.lower()


def get_confirmation() -> dict:
    """
    Handles confirmation or correction after a prediction.

    Returns:
        {
            "confirmed": bool,
            "corrected_label": str | None
        }
    """
    response_text = _listener.listen_once()
    intent = _parser.parse(response_text)

    if intent == "CONFIRM_YES":
        return {
            "confirmed": True,
            "corrected_label": None
        }

    if intent == "CONFIRM_NO":
        print("Please say the correct name of the object.")
        corrected_label = _listener.listen_once()

        return {
            "confirmed": False,
            "corrected_label": corrected_label
        }

    return {
        "confirmed": False,
        "corrected_label": None
    }