import apiClient from '@/shared/services/apiClient';

export const chatApi = {
    query: (data) => apiClient.post('/chat/query', data),
    getSessions: () => apiClient.get('/chat/sessions'),
    getHistory: (id) => apiClient.get(`/chat/history/${id}`),
    deleteHistory: (id) => apiClient.delete(`/chat/history/${id}`),
    transcribe: (audioBlob) => {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');
        return apiClient.post('/chat/transcribe', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

export default chatApi;
