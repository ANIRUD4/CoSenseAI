/**
 * companion-app/src/services/api.js
 * Connects the companion mobile app to the IntelShare AI backend.
 * Update BASE_URL to your Raspberry Pi's local IP address.
 */

import axios from 'axios';

// ── Configuration ──────────────────────────────────────────────────────────────
// Change this to the IP of your Raspberry Pi on your local network:
export const PI_BASE_URL = 'http://10.47.44.53:8000';

const api = axios.create({ baseURL: PI_BASE_URL, timeout: 15000 });
const boostApi = axios.create({ baseURL: PI_BASE_URL, timeout: 600000 }); // 10-min timeout for boosts

// ── Action Mapping ─────────────────────────────────────────────────────────────
/** GET /act/actions — list all label→action mappings */
export const getActionMappings = () => api.get('/act/actions');

// Note: action text is stored per-label when teaching (via /learn/commit with `action` field).
// This endpoint lets the companion app read current mappings for display.

// ── Marketplace ────────────────────────────────────────────────────────────────
/** GET /share/list — list all models in the marketplace */
export const listModels = () => api.get('/share/list');

/** POST /share/export — publish current model to marketplace */
export const exportModel = (data) => api.post('/share/export', data);

/** POST /share/import/:id — import a marketplace model */
export const importModel = (modelId) => api.post(`/share/import/${modelId}`);

/** GET /share/user/:userId/models — get models uploaded by a user */
export const getUserModels = (userId) => api.get(`/share/user/${userId}/models`);

// ── Memory / Knowledge ─────────────────────────────────────────────────────────
/** GET /learn/images/:label — list collected images for a label */
export const getLabelImages = (label) => api.get(`/learn/images/${label}`);

/** POST /learn/augment/:label — trigger manual LLM augmentation (legacy) */
export const triggerAugmentation = (label) => api.post(`/learn/augment/${label}`);

// ── Boost Accuracy (Large Dataset) ────────────────────────────────────────────
/** POST /boost/start — start a large dataset boost job for a label */
export const triggerBoost = (label, maxImages = 150) =>
    boostApi.post('/boost/start', { label, max_images: maxImages });

/** GET /boost/status/:jobId — poll progress of a running boost job */
export const getBoostStatus = (jobId) => api.get(`/boost/status/${jobId}`);

/** GET /learn/sync/:label — fetch updated centroid + stats after boost */
export const syncLabelCentroid = (label) => api.get(`/learn/sync/${label}`);

// ── Health ─────────────────────────────────────────────────────────────────────
export const checkHealth = () => api.get('/');

export default api;
