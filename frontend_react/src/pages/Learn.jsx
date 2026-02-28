import React, { useState } from 'react';
import Camera from '../components/Camera';
import { teachModel } from '../services/api';
import { Check, Loader2, Mic, MicOff } from 'lucide-react';

const Learn = () => {
    const [label, setLabel] = useState("");
    const [action, setAction] = useState("");
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [listeningData, setListeningData] = useState(null); // 'label' or 'action' or null

    const startListening = (field) => {
        setError(null);
        if (!('webkitSpeechRecognition' in window)) {
            setError("Voice input not supported in this browser. Please use Chrome.");
            return;
        }

        const recognition = new window.webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        setListeningData(field);

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (field === 'label') setLabel(transcript);
            if (field === 'action') setAction(transcript);
            setListeningData(null);
        };

        recognition.onerror = (event) => {
            setListeningData(null);
            console.error("DEBUG SPEECH ERROR:", event); // Log FULL event for debugging
            console.error("Error code:", event.error);
            console.error("Message:", event.message);

            // Handle specific errors gracefully without spamming console
            if (event.error === 'network') {
                setError("Voice unavailable (Network/Firewall blocked). Please type.");
            } else if (event.error === 'not-allowed') {
                setError("Microphone blocked. Check permissions.");
            } else if (event.error === 'no-speech') {
                // Ignore no-speech, just stop listening
                return;
            } else {
                console.warn("Voice input error:", event.error);
                setError(`Voice failed: ${event.error}. Please type.`);
            }
        };

        recognition.onend = () => {
            setListeningData(null);
        };

        recognition.start();
    };

    const handleCapture = async (frame) => {
        setError(null);
        if (!label) {
            setError("Please enter a label first!");
            return;
        }

        setLoading(true);
        setSuccess(null);

        // Prepare data directly for backend/routes/learn.py -> @router.post("/")
        // It expects LearnRequest(label: str, image: str, action: str)
        // We might need to check the pydantic model in backend/schemas/learn_schema.py or similar to be sure.
        // Based on orchestrator.py learning_flow, it takes image_frame.
        // Let's assume the API wrapper handles it or we send as JSON.

        try {
            // The backend likely expects a JSON with image as base64 and label.
            await teachModel({
                image_base64: frame, // Base64 string
                label: label,
                action: action // Added action mapping
            });

            setSuccess(`Learned: ${label}`);
            setLabel("");
            setAction("");
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            console.error(err);
            setError("Failed to learn object. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-3xl font-bold text-primary mb-8">Teach New Objects</h2>

            {error && (
                <div className="mb-6 bg-red-50 text-red-600 px-4 py-3 rounded-xl flex items-center gap-2 animate-fade-in border border-red-100">
                    <span className="font-bold">Error:</span> {error}
                </div>
            )}

            <div className="grid lg:grid-cols-2 gap-12 items-start">
                {/* Left: Controls */}
                <div className="space-y-6">
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                        <label className="block text-sm font-medium text-secondary mb-2">Object Name</label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={label}
                                onChange={(e) => setLabel(e.target.value)}
                                placeholder="e.g. Red Cup"
                                className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all font-medium"
                            />
                            <button
                                onClick={() => startListening('label')}
                                className={`p-3 rounded-lg border transition-colors ${listeningData === 'label' ? 'bg-red-50 border-red-200 text-red-500 animate-pulse' : 'border-slate-200 text-slate-400 hover:text-accent hover:border-accent'}`}
                            >
                                {listeningData === 'label' ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                        <label className="block text-sm font-medium text-secondary mb-2">Associated Action (Optional)</label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={action}
                                onChange={(e) => setAction(e.target.value)}
                                placeholder="e.g. Pick it up"
                                className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all font-medium"
                            />
                            <button
                                onClick={() => startListening('action')}
                                className={`p-3 rounded-lg border transition-colors ${listeningData === 'action' ? 'bg-red-50 border-red-200 text-red-500 animate-pulse' : 'border-slate-200 text-slate-400 hover:text-accent hover:border-accent'}`}
                            >
                                {listeningData === 'action' ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                            </button>
                        </div>
                        <p className="text-xs text-slate-400 mt-2">
                            The system will suggest this action when it recognizes the object.
                        </p>
                    </div>

                    {success && (
                        <div className="bg-green-50 text-green-700 px-4 py-3 rounded-xl flex items-center gap-2 animate-fade-in">
                            <Check className="w-5 h-5" />
                            <span className="font-medium">{success}</span>
                        </div>
                    )}

                    <div className="bg-blue-50 text-blue-700 px-4 py-4 rounded-xl text-sm">
                        <p><strong>Instructions:</strong></p>
                        <ul className="list-disc ml-5 mt-1 space-y-1">
                            <li>Enter the name of the object.</li>
                            <li>Position the object in the camera frame.</li>
                            <li>Click the Camera icon on the video feed to capture and teach.</li>
                        </ul>
                    </div>
                </div>

                {/* Right: Camera */}
                <div>
                    {loading ? (
                        <div className="aspect-video bg-slate-900 rounded-xl flex flex-col items-center justify-center text-white">
                            <Loader2 className="w-10 h-10 animate-spin mb-4" />
                            <p>Processing...</p>
                        </div>
                    ) : (
                        <Camera onCapture={handleCapture} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default Learn;
