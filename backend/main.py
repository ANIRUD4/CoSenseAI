# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from backend.routes import learn, infer, confirm, export_import, perceive, speech, act
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="IntelShare")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
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

@app.get("/")
def health():
    return {"status": "IntelShare running"}
