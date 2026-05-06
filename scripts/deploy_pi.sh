#!/bin/bash
# scripts/deploy_pi.sh

# Exit on any error
set -e

echo "===================================================="
echo "   IntelShareAI Deployment Script (Raspberry Pi 5)  "
echo "===================================================="

# 1. System Dependencies
echo "Step 1: Installing System Dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg libopenblas-dev \
                    chromium curl nodejs npm git libopenjp2-7 \
                    libtiff6 libxcb1 libx11-6 swig build-essential \
                    python3-dev liblgpio-dev

# 1.5 Increase Swap Space (Fixes build bus errors)
echo "Step 1.5: Optimizing System Memory (Swap)..."
if [ -f /etc/dphys-swapfile ]; then
    CURRENT_SWAP=$(free -m | grep Swap | awk '{print $2}')
    if [ "$CURRENT_SWAP" -lt 2000 ]; then
        echo "Increasing swap size to 2GB..."
        sudo dphys-swapfile swapoff
        sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
        sudo dphys-swapfile setup
        sudo dphys-swapfile swapon
    fi
else
    echo "WARNING: /etc/dphys-swapfile not found. Skipping swap optimization."
fi

# 2. Setup Python Virtual Environment
echo "Step 2: Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Install Torch (ARM64 optimized)
echo "Step 3: Installing Torch..."
source venv/bin/activate
pip install --upgrade pip

# Check for 64-bit
ARCH=$(getconf LONG_BIT)
if [ "$ARCH" != "64" ]; then
    echo "ERROR: You are running a $ARCH-bit OS. PyTorch requires 64-bit Raspberry Pi OS."
    exit 1
fi

# Try standard PyPI first (official aarch64 wheels are now common)
# If that fails, fall back to the specialized CPU index
pip install torch torchvision || \
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Install TFLite Runtime (Special handling for ARM64)
echo "Step 4: Installing TFLite Runtime..."
source venv/bin/activate
# Try standard PyPI, then Google's repo, then the new package name
pip install tflite-runtime || \
pip install --extra-index-url https://google-coral.github.io/py-repo/ tflite-runtime || \
pip install ai-edge-litert || \
echo "WARNING: Could not install tflite-runtime. System will fall back to Simple CV mode for some tasks."

# 5. Install Project Requirements
echo "Step 5: Installing Project Requirements..."
pip install -r requirements.txt

# 6. Build React Frontend
echo "Step 6: Building React Frontend..."
cd frontend_react
npm install --fetch-retry-maxtimeout=600000 --fetch-retries=5 --no-audit --no-fund || \
npm install --registry=https://registry.npmjs.org/ --fetch-retry-maxtimeout=600000 --no-audit --no-fund
export NODE_OPTIONS="--max-old-space-size=2048"
npm run build
cd ..

# 7. Configure Systemd Service
echo "Step 7: Registering Systemd Service..."
# Note: This assumes the project is in /home/cyril/IntelShareAI
# If you are in a different directory, edit scripts/intelshare.service first.
sudo cp scripts/intelshare.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable intelshare.service
sudo systemctl restart intelshare.service

# 8. Final Touches
echo "Step 8: Finalizing Permissions..."
chmod +x scripts/autostart_kiosk.sh

echo ""
echo "===================================================="
echo "DEPLOYMENT SUCCESSFUL!"
echo "----------------------------------------------------"
echo "To finish the setup, add the following line to your "
echo "~/.config/wayfire/wayfire.ini file under [autostart]:"
echo ""
echo "intelshare = /home/cyril/IntelShareAI/scripts/autostart_kiosk.sh"
echo "===================================================="
