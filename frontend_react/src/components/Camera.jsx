import React, { useRef, useEffect, useState, useImperativeHandle, forwardRef } from 'react';
import { Camera as CameraIcon } from 'lucide-react';

const Camera = forwardRef(({ onCapture, isActive = true }, ref) => {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [stream, setStream] = useState(null);

    // BBox Drawing State
    const [isDrawing, setIsDrawing] = useState(false);
    const [startPos, setStartPos] = useState(null);
    const [currentPos, setCurrentPos] = useState(null);
    const [bbox, setBbox] = useState(null); // {x, y, w, h} in %

    const [devices, setDevices] = useState([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState(null);

    // Expose capture method to parents via ref
    useImperativeHandle(ref, () => ({
        capture: () => {
            captureFrame();
        }
    }));

    useEffect(() => {
        // First get the list of devices
        navigator.mediaDevices.enumerateDevices().then(deviceInfos => {
            const videoInputs = deviceInfos.filter(device => device.kind === 'videoinput');
            setDevices(videoInputs);
            if (videoInputs.length > 0) {
                // Try to find a USB or Webcam device by default
                const usbCam = videoInputs.find(d => d.label.toLowerCase().includes('usb') || d.label.toLowerCase().includes('webcam'));
                setSelectedDeviceId(usbCam ? usbCam.deviceId : videoInputs[0].deviceId);
            }
        }).catch(err => {
            console.error("Device enumeration failed", err);
        });
    }, []);

    useEffect(() => {
        if (selectedDeviceId) {
            startCamera(selectedDeviceId);
        }
        return () => stopCamera();
    }, [selectedDeviceId]);

    const startCamera = async (deviceId) => {
        stopCamera(); // stop existing stream
        try {
            const constraints = {
                video: {
                    deviceId: { exact: deviceId },
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            };
            const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
        } catch (err) {
            console.error("Error accessing camera:", err);
            // Alert added so we can see the exact error on the kiosk screen!
            alert("CAMERA ERROR: " + err.message + " (" + err.name + ")");
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    const getPos = (e) => {
        const rect = containerRef.current.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: ((clientX - rect.left) / rect.width),
            y: ((clientY - rect.top) / rect.height)
        };
    };

    const handleStart = (e) => {
        const pos = getPos(e);
        setIsDrawing(true);
        setStartPos(pos);
        setCurrentPos(pos);
        setBbox(null);
    };

    const handleMove = (e) => {
        if (!isDrawing) return;
        const pos = getPos(e);
        setCurrentPos(pos);
    };

    const handleEnd = () => {
        if (!isDrawing) return;
        setIsDrawing(false);

        // Finalize BBox
        const x = Math.min(startPos.x, currentPos.x);
        const y = Math.min(startPos.y, currentPos.y);
        const w = Math.abs(startPos.x - currentPos.x);
        const h = Math.abs(startPos.y - currentPos.y);

        if (w > 0.05 && h > 0.05) { // Min size requirement
            setBbox({ x, y, w, h });
        } else {
            setBbox(null);
        }
    };

    const captureFrame = () => {
        if (!videoRef.current || !canvasRef.current || !containerRef.current) return;

        const cw = containerRef.current.clientWidth;
        const ch = containerRef.current.clientHeight;

        if (cw === 0 || ch === 0) return;

        canvasRef.current.width = cw;
        canvasRef.current.height = ch;

        const context = canvasRef.current.getContext('2d');
        
        const vw = videoRef.current.videoWidth;
        const vh = videoRef.current.videoHeight;
        
        if (!vw || !vh) {
            // Fallback if video isn't ready
            context.drawImage(videoRef.current, 0, 0, cw, ch);
            const frame = canvasRef.current.toDataURL('image/jpeg');
            if (onCapture) {
                onCapture(frame, bbox);
            }
            return;
        }

        // Emulate object-cover so bbox matches the captured image perfectly
        const cr = cw / ch;
        const vr = vw / vh;

        let sWidth = vw;
        let sHeight = vh;
        let sx = 0;
        let sy = 0;

        if (cr > vr) {
            sHeight = vw / cr;
            sy = (vh - sHeight) / 2;
        } else {
            sWidth = vh * cr;
            sx = (vw - sWidth) / 2;
        }

        context.drawImage(videoRef.current, sx, sy, sWidth, sHeight, 0, 0, cw, ch);

        const frame = canvasRef.current.toDataURL('image/jpeg');

        if (onCapture) {
            // Pass frame and optional manual bbox
            onCapture(frame, bbox);
        }
    };

    return (
        <div className="relative group">
            {/* Camera Selector Dropdown (Visible on touch/hover) */}
            {devices.length > 1 && (
                <div className="absolute top-2 right-2 z-50 opacity-50 hover:opacity-100 focus-within:opacity-100 transition-opacity bg-black/50 p-2 rounded-lg backdrop-blur-md">
                    <select 
                        className="bg-transparent text-white text-xs outline-none cursor-pointer max-w-[150px] truncate"
                        value={selectedDeviceId || ''}
                        onChange={(e) => setSelectedDeviceId(e.target.value)}
                    >
                        {devices.map((device, idx) => (
                            <option key={device.deviceId} value={device.deviceId} className="bg-slate-900">
                                {device.label || `Camera ${idx + 1}`}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            <div
                ref={containerRef}
                className="relative rounded-xl overflow-hidden shadow-lg bg-black aspect-video cursor-crosshair touch-none"
                onMouseDown={handleStart}
                onMouseMove={handleMove}
                onMouseUp={handleEnd}
                onTouchStart={handleStart}
                onTouchMove={handleMove}
                onTouchEnd={handleEnd}
            >
                <div className="absolute top-0 left-0 bg-red-600 text-white font-bold px-2 py-1 z-50">
                    DEBUG: v4
                </div>
            <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover pointer-events-none"
            />
            <canvas ref={canvasRef} width="640" height="480" className="hidden" />

            {/* Manual BBox Overlay */}
            {(isDrawing || bbox) && (
                <div
                    className="absolute border-2 border-accent border-dashed rounded-lg bg-accent/10 pointer-events-none z-10"
                    style={{
                        left: `${(isDrawing ? Math.min(startPos.x, currentPos.x) : bbox.x) * 100}%`,
                        top: `${(isDrawing ? Math.min(startPos.y, currentPos.y) : bbox.y) * 100}%`,
                        width: `${(isDrawing ? Math.abs(startPos.x - currentPos.x) : bbox.w) * 100}%`,
                        height: `${(isDrawing ? Math.abs(startPos.y - currentPos.y) : bbox.h) * 100}%`
                    }}
                >
                    <div className="absolute -top-7 left-0 px-2 py-1 bg-accent text-white text-[10px] rounded-t-md font-bold uppercase tracking-wider">
                        Manual ROI
                    </div>
                </div>
            )}

            {/* Default ROI hint (if no manual box) */}
            {!isDrawing && !bbox && (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] 
                                border-2 border-white/30 border-dashed rounded-lg pointer-events-none z-0 
                                flex flex-col items-center justify-center">
                    <div className="bg-black/40 backdrop-blur-sm px-3 py-1.5 rounded-full text-xs text-white/80 font-medium">
                        Draw Box or Tap Focus
                    </div>
                </div>
            )}

            {isActive && (
                <button
                    title="capture-trigger"
                    onClick={(e) => {
                        e.stopPropagation(); // Don't trigger startPos on click
                        captureFrame();
                    }}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white/20 backdrop-blur-md p-4 rounded-full hover:bg-white/40 transition-all border border-white/50 z-20 shadow-xl"
                >
                    <CameraIcon className="w-8 h-8 text-white" />
                </button>
            )}
        </div>
        </div>
    );
});

export default Camera;
