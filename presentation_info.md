# IntelShareAI - Project Presentation Guide

This document contains all the necessary technical and architectural information about the **IntelShareAI** project to help you build a comprehensive PowerPoint presentation.

## 1. Project Overview
**IntelShareAI** is an advanced edge-AI system featuring seamless computer vision and offline voice interaction. It is designed around the principles of **Continuous Incremental Learning** (few-shot learning), allowing the system to learn new objects in real-time through user interactions. The system is heavily optimized for deployment on edge devices like the **Raspberry Pi** while maintaining cloud synchronization capabilities via **AWS S3**.

## 2. Core Modules & Architecture

### A. Perception & Vision Engine (`perception/`)
*   **Deep Learning Feature Extraction**: Utilizes **MobileNetV3-Small** (quantized) via **TensorFlow Lite** to extract high-dimensional semantic visual embeddings. 
*   **Edge Optimization**: specifically tailored for the Raspberry Pi environment using `tflite_runtime` for fast, lightweight inference.
*   **Robust Fallback**: If the Deep Learning model is unavailable, the system intelligently falls back to explainable computer vision features (Grayscale Histograms and Canny Edge detection via OpenCV).

### B. Voice Interaction (`interaction/`)
*   **Offline Voice Recognition**: Employs **Vosk** and **KaldiRecognizer** for completely offline, privacy-preserving speech-to-text.
*   **Audio Pipeline**: Uses `ffmpeg` for robust audio processing and conversion before feeding byte data into the inference pipeline.
*   **Intent Parsing & Feedback Loop**: Listens for user labels and confirmations to drive the real-time learning process.

### C. Continuous Incremental Learning Framework (`learning/`)
*   **Multi-Shot Learning Flow**: Captures multiple frames (e.g., $k=10$) of a new object with a slight delay, extracts embeddings, and saves them as distinct prototypes under a specific label.
*   **Prototype Management**: Manages a dynamically growing store of embeddings (prototypes) per label.
*   **Concept Drift & Pruning**: Periodically prunes weak or outdated prototypes to keep the model fast and prevent memory degradation.

### D. Inference & Decision Engine (`backend/`)
*   **Similarity Computation**: Calculates similarity between real-time camera embeddings and stored prototypes.
*   **Confidence Calibration**: Uses Temperature-scaled Softmax to calculate confidence probabilities.
*   **Advanced Decision Logic**:
    *   **Open-Set Rejection**: Rejects objects with similarity below a certain threshold (Unknown objects).
    *   **Low Confidence**: Prompts the user to teach it if confidence is too low.
    *   **Ambiguity Detection**: Computes the margin/gap between the top 2 predictions and prompts for user confirmation if the gap is too small.
*   **Throttling Mechanics**: Includes inference cooldowns (e.g., 500ms) to prevent CPU spam and thermal throttling on the Raspberry Pi.

### E. Storage & Cloud Integration (`backend/storage/`)
*   **Local Persistence**: Stores prototypes and actions locally for offline capability.
*   **AWS Cloud Sync**: Uses **Boto3** to synchronize learned prototypes and system state with an AWS S3 backend, ensuring memories are never lost and can be shared across devices.

## 3. Technology Stack SUMMARY
*   **Backend / API**: Python, FastAPI, Uvicorn, Pydantic
*   **Computer Vision**: OpenCV, MediaPipe
*   **Machine Learning / Edge AI**: TensorFlow Lite, MobileNetV3, Scikit-Learn, NumPy
*   **Speech / Audio**: Vosk (Offline NLP), Soundfile, FFmpeg
*   **Cloud Infrastructure**: AWS S3 (via Boto3)

## 4. Key Selling Points (For Presentation Slides)
1.  **True Edge AI**: Runs fully offline on a Raspberry Pi without requiring a constant internet connection for core inference.
2.  **Teach-on-the-Fly**: Users don't need to retrain a massive network; the system learns new objects instantly via few-shot prototype registration.
3.  **Privacy-First Voice**: Voice commands are processed locally, ensuring data privacy and reducing latency.
4.  **Resilient & Self-Calibrating**: Features open-set rejection (knows what it *doesn't* know) and automatically prunes old memories to prevent performance degradation.
5.  **Cloud-Backed**: Keeps the benefits of offline edge computing while safely backing up knowledge to AWS S3.
