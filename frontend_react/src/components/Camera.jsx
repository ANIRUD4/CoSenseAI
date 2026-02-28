import React, { useRef, useEffect, useState } from 'react';
import { Camera as CameraIcon } from 'lucide-react';

const Camera = ({ onCapture, isActive = true }) => {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const [stream, setStream] = useState(null);

    useEffect(() => {
        startCamera();
        return () => stopCamera();
    }, []);

    const startCamera = async () => {
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
        } catch (err) {
            console.error("Error accessing camera:", err);
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    const captureFrame = () => {
        if (!videoRef.current || !canvasRef.current) return;

        const context = canvasRef.current.getContext('2d');
        context.drawImage(videoRef.current, 0, 0, 640, 480);

        // Get base64 string
        const frame = canvasRef.current.toDataURL('image/jpeg');
        // Remove prefix for backend compatibility if needed, but normally backend might need to strip "data:image/jpeg;base64,"
        // backend/adapters.py -> get_embedding -> likely expects raw bytes or handles base64?
        // Looking at backend code, it usually expects numpy array or similar. 
        // We will send base64 and ensure backend handles it.

        if (onCapture) onCapture(frame);
    };

    return (
        <div className="relative rounded-xl overflow-hidden shadow-lg bg-black aspect-video">
            <video
                ref={videoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
            />
            <canvas ref={canvasRef} width="640" height="480" className="hidden" />

            {/* Center ROI Bounding Box Overlay */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] 
                            border-2 border-white/60 border-dashed rounded-lg pointer-events-none z-10 
                            flex flex-col items-center justify-center">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-black/50 backdrop-blur-md rounded text-[10px] text-white/90 font-medium tracking-wide">
                    Place Object Here
                </div>
            </div>

            {isActive && (
                <button
                    onClick={captureFrame}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white/20 backdrop-blur-md p-4 rounded-full hover:bg-white/40 transition-all border border-white/50 z-20"
                >
                    <CameraIcon className="w-8 h-8 text-white" />
                </button>
            )}
        </div>
    );
};

export default Camera;
