/**
 * companion-app/src/services/api.js
 * Connects the companion mobile app to the IntelShare AI backend.
 * Update BASE_URL to your Raspberry Pi's local IP address.
 */

import axios from 'axios';

// ── Configuration ──────────────────────────────────────────────────────────────
// Change this to the IP of your Raspberry Pi on your local network:
export const PI_BASE_URL = 'http://192.168.1.100:8000';

const api = axios.create({ baseURL: PI_BASE_URL, timeout: 15000 });

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

// ── Health ─────────────────────────────────────────────────────────────────────
export const checkHealth = () => api.get('/');

export default api;
