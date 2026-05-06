#!/bin/bash
# scripts/autostart_kiosk.sh
# Demo-ready kiosk launcher for IntelShareAI on Raspberry Pi 5

# Disable screen blanking / power saving
xset s off
xset -dpms
xset s noblank

# Wait for the backend (FastAPI on port 8000) to become healthy
echo "Waiting for IntelShare backend to start..."
MAX_WAIT=60
WAITED=0
while ! curl -s http://localhost:8000/health > /dev/null; do
  echo "  Still waiting... (${WAITED}s elapsed)"
  sleep 2
  WAITED=$((WAITED + 2))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "ERROR: Backend did not start within ${MAX_WAIT}s. Aborting."
    exit 1
  fi
done

echo "Backend is up! Preparing camera and launching kiosk..."

# WARNING: Linux only allows ONE app to use the webcam at a time.
# If ffplay or libcamera was run earlier and is still lingering in the background, 
# Chromium will silently fail to open the camera. We must kill them first.
pkill -f ffplay || true
pkill -f libcamera || true
pkill -f chromium || true

# Extra buffer for all routes and static files to be registered
sleep 2

# Launch Chromium pointing to the production UI served by FastAPI
chromium \
  --start-maximized \
  --noerrdialogs \
  --disable-infobars \
  --disable-gpu \
  --autoplay-policy=no-user-gesture-required \
  --allow-insecure-localhost \
  --unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:8000 \
  --disable-features=VideoCaptureUseGpuMemoryBuffer \
  --app=http://127.0.0.1:8000/pi
