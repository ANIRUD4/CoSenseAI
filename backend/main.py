# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routes import learn, infer, confirm, export_import, perceive, speech, act, metrics, boost, admin
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
app.include_router(boost.router)
app.include_router(admin.router)

@app.get("/health")
def health():
    return {"status": "IntelShare running"}

@app.get("/")
def root():
    return {"status": "IntelShare online", "version": "1.0.4"}

# Serve static files from the React app
# Ensure the React app is built (npm run build) before running the backend in production
if os.path.exists("frontend_react/dist"):
    app.mount("/", StaticFiles(directory="frontend_react/dist", html=True), name="static")
