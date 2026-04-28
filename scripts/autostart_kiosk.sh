#!/bin/bash
# scripts/autostart_kiosk.sh

# Wait for backend to be healthy
while ! curl -s http://localhost:8000/health > /dev/null; do
  echo "Waiting for IntelShare backend..."
  sleep 2
done

# Optional: Wait a bit more for the browser to render properly
sleep 2

# Launch Chromium in Kiosk mode
# --kiosk: Full screen
# --noerrdialogs: Hides error dialogs
# --disable-infobars: Hides the "Chromium is not your default browser" bar
# --app: Minimal UI
chromium --kiosk --noerrdialogs --disable-infobars --app=http://localhost:8000
