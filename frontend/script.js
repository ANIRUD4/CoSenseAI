// =============================
// IntelShare Frontend Script
// Clean version (single camera pipeline)
// =============================

// --- DOM elements ---
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const statusText = document.getElementById("status");
const output = document.getElementById("output");

// optional containers
const candidatesDiv = document.getElementById("candidates");
const actionsDiv = document.getElementById("actions");
const teachHintDiv = document.getElementById("teachHint");

// --- Global state ---
let lastEmbedding = null;
let lastInference = null;
let waitingForDecision = false;

// =============================
// 1) Start Camera
// =============================
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    // Wait until video has dimensions
    await new Promise((resolve) => {
      video.onloadedmetadata = () => resolve();
    });

    console.log("✅ Camera started");
  } catch (err) {
    console.error("Camera error:", err);
    alert("Camera access denied or unavailable.");
  }
}
startCamera();

// =============================
// 2) Capture Frame (from <video>)
// =============================
function captureFrame() {
  if (!video) throw new Error("Video element not found (id='video')");
  if (!canvas) throw new Error("Canvas element not found (id='canvas')");

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas context not available");

  // fallback sizes
  const w = video.videoWidth || 640;
  const h = video.videoHeight || 480;

  canvas.width = w;
  canvas.height = h;

  ctx.drawImage(video, 0, 0, w, h);

  return canvas.toDataURL("image/jpeg");
}

// =============================
// 3) Get Real Embedding (perceive API)
// =============================
async function getRealEmbedding() {
  // capture image
  const dataUrl = captureFrame();
  const blob = await fetch(dataUrl).then((r) => r.blob());

  // prepare multipart form
  const formData = new FormData();
  formData.append("file", blob, "frame.jpg");

  // NOTE: check Swagger for trailing slash
  const res = await fetch("http://127.0.0.1:8000/perceive/embedding", {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Perceive failed (${res.status}): ${errText}`);
  }

  const data = await res.json();

  if (!data.embedding || !Array.isArray(data.embedding)) {
    throw new Error("Invalid /perceive response: missing embedding");
  }

  return data.embedding;
}

// =============================
// 4) Multi-shot embeddings for prototype learning
// =============================
async function getMultiEmbeddings(k = 10, delayMs = 120) {
  const list = [];

  for (let i = 0; i < k; i++) {
    try {
      const emb = await getRealEmbedding();

      if (Array.isArray(emb) && emb.length > 0) {
        list.push(emb);
      } else {
        console.warn("Skipping bad embedding:", emb);
      }

    } catch (e) {
      console.error("Perceive failed:", e);
    }

    await new Promise((r) => setTimeout(r, delayMs));
  }

  return list;
}


async function recordAudio(duration = 3000) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  const chunks = [];

  mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
  mediaRecorder.start();

  await new Promise((resolve) => setTimeout(resolve, duration));

  mediaRecorder.stop();

  await new Promise((resolve) => {
    mediaRecorder.onstop = resolve;
  });

  stream.getTracks().forEach((track) => track.stop());

  return new Blob(chunks, { type: "audio/webm" });
}

async function getLabelFromVosk() {
  statusText.innerText = "Status: Listening for label (voice)...";

  const audioBlob = await recordAudio(3000);
  const formData = new FormData();
  formData.append("file", audioBlob, "speech.webm");

  const res = await fetch("http://127.0.0.1:8000/speech/transcribe", {
    method: "POST",
    body: formData
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Speech API failed");
  }

  // Expect: { text: "apple" }
  const text = (data.text || "").trim().toLowerCase();

  if (!text) {
    throw new Error("No voice detected. Try again.");
  }

  return text;
}

// =============================
// 5) Learn (prototype learning)
// =============================
async function learn() {
  try {
    statusText.innerText = "Status: Capturing multi-shot embeddings...";
    output.innerText = "";

    const embeddings = await getMultiEmbeddings(10);

    console.log("DEBUG embeddings:", embeddings);
    console.log("DEBUG count:", embeddings.length);
    console.log("DEBUG first:", embeddings[0]);


    // ✅ Voice label from Vosk
    let label;
    try {
      label = await getLabelFromVosk();
      console.log("VOICE LABEL:", label);
    } catch (e) {
      console.warn("Voice failed, fallback to prompt:", e);
      label = prompt("Voice failed. Enter label manually:", "apple");
    }

    if (!label || label.trim() === "") {
      statusText.innerText = "Status: Learn cancelled";
      return;
    }

    statusText.innerText = "Status: Saving prototype...";

    if (!embeddings || embeddings.length < 2) {
      alert("Failed to capture embeddings. Try again.");
      console.error("Invalid embeddings:", embeddings);
      return;
    }

    for (let e of embeddings) {
      if (!Array.isArray(e) || e.length === 0) {
        alert("Bad embedding detected. Retake.");
        console.error("Bad embedding:", e);
        return;
      }
    }


    const res = await fetch("http://127.0.0.1:8000/learn/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label, embeddings })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    output.innerText = JSON.stringify(data, null, 2);
    statusText.innerText = `Status: Learned "${label}" ✅`;

  } catch (err) {
    console.error("Learn error:", err);
    statusText.innerText = "Status: Learn failed. Check console.";
  }
}


// =============================
// 6) Infer
// =============================
async function infer() {
  try {
    statusText.innerText = "Status: Inferring...";
    output.innerText = "";
    if (waitingForDecision) {
      alert("Please confirm/correct first.");
      return;
    }
    // Real embedding
    const embedding = await getRealEmbedding();
    lastEmbedding = embedding;

    const res = await fetch("http://127.0.0.1:8000/infer/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ embedding })
    });

    const data = await res.json();
    lastInference = data;

    if (!res.ok) {
      throw new Error(JSON.stringify(data));
    }

    statusText.innerText = "Status: Inference Done ✅";
    output.innerText = JSON.stringify(data, null, 2);

    // candidates
    showCandidates(data.candidates || []);
    waitingForDecision = true;
    statusText.innerText = "Status: Waiting for confirmation...";

    // show unknown hint
    if (teachHintDiv) {
      if (data.decision && String(data.decision).startsWith("unknown")) {
        teachHintDiv.innerText =
          `Not confident: top1=${data.top1} gap=${data.gap}. Please teach this object.`;
      } else {
        teachHintDiv.innerText = "";
      }
    }

    // show actions only when confident
    if (data.candidates && data.candidates.length > 0 && data.decision === "confident") {
      showActions(data.candidates[0].label);
    } else {
      if (actionsDiv) actionsDiv.innerHTML = "";
    }

  } catch (err) {
    console.error("Infer error:", err);
    statusText.innerText = "Status: Infer failed. Check console.";
  }
}

// =============================
// 7) Show Candidates
// =============================
function showCandidates(candidates) {
  if (!candidatesDiv) return;

  candidatesDiv.innerHTML = "";

  if (!candidates || candidates.length === 0) {
    candidatesDiv.innerHTML = "<p>No candidates</p>";
    return;
  }

  candidates.forEach((c) => {
    const div = document.createElement("div");
    div.style.marginBottom = "8px";

    const conf = (typeof c.confidence === "number")
      ? c.confidence.toFixed(3)
      : c.confidence;

    div.innerHTML = `
      <b>${c.label}</b> (conf: ${conf})
      <button onclick="confirmYes('${c.label}')">Confirm</button>
      <button onclick="confirmNo('${c.label}')">Correct</button>
    `;

    candidatesDiv.appendChild(div);
  });
}

// =============================
// 8) Confirm / Correct (prototype update)
// =============================
async function confirmYes(predictedLabel) {
  try {
    if (!lastEmbedding) {
      alert("Infer first (no embedding available).");
      return;
    }

    statusText.innerText = `Status: Confirming (${predictedLabel})...`;

    const res = await fetch("http://127.0.0.1:8000/confirm/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        predicted_label: predictedLabel,
        confirmed: true,
        corrected_label: null,
        embedding: lastEmbedding
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    alert(`Confirmed: ${predictedLabel} ✅`);
    statusText.innerText = "Status: Confirmed ✅ Prototype reinforced";

    // refresh inference to show confidence improvement
    // await infer();

  } catch (err) {
    console.error("ConfirmYes error:", err);
    statusText.innerText = "Status: Confirm failed. Check console.";
  }
  waitingForDecision = false;
}

async function confirmNo(predictedLabel) {
  try {
    if (!lastEmbedding) {
      alert("Infer first (no embedding available).");
      return;
    }

    const corrected = prompt(`Prediction was "${predictedLabel}". Correct label?`);
    if (!corrected || corrected.trim() === "") return;

    statusText.innerText = `Status: Correcting → ${corrected}...`;

    const res = await fetch("http://127.0.0.1:8000/confirm/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        predicted_label: predictedLabel,
        confirmed: false,
        corrected_label: corrected,
        embedding: lastEmbedding
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    alert(`Corrected: ${corrected} ✅`);
    statusText.innerText = `Status: Corrected ✅ (${corrected})`;

    // refresh inference to show improvement
    // await infer();

  } catch (err) {
    console.error("ConfirmNo error:", err);
    statusText.innerText = "Status: Correction failed. Check console.";
  }
  waitingForDecision = false;
}

// =============================
// 9) Actions
// =============================
function showActions(topLabel) {
  if (!actionsDiv) return;

  actionsDiv.innerHTML = `
    <h3>Actions for ${topLabel}</h3>
    <button onclick="sendAction('${topLabel}', 'highlight')">Highlight</button>
    <button onclick="sendAction('${topLabel}', 'alert')">Alert</button>
    <button onclick="sendAction('${topLabel}', 'stop')">Stop</button>
  `;
}

async function sendAction(label, intent) {
  try {
    const res = await fetch("http://127.0.0.1:8000/act/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label, intent })
    });

    const data = await res.json();

    if (!res.ok) {
      alert(`No action mapped for "${label}" + "${intent}"`);
      console.warn("Action error:", data);
      return;
    }

    console.log("ACTION RESPONSE:", data);
    alert(`Action executed: ${intent} ✅`);

  } catch (err) {
    console.error("Action error:", err);
    alert("Action failed. Check console.");
  }
}
