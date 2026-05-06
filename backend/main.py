# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from backend.routes import learn, infer, confirm, export_import, perceive, speech, act, metrics, boost, admin
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from interaction.gpio_controller import hw
from backend.camera import camera_stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    hw.boot()
    hw.ready()
    camera_stream.start()
    yield
    # Shutdown sequence
    camera_stream.stop()
    hw.cleanup()

app = FastAPI(title="IntelShare", lifespan=lifespan)

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

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        camera_stream.get_frame(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.get("/health")
def health():
    return {"status": "IntelShare running"}

@app.get("/test_gpio")
def test_gpio():
    # Force a beep and return the current hardware availability
    from interaction.gpio_controller import _HW_AVAILABLE, _INIT_ERROR
    hw.ready() # triggers 1 long beep
    return {
        "status": "triggered ready sequence",
        "hardware_available": _HW_AVAILABLE,
        "error_log": _INIT_ERROR
    }

@app.get("/blink")
def blink_test():
    """Blink LEDs and beep to test hardware wiring."""
    hw.blink_test()
    return {"status": "triggered blink test"}

@app.get("/")
def read_root():
    # Redirect root to the Pi UI (React app served at /pi)
    return RedirectResponse(url="/pi")

# Serve the React build at /pi — matches Vite's base: '/pi' config
if os.path.exists("frontend_react/dist"):
    app.mount("/pi", StaticFiles(directory="frontend_react/dist", html=True), name="static")


