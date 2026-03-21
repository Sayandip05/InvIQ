import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
});

export const analytics = {
    getStats: () => api.get('/analytics/dashboard/stats'),
};

export const inventory = {
    getLocations: () => api.get('/inventory/locations'),
    getItems: () => api.get('/inventory/items'),
    getLocationItems: (locationId) => api.get(`/inventory/location/${locationId}/items`),
    addTransaction: (data) => api.post('/inventory/transaction', data),
    addBulkTransaction: (data) => api.post('/inventory/bulk-transaction', data),
};

export const chat = {
    query: (data) => api.post('/chat/query', data),
    getSessions: () => api.get('/chat/sessions'),
    getHistory: (id) => api.get(`/chat/history/${id}`),
    transcribe: (audioBlob) => {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');
        return api.post('/chat/transcribe', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

export const requisition = {
    create: (data) => api.post('/requisition/create', data),
    list: (params) => api.get('/requisition/list', { params }),
    get: (id) => api.get(`/requisition/${id}`),
    stats: () => api.get('/requisition/stats'),
    approve: (id, data) => api.put(`/requisition/${id}/approve`, data),
    reject: (id, data) => api.put(`/requisition/${id}/reject`, data),
    cancel: (id, data) => api.put(`/requisition/${id}/cancel`, data),
};

export default api;

