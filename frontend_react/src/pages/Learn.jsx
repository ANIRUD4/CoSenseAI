import React, { useState, useRef } from 'react';
import Camera from '../components/Camera';
import { teachModel, transcribeSpeech } from '../services/api';
import { Check, Loader2, Mic, MicOff } from 'lucide-react';

const Learn = () => {
    const [label, setLabel] = useState("");
    const [action, setAction] = useState("");
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [listeningData, setListeningData] = useState(null); // 'label' or 'action' or null
    const mediaRecorderRef = useRef(null);

    const startListening = async (field) => {
        setError(null);
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            const audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                setListeningData(null);
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                try {
                    const response = await transcribeSpeech(audioBlob);
                    const transcript = response.data.text;
                    
                    if (transcript) {
                        if (field === 'label') setLabel(transcript);
                        if (field === 'action') setAction(transcript);
                    } else {
                        setError("Could not hear anything clearly. Please try again.");
                    }
                } catch (err) {
                    console.error("Transcription error:", err);
                    setError("Failed to transcribe audio. Is the backend running?");
                }
                
                // Stop all tracks to release microphone
                stream.getTracks().forEach(track => track.stop());
            };

            setListeningData(field);
            mediaRecorder.start();

            // Automatically stop recording after 4 seconds
            setTimeout(() => {
                if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                    mediaRecorderRef.current.stop();
                }
            }, 4000);

        } catch (err) {
            console.error("Mic access error:", err);
            setError("Microphone access denied or unavailable.");
            setListeningData(null);
        }
    };

    const handleCapture = async (frame, bbox) => {
        setError(null);
        if (!label) {
            setError("Please enter a label first!");
            return;
        }

        setLoading(true);
        setSuccess(null);

        try {
            await teachModel({
                image_base64: frame,
                label: label,
                action: action,
                roi_bbox: bbox // Pass the manual bounding box
            });

            setSuccess(`Learned: ${label}${bbox ? ' (Manual ROI)' : ''}`);
            // Don't clear label immediately so user can take multiple shots of same object
            // setLabel(""); 
            setAction("");
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            console.error(err);
            const detail = err.response?.data?.detail || "Unknown error";
            setError(`Failed to learn: ${detail}`);
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
