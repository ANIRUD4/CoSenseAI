from learning.incremental_learner import IncrementalLearner

learner = IncrementalLearner(embedding_dim=128)

dummy_embedding = [0.1] * 128

# First label (buffered, no training yet)
learner.learn(dummy_embedding, "cup")

# Second label (now training starts)
learner.learn(dummy_embedding, "bottle")

result = learner.predict(dummy_embedding)
print(result)
