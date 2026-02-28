from interaction.voice_listener import VoiceListener

_listener = VoiceListener(model_path="models/vosk-model-small-en-us-0.15")

def transcribe_audio(audio_bytes: bytes) -> str:
    return _listener.transcribe_bytes(audio_bytes)
