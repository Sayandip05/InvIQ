import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
});

// ── Request Interceptor: attach JWT to every request ─────────────────────
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ── Response Interceptor: handle expired / invalid tokens ─────────────────
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error?.response?.status === 401) {
            // Token expired or invalid → clear storage and redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
    login: (data) => api.post('/auth/login', data),
    logout: () => api.post('/auth/logout'),
    register: (data) => api.post('/auth/register', data),
    profile: () => api.get('/auth/profile'),
    listUsers: (params) => api.get('/auth/users', { params }),
    activateUser: (id) => api.put(`/auth/users/${id}/activate`),
    deactivateUser: (id) => api.put(`/auth/users/${id}/deactivate`),
    resetPassword: (id, data) => api.post(`/auth/users/${id}/reset-password`, data),
    updateRole: (id, data) => api.put(`/auth/users/${id}/role`, data),
    changePassword: (data) => api.post('/auth/change-password', data),
    refresh: (data) => api.post('/auth/refresh', data),
};

// ── Analytics ─────────────────────────────────────────────────────────────
export const analytics = {
    getStats: () => api.get('/analytics/dashboard/stats'),
    getHeatmap: () => api.get('/analytics/heatmap'),
    getAlerts: (params) => api.get('/analytics/alerts', { params }),
    getSummary: () => api.get('/analytics/summary'),
};

// ── Inventory ─────────────────────────────────────────────────────────────
export const inventory = {
    getLocations: () => api.get('/inventory/locations'),
    getItems: () => api.get('/inventory/items'),
    getLocationItems: (locationId) => api.get(`/inventory/location/${locationId}/items`),
    addTransaction: (data) => api.post('/inventory/transaction', data),
    addBulkTransaction: (data) => api.post('/inventory/bulk-transaction', data),
};

// ── Chat ──────────────────────────────────────────────────────────────────
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

// ── Requisitions ──────────────────────────────────────────────────────────
export const requisition = {
    create: (data) => api.post('/requisition/create', data),
    list: (params) => api.get('/requisition/list', { params }),
    get: (id) => api.get(`/requisition/${id}`),
    stats: () => api.get('/requisition/stats'),
    approve: (id, data) => api.put(`/requisition/${id}/approve`, data),
    reject: (id, data) => api.put(`/requisition/${id}/reject`, data),
    cancel: (id, data) => api.put(`/requisition/${id}/cancel`, data),
};

// ── Admin ─────────────────────────────────────────────────────────────────
export const admin = {
    overview: () => api.get('/admin/overview'),
    auditLogs: (params) => api.get('/admin/audit-logs', { params }),
    usersSummary: () => api.get('/admin/users/summary'),
};

export default api;
