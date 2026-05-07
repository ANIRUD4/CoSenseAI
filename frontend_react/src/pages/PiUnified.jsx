import React, { useState, useRef, useCallback } from 'react';
import Camera from '../components/Camera';
import { teachModel, inferFrame, correctPrediction, executeAction } from '../services/api';
import {
    Check, Loader2, Mic, Brain, Search,
    ThumbsUp, ThumbsDown, X, Zap, Circle
} from 'lucide-react';

const RECOMMENDED_CAPTURES = 5;
const API_BASE = import.meta.env.VITE_API_URL || '';

const PiUnified = () => {
    // ── UI state ───────────────────────────────────────────────────────────────
    const [mode, setMode] = useState('infer');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [isListening, setIsListening] = useState(null);

    // ── Learn state ────────────────────────────────────────────────────────────
    const [label, setLabel] = useState('');
    const [action, setAction] = useState('');
    const [learnCount, setLearnCount] = useState(0);

    // ── Infer state ────────────────────────────────────────────────────────────
    const [pendingResult, setPendingResult] = useState(null);
    const [correctLabel, setCorrectLabel] = useState('');
    const [showCorrection, setShowCorrection] = useState(false);
    const [actionOutput, setActionOutput] = useState(null);

    const latestFrameRef = useRef(null);
    const latestBboxRef = useRef(null);
    const cameraRef = useRef(null);
    const [resetting, setResetting] = useState(false);

    // ─── Helpers ─────────────────────────────────────────────────────────────
    const showSuccess = (msg, ms = 2500) => {
        setSuccess(msg);
        setTimeout(() => setSuccess(null), ms);
    };

    const resetKnowledge = async () => {
        if (!window.confirm('Clear ALL learned objects? This cannot be undone.')) return;
        setResetting(true);
        try {
            const res = await fetch(`${API_BASE}/admin/clear`, { method: 'DELETE' });
            if (res.ok) {
                setLearnCount(0);
                setLabel('');
                setPendingResult(null);
                showSuccess('✓ Reset complete', 3000);
            } else {
                setError('Reset failed');
            }
        } catch (e) {
            setError('Reset failed');
        } finally {
            setResetting(false);
        }
    };

    const handleCameraCapture = useCallback(async (frame, bbox) => {
        latestFrameRef.current = frame;
        latestBboxRef.current = bbox;

        if (mode === 'learn') {
            await doLearn(frame, bbox);
        }
    }, [mode, label, action, learnCount]); // eslint-disable-line

    const startListening = (field) => {
        setError(null);
        if (!('webkitSpeechRecognition' in window)) {
            setError('Voice not supported');
            return;
        }
        const rec = new window.webkitSpeechRecognition();
        rec.continuous = false;
        rec.lang = 'en-US';
        setIsListening(field);
        rec.onresult = (e) => {
            const t = e.results[0][0].transcript;
            if (field === 'label') setLabel(t);
            if (field === 'action') setAction(t);
            if (field === 'correction') setCorrectLabel(t);
            setIsListening(null);
        };
        rec.onerror = () => setIsListening(null);
        rec.onend = () => setIsListening(null);
        rec.start();
    };

    const doLearn = async (frame, bbox) => {
        if (!label.trim()) {
            setError('Label required');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const validBbox = (bbox && typeof bbox.x === 'number') ? bbox : null;
            await teachModel({
                image_base64: frame,
                label: label.trim(),
                action: action.trim() || undefined,
                roi_bbox: validBbox,
            });
            const count = learnCount + 1;
            setLearnCount(count);
            setAction('');
            showSuccess(`Captured ${count} — "${label.trim()}"`);
        } catch (err) {
            setError(err.response?.data?.detail || 'Capture failed');
        } finally {
            setLoading(false);
        }
    };

    const triggerLearnCapture = () => {
        if (cameraRef.current) cameraRef.current.capture();
    };

    const triggerInferCapture = async () => {
        if (!cameraRef.current) return;
        setLoading(true);
        setError(null);

        cameraRef.current.capture();
        await new Promise(r => setTimeout(r, 80));

        const frame = latestFrameRef.current;
        if (!frame) {
            setLoading(false);
            return;
        }

        try {
            const res = await inferFrame({ image_base64: frame });
            setPendingResult(res.data);
        } catch (err) {
            setError(err?.response?.data?.detail || 'Inference failed');
        } finally {
            setLoading(false);
        }
    };

    const confirmResult = async () => {
        if (!pendingResult) return;
        const top = pendingResult.candidates?.[0];
        try {
            await correctPrediction({
                confirmed: true,
                predicted_label: top?.label,
                embedding: pendingResult.embedding,
                confidence: top?.confidence ?? 0.5,
            });
            if (top?.label) {
                const actRes = await executeAction({ label: top.label });
                setActionOutput(actRes.data.action);
            }
            showSuccess(`✓ Confirmed: ${top?.label}`, 3000);
        } catch (_) {
            setError('Confirm failed');
        } finally {
            setPendingResult(null);
            setShowCorrection(false);
            setCorrectLabel('');
        }
    };

    const submitCorrection = async () => {
        if (!correctLabel.trim() || !pendingResult) return;
        try {
            const top = pendingResult.candidates?.[0];
            await correctPrediction({
                confirmed: false,
                predicted_label: top?.label,
                corrected_label: correctLabel.trim(),
                embedding: pendingResult.embedding,
                confidence: top?.confidence ?? 0.5,
            });
            showSuccess(`✓ Corrected to: ${correctLabel.trim()}`, 3000);
        } catch (_) {
            setError('Correction failed');
        } finally {
            setPendingResult(null);
            setShowCorrection(false);
            setCorrectLabel('');
        }
    };

    const top = pendingResult?.candidates?.[0];
    const confPct = Math.round((top?.confidence ?? 0) * 100);

    return (
        <div className="relative h-screen w-screen bg-black text-white overflow-hidden font-sans select-none">
            
            {/* ── Background Full-Screen Camera ──────────────────────────── */}
            <div className="absolute inset-0 z-0">
                <Camera
                    ref={cameraRef}
                    onCapture={handleCameraCapture}
                    isActive={false} // hide default shutter
                />
            </div>

            {/* Loading Overlay */}
            {loading && (
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center z-50">
                    <Loader2 className="w-12 h-12 animate-spin text-blue-400 drop-shadow-lg" />
                    <p className="text-xs font-black uppercase tracking-widest text-blue-300 mt-3 animate-pulse drop-shadow-md">
                        {mode === 'learn' ? 'Teaching Model…' : 'Processing…'}
                    </p>
                </div>
            )}

            {/* Toasts */}
            <div className="absolute top-12 left-2 right-40 z-50 flex flex-col gap-2 pointer-events-none">
                {success && (
                    <div className="bg-emerald-500/90 backdrop-blur-md p-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-xl animate-slideDown">
                        <Check className="w-4 h-4" /> {success}
                    </div>
                )}
                {error && (
                    <div className="bg-red-500/90 backdrop-blur-md p-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-xl animate-slideDown pointer-events-auto">
                        ⚠ {error}
                        <button onClick={() => setError(null)} className="ml-auto p-1"><X className="w-3 h-3" /></button>
                    </div>
                )}
            </div>

            {/* Action Output Overlay */}
            {actionOutput && !pendingResult && (
                <div className="absolute bottom-4 left-4 right-44 bg-blue-600/90 backdrop-blur-md px-4 py-3 rounded-2xl flex items-center gap-3 z-30 shadow-2xl animate-slideDown">
                    <div className="p-2 bg-yellow-400 rounded-full">
                        <Zap className="w-5 h-5 text-blue-900 shrink-0" />
                    </div>
                    <p className="text-sm font-bold flex-1 truncate text-white">{actionOutput}</p>
                    <button onClick={() => setActionOutput(null)} className="p-2 bg-black/20 rounded-full"><X className="w-4 h-4 text-white" /></button>
                </div>
            )}

            {/* ── Floating Top Bar ──────────────────────────────────────── */}
            <header className="absolute top-0 left-0 right-0 h-10 px-3 bg-black/40 backdrop-blur-md border-b border-white/10 flex items-center justify-between z-20">
                <span className="text-xs font-black uppercase tracking-widest text-white/80 drop-shadow-md">
                    IntelShare
                </span>
                <div className="flex bg-black/40 rounded-lg p-0.5 gap-0.5 border border-white/10">
                    <button
                        onClick={() => { setMode('infer'); setPendingResult(null); }}
                        className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-black uppercase transition-all
                            ${mode === 'infer' ? 'bg-emerald-500 text-white shadow-md' : 'text-white/60'}`}
                    >
                        <Search className="w-3 h-3" /> INFER
                    </button>
                    <button
                        onClick={() => { setMode('learn'); setPendingResult(null); }}
                        className={`flex items-center gap-1 px-3 py-1 rounded-md text-[10px] font-black uppercase transition-all
                            ${mode === 'learn' ? 'bg-blue-500 text-white shadow-md' : 'text-white/60'}`}
                    >
                        <Brain className="w-3 h-3" /> LEARN
                    </button>
                </div>
                <button
                    onClick={resetKnowledge}
                    disabled={resetting}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/20 border border-red-500/30 text-red-300 text-[10px] font-black uppercase tracking-wider hover:bg-red-500/40 transition-all disabled:opacity-40"
                >
                    {resetting ? <Loader2 className="w-3 h-3 animate-spin" /> : <X className="w-3 h-3" />}
                    Reset
                </button>
            </header>

            {/* ── Floating Right Control Panel ──────────────────────────── */}
            <div className="absolute top-12 right-2 bottom-2 w-44 flex flex-col gap-2 z-20 pointer-events-none">
                
                {/* Mode-specific content */}
                {mode === 'learn' ? (
                    <>
                        <div className="bg-black/50 backdrop-blur-xl border border-white/10 rounded-2xl p-2 flex flex-col gap-2 pointer-events-auto shadow-2xl">
                            <div className="flex gap-1">
                                <input
                                    type="text" value={label}
                                    onChange={e => setLabel(e.target.value)}
                                    placeholder="Label (req)"
                                    className="flex-1 min-w-0 bg-white/10 border border-white/20 rounded-lg px-2 py-2 text-xs text-white placeholder-white/50 outline-none focus:border-blue-400 font-medium shadow-inner"
                                />
                                <button onClick={() => startListening('label')}
                                    className={`w-9 h-9 flex items-center justify-center rounded-lg shrink-0 transition-all ${isListening === 'label' ? 'bg-red-500 animate-pulse' : 'bg-white/10 hover:bg-white/20'}`}>
                                    <Mic className="w-4 h-4 text-white" />
                                </button>
                            </div>
                            <div className="flex gap-1">
                                <input
                                    type="text" value={action}
                                    onChange={e => setAction(e.target.value)}
                                    placeholder="Action (opt)"
                                    className="flex-1 min-w-0 bg-white/10 border border-white/20 rounded-lg px-2 py-2 text-xs text-white placeholder-white/50 outline-none focus:border-blue-400 font-medium shadow-inner"
                                />
                                <button onClick={() => startListening('action')}
                                    className={`w-9 h-9 flex items-center justify-center rounded-lg shrink-0 transition-all ${isListening === 'action' ? 'bg-red-500 animate-pulse' : 'bg-white/10 hover:bg-white/20'}`}>
                                    <Mic className="w-4 h-4 text-white" />
                                </button>
                            </div>
                            {learnCount > 0 && (
                                <div className="flex items-center gap-1.5 px-1 pb-1">
                                    <div className="flex-1 h-1.5 bg-black/50 rounded-full overflow-hidden shadow-inner">
                                        <div
                                            className={`h-full rounded-full transition-all duration-300 shadow-glow ${learnCount >= RECOMMENDED_CAPTURES ? 'bg-emerald-400' : 'bg-blue-400'}`}
                                            style={{ width: `${Math.min(100, (learnCount / RECOMMENDED_CAPTURES) * 100)}%` }}
                                        />
                                    </div>
                                    <span className={`text-[10px] font-black shrink-0 ${learnCount >= RECOMMENDED_CAPTURES ? 'text-emerald-300' : 'text-blue-200'}`}>
                                        {learnCount}/{RECOMMENDED_CAPTURES}
                                    </span>
                                </div>
                            )}
                        </div>
                        
                        {/* Shutter Button (Bottom Right) */}
                        <div className="mt-auto pointer-events-auto">
                            <button
                                onClick={triggerLearnCapture} disabled={loading}
                                className="w-full flex flex-col items-center justify-center py-5 rounded-2xl bg-white/20 backdrop-blur-xl border border-white/30 active:scale-95 transition-all disabled:opacity-40 shadow-[0_8px_32px_rgba(0,0,0,0.4)] hover:bg-white/30"
                            >
                                <div className="w-12 h-12 rounded-full border-4 border-white/50 flex items-center justify-center mb-1">
                                    <div className="w-8 h-8 rounded-full bg-white shadow-lg" />
                                </div>
                                <span className="text-white font-black text-[11px] uppercase tracking-widest drop-shadow-md">
                                    {loading ? 'Wait' : 'Snap'}
                                </span>
                            </button>
                        </div>
                    </>
                ) : (
                    <div className="mt-auto pointer-events-auto">
                        <button onClick={triggerInferCapture} disabled={loading}
                            className="w-full flex flex-col items-center justify-center py-6 rounded-2xl bg-emerald-500/80 backdrop-blur-xl border border-emerald-400/50 active:scale-95 transition-all disabled:opacity-40 shadow-[0_8px_32px_rgba(16,185,129,0.4)] hover:bg-emerald-500">
                            <div className="w-14 h-14 rounded-full border-4 border-white/50 flex items-center justify-center mb-2">
                                <Search className="w-6 h-6 text-white drop-shadow-md" />
                            </div>
                            <span className="text-white font-black text-[11px] uppercase tracking-widest text-center leading-tight drop-shadow-md">
                                {loading ? 'Scanning…' : 'Capture &\nIdentify'}
                            </span>
                        </button>
                    </div>
                )}
            </div>

            {/* ── Confirmation Modal ────────────────────────────────────── */}
            {pendingResult && (
                <div className="absolute inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
                    <div className="w-full max-w-sm bg-gray-900/90 border border-gray-700/50 rounded-3xl p-5 shadow-2xl backdrop-blur-xl animate-slideDown">
                        {!showCorrection ? (
                            <>
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-1">
                                    {pendingResult.decision === 'confident' ? 'Recognised' : 'Status'}
                                </p>
                                {pendingResult.decision !== 'confident' && pendingResult.message && (
                                    <h3 className="text-sm font-bold text-yellow-400 mb-1">{pendingResult.message}</h3>
                                )}
                                <h2 className={`text-3xl font-black truncate drop-shadow-md ${pendingResult.decision === 'confident' ? 'text-emerald-400' : 'text-gray-100'}`}>
                                    {top?.label ?? 'Unknown'}
                                </h2>
                                {top && (
                                    <div className="mt-2 mb-4 flex items-center gap-3">
                                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden shadow-inner border border-gray-700">
                                            <div className="h-full bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.8)]" style={{ width: `${confPct}%` }} />
                                        </div>
                                        <span className="text-xs font-black text-emerald-400">{confPct}%</span>
                                    </div>
                                )}
                                {top?.action && (
                                    <div className="bg-blue-900/40 border border-blue-500/30 px-3 py-2 rounded-xl mb-4 flex items-center gap-2">
                                        <Zap className="w-4 h-4 text-blue-400" />
                                        <span className="text-sm text-blue-100 font-medium">{top.action}</span>
                                    </div>
                                )}
                                <div className="flex gap-2 mt-4">
                                    {top && (
                                        <button onClick={confirmResult}
                                            className="flex-1 bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition-all rounded-xl py-3 font-black flex items-center justify-center gap-2 text-sm shadow-lg border border-emerald-400/30">
                                            <ThumbsUp className="w-4 h-4" /> Yes
                                        </button>
                                    )}
                                    <button onClick={() => setShowCorrection(true)}
                                        className="flex-1 bg-gray-800 hover:bg-gray-700 active:scale-95 transition-all rounded-xl py-3 font-black flex items-center justify-center gap-2 text-sm text-white shadow-lg border border-gray-600/50">
                                        {top ? <><ThumbsDown className="w-4 h-4 text-red-400" /> Wrong</> : <><Search className="w-4 h-4 text-blue-400" /> Label</>}
                                    </button>
                                </div>
                                <button onClick={() => setPendingResult(null)} className="w-full mt-3 py-2 text-[10px] text-gray-500 hover:text-gray-300 font-bold uppercase transition-colors">
                                    Dismiss
                                </button>
                            </>
                        ) : (
                            <>
                                <p className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2">Provide correct label</p>
                                <div className="flex gap-2 mb-4">
                                    <input
                                        type="text" value={correctLabel} onChange={e => setCorrectLabel(e.target.value)}
                                        placeholder="Label..."
                                        className="flex-1 min-w-0 bg-black/50 border border-gray-600 rounded-xl px-3 py-3 text-sm text-white outline-none focus:border-blue-500 shadow-inner"
                                        autoFocus
                                    />
                                    <button onClick={() => startListening('correction')}
                                        className={`w-12 h-12 flex items-center justify-center rounded-xl shrink-0 transition-all ${isListening === 'correction' ? 'bg-red-500 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]' : 'bg-gray-800 hover:bg-gray-700'}`}>
                                        <Mic className="w-5 h-5 text-white" />
                                    </button>
                                </div>
                                <div className="flex gap-2">
                                    <button onClick={submitCorrection}
                                        className="flex-1 bg-blue-600 hover:bg-blue-500 active:scale-95 transition-all rounded-xl py-3 font-black text-sm text-white shadow-lg border border-blue-400/30">
                                        Update Model
                                    </button>
                                    <button onClick={() => setShowCorrection(false)}
                                        className="w-12 bg-gray-800 hover:bg-gray-700 active:scale-95 transition-all rounded-xl flex items-center justify-center shrink-0 border border-gray-600/50">
                                        <X className="w-5 h-5 text-gray-300" />
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes slideDown { from { transform: translateY(-10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                .animate-slideDown { animation: slideDown 0.2s cubic-bezier(0.16, 1, 0.3, 1); }
            `}} />
        </div>
    );
};

export default PiUnified;

