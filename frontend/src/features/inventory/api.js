import apiClient from '@/shared/services/apiClient';

export const inventoryApi = {
    getLocations: () => apiClient.get('/inventory/locations'),
    getItems: (params) => apiClient.get('/inventory/items', { params }),
    getItem: (id) => apiClient.get(`/inventory/items/${id}`),
    getItemByBarcode: (barcode) => apiClient.get(`/inventory/items/barcode/${barcode}`),
    createItem: (data) => apiClient.post('/inventory/items', data),
    updateItem: (id, data) => apiClient.put(`/inventory/items/${id}`, data),
    deleteItem: (id) => apiClient.delete(`/inventory/items/${id}`),
    getLocationItems: (locationId) => apiClient.get(`/inventory/location/${locationId}/items`),
    getPackagings: (itemId) => apiClient.get(`/inventory/items/${itemId}/packagings`),
    addPackaging: (itemId, data) => apiClient.post(`/inventory/items/${itemId}/packagings`, data),
    updatePackaging: (itemId, pkgId, data) => apiClient.put(`/inventory/items/${itemId}/packagings/${pkgId}`, data),
    deletePackaging: (itemId, pkgId) => apiClient.delete(`/inventory/items/${itemId}/packagings/${pkgId}`),
    addTransaction: (data) => apiClient.post('/inventory/transaction', data),
    addBulkTransaction: (data) => apiClient.post('/inventory/bulk-transaction', data),
    scanDispense: (data) => apiClient.post('/inventory/scan-dispense', data),
    getVendorTemplate: () => apiClient.get('/vendor/template', { responseType: 'blob' }),
    getVendorUploads: () => apiClient.get('/vendor/my-uploads'),
    getVendorInvoices: () => apiClient.get('/vendor/invoices'),
    getVendorInvoicePdf: (invoiceId) => apiClient.get(`/vendor/invoices/${invoiceId}/pdf`, { responseType: 'blob' }),
    uploadDeliveryManifest: (locationId, formData) => apiClient.post(`/vendor/upload-delivery?location_id=${locationId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

export default inventoryApi;
