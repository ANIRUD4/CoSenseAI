import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Camera from '../components/Camera';
import { inferFrame, correctPrediction } from '../services/api';
import { ArrowLeft, Loader2, ThumbsUp, ThumbsDown, HelpCircle, Search, Edit3, Check } from 'lucide-react';

const PiInfer = () => {
    const navigate = useNavigate();
    const [prediction, setPrediction] = useState(null);
    const [isInferring, setIsInferring] = useState(false);
    const [showCorrection, setShowCorrection] = useState(false);
    const [correctLabel, setCorrectLabel] = useState("");

    const cameraRef = useRef(null);

    const handleCapture = async (frame) => {
        setIsInferring(true);
        setPrediction(null);
        setShowCorrection(false);
        try {
            const res = await inferFrame({ image_base64: frame });
            setPrediction(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setIsInferring(false);
        }
    };

    const confirm = async () => {
        try {
            await correctPrediction({
                confirmed: true,
                predicted_label: prediction.candidates?.[0]?.label,
                embedding: prediction?.embedding,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setPrediction(null);
        } catch (e) {
            alert("Error");
        }
    }

    const submitCorrection = async () => {
        if (!correctLabel) return;
        try {
            await correctPrediction({
                confirmed: false,
                predicted_label: prediction.candidates?.[0]?.label,
                corrected_label: correctLabel,
                embedding: prediction?.embedding,
                confidence: prediction.candidates?.[0]?.confidence || 0.5
            });
            setShowCorrection(false);
            setCorrectLabel("");
            setPrediction(null);
        } catch (err) {
            alert("Failed");
        }
    };

    const triggerCapture = () => {
        if (cameraRef.current) {
            cameraRef.current.capture();
        }
    };

    return (
        <div className="h-screen w-screen flex flex-row bg-slate-900 text-white overflow-hidden font-sans select-none">
            {/* Left: Content Column */}
            <div className="flex-1 flex flex-col p-2 space-y-2 border-r border-slate-800 relative">
                {/* Header Row */}
                <div className="flex items-center gap-1 shrink-0 mb-1">
                    <button onClick={() => navigate('/pi')} className="p-1 active:bg-slate-700 rounded-full">
                        <ArrowLeft className="w-5 h-5 text-slate-400" />
                    </button>
                    <span className="text-xs font-black uppercase text-green-400 tracking-tighter">Recognition Mode</span>
                </div>

                {/* Camera View Area - Limited height on large screens */}
                <div className="relative w-full overflow-hidden border border-slate-700 rounded-lg bg-black shrink-0"
                    style={{ aspectRatio: '16/9', maxHeight: '45vh' }}>
                    <Camera ref={cameraRef} onCapture={handleCapture} isActive={false} />

                    {isInferring && (
                        <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center z-50">
                            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-2" />
                            <p className="font-black text-blue-400 animate-pulse tracking-widest text-[10px]">SCANNING...</p>
                        </div>
                    )}
                </div>

                {/* Results Area */}
                <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
                    {!prediction && !isInferring && (
                        <div className="flex-1 flex flex-col items-center justify-center text-slate-600 bg-slate-800/20 rounded-lg border-2 border-dashed border-slate-800">
                            <HelpCircle className="w-10 h-10 mb-2 opacity-10" />
                            <p className="text-[10px] uppercase font-bold tracking-widest">Aim & Snap</p>
                        </div>
                    )}

                    {prediction && !showCorrection && (
                        <div className="flex-1 bg-slate-800 p-2 rounded-lg border border-slate-700 animate-slide-up flex flex-col">
                            <div className="flex justify-between items-start mb-0.5">
                                <h3 className="text-xl font-black text-blue-400 leading-none truncate max-w-[70%]">
                                    {prediction.candidates?.[0]?.label || "???"}
                                </h3>
                                <div className="bg-blue-600 px-1.5 py-0.5 rounded font-black text-[9px]">
                                    {Math.round((prediction.candidates?.[0]?.confidence || 0) * 100)}%
                                </div>
                            </div>
                            <p className="text-[10px] text-slate-400 uppercase font-black truncate mb-2">
                                {prediction.candidates?.[0]?.action || "No Action"}
                            </p>

                            <div className="flex gap-1.5 mt-auto h-10">
                                <button onClick={confirm} className="flex-1 bg-green-600 active:bg-green-700 rounded-lg font-bold flex items-center justify-center gap-1 text-sm">
                                    <ThumbsUp className="w-4 h-4" /> YES
                                </button>
                                <button onClick={() => setShowCorrection(true)} className="flex-1 bg-red-600 active:bg-red-700 rounded-lg font-bold flex items-center justify-center gap-1 text-sm">
                                    <ThumbsDown className="w-4 h-4" /> NO
                                </button>
                            </div>
                        </div>
                    )}

                    {showCorrection && (
                        <div className="flex-1 bg-slate-800 p-2 rounded-lg border border-slate-700 animate-fade-in flex flex-col">
                            <label className="text-[8px] font-black text-slate-500 uppercase mb-1 ml-1">Correction:</label>
                            <input
                                type="text"
                                value={correctLabel}
                                onChange={(e) => setCorrectLabel(e.target.value)}
                                className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm outline-none focus:border-blue-500"
                                autoFocus
                            />
                            <div className="flex gap-1.5 mt-auto h-10">
                                <button onClick={submitCorrection} className="flex-1 bg-blue-600 rounded-lg font-black text-xs flex items-center justify-center gap-1">
                                    <Check className="w-3 h-3" /> SUBMIT
                                </button>
                                <button onClick={() => setShowCorrection(false)} className="px-3 bg-slate-700 rounded-lg font-bold">X</button>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Right: Shutter Column */}
            <div className="w-20 bg-slate-800 flex flex-col items-center justify-center shrink-0">
                <button
                    onClick={triggerCapture}
                    disabled={isInferring || showCorrection}
                    className="group relative flex items-center justify-center select-none"
                    style={{ WebkitTapHighlightColor: 'transparent' }}
                >
                    {/* Outer Ring */}
                    <div className="w-16 h-16 rounded-full border-4 border-slate-600 flex items-center justify-center">
                        {/* Shutter Button */}
                        <div className={`w-12 h-12 rounded-full bg-white shadow-inner transition-transform active:scale-90 ${isInferring || showCorrection ? 'opacity-30' : 'opacity-100'}`}></div>
                    </div>

                    {/* Label */}
                    <div className="absolute -bottom-6 text-[10px] font-black text-slate-500 uppercase tracking-widest whitespace-nowrap">
                        {isInferring ? 'WAIT' : 'SCAN'}
                    </div>
                </button>
            </div>
        </div>
    );
};

export default PiInfer;
