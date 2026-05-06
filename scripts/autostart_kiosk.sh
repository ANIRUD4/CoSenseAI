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

echo "Backend is up! Launching kiosk UI..."

# Extra buffer for all routes and static files to be registered
sleep 2

# Launch Chromium in Kiosk mode pointing to the production UI served by FastAPI
# --kiosk            : True fullscreen (no title bar, no address bar)
# --noerrdialogs     : Suppress crash dialogs
# --disable-infobars : No "Chromium is not your default browser" bar
# --incognito        : No cached sessions / state from previous runs
# --app              : Minimal single-app mode (no tabs)
chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --app=http://localhost:8000/pi
