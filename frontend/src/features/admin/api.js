import apiClient from '@/shared/services/apiClient';

export const adminApi = {
    overview: () => apiClient.get('/admin/overview'),
    auditLogs: (params) => apiClient.get('/admin/audit-logs', { params }),
    usersSummary: () => apiClient.get('/admin/users/summary'),
    generateReport: (reportType, params) => apiClient.get(`/admin/reports/generate?report_type=${reportType}&${params}`, { responseType: 'blob' }),
    getMonthlySalesReport: (year, month) => apiClient.get(`/admin/reports/monthly-sales?year=${year}&month=${month}`),
    getSuppliers: () => apiClient.get('/admin/suppliers'),
    createSupplier: (data) => apiClient.post('/admin/suppliers', data),
    updateSupplier: (id, data) => apiClient.put(`/admin/suppliers/${id}`, data),
    deleteSupplier: (id) => apiClient.delete(`/admin/suppliers/${id}`),
};

export default adminApi;
