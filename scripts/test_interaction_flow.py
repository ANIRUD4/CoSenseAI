from interaction.voice_listener import VoiceListener
from interaction.intent_parser import IntentParser

listener = VoiceListener(
    model_path="models/vosk-model-small-en-us-0.15"
)
parser = IntentParser()

print("Speak command...")
text = listener.listen_once(duration=4)
intent = parser.parse(text)

print("Recognized text:", text)
print("Detected intent:", intent)
