import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Camera from '../components/Camera';
import { teachModel } from '../services/api';
import { Check, Loader2, Mic, MicOff, ArrowLeft, Type } from 'lucide-react';

const PiLearn = () => {
    const navigate = useNavigate();
    const [label, setLabel] = useState("");
    const [action, setAction] = useState("");
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [isListening, setIsListening] = useState(null); // 'label' or 'action' or null

    const cameraRef = useRef(null);

    const startListening = (field) => {
        setError(null);
        if (!('webkitSpeechRecognition' in window)) {
            setError("No Voice Support");
            return;
        }

        const recognition = new window.webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        setIsListening(field);

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (field === 'label') setLabel(transcript);
            if (field === 'action') setAction(transcript);
            setIsListening(null);
        };

        recognition.onerror = () => setIsListening(null);
        recognition.onend = () => setIsListening(null);
        recognition.start();
    };

    const handleCapture = async (frame, bbox) => {
        if (!label || !label.trim()) {
            setError("Enter Label!");
            const input = document.getElementById('pi-label-input');
            if (input) input.focus();
            return;
        }

        // Validate bbox to prevent 400 errors from NaN/invalid values
        const validBbox = bbox &&
            typeof bbox.x === 'number' && !isNaN(bbox.x) &&
            typeof bbox.y === 'number' && !isNaN(bbox.y) &&
            typeof bbox.w === 'number' && !isNaN(bbox.w) &&
            typeof bbox.h === 'number' && !isNaN(bbox.h)
            ? bbox : null;

        setLoading(true);
        setError(null);
        console.log("TEACH PAYLOAD:", {
            label,
            action,
            has_image: !!frame,
            bbox
        });
        try {
            const response = await teachModel({
                image_base64: frame,
                label: label.trim(),
                action: action.trim(),
                roi_bbox: validBbox
            });
            console.log("TEACH RESPONSE:", response.data);
            setSuccess(`Learned: ${label}`);
            setAction("");
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            console.error("TEACH ERROR:", err.response?.data || err.message);
            setError(err.response?.data?.detail || "Failed to Save");
        } finally {
            setLoading(false);
        }
    };

    const triggerCapture = () => {
        if (cameraRef.current) {
            cameraRef.current.capture();
        }
    };

    return (
        <div className="h-screen w-screen flex flex-row bg-slate-900 text-white overflow-hidden font-sans select-none">
            {/* Left Sidebar: Controls (approx 65% width) */}
            <div className="flex-1 flex flex-col p-2 space-y-2 relative border-r border-slate-800">
                {/* Header Row */}
                <div className="flex items-center gap-1 shrink-0 mb-1">
                    <button onClick={() => navigate('/pi')} className="p-1 active:bg-slate-700 rounded-full">
                        <ArrowLeft className="w-5 h-5 text-slate-400" />
                    </button>
                    <span className="text-xs font-black uppercase text-blue-400 tracking-tighter">Teaching Mode</span>
                </div>

                {/* Camera View Area - Limited height on large screens */}
                <div className="relative w-full overflow-hidden border border-slate-700 rounded-lg bg-black shrink-0"
                    style={{ aspectRatio: '16/9', maxHeight: '45vh' }}>
                    <Camera ref={cameraRef} onCapture={handleCapture} isActive={false} />

                    {loading && (
                        <div className="absolute inset-0 bg-black/70 flex items-center justify-center z-50">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                        </div>
                    )}

                    {/* Feedback Overlays */}
                    {success && (
                        <div className="absolute top-2 left-2 right-2 bg-green-600 p-2 rounded text-[10px] font-bold flex items-center gap-2 animate-fade-in z-[60]">
                            <Check className="w-3 h-3" /> {success}
                        </div>
                    )}
                    {error && (
                        <div className="absolute top-2 left-2 right-2 bg-red-600 p-2 rounded text-[10px] font-bold z-[60] flex items-center gap-1">
                            <span>⚠️</span> {error}
                        </div>
                    )}
                </div>

                {/* Inputs Area - Scrollable */}
                <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto p-1 bg-slate-800/20 rounded-lg">
                    {/* Label */}
                    <div className="flex flex-col gap-0.5">
                        <label className="text-[10px] text-slate-400 font-black uppercase ml-1">Object Name</label>
                        <div className="flex gap-2 h-10">
                            <input
                                id="pi-label-input"
                                type="text"
                                value={label}
                                onChange={(e) => setLabel(e.target.value)}
                                placeholder="Required..."
                                className="flex-1 px-3 bg-slate-800 border border-slate-600 rounded-lg text-sm outline-none focus:border-blue-500 text-white"
                            />
                            <button
                                onClick={() => startListening('label')}
                                className={`w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${isListening === 'label' ? 'bg-red-600 animate-pulse' : 'bg-slate-700 active:bg-slate-600'}`}
                            >
                                <Mic className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Action */}
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-slate-400 font-black uppercase ml-1">Action</label>
                        <div className="flex gap-2 h-10">
                            <input
                                type="text"
                                value={action}
                                onChange={(e) => setAction(e.target.value)}
                                placeholder="Optional..."
                                className="flex-1 px-3 bg-slate-800 border border-slate-600 rounded-lg text-sm outline-none focus:border-blue-500 text-white"
                            />
                            <button
                                onClick={() => startListening('action')}
                                className={`w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${isListening === 'action' ? 'bg-red-600 animate-pulse' : 'bg-slate-700 active:bg-slate-600'}`}
                            >
                                <Mic className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side: Shutter Column (approx 35% width) */}
            <div className="w-20 bg-slate-800 flex flex-col items-center justify-center shrink-0">
                <button
                    onClick={triggerCapture}
                    disabled={loading}
                    className="group relative flex items-center justify-center select-none"
                    style={{ WebkitTapHighlightColor: 'transparent' }}
                >
                    {/* Outer Ring */}
                    <div className="w-16 h-16 rounded-full border-4 border-slate-600 flex items-center justify-center">
                        {/* Shutter Button - White Circle */}
                        <div className={`w-12 h-12 rounded-full bg-white shadow-inner transition-transform active:scale-90 ${loading ? 'opacity-30' : 'opacity-100'}`}></div>
                    </div>

                    {/* Label */}
                    <div className="absolute -bottom-6 text-[10px] font-black text-slate-500 uppercase tracking-widest whitespace-nowrap">
                        {loading ? 'WAIT' : 'SNAP'}
                    </div>
                </button>
            </div>
        </div>
    );
};

export default PiLearn;
