#!/bin/bash
# scripts/autostart_kiosk.sh
# Demo-ready kiosk launcher for IntelShareAI on Raspberry Pi 5

# ── Log file (helpful for SSH debugging) ────────────────────────────────────
LOG_FILE="/tmp/intelshare_kiosk.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Kiosk autostart: $(date) ==="

# ── Disable screen blanking / power saving ───────────────────────────────────
xset s off
xset -dpms
xset s noblank

# ── Wait for the backend (FastAPI on port 8000) to become healthy ────────────
echo "Waiting for IntelShare backend to start..."
MAX_WAIT=90
WAITED=0
while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
  echo "  Still waiting... (${WAITED}s elapsed)"
  sleep 2
  WAITED=$((WAITED + 2))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "ERROR: Backend did not start within ${MAX_WAIT}s. Aborting."
    exit 1
  fi
done

echo "Backend is up after ${WAITED}s!"

# ── Verify GPIO/hardware status ──────────────────────────────────────────────
echo "Checking hardware (GPIO) status..."
HW_STATUS=$(curl -s http://localhost:8000/test_gpio 2>/dev/null)
echo "  Hardware status: $HW_STATUS"

# Extract hardware_available field
HW_AVAILABLE=$(echo "$HW_STATUS" | grep -o '"hardware_available": *[a-z]*' | grep -o '[a-z]*$')

if [ "$HW_AVAILABLE" = "true" ]; then
  echo "  ✓ GPIO hardware is ACTIVE — LEDs and buzzer should be firing."
else
  echo "  ✗ GPIO hardware is in MOCK mode — check service logs!"
  echo "    Run: sudo journalctl -u intelshare.service -n 50 --no-pager"
  echo "    Also check: groups \$(whoami) | grep gpio"
fi

# ── Kill any lingering camera/display processes ───────────────────────────────
# Linux only allows ONE app to use the webcam at a time.
pkill -f ffplay   || true
pkill -f libcamera || true
pkill -f chromium  || true

# ── Extra buffer for all routes and static files to be registered ─────────────
sleep 2

# ── Launch Chromium pointing to the production UI served by FastAPI ───────────
echo "Launching Chromium kiosk at http://127.0.0.1:8000/pi ..."
chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-gpu \
  --autoplay-policy=no-user-gesture-required \
  --use-fake-ui-for-media-stream \
  --allow-insecure-localhost \
  --unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:8000 \
  --disable-features=VideoCaptureUseGpuMemoryBuffer \
  --app=http://127.0.0.1:8000/pi
