from fastapi import APIRouter, UploadFile, File, HTTPException
from interaction.voice_api import transcribe_audio

router = APIRouter(prefix="/speech", tags=["Speech"])

@router.post("/transcribe")
def transcribe(file: UploadFile = File(...)):
    try:
        audio_bytes = file.file.read()
        text = transcribe_audio(audio_bytes)

        if not text:
            return {"text": ""}

        return {"text": text.lower()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
