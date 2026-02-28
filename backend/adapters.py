USE_MOCKS = False

if USE_MOCKS:
    from mocks.perception_mock import get_embedding
    from mocks.learning_mock import predict, update
    from mocks.interaction_mock import get_intent, get_confirmation
else:
    from perception.interface import get_embedding
    from learning.interface import predict, update
    from interaction.interface import get_intent, get_confirmation
