import sounddevice as sd
from vosk import Model, KaldiRecognizer
import tempfile, subprocess, wave, json, os, queue

class VoiceListener:
    """
    Offline voice listener for IntelShare.
    Listens ONLY when explicitly called by backend.
    """

    def __init__(self, model_path="models/vosk-model"):
        self.is_mocked = False
        try:
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, 16000)
            print(f"VOSK: Model loaded successfully from {model_path}")
        except Exception as e:
            self.model = None
            self.recognizer = None
            self.is_mocked = True
            print(f"WARNING: VOSK model failed to load from {model_path}: {e}")
            print("VOSK: Running in MOCK mode.")
            
        self.audio_queue = queue.Queue()

    def _callback(self, indata, frames, time, status):
        self.audio_queue.put(bytes(indata))

    def listen_once(self, duration=4):
        """
        Listen for a short duration and return recognized text.
        """
        if self.is_mocked:
            print("VOSK (MOCK): simulating listening...")
            return "mock transcription from listener"

        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback
        ):
            for _ in range(int(16000 / 8000 * duration)):
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    return result.get("text", "")

        final = json.loads(self.recognizer.FinalResult())
        return final.get("text", "")

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        if self.is_mocked:
            print(f"VOSK (MOCK): transcribing {len(audio_bytes)} bytes...")
            return "mock transcription from bytes"

        print("VOSK: received audio bytes =", len(audio_bytes))

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_in:
            temp_in.write(audio_bytes)
            temp_in_path = temp_in.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_out:
            temp_out_path = temp_out.name

        print("VOSK: converting with ffmpeg...")
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", temp_in_path,
                "-ar", "16000",
                "-ac", "1",
                temp_out_path
            ],
            capture_output=True,
            text=True
        )

        print("FFMPEG stdout:", result.stdout)
        print("FFMPEG stderr:", result.stderr)

        if not os.path.exists(temp_out_path) or os.path.getsize(temp_out_path) == 0:
            raise ValueError("FFmpeg failed to produce WAV")

        print("VOSK: opening wav file")

        wf = wave.open(temp_out_path, "rb")
        print("WAV params:", wf.getnchannels(), wf.getframerate())

        rec = KaldiRecognizer(self.model, wf.getframerate())

        text = ""

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                text += json.loads(rec.Result()).get("text", "") + " "

        text += json.loads(rec.FinalResult()).get("text", "")
        print("VOSK FINAL TEXT:", text)

        return text.strip()
