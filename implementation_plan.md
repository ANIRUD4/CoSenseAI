# Raspberry Pi 5 Deployment Guide (Sparse Checkout Method)

This plan outlines the exact steps to transfer the necessary code to your Raspberry Pi 5 and verify that everything is working correctly.

## 1. Prerequisites
- **GitHub Repository**: Ensure your latest code is pushed to a remote repository.
- **Network**: Your Raspberry Pi 5 must have internet access.
- **Environment Variables**: You will need to manually create the `.env` file on the Pi after pulling the code.

## 2. Step-by-Step Guide

### Phase 1: Sparse Checkout (Code Transfer)
Instead of downloading the entire repository, we will only pull the folders required for the Pi's operation.

1.  **Login to your Raspberry Pi** (via SSH or directly).
2.  **Initialize the repository**:
    ```bash
    mkdir -p /home/pi/IntelShareAI
    cd /home/pi/IntelShareAI
    git init
    git remote add origin https://github.com/your-username/your-repo-name.git
    ```
3.  **Enable Sparse Checkout**:
    ```bash
    git config core.sparseCheckout true
    ```
4.  **Specify required directories**:
    Create the configuration file to tell Git which folders to download:
    ```bash
    echo "backend/" >> .git/info/sparse-checkout
    echo "frontend_react/" >> .git/info/sparse-checkout
    echo "interaction/" >> .git/info/sparse-checkout
    echo "learning/" >> .git/info/sparse-checkout
    echo "perception/" >> .git/info/sparse-checkout
    echo "scripts/" >> .git/info/sparse-checkout
    echo "data/" >> .git/info/sparse-checkout
    echo "requirements.txt" >> .git/info/sparse-checkout
    ```
5.  **Pull the code**:
    ```bash
    git pull origin main
    ```

### Phase 2: Setup and Deployment
Now that the code is on the Pi, we need to install dependencies and build the UI.

1.  **Run the automated deployment script**:
    ```bash
    bash scripts/deploy_pi.sh
    ```
    *This will install system packages, setup the Python venv, install requirements, build the React UI, and register the systemd service.*

2.  **Create the `.env` file**:
    Since `.env` is typically ignored by Git, you must create it manually on the Pi:
    ```bash
    nano .env
    ```
    Paste your environment variables (API keys, etc.) and save (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Phase 3: Testing the System
Verify each component of the Raspberry Pi 5 setup.

1.  **Verify Backend Health**:
    Check if the FastAPI server is running:
    ```bash
    curl http://localhost:8000/health
    ```
    *Expected output: `{"status": "IntelShare running"}`*

2.  **Test Hardware (GPIO)**:
    Run the GPIO test script to verify LEDs/Buttons:
    ```bash
    source venv/bin/activate
    python3 scripts/test_gpio.py
    ```

3.  **Launch the UI**:
    Start the kiosk browser manually to see if the UI loads:
    ```bash
    bash scripts/autostart_kiosk.sh
    ```

## 3. Final Configuration (Optional)
To make the UI launch automatically every time the Pi boots:
1.  Edit the Wayfire configuration:
    ```bash
    nano ~/.config/wayfire/wayfire.ini
    ```
2.  Add the following line under the `[autostart]` section:
    ```ini
    intelshare = /home/pi/IntelShareAI/scripts/autostart_kiosk.sh
    ```

## User Review Required
> [!IMPORTANT]
> Please confirm your **GitHub Repository URL** and the **Branch name** (e.g., `main` or `master`) before running the commands.

## Verification Plan
- **Git Check**: Verify only specified folders are present in `/home/pi/IntelShareAI`.
- **Build Check**: Ensure `frontend_react/dist` exists after the deployment script finishes.
- **Service Check**: Run `systemctl status intelshare.service` to ensure the backend is running as a background process.
- **UI Check**: Verify Chromium opens in full-screen on the 3.5-inch display.
