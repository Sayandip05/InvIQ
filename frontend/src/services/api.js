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
            // Only redirect to /signin if the request carried a token — that
            // means a real session has expired. Guests (no token) should never
            // be silently redirected; the UI handles them via AuthGateModal.
            const hadToken = !!localStorage.getItem('access_token');
            if (hadToken && window.location.pathname !== '/signin') {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/signin';
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
    me: () => api.get('/auth/me'),
    list: (params) => api.get('/auth/users', { params }),
    get: (id) => api.get(`/auth/users/${id}`),
    update: (id, data) => api.put(`/auth/users/${id}`, data),
    delete: (id) => api.delete(`/auth/users/${id}`),
    activateUser: (id) => api.put(`/auth/users/${id}/activate`),
    deactivateUser: (id) => api.put(`/auth/users/${id}/deactivate`),
    resetPassword: (id, data) => api.post(`/auth/users/${id}/reset-password`, data),
    updateRole: (id, data) => api.put(`/auth/users/${id}/role`, data),
    changePassword: (data) => api.post('/auth/change-password', data),
    refresh: (data) => api.post('/auth/refresh', data),
    // Password reset
    requestPasswordReset: (data) => api.post('/auth/request-password-reset', data),
    resetPassword: (data) => api.post('/auth/reset-password', data),
    verifyEmail: (data) => api.post('/auth/verify-email', data),
    // OAuth
    googleAuth: (idToken) => api.post('/auth/google-auth', { id_token: idToken }),
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
    generateReport: (reportType, params) => api.get(`/admin/reports/generate?report_type=${reportType}&${params}`, { responseType: 'blob' }),
};

export default api;
