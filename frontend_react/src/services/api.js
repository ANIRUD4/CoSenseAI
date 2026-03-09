import axios from 'axios';

const API_URL = `http://${window.location.hostname}:8000`;

const api = axios.create({
    baseURL: API_URL,
});

export const checkHealth = () => api.get('/');

// Learn
export const teachModel = (data) => api.post('/learn/commit', data);

// Infer
export const inferFrame = (data) => api.post('/infer/', data);
export const correctPrediction = (data) => api.post('/confirm/', data);

// Marketplace / Share
export const listSharedModels = () => api.get('/share/list');
export const exportModel = (data) => api.post('/share/export', data);
export const importModel = (modelId) => api.post(`/share/import/${modelId}`);

// Actions
export const executeAction = (data) => api.post('/act/', data);
export const getActionMappings = () => api.get('/act/actions');

export default api;
