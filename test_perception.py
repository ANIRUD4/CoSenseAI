from perception.camera import Camera
from perception.preprocessor import Preprocessor
from perception.embedding_engine import EmbeddingEngine

cam = Camera()
pre = Preprocessor()
embedder = EmbeddingEngine()

frame = cam.capture_frame()
# import cv2

# cv2.imshow("Captured Image (IntelShare Demo)", frame)
# cv2.waitKey(2000)  # show for 2 seconds
# cv2.destroyAllWindows()

image = pre.process(frame)
embedding = embedder.get_embedding(image)

# perception → backend output
output = {
    "embedding": embedding
}

print(output)

cam.close()
