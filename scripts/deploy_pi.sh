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
                    libtiff6 libxcb1 libx11-6

# 2. Setup Python Virtual Environment
echo "Step 2: Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Install ARM-optimized Torch (Highly recommended for Pi)
echo "Step 3: Installing ARM-optimized Torch..."
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Install Project Requirements
echo "Step 4: Installing Project Requirements..."
pip install -r requirements.txt

# 5. Build React Frontend
echo "Step 5: Building React Frontend..."
cd frontend_react
npm install
npm run build
cd ..

# 6. Configure Systemd Service
echo "Step 6: Registering Systemd Service..."
# Note: This assumes the project is in /home/cyril/IntelShareAI
# If you are in a different directory, edit scripts/intelshare.service first.
sudo cp scripts/intelshare.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable intelshare.service
sudo systemctl restart intelshare.service

# 7. Final Touches
echo "Step 7: Finalizing Permissions..."
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
