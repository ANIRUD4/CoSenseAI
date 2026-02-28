def get_intent() -> str:
    """
    Simulates a human intent.
    """
    return "infer"

def get_confirmation() -> dict:
    """
    Simulates human confirmation.
    """
    return {
        "confirmed": True,
        "corrected_label": None
    }
