# IntelShareAI - Project Context for PO/PSO Mapping

This document provides a comprehensive technical overview of the "IntelShareAI" project. It is designed to be fed directly into an AI assistant (like ChatGPT, Gemini, or Claude) to automatically generate PO (Program Outcomes) and PSO (Program Specific Outcomes) mapping matrices and justifications for your academic report.

## 1. Project Title & Vision
**Title:** IntelShareAI: Edge-Optimized Continuous Incremental Learning System
**Objective:** To build a privacy-first, offline-capable edge AI system on a Raspberry Pi 4B that can dynamically learn to recognize new objects using multi-shot prototype registration and voice-driven interactions, without relying on continuous cloud connectivity or heavy model retraining.

## 2. Core Technical Architecture
The system consists of several sophisticated subsystems:
*   **Edge Vision Pipeline:** Utilizes a highly optimized, int8 quantized **MobileNetV3-Small** model via **TensorFlow Lite (TFLite)** to extract 576-dimensional feature vectors (embeddings) from live camera feeds (224x224 RGB). It also includes a robust **OpenCV fallback engine** (Grayscale, Canny edge, Histograms) in case the neural network fails.
*   **Offline Speech Recognition:** Uses the **Vosk STT** engine and KaldiRecognizer, combined with **FFmpeg** audio processing, to transcribe 16kHz microphone audio offline. It uses a bespoke **NLP Intent Parser** to trigger system actions (e.g., "learn this object").
*   **Continuous Incremental Learning Engine:** Employs few-shot metric learning using **Cosine Similarity** and **Temperature-scaled Softmax Calibration**. It registers new objects on the fly by saving the average prototype centroid ($C_k$) to a local JSON database without retraining weights. Rejects unknown objects using strict statistical thresholds.
*   **Hardware Abstraction Layer:** Interacts heavily with **Raspberry Pi GPIO**, managing strict power and thermal constraints while firing external **LEDs and buzzers** to provide the user with tactile/auditory feedback during operations.
*   **Cloud Orchestration:** A **FastAPI** backend supervisor manages asynchronous background tasks. It syncs the lightweight JSON prototype knowledge to an **AWS S3** bucket using **Boto3** and ETag deduplication hashes for low-bandwidth cloud backups.

## 3. Team Member Contributions
*   **Aman Mohammed:** Core Algorithm Developer. Handled the complex mathematics of continuous metric learning, prototype registration, concept drift detection, softmax calibration, and local JSON durability.
*   **Anirudh Anilkumar:** Edge Vision & Hardware Engineer. Handled TFLite quantization deployment, OpenCV fallback mechanisms, Raspberry Pi 4B thermal optimization, preprocessing frames, and strict GPIO hardware integrations (LEDS/Buzzer).
*   **Azim Palakkal:** Voice & NLP Engineer. Developed the offline Vosk STT module, concurrent audio multi-threading (to prevent inference stuttering), and rule-based NLP intent extraction. 
*   **Cyril Pius:** Cloud & Backend Architect. Handled FastAPI orchestration, asynchronous task pipelines, Boto3 AWS S3 synchronization with ETag deduplication, and secure RESTful monitoring endpoints.

## 4. Characteristics Relevant to Engineering POs
*   **PO1 (Engineering Knowledge):** Heavy use of mathematical concepts out of linear algebra (cosine similarity vectors), probability theory (temperature-scaled softmax calibration), and applied computer science algorithms.
*   **PO2 (Problem Analysis):** Addressed the specific problem of high latency, bandwidth reliance, and privacy loss in traditional cloud-based AI by designing a decentralized edge AI architecture. 
*   **PO3 (Design/Development of Solutions):** Designed custom fallback algorithms to ensure system resilience and managed strict performance/thermal constraints on IoT nodes.
*   **PO4 (Conduct Investigations of Complex Problems):** Evaluated performance metrics of float32 versus int8 models and optimized multi-threading locks in audio-visual parallel processing to prevent resource starvation.
*   **PO5 (Modern Tool Usage):** Extensively used Docker, TensorFlow Lite, FastAPI, Boto3, Vosk, LaTeX, AWS S3, and OpenCV.
*   **PO6 (The Engineer and Society):** Empowering decentralized automation and privacy-conscious smart vision solutions for general society applications.
*   **PO7 (Environment and Sustainability):** Utilizing low-power ARM architecture (Raspberry Pi) and int8 quantized minimal models severely reduces carbon footprints and energy consumption compared to heavily cooled server racks.
*   **PO8 (Ethics):** Offline processing ensures raw image and audio data NEVER leaves the device. Only mathematically irreversible, lightweight mathematical embeddings and JSON labels are backed up to the cloud. Total user privacy is guaranteed.
*   **PO9 (Individual and Team Work):** Segmented architecture (ML, Hardware, NLP, Cloud) allowed a 4-person team to work aggressively in parallel on microservices.
*   **PO10 (Communication):** System uses multi-modal communication (Voice STT, Visual Camera, LED/Buzzer hardware feedback).
*   **PO11 (Project Management):** Managed complex integration across multiple different programming paradigms (async cloud vs sync hardware strobe).
*   **PO12 (Life-long Learning):** The project intrinsically supports "Continuous Incremental Learning," modeling life-long learning paradigms by constantly updating its prototype database dynamically as new objects are introduced. 

---

## Instructions for your Teammate:
Copy this entire document and paste it into ChatGPT, Claude, or Gemini along with the following prompt:

> **"I am writing an engineering project report requiring PO (Program Outcomes) and PSO (Program Specific Outcomes) mapping. Based on the comprehensive project context provided above, please generate a formal PO and PSO mapping matrix (Scale 1 to 3, where 3 is high). Include a clear, 1-2 sentence justification explaining why each specific PO and PSO received that score based on the technical details provided."**
