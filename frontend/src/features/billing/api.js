import apiClient from '@/shared/services/apiClient';

export const billingApi = {
    openSession: (data) => apiClient.post('/billing/sessions', data),
    scanItem: (sessionId, data) => apiClient.post(`/billing/sessions/${sessionId}/scan`, data),
    removeItem: (sessionId, itemId) => apiClient.delete(`/billing/sessions/${sessionId}/items/${itemId}`),
    closeSession: (sessionId) => apiClient.post(`/billing/sessions/${sessionId}/close`),
    cancelSession: (sessionId) => apiClient.post(`/billing/sessions/${sessionId}/cancel`),
    getSession: (sessionId) => apiClient.get(`/billing/sessions/${sessionId}`),
};

export default billingApi;
