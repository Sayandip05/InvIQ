import apiClient from '@/shared/services/apiClient';

export const requisitionApi = {
    create: (data) => apiClient.post('/requisition/create', data),
    list: (params) => apiClient.get('/requisition/list', { params }),
    get: (id) => apiClient.get(`/requisition/${id}`),
    stats: () => apiClient.get('/requisition/stats'),
    approve: (id, data) => apiClient.put(`/requisition/${id}/approve`, data),
    reject: (id, data) => apiClient.put(`/requisition/${id}/reject`, data),
    cancel: (id, data) => apiClient.put(`/requisition/${id}/cancel`, data),
    fulfill: (id) => apiClient.put(`/requisition/${id}/fulfill`),
};

export default requisitionApi;
