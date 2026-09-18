import { useState, useEffect, useCallback } from 'react';
import { inventoryApi } from '@/features/inventory/api';

export function useDeliveryUpload() {
    const [locations, setLocations] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [file, setFile] = useState(null);
    const [uploads, setUploads] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const fetchLocations = useCallback(async () => {
        try {
            const response = await inventoryApi.getLocations();
            const locs = response.data?.data || [];
            setLocations(locs);
            if (locs.length > 0) {
                setSelectedLocation((prev) => prev || locs[0].id);
            }
        } catch (e) {
            console.error('Failed to fetch locations:', e);
        }
    }, []);

    const fetchUploadHistory = useCallback(async () => {
        try {
            const response = await inventoryApi.getVendorUploads();
            setUploads(response.data?.data || []);
        } catch (e) {
            console.error('Failed to fetch upload history:', e);
        }
    }, []);

    const fetchInvoices = useCallback(async () => {
        try {
            const response = await inventoryApi.getVendorInvoices();
            setInvoices(response.data?.data?.invoices || response.data?.data || []);
        } catch {
            setInvoices([]);
        }
    }, []);

    const loadData = useCallback(async () => {
        setFetching(true);
        try {
            await Promise.all([
                fetchLocations(),
                fetchUploadHistory(),
                fetchInvoices(),
            ]);
        } finally {
            setFetching(false);
        }
    }, [fetchLocations, fetchUploadHistory, fetchInvoices]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleDownloadTemplate = async () => {
        try {
            const response = await inventoryApi.getVendorTemplate();
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'InvIQ_Medicine_Delivery_Template.xlsx');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch {
            setError('Failed to download template. Please try again.');
        }
    };

    const handleDownloadInvoice = async (invoiceId, invoiceNumber) => {
        try {
            const response = await inventoryApi.getVendorInvoicePdf(invoiceId);
            const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Invoice_${invoiceNumber || invoiceId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch {
            setError('Failed to download invoice PDF.');
        }
    };

    const handleFileChange = (selectedFile) => {
        if (!selectedFile) return;
        if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls') && !selectedFile.name.endsWith('.csv')) {
            setError('Only .xlsx, .xls, or .csv files are accepted');
            setFile(null);
            return;
        }
        if (selectedFile.size > 10 * 1024 * 1024) {
            setError('File size must be under 10MB');
            setFile(null);
            return;
        }
        setFile(selectedFile);
        setError('');
        setSuccess('');
    };

    const handleInputChange = (e) => handleFileChange(e.target.files?.[0]);

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        if (e.dataTransfer?.files?.[0]) {
            handleFileChange(e.dataTransfer.files[0]);
        }
    };

    const handleUpload = async (e) => {
        if (e && e.preventDefault) e.preventDefault();
        if (!selectedLocation) {
            setError('Please select a target pharmacy branch');
            return;
        }
        if (!file) {
            setError('Please select an Excel or CSV delivery file');
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await inventoryApi.uploadDeliveryManifest(selectedLocation, formData);
            const processedCount = res.data?.data?.rows_processed ?? res.data?.rows_processed ?? 'all';
            setSuccess(`Delivery manifest uploaded successfully! ${processedCount} medicine items ingested into inventory.`);
            setFile(null);
            const fileInput = document.getElementById('file-upload');
            if (fileInput) fileInput.value = '';
            fetchUploadHistory();
            fetchInvoices();
        } catch (uploadErr) {
            const msg = uploadErr?.response?.data?.error?.message
                || uploadErr?.response?.data?.detail
                || uploadErr?.response?.data?.message
                || 'Upload failed. Please check file format.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return {
        locations,
        selectedLocation,
        setSelectedLocation,
        file,
        setFile,
        uploads,
        invoices,
        loading,
        fetching,
        error,
        setError,
        success,
        setSuccess,
        dragOver,
        setDragOver,
        searchQuery,
        setSearchQuery,
        loadData,
        handleDownloadTemplate,
        handleDownloadInvoice,
        handleFileChange,
        handleInputChange,
        handleDrop,
        handleUpload,
    };
}

export default useDeliveryUpload;
