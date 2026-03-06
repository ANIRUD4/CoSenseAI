import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Camera from '../components/Camera';
import { teachModel, inferFrame, correctPrediction } from '../services/api';
import {
    Check,
    Loader2,
    Mic,
    ArrowLeft,
    Brain,
    Search,
    ThumbsUp,
    ThumbsDown,
    HelpCircle,
    X
} from 'lucide-react';

const PiUnified = () => {
    const navigate = useNavigate();

    // --- UI State ---
    const [mode, setMode] = useState('infer'); // 'learn' or 'infer'
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [isListening, setIsListening] = useState(null);

    // --- Learn Mode State ---
    const [label, setLabel] = useState("");
    const [action, setAction] = useState("");

    // --- Infer Mode State ---
    const [prediction, setPrediction] = useState(null);
    const [showCorrection, setShowCorrection] = useState(false);
    const [correctLabel, setCorrectLabel] = useState("");

    const cameraRef = useRef(null);

    // --- Voice Implementation ---
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
            if (field === 'correction') setCorrectLabel(transcript);
            setIsListening(null);
        };

        recognition.onerror = () => setIsListening(null);
        recognition.onend = () => setIsListening(null);
        recognition.start();
    };

    // --- Core Actions ---
    const handleCapture = async (frame, bbox) => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        if (mode === 'learn') {
            await handleLearn(frame, bbox);
        } else {
            await handleInfer(frame);
        }
        setLoading(false);
    };

    const handleLearn = async (frame, bbox) => {
        if (!label || !label.trim()) {
            setError("Enter Label!");
            const input = document.getElementById('pi-label-input');
            if (input) input.focus();
            return;
        }

        const validBbox = bbox &&
            typeof bbox.x === 'number' && !isNaN(bbox.x) &&
            typeof bbox.y === 'number' && !isNaN(bbox.y) &&
            typeof bbox.w === 'number' && !isNaN(bbox.w) &&
            typeof bbox.h === 'number' && !isNaN(bbox.h)
            ? bbox : null;

        try {
            await teachModel({
                image_base64: frame,
                label: label.trim(),
                action: action.trim(),
                roi_bbox: validBbox
            });
            setSuccess(`Learned: ${label}`);
            setAction("");
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            setError(err.response?.data?.detail || "Save Failed");
        }
    };

    const handleInfer = async (frame) => {
        setPrediction(null);
        setShowCorrection(false);
        try {
            const res = await inferFrame({ image_base64: frame });
            setPrediction(res.data);
        } catch (err) {
            setError("Scan Failed");
        }
    };

    const confirmResult = async () => {
        if (!prediction) return;
        try {
            await correctPrediction({
                confirmed: true,
                predicted_label: prediction.candidates?.[0]?.label,
                embedding: prediction?.embedding,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setSuccess("Confirmed!");
            setTimeout(() => {
                setSuccess(null);
                setPrediction(null);
            }, 1500);
        } catch (e) {
            setError("Update Failed");
        }
    };

    const submitCorrection = async () => {
        if (!correctLabel || !prediction) return;
        try {
            await correctPrediction({
                confirmed: false,
                predicted_label: prediction.candidates?.[0]?.label,
                corrected_label: correctLabel.trim(),
                embedding: prediction?.embedding,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setShowCorrection(false);
            setCorrectLabel("");
            setSuccess("Corrected!");
            setTimeout(() => {
                setSuccess(null);
                setPrediction(null);
            }, 1500);
        } catch (err) {
            setError("Correction Failed");
        }
    };

    const triggerCapture = () => {
        if (cameraRef.current) {
            cameraRef.current.capture();
        }
    };

    return (
        <div className="h-screen w-screen flex flex-row bg-slate-900 text-white overflow-hidden font-sans select-none">
            {/* Left Column: UI Controls */}
            <div className="flex-1 flex flex-col p-2 space-y-2 relative border-r border-slate-800 border-dashed min-w-0">

                {/* Header & Mode Switch */}
                <div className="flex items-center gap-2 shrink-0 h-10">
                    <button
                        onClick={() => navigate('/')}
                        className="p-1.5 active:bg-slate-700 rounded-full text-slate-400"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>

                    <div className="flex flex-1 bg-slate-800 rounded-lg p-1">
                        <button
                            onClick={() => { setMode('infer'); setPrediction(null); }}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[10px] font-black uppercase transition-all ${mode === 'infer' ? 'bg-green-600 text-white shadow-lg' : 'text-slate-500'}`}
                        >
                            <Search className="w-3.5 h-3.5" /> INFER
                        </button>
                        <button
                            onClick={() => { setMode('learn'); setPrediction(null); }}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[10px] font-black uppercase transition-all ${mode === 'learn' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-500'}`}
                        >
                            <Brain className="w-3.5 h-3.5" /> LEARN
                        </button>
                    </div>
                </div>

                {/* Camera Feed */}
                <div className="relative w-full overflow-hidden border border-slate-700 rounded-xl bg-black shrink-0"
                    style={{ aspectRatio: '16/9', maxHeight: '42vh' }}>
                    <Camera ref={cameraRef} onCapture={handleCapture} isActive={false} />

                    {loading && (
                        <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center z-50">
                            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-2" />
                            <p className="text-[10px] font-black uppercase tracking-widest text-blue-400 animate-pulse">
                                {mode === 'learn' ? 'TEACHING...' : 'SCANNING...'}
                            </p>
                        </div>
                    )}

                    {/* Notification Overlays */}
                    {success && (
                        <div className="absolute top-2 left-2 right-2 bg-green-600 p-2 rounded-lg text-[10px] font-bold flex items-center gap-2 animate-slide-down z-[60] shadow-xl">
                            <Check className="w-4 h-4" /> {success}
                        </div>
                    )}
                    {error && (
                        <div className="absolute top-2 left-2 right-2 bg-red-600 p-2 rounded-lg text-[10px] font-bold z-[60] flex items-center gap-2 animate-shake shadow-xl">
                            <span className="text-sm">⚠️</span> {error}
                            <button onClick={() => setError(null)} className="ml-auto"><X className="w-3 h-3" /></button>
                        </div>
                    )}
                </div>

                {/* Dynamic Bottom Area */}
                <div className="flex-1 min-h-0 flex flex-col bg-slate-800/20 rounded-xl overflow-hidden">
                    {mode === 'learn' ? (
                        /* LEARN INPUTS */
                        <div className="p-2 space-y-3 overflow-y-auto">
                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-slate-500 font-black uppercase ml-1 tracking-wider">Object Label</label>
                                <div className="flex gap-2 h-11">
                                    <input
                                        id="pi-label-input"
                                        type="text"
                                        value={label}
                                        onChange={(e) => setLabel(e.target.value)}
                                        placeholder="Required..."
                                        className="flex-1 px-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-blue-500 text-white font-medium"
                                    />
                                    <button
                                        onClick={() => startListening('label')}
                                        className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all shadow-md active:scale-90 ${isListening === 'label' ? 'bg-red-600 animate-pulse' : 'bg-slate-700 active:bg-slate-600'}`}
                                    >
                                        <Mic className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-slate-500 font-black uppercase ml-1 tracking-wider">Default Action</label>
                                <div className="flex gap-2 h-11">
                                    <input
                                        type="text"
                                        value={action}
                                        onChange={(e) => setAction(e.target.value)}
                                        placeholder="Optional callback..."
                                        className="flex-1 px-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-blue-500 text-white font-medium"
                                    />
                                    <button
                                        onClick={() => startListening('action')}
                                        className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all shadow-md active:scale-90 ${isListening === 'action' ? 'bg-red-600 animate-pulse' : 'bg-slate-700 active:bg-slate-600'}`}
                                    >
                                        <Mic className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* INFER RESULTS */
                        <div className="flex-1 p-2 flex flex-col min-h-0">
                            {!prediction ? (
                                <div className="flex-1 flex flex-col items-center justify-center text-slate-700 border-2 border-dashed border-slate-800 rounded-lg">
                                    <HelpCircle className="w-10 h-10 mb-2 opacity-10" />
                                    <p className="text-[10px] uppercase font-black tracking-[0.2em] opacity-30">Snap to scan</p>
                                </div>
                            ) : (
                                <div className="flex-1 flex flex-col animate-slide-up">
                                    {!showCorrection ? (
                                        <div className="flex-1 flex flex-col">
                                            <div className="flex justify-between items-start mb-1">
                                                <h3 className="text-2xl font-black text-green-400 truncate tracking-tight">
                                                    {prediction.candidates?.[0]?.label || "???"}
                                                </h3>
                                                <div className="bg-green-600/20 text-green-400 px-2 py-0.5 rounded-full font-black text-[10px] border border-green-600/30">
                                                    {Math.round((prediction.candidates?.[0]?.confidence || 0) * 100)}%
                                                </div>
                                            </div>
                                            <p className="text-xs text-slate-400 font-bold uppercase tracking-wide mb-3">
                                                {prediction.candidates?.[0]?.action || "No action set"}
                                            </p>

                                            <div className="flex gap-2 mt-auto h-12">
                                                <button onClick={confirmResult} className="flex-1 bg-green-600 active:bg-green-700 rounded-xl font-black flex items-center justify-center gap-2 text-sm shadow-lg shadow-green-900/20 active:scale-95 transition-transform">
                                                    <ThumbsUp className="w-5 h-5" /> CORRECT
                                                </button>
                                                <button onClick={() => setShowCorrection(true)} className="flex-1 bg-red-600/20 border border-red-600/30 active:bg-red-600 group rounded-xl font-black flex items-center justify-center gap-2 text-sm active:scale-95 transition-transform">
                                                    <ThumbsDown className="w-5 h-5 text-red-500 group-active:text-white" /> WRONG
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="flex-1 flex flex-col">
                                            <div className="flex justify-between items-center mb-1 px-1">
                                                <label className="text-[10px] font-black text-slate-500 uppercase">Correct Label:</label>
                                                <button onClick={() => setShowCorrection(false)} className="text-slate-400"><X className="w-4 h-4" /></button>
                                            </div>
                                            <div className="flex gap-2 h-11 mb-2">
                                                <input
                                                    type="text"
                                                    value={correctLabel}
                                                    onChange={(e) => setCorrectLabel(e.target.value)}
                                                    className="flex-1 px-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-blue-500 font-bold"
                                                    autoFocus
                                                />
                                                <button
                                                    onClick={() => startListening('correction')}
                                                    className={`w-11 h-11 flex items-center justify-center rounded-xl bg-slate-700 ${isListening === 'correction' ? 'bg-red-600 animate-pulse' : ''}`}
                                                >
                                                    <Mic className="w-5 h-5" />
                                                </button>
                                            </div>
                                            <button
                                                onClick={submitCorrection}
                                                className="w-full h-12 bg-blue-600 rounded-xl font-black text-sm shadow-lg shadow-blue-900/20 active:scale-95 transition-transform"
                                            >
                                                UPDATE MODEL
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Right Column: Shutter Area */}
            <div className="w-24 bg-slate-800 flex flex-col items-center justify-center shrink-0 shadow-[inset_4px_0_10px_rgba(0,0,0,0.3)]">
                <button
                    onClick={triggerCapture}
                    disabled={loading || isListening}
                    className="group flex flex-col items-center cursor-pointer"
                    style={{ WebkitTapHighlightColor: 'transparent' }}
                >
                    <div className={`p-1 rounded-full border-4 ${mode === 'learn' ? 'border-blue-500/30' : 'border-green-500/30'} transition-colors mb-2`}>
                        <div className="w-16 h-16 rounded-full bg-white shadow-inner flex items-center justify-center group-active:scale-90 transition-transform">
                            <div className={`w-14 h-14 rounded-full border-2 border-slate-200 ${loading ? 'opacity-20' : 'opacity-100'}`}></div>
                        </div>
                    </div>
                    <span className={`text-[11px] font-black uppercase tracking-[0.2em] ${loading ? 'text-slate-600 animate-pulse' : mode === 'learn' ? 'text-blue-400' : 'text-green-400'}`}>
                        {loading ? 'WAIT' : 'SNAP'}
                    </span>
                </button>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes slide-up {
                    from { transform: translateY(10px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes slide-down {
                    from { transform: translateY(-10px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-4px); }
                    75% { transform: translateX(4px); }
                }
                .animate-slide-up { animation: slide-up 0.3s ease-out; }
                .animate-slide-down { animation: slide-down 0.3s ease-out; }
                .animate-shake { animation: shake 0.2s ease-in-out infinite; }
            `}} />
        </div>
    );
};

export default PiUnified;
