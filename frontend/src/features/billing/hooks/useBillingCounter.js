import { useState, useRef, useEffect, useCallback } from 'react';
import { billingApi } from '@/features/billing/api';
import { inventoryApi } from '@/features/inventory/api';

export function useBillingCounter() {
    // Session state
    const [sessionId, setSessionId] = useState(null);
    const [status, setStatus] = useState('idle'); // idle | open | closed | cancelled
    const [items, setItems] = useState([]);
    const [billingPreview, setBillingPreview] = useState(null);
    const [closedSession, setClosedSession] = useState(null);

    // Location
    const [locations, setLocations] = useState([]);
    const [locationId, setLocationId] = useState('');

    // Scan
    const [barcode, setBarcode] = useState('');
    const [qty, setQty] = useState(1);
    const [scanning, setScanning] = useState(false);
    const barcodeRef = useRef(null);

    // Loading / errors
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Auto-focus barcode field when session is open
    useEffect(() => {
        if (status === 'open' && barcodeRef.current) {
            barcodeRef.current.focus();
        }
    }, [status]);

    // Fetch locations on mount
    useEffect(() => {
        inventoryApi.getLocations()
            .then(res => {
                const data = res.data?.data || [];
                setLocations(data);
                if (data.length > 0) {
                    setLocationId(prev => prev || String(data[0].id));
                }
            })
            .catch(() => {});
    }, []);

    const clearMessages = useCallback(() => {
        setError(null);
        setSuccess(null);
    }, []);

    // ── Open Session ─────────────────────────────────────────────────────────
    const handleOpen = async () => {
        if (!locationId) {
            setError('Select a counter / location first.');
            return;
        }
        clearMessages();
        setLoading(true);
        try {
            const res = await billingApi.openSession({ location_id: parseInt(locationId, 10) });
            const json = res.data;
            if (json.success) {
                setSessionId(json.data.session_id);
                setItems([]);
                setBillingPreview(null);
                setClosedSession(null);
                setStatus('open');
                setTimeout(() => barcodeRef.current?.focus(), 100);
            } else {
                setError(json.detail || json.message || 'Failed to open billing session');
            }
        } catch (e) {
            setError(e.response?.data?.detail || e.message || 'Failed to open billing session');
        } finally {
            setLoading(false);
        }
    };

    // ── Scan ─────────────────────────────────────────────────────────────────
    const handleScan = async (e) => {
        if (e && e.preventDefault) e.preventDefault();
        if (!barcode.trim()) return;
        clearMessages();
        setScanning(true);
        try {
            const res = await billingApi.scanItem(sessionId, {
                barcode: barcode.trim(),
                qty: parseInt(qty, 10) || 1,
            });
            const json = res.data;
            if (json.success) {
                setItems(json.data.items);
                setBillingPreview(json.data);
                setBarcode('');
                setQty(1);
                setSuccess(`Scanned: ${json.data.scanned_item?.item_name || barcode}`);
                setTimeout(() => setSuccess(null), 2500);
            } else {
                setError(json.detail || json.message || 'Item scan failed');
            }
        } catch (e) {
            setError(e.response?.data?.detail || e.message || 'Item scan failed');
        } finally {
            setScanning(false);
            barcodeRef.current?.focus();
        }
    };

    // ── Remove Item ──────────────────────────────────────────────────────────
    const handleRemove = async (itemId) => {
        clearMessages();
        try {
            const res = await billingApi.removeItem(sessionId, itemId);
            const json = res.data;
            if (json.success) {
                setItems(json.data.items);
                setBillingPreview(json.data);
            } else {
                setError(json.detail || 'Failed to remove item');
            }
        } catch (e) {
            setError(e.response?.data?.detail || e.message || 'Failed to remove item');
        }
    };

    // ── Close / Complete ─────────────────────────────────────────────────────
    const handleClose = async () => {
        if (!window.confirm('Confirm payment and close this bill?')) return;
        clearMessages();
        setLoading(true);
        try {
            const res = await billingApi.closeSession(sessionId);
            const json = res.data;
            if (json.success) {
                setClosedSession(json.data);
                setStatus('closed');
                setSuccess(`Bill #${sessionId} closed. Total: ₹${json.data.net_total?.toFixed(2)}`);
            } else {
                setError(json.detail || 'Failed to close billing session');
            }
        } catch (e) {
            setError(e.response?.data?.detail || e.message || 'Failed to close session');
        } finally {
            setLoading(false);
        }
    };

    // ── Cancel ───────────────────────────────────────────────────────────────
    const handleCancel = async () => {
        if (!window.confirm('Cancel this billing session? Scanned stock reservations will be restored.')) return;
        clearMessages();
        setLoading(true);
        try {
            const res = await billingApi.cancelSession(sessionId);
            const json = res.data;
            if (json.success) {
                setStatus('idle');
                setSessionId(null);
                setItems([]);
                setBillingPreview(null);
                setSuccess('Billing session cancelled.');
            } else {
                setError(json.detail || 'Failed to cancel session');
            }
        } catch (e) {
            setError(e.response?.data?.detail || e.message || 'Failed to cancel session');
        } finally {
            setLoading(false);
        }
    };

    const handleNewBill = () => {
        setSessionId(null);
        setStatus('idle');
        setItems([]);
        setBillingPreview(null);
        setClosedSession(null);
        clearMessages();
    };

    return {
        sessionId,
        status,
        items,
        billingPreview,
        closedSession,
        locations,
        locationId,
        setLocationId,
        barcode,
        setBarcode,
        qty,
        setQty,
        scanning,
        barcodeRef,
        loading,
        error,
        setError,
        success,
        setSuccess,
        clearMessages,
        handleOpen,
        handleScan,
        handleRemove,
        handleClose,
        handleCancel,
        handleNewBill,
    };
}

export default useBillingCounter;
