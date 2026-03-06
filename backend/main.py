# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from backend.routes import learn, infer, confirm, export_import, perceive, speech, act, metrics
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="IntelShare")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(act.router)
app.include_router(perceive.router)
app.include_router(speech.router)
app.include_router(learn.router)
app.include_router(infer.router)
app.include_router(confirm.router)
app.include_router(export_import.router)
app.include_router(metrics.router)

@app.get("/")
def health():
    return {"status": "IntelShare running"}
