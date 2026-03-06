import React, { useState, useEffect, useRef } from 'react';
import Camera from '../components/Camera';
import { inferFrame, correctPrediction } from '../services/api';
import { AlertCircle, CheckCircle, HelpCircle, ThumbsUp, ThumbsDown, Edit2 } from 'lucide-react';

const Infer = () => {
    const [prediction, setPrediction] = useState(null);
    const [isInferring, setIsInferring] = useState(false);
    const [showCorrection, setShowCorrection] = useState(false);
    const [correctLabel, setCorrectLabel] = useState("");

    // Ref to control the loop
    const intervalRef = useRef(null);
    // Ref to hold the latest frame capture function from Camera if needed, 
    // but Camera component abstracts it. Ideally Camera should expose a "getFrame" method or auto-push.
    // My Camera component only pushes on click.
    // I need to update Camera or use a trick.
    // TRICK: I will modify Camera to accept a `triggerCapture` prop or ref.
    // But for now, let's keep it simple: "Click to Recognize" or "Auto Mode".
    // The user requirement says "system must be able to recognise the object...".
    // Let's implement an "Auto Mode" toggle that simulates clicking capture every 2 seconds.

    // Since Camera component doesn't expose capture method easily without forwardRef, 
    // I'll update Camera component to allow external trigger if I can, OR just use a button for MVP "Recognize" and "Auto Recognize".

    // Actually, I can pass a `ref` to Camera and use `useImperativeHandle` inside Camera, or just standard ref to the button and click it programmatically? No, that's hacky.
    // I will update Camera component to be more flexible in the next step if needed, 
    // but for now let's implement Infer with a "Scan Object" button and "Auto Scan" switch.

    // WAIT: I can just put the capture logic IN the parent if I lift the video ref, 
    // OR I can use a simpler pattern: The Camera component is for "User Intent" capture.
    // For interaction, we want the system to "see".
    // Let's modify Camera to accept an `autoCaptureInterval` prop?
    // Or just stick to "Click to Identify" for the first iteration to ensure reliability.
    // User said "interactive with human... mention the action mapped".

    // Let's do "Click to Identify" (Manual) + "Continuous Mode" (Auto)
    // I will wrap Camera with a hidden specific implementation for Infer if needed, or just let Camera component handle it.
    // Better: I will use a simple "Scan" button for now to avoid ref complexity in this turn.

    const handleCapture = async (frame) => {
        setIsInferring(true);
        try {
            const res = await inferFrame({ image_base64: frame });
            // Backend should return { prediction: "Label", confidence: 0.9, action: "Action" }
            // If backend returns simple string, handle it.
            // Based on orchestrator `inference_flow`, it returns { embedding, prediction }.
            // `prediction` probably contains label/action.

            setPrediction(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setIsInferring(false);
        }
    };

    const handleCorrection = async () => {
        if (!correctLabel) return;
        try {
            // Backend `feedback_flow` or `confirm` 
            await correctPrediction({
                confirmed: false,
                predicted_label: prediction.candidates?.[0]?.label,
                corrected_label: correctLabel,
                embedding: prediction?.embedding,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setShowCorrection(false);
            setCorrectLabel("");
            setPrediction(null); // Clear after correction
            alert("Thanks for the correction! I've updated my learning.");
        } catch (err) {
            console.error(err);
            const detail = err.response?.data?.detail || "Connection failure or unknown error";
            alert(`Failed to update: ${detail}`);
        }
    };

    const confirmPrediction = async () => {
        try {
            await correctPrediction({
                confirmed: true,
                predicted_label: prediction.candidates?.[0]?.label,
                embedding: prediction?.embedding,
                corrected_label: null,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setPrediction(null);
        } catch (e) {
            console.error(e);
            const detail = e.response?.data?.detail || "Connection failure or unknown error";
            alert(`Error: ${detail}`);
        }
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-8">
                <h2 className="text-3xl font-bold text-primary">Inference Mode</h2>
            </div>

            <div className="grid lg:grid-cols-2 gap-12">
                {/* Camera Feed */}
                <div>
                    <div className="relative">
                        <Camera onCapture={handleCapture} />
                        <div className="absolute top-4 right-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
                            {isInferring ? "Analyzing..." : "Ready to Scan"}
                        </div>
                    </div>
                    <p className="text-center text-slate-500 mt-4">
                        Click the camera icon to identify the object.
                    </p>
                </div>

                {/* Results & Interaction */}
                <div className="space-y-6">
                    {!prediction && (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-2xl p-12">
                            <HelpCircle className="w-16 h-16 mb-4 opacity-20" />
                            <p className="text-lg">Scan an object to see results</p>
                        </div>
                    )}

                    {prediction && (
                        <div className="bg-white p-8 rounded-2xl shadow-xl border border-slate-100 animate-slide-up">
                            <div className="flex items-start justify-between mb-6">
                                <div>
                                    <p className="text-sm text-slate-500 uppercase tracking-widest font-semibold mb-1">Detected Object</p>
                                    <h3 className="text-4xl font-extrabold text-primary">{prediction.candidates?.[0]?.label || "Unknown"}</h3>
                                </div>
                                <div className={`px-4 py-2 rounded-lg font-bold ${prediction.candidates?.[0]?.confidence > 0.8 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                    {Math.round((prediction.candidates?.[0]?.confidence || 0) * 100)}%
                                </div>
                            </div>

                            <div className="bg-slate-50 p-6 rounded-xl mb-8 border border-slate-100">
                                <p className="text-sm text-slate-500 uppercase tracking-widest font-semibold mb-2">Suggested Action</p>
                                <p className="text-2xl font-medium text-accent">
                                    {prediction.candidates?.[0]?.action || "No action mapped"}
                                </p>
                            </div>

                            {!showCorrection ? (
                                <div>
                                    <p className="text-sm text-center text-secondary mb-4">Is this correct?</p>
                                    <div className="flex gap-4">
                                        <button onClick={confirmPrediction} className="flex-1 bg-green-500 hover:bg-green-600 text-white py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all">
                                            <ThumbsUp className="w-5 h-5" /> Yes
                                        </button>
                                        <button onClick={() => setShowCorrection(true)} className="flex-1 bg-red-500 hover:bg-red-600 text-white py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all">
                                            <ThumbsDown className="w-5 h-5" /> No
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-slate-50 p-6 rounded-xl animate-fade-in">
                                    <h4 className="font-bold text-primary mb-4 flex items-center gap-2">
                                        <Edit2 className="w-4 h-4" /> Correct the AI
                                    </h4>
                                    <input
                                        type="text"
                                        value={correctLabel}
                                        onChange={(e) => setCorrectLabel(e.target.value)}
                                        placeholder="What is this object?"
                                        className="w-full px-4 py-3 rounded-lg border border-slate-200 mb-4 focus:outline-none focus:ring-2 focus:ring-accent"
                                    />
                                    <div className="flex gap-2">
                                        <button onClick={handleCorrection} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium shadow-md transition-colors">
                                            Submit Correction
                                        </button>
                                        <button onClick={() => setShowCorrection(false)} className="px-4 py-2 text-slate-500 hover:bg-slate-200 rounded-lg">
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Infer;
