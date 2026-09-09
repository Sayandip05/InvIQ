import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

let inMemoryAccessToken = null;

export const setAuthToken = (token) => {
    inMemoryAccessToken = token;
    if (token) {
        sessionStorage.setItem('access_token', token);
    } else {
        sessionStorage.removeItem('access_token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
};

export const getAuthToken = () => {
    return inMemoryAccessToken || sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
};

export const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    withCredentials: true, // Send HttpOnly SameSite cookies automatically
});

// ── Request Interceptor: attach JWT if present ────────────────────────────
apiClient.interceptors.request.use(
    (config) => {
        const token = getAuthToken();
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export default apiClient;
