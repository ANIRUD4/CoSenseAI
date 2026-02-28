from interaction.voice_listener import VoiceListener

listener = VoiceListener(
    model_path="models/vosk-model-small-en-us-0.15"
)

print("Speak now...")
text = listener.listen_once(duration=4)
print("You said:", text)
