# IntelShareAI: Algorithm Flowchart

This document visualizes the "Thinking Eye" of the IntelShareAI system, mapping out how the AI perceives objects and learns from your feedback in real-time.

---

## 🔍 1. Real-Time Inference Loop
This flow happens continuously (multiple times per second) as the camera looks for objects.

```mermaid
graph TD
    A[Camera Feed] --> B[OpenCV Image Decode]
    B --> C[ROI Extraction<br/>Focus & Edge Density]
    C --> D[OpenCLIP Model<br/>Feature Embedding]
    
    D --> E{Memory Retrieval}
    E --> F[Load Prototypes & Means]
    
    F --> G{Scoring Tier}
    G -- "Samples < 3" --> H[Individual Prototype Similarity]
    G -- "Samples >= 3" --> I[Class Mean Similarity]
    
    H & I --> J[Apply Hard-Negative Penalties]
    J --> K[Softmax Confidence Calculation]
    
    K --> L{Adaptive Threshold}
    L -- "Score > Threshold" --> M[Success: Identify Object]
    L -- "Score < Threshold" --> N[Decision: Unknown / Low Conf]
    
    M & N --> O[Temporal Smoothing<br/>7-Frame EMA]
    O --> P[Final Frontend Display]
```

---

## 🛠️ 2. Learning & Feedback Loop
This flow is triggered when you interact with the AI (Confirm, Correct, or Teach).

```mermaid
graph LR
    subgraph "User Interaction"
    U[Confirm]
    C[Correct]
    L[Learn New]
    end

    U --> U1[Reinforce Best Prototype]
    U1 --> U2[Boost Weight + Update Mean]
    
    C --> C1[Add Hard Negative]
    C1 --> C2[Penalize Wrong Class]
    C2 --> C3[Add Prototype to Correct Class]
    
    L --> L1[Diversity Buffer Check]
    L1 --> L2[Create New Class Entry]
    
    U2 & C3 & L2 --> S[Save prototypes.json]
    S --> M[Update metrics.json]
```

---

## 💡 Key Design Principles
*   **Dual-Tier Memory**: Uses fast "Individual Match" for new items and robust "Mean Match" for experts.
*   **Hard-Negative Mining**: Remembers mistakes specifically to subtract points from similar confusing views.
*   **Temporal Stability**: Prevents flickering using Exponential Moving Averages (EMA).
*   **Class-Aware Thresholds**: Each object has its own pass-mark based on how well the AI knows it.
