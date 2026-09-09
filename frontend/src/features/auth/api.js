import apiClient from '@/shared/services/apiClient';

export const authApi = {
    login: (data) => apiClient.post('/auth/login', data),
    logout: () => apiClient.post('/auth/logout'),
    register: (data) => apiClient.post('/auth/signup', data),
    adminCreateUser: (data) => apiClient.post('/auth/register', data),
    me: () => apiClient.get('/auth/me'),
    list: (params) => apiClient.get('/auth/users', { params }),
    get: (id) => apiClient.get(`/auth/users/${id}`),
    update: (id, data) => apiClient.put(`/auth/users/${id}`, data),
    delete: (id) => apiClient.delete(`/auth/users/${id}`),
    activateUser: (id) => apiClient.put(`/auth/users/${id}/activate`),
    deactivateUser: (id) => apiClient.put(`/auth/users/${id}/deactivate`),
    adminResetPassword: (id, data) => apiClient.post(`/auth/users/${id}/reset-password`, data),
    updateRole: (id, data) => apiClient.put(`/auth/users/${id}/role`, data),
    getProfile: () => apiClient.get('/auth/me'),
    updateProfile: (data) => apiClient.patch('/auth/me', data),
    changePassword: (data) => apiClient.post('/auth/change-password', data),
    refresh: (data) => apiClient.post('/auth/refresh', data),
    requestPasswordReset: (data) => apiClient.post('/auth/request-password-reset', data),
    resetPassword: (data) => apiClient.post('/auth/reset-password', data),
    verifyEmail: (data) => apiClient.post('/auth/verify-email', data),
    googleAuth: (idToken) => apiClient.post('/auth/google-auth', { id_token: idToken }),
};

export default authApi;
