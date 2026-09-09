import apiClient from '@/shared/services/apiClient';

export const analyticsApi = {
    getStats: (params) => apiClient.get('/analytics/dashboard/stats', { params }),
    getHeatmap: () => apiClient.get('/analytics/heatmap'),
    getAlerts: (params) => apiClient.get('/analytics/alerts', { params }),
    getSummary: () => apiClient.get('/analytics/summary'),
};

export default analyticsApi;
