import random

EMBEDDING_SIZE = 128


def get_embedding(
    image_frame=None,
    use_center_roi: bool = False,
    use_saliency_roi: bool = False,
    use_focus_roi: bool = False,
) -> dict:
    """
    Mock embedding generator.
    Returns the same dict structure as perception.interface.get_embedding
    so USE_MOCKS=True callers work identically.
    """
    return {
        "embedding": [round(random.random(), 4) for _ in range(EMBEDDING_SIZE)],
        "focus_hint": None,
        "roi_mode": "mock",
    }
