import React, { useState, useRef, useEffect, useCallback } from 'react';
import Camera from '../components/Camera';
import { teachModel, inferFrame, correctPrediction, executeAction } from '../services/api';
import {
    Check, Loader2, Mic, Brain, Search,
    ThumbsUp, ThumbsDown, X, Zap, Circle
} from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────
const INFER_INTERVAL_MS = 1800;
const CONFIDENCE_THRESHOLD = 0.65;

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
    const [isInferring, setIsInferring] = useState(false);
    const [pendingResult, setPendingResult] = useState(null);
    const [correctLabel, setCorrectLabel] = useState('');
    const [showCorrection, setShowCorrection] = useState(false);
    const [actionOutput, setActionOutput] = useState(null);

    // Stored latest frame from camera callback
    const latestFrameRef = useRef(null);
    const latestBboxRef = useRef(null);
    const cameraRef = useRef(null);
    const inferTimer = useRef(null);

    // ─── Helpers ─────────────────────────────────────────────────────────────
    const showSuccess = (msg, ms = 2500) => {
        setSuccess(msg);
        setTimeout(() => setSuccess(null), ms);
    };

    // ─── Camera callback — called by Camera component on every capture ────────
    // In learn mode: fires when user clicks the white circle button (via isActive)
    // In infer mode: we trigger capture() on a timer and read from latestFrameRef
    const handleCameraCapture = useCallback(async (frame, bbox) => {
        latestFrameRef.current = frame;
        latestBboxRef.current = bbox;

        if (mode === 'learn') {
            await doLearn(frame, bbox);
        }
        // Infer mode reads latestFrameRef in the timer loop
    }, [mode, label, action, learnCount]); // eslint-disable-line

    // ─── Voice input ──────────────────────────────────────────────────────────
    const startListening = (field) => {
        setError(null);
        if (!('webkitSpeechRecognition' in window)) {
            setError('Voice not supported in this browser');
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

    // ─── Learn Mode ──────────────────────────────────────────────────────────
    const doLearn = async (frame, bbox) => {
        if (!label.trim()) {
            setError('Label is required');
            document.getElementById('pi-label')?.focus();
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const validBbox = (bbox &&
                typeof bbox.x === 'number' && !isNaN(bbox.x) &&
                typeof bbox.y === 'number' && !isNaN(bbox.y)
            ) ? bbox : null;

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

    // Manual learn trigger: tell Camera to capture (fires handleCameraCapture)
    const triggerLearnCapture = () => {
        if (cameraRef.current) cameraRef.current.capture();
    };

    // ─── Infer Mode – real-time loop ─────────────────────────────────────────
    const runOneInfer = useCallback(async () => {
        if (pendingResult) return; // paused while modal is open
        if (!cameraRef.current) return;

        // Trigger a camera capture to update latestFrameRef
        cameraRef.current.capture();
        // Wait a tick for the capture callback to populate latestFrameRef
        await new Promise(r => setTimeout(r, 80));

        const frame = latestFrameRef.current;
        if (!frame) return;

        try {
            const res = await inferFrame({ image_base64: frame });
            const data = res.data;
            const top = data.candidates?.[0];

            if (
                data.decision === 'confident' &&
                top &&
                (top.confidence ?? 0) >= CONFIDENCE_THRESHOLD
            ) {
                setPendingResult(data);
            }
        } catch (_) { /* silent */ }
    }, [pendingResult]);

    useEffect(() => {
        if (mode !== 'infer' || !isInferring || pendingResult) return;
        inferTimer.current = setInterval(runOneInfer, INFER_INTERVAL_MS);
        return () => clearInterval(inferTimer.current);
    }, [mode, isInferring, pendingResult, runOneInfer]);

    const startRealtime = () => { setError(null); setIsInferring(true); };
    const stopRealtime = () => { setIsInferring(false); clearInterval(inferTimer.current); };

    // ─── Confirmation flow ────────────────────────────────────────────────────
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

    const dismissModal = () => {
        setPendingResult(null);
        setShowCorrection(false);
        setCorrectLabel('');
    };

    // ─── Mode switch ──────────────────────────────────────────────────────────
    const switchMode = (next) => {
        stopRealtime();
        setPendingResult(null);
        setActionOutput(null);
        setMode(next);
    };

    // ─── Render ───────────────────────────────────────────────────────────────
    const top = pendingResult?.candidates?.[0];
    const confPct = Math.round((top?.confidence ?? 0) * 100);

    return (
        <div className="h-screen w-screen flex flex-col bg-gray-950 text-white overflow-hidden font-sans select-none">

            {/* ── Top bar ─────────────────────────────────────────────── */}
            <header className="flex items-center px-3 py-2 bg-gray-900 border-b border-gray-800 shrink-0">
                <span className="text-sm font-black uppercase tracking-widest text-gray-400 mr-auto">
                    IntelShare
                </span>
                <div className="flex bg-gray-800 rounded-lg p-0.5 gap-0.5">
                    <button
                        onClick={() => switchMode('infer')}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[10px] font-black uppercase transition-all
                            ${mode === 'infer' ? 'bg-emerald-600 text-white shadow' : 'text-gray-500'}`}
                    >
                        <Search className="w-3 h-3" /> INFER
                    </button>
                    <button
                        onClick={() => switchMode('learn')}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[10px] font-black uppercase transition-all
                            ${mode === 'learn' ? 'bg-blue-600 text-white shadow' : 'text-gray-500'}`}
                    >
                        <Brain className="w-3 h-3" /> LEARN
                    </button>
                </div>
            </header>

            {/* ── Camera ──────────────────────────────────────────────── */}
            <div className="relative flex-1 bg-black overflow-hidden">
                {/* Camera always active so it streams; we drive capture() manually */}
                <Camera
                    ref={cameraRef}
                    onCapture={handleCameraCapture}
                    isActive={false}  // hide Camera's own shutter button; we have our own
                />

                {/* Realtime indicator */}
                {mode === 'infer' && isInferring && !pendingResult && (
                    <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/60 px-2 py-1 rounded-full pointer-events-none">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Live</span>
                    </div>
                )}

                {/* Loading spinner */}
                {loading && (
                    <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center z-20">
                        <Loader2 className="w-10 h-10 animate-spin text-blue-400" />
                        <p className="text-[10px] font-black uppercase tracking-widest text-blue-300 mt-2 animate-pulse">
                            Teaching…
                        </p>
                    </div>
                )}

                {/* Toast overlays */}
                {success && (
                    <div className="absolute top-2 left-2 right-2 bg-emerald-700/90 backdrop-blur p-2 rounded-xl
                                    text-xs font-bold flex items-center gap-2 z-30 shadow-xl animate-slideDown">
                        <Check className="w-4 h-4" /> {success}
                    </div>
                )}
                {error && (
                    <div className="absolute top-2 left-2 right-2 bg-red-700/90 backdrop-blur p-2 rounded-xl
                                    text-xs font-bold flex items-center gap-2 z-30 shadow-xl">
                        ⚠ {error}
                        <button onClick={() => setError(null)} className="ml-auto"><X className="w-3 h-3" /></button>
                    </div>
                )}

                {/* ── Confirmation modal ────────────────────────────── */}
                {pendingResult && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center z-40 px-4">
                        <div className="w-full max-w-xs bg-gray-900 rounded-2xl p-4 shadow-2xl border border-gray-700">
                            {!showCorrection ? (
                                <>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">Recognised</p>
                                    <h2 className="text-3xl font-black text-emerald-400 truncate">{top?.label ?? '?'}</h2>
                                    <div className="mt-1 mb-3 flex items-center gap-2">
                                        <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${confPct}%` }} />
                                        </div>
                                        <span className="text-[10px] font-black text-emerald-400">{confPct}%</span>
                                    </div>
                                    {top?.action && (
                                        <p className="text-xs text-blue-300 bg-blue-900/30 px-2 py-1 rounded-lg mb-3 font-medium">
                                            ⚡ {top.action}
                                        </p>
                                    )}
                                    <div className="flex gap-2">
                                        <button onClick={confirmResult}
                                            className="flex-1 bg-emerald-600 active:scale-95 transition-transform rounded-xl py-3 font-black flex items-center justify-center gap-2 text-sm">
                                            <ThumbsUp className="w-4 h-4" /> Yes
                                        </button>
                                        <button onClick={() => setShowCorrection(true)}
                                            className="flex-1 bg-red-600/20 border border-red-600/30 active:scale-95 transition-transform rounded-xl py-3 font-black flex items-center justify-center gap-2 text-sm text-red-400">
                                            <ThumbsDown className="w-4 h-4" /> Wrong
                                        </button>
                                    </div>
                                    <button onClick={dismissModal} className="w-full mt-2 py-2 text-[10px] text-gray-600 font-bold uppercase">
                                        Dismiss
                                    </button>
                                </>
                            ) : (
                                <>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Correct label</p>
                                    <div className="flex gap-2 mb-3">
                                        <input
                                            type="text"
                                            value={correctLabel}
                                            onChange={e => setCorrectLabel(e.target.value)}
                                            onKeyDown={e => e.key === 'Enter' && submitCorrection()}
                                            placeholder="Enter correct label…"
                                            className="flex-1 bg-gray-800 border border-gray-600 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500"
                                            autoFocus
                                        />
                                        <button onClick={() => startListening('correction')}
                                            className={`w-11 h-11 flex items-center justify-center rounded-xl ${isListening === 'correction' ? 'bg-red-600 animate-pulse' : 'bg-gray-700'}`}>
                                            <Mic className="w-5 h-5" />
                                        </button>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={submitCorrection}
                                            className="flex-1 bg-blue-600 active:scale-95 transition-transform rounded-xl py-3 font-black text-sm">
                                            Update Model
                                        </button>
                                        <button onClick={() => setShowCorrection(false)}
                                            className="w-11 bg-gray-700 rounded-xl flex items-center justify-center">
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}

                {/* ── Action output banner ─────────────────────────── */}
                {actionOutput && !pendingResult && (
                    <div className="absolute bottom-2 left-2 right-2 bg-blue-800/90 backdrop-blur px-3 py-2 rounded-xl
                                    flex items-center gap-2 z-30 shadow-xl">
                        <Zap className="w-4 h-4 text-yellow-300 shrink-0" />
                        <p className="text-sm font-bold flex-1">{actionOutput}</p>
                        <button onClick={() => setActionOutput(null)}><X className="w-3 h-3 text-gray-400" /></button>
                    </div>
                )}
            </div>

            {/* ── Bottom control strip ─────────────────────────────── */}
            <div className="bg-gray-900 border-t border-gray-800 px-3 pt-3 pb-4 shrink-0">
                {mode === 'learn' ? (
                    <div className="space-y-2">
                        <div className="flex gap-2">
                            <input id="pi-label" type="text" value={label} onChange={e => setLabel(e.target.value)}
                                placeholder="Object label (required)…"
                                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue-500 font-medium" />
                            <button onClick={() => startListening('label')}
                                className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all shrink-0 ${isListening === 'label' ? 'bg-red-600 animate-pulse' : 'bg-gray-700'}`}>
                                <Mic className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="flex gap-2">
                            <input type="text" value={action} onChange={e => setAction(e.target.value)}
                                placeholder="Action (e.g. Refill the bottle)…"
                                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue-500 font-medium" />
                            <button onClick={() => startListening('action')}
                                className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all shrink-0 ${isListening === 'action' ? 'bg-red-600 animate-pulse' : 'bg-gray-700'}`}>
                                <Mic className="w-5 h-5" />
                            </button>
                        </div>
                        {/* White circle capture button */}
                        <button onClick={triggerLearnCapture} disabled={loading}
                            className="w-full flex items-center justify-center gap-2 py-3 rounded-full bg-white active:scale-95 transition-transform disabled:opacity-40 shadow-lg">
                            <Circle className="w-5 h-5 text-gray-900 fill-gray-900" />
                            <span className="text-gray-900 font-black text-sm uppercase tracking-widest">
                                {loading ? 'Saving…' : `Capture${learnCount > 0 ? ` (${learnCount})` : ''}`}
                            </span>
                        </button>
                        {learnCount > 0 && (
                            <p className="text-center text-[10px] text-gray-500 font-medium">
                                {learnCount < 5
                                    ? `${5 - learnCount} more capture${5 - learnCount !== 1 ? 's' : ''} recommended`
                                    : '✓ Enough captures — model is learning in background!'}
                            </p>
                        )}
                    </div>
                ) : (
                    <div className="flex gap-2">
                        <button
                            onClick={isInferring ? stopRealtime : startRealtime}
                            disabled={!!pendingResult}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-full font-black text-sm uppercase tracking-widest transition-all active:scale-95 shadow-lg
                                ${isInferring ? 'bg-red-700 text-white' : 'bg-emerald-600 text-white'}`}>
                            {isInferring
                                ? <><X className="w-4 h-4" /> Stop</>
                                : <><Search className="w-4 h-4" /> Start Scanning</>}
                        </button>
                    </div>
                )}
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes slideDown { from { transform: translateY(-8px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                .animate-slideDown { animation: slideDown 0.2s ease-out; }
            `}} />
        </div>
    );
};

export default PiUnified;
