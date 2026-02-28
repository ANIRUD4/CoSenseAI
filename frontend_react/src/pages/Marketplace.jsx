import React, { useEffect, useState } from 'react';
import { listSharedModels, exportModel, importModel } from '../services/api';
import { Download, Upload, Box, Clock, User, Plus, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

const Marketplace = () => {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showExportModal, setShowExportModal] = useState(false);

    // Loading states
    const [exporting, setExporting] = useState(false);
    const [importingId, setImportingId] = useState(null);

    // Toast notification state
    const [toast, setToast] = useState({ show: false, message: '', type: '' });

    // Export Form State
    const [exportName, setExportName] = useState("");
    const [exportDesc, setExportDesc] = useState("");
    const [exportAuthor, setExportAuthor] = useState("");

    useEffect(() => {
        fetchModels();
    }, []);

    const fetchModels = async () => {
        try {
            setLoading(true);
            const res = await listSharedModels();
            setModels(res.data.models);
        } catch (err) {
            console.error(err);
            showToast('Failed to load marketplace models', 'error');
        } finally {
            setLoading(false);
        }
    };

    const showToast = (message, type = 'success') => {
        setToast({ show: true, message, type });
        setTimeout(() => setToast({ show: false, message: '', type: '' }), 4000);
    };

    const handleExport = async (e) => {
        e.preventDefault();
        setExporting(true);
        try {
            const response = await exportModel({
                name: exportName,
                description: exportDesc,
                author: exportAuthor
            });

            setShowExportModal(false);
            setExportName("");
            setExportDesc("");
            setExportAuthor("");

            fetchModels(); // Refresh list

            const fileSize = response.data.file_size_mb || 'Unknown';
            showToast(`Model "${exportName}" exported successfully! (${fileSize} MB)`, 'success');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || 'Export failed. Please check your AWS credentials.';
            showToast(errorMsg, 'error');
            console.error('Export error:', err);
        } finally {
            setExporting(false);
        }
    };

    const handleImport = async (id, name) => {
        setImportingId(id);
        try {
            const response = await importModel(id);
            const fileSize = response.data.file_size_mb || 'Unknown';
            showToast(`Model "${name}" imported successfully! (${fileSize} MB)`, 'success');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || 'Import failed. Please try again.';
            showToast(errorMsg, 'error');
            console.error('Import error:', err);
        } finally {
            setImportingId(null);
        }
    };

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Toast Notification */}
            {toast.show && (
                <div className={`fixed top-4 right-4 z-50 px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 animate-slide-in ${toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                    }`}>
                    {toast.type === 'success' ? (
                        <CheckCircle className="w-5 h-5" />
                    ) : (
                        <AlertCircle className="w-5 h-5" />
                    )}
                    <span className="font-medium">{toast.message}</span>
                </div>
            )}

            <div className="flex justify-between items-end mb-12">
                <div>
                    <h2 className="text-3xl font-bold text-primary mb-2">Model Marketplace</h2>
                    <p className="text-secondary">Discover and share AI models with the community.</p>
                </div>
                <button
                    onClick={() => setShowExportModal(true)}
                    disabled={exporting}
                    className="bg-accent hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {exporting ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Exporting...
                        </>
                    ) : (
                        <>
                            <Upload className="w-5 h-5" /> Share Current Model
                        </>
                    )}
                </button>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 className="w-12 h-12 text-accent animate-spin mb-4" />
                    <p className="text-secondary">Loading marketplace...</p>
                </div>
            ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {models.map((model) => (
                        <div key={model.id} className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-all flex flex-col">
                            <div className="flex items-start justify-between mb-4">
                                <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600">
                                    <Box className="w-6 h-6" />
                                </div>
                                <span className="text-xs font-mono bg-slate-100 text-slate-500 px-2 py-1 rounded">
                                    {new Date(model.created_at * 1000).toLocaleDateString()}
                                </span>
                            </div>

                            <h3 className="text-xl font-bold text-primary mb-2">{model.name}</h3>
                            <p className="text-secondary text-sm mb-4 flex-1">{model.description}</p>

                            <div className="flex items-center gap-2 text-xs text-slate-400 mb-4">
                                <User className="w-3 h-3" />
                                <span>By {model.author || "Anonymous"}</span>
                            </div>

                            {model.file_size && (
                                <div className="text-xs text-slate-400 mb-4">
                                    Size: {(model.file_size / 1024 / 1024).toFixed(2)} MB
                                </div>
                            )}

                            <button
                                onClick={() => handleImport(model.id, model.name)}
                                disabled={importingId === model.id}
                                className="w-full bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {importingId === model.id ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Importing...
                                    </>
                                ) : (
                                    <>
                                        <Download className="w-4 h-4" /> Import Model
                                    </>
                                )}
                            </button>
                        </div>
                    ))}

                    {models.length === 0 && (
                        <div className="col-span-full py-12 text-center text-slate-400 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                            <Box className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                            <p className="text-lg font-medium mb-2">No models available yet</p>
                            <p className="text-sm">Be the first to share a model!</p>
                        </div>
                    )}
                </div>
            )}

            {/* Export Modal */}
            {showExportModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm">
                    <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl animate-scale-up">
                        <h3 className="text-2xl font-bold text-primary mb-6">Share Model</h3>
                        <form onSubmit={handleExport} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-secondary mb-1">Model Name *</label>
                                <input
                                    required
                                    className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition"
                                    value={exportName}
                                    onChange={e => setExportName(e.target.value)}
                                    placeholder="e.g., Gesture Recognition v1.0"
                                    disabled={exporting}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-secondary mb-1">Description *</label>
                                <textarea
                                    required
                                    className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition resize-none"
                                    rows="3"
                                    value={exportDesc}
                                    onChange={e => setExportDesc(e.target.value)}
                                    placeholder="Describe your model's capabilities..."
                                    disabled={exporting}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-secondary mb-1">Author</label>
                                <input
                                    className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition"
                                    value={exportAuthor}
                                    onChange={e => setExportAuthor(e.target.value)}
                                    placeholder="Your name (optional)"
                                    disabled={exporting}
                                />
                            </div>
                            <div className="flex gap-3 mt-8">
                                <button
                                    type="button"
                                    onClick={() => setShowExportModal(false)}
                                    className="flex-1 px-4 py-2 text-slate-500 hover:bg-slate-100 rounded-lg transition"
                                    disabled={exporting}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 bg-accent text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                    disabled={exporting}
                                >
                                    {exporting ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Publishing...
                                        </>
                                    ) : (
                                        'Publish'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Marketplace;
