import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, Search } from 'lucide-react';

const PiHome = () => {
    const navigate = useNavigate();

    return (
        <div className="h-screen w-screen flex flex-col bg-slate-900 text-white p-4 items-center justify-center overflow-hidden">
            <h1 className="text-xl font-bold mb-6 text-blue-400">IntelShare AI (Pi)</h1>

            <div className="grid grid-cols-2 gap-4 w-full h-[60%]">
                <button
                    onClick={() => navigate('/pi/learn')}
                    className="flex flex-col items-center justify-center bg-blue-600 rounded-2xl active:bg-blue-700 transition-colors shadow-lg active:scale-95 transform"
                >
                    <Brain className="w-12 h-12 mb-2" />
                    <span className="text-xl font-bold">LEARN</span>
                </button>

                <button
                    onClick={() => navigate('/pi/infer')}
                    className="flex flex-col items-center justify-center bg-green-600 rounded-2xl active:bg-green-700 transition-colors shadow-lg active:scale-95 transform"
                >
                    <Search className="w-12 h-12 mb-2" />
                    <span className="text-xl font-bold">INFER</span>
                </button>
            </div>

            <p className="mt-6 text-xs text-slate-500 uppercase tracking-widest">
                3.5" Touch Interface v1.0
            </p>
        </div>
    );
};

export default PiHome;
