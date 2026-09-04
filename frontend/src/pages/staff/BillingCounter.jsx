import React, { useState, useRef, useEffect } from 'react';
import {
    ScanBarcode,
    ShoppingCart,
    CheckCircle2,
    AlertCircle,
    Trash2,
    XCircle,
    Receipt,
    Tag,
    Loader2,
    RotateCcw,
    MapPin,
    Building2,
    Plus,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function BillingCounter() {
    const { user } = useAuth();

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
        fetch('/api/inventory/locations', { credentials: 'include' })
            .then(r => r.json())
            .then(j => {
                if (j.success) setLocations(j.data || []);
            })
            .catch(() => {});
    }, []);

    const clearMessages = () => { setError(null); setSuccess(null); };

    // ── Open Session ─────────────────────────────────────────────────────────
    const handleOpen = async () => {
        if (!locationId) { setError('Select a counter / location first.'); return; }
        clearMessages();
        setLoading(true);
        try {
            const res = await fetch('/api/billing/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ location_id: parseInt(locationId) }),
            });
            const json = await res.json();
            if (res.ok && json.success) {
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
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    // ── Scan ─────────────────────────────────────────────────────────────────
    const handleScan = async (e) => {
        if (e) e.preventDefault();
        if (!barcode.trim()) return;
        clearMessages();
        setScanning(true);
        try {
            const res = await fetch(`/api/billing/sessions/${sessionId}/scan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ barcode: barcode.trim(), qty: parseInt(qty) || 1 }),
            });
            const json = await res.json();
            if (res.ok && json.success) {
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
            setError(e.message);
        } finally {
            setScanning(false);
            barcodeRef.current?.focus();
        }
    };

    // ── Remove Item ──────────────────────────────────────────────────────────
    const handleRemove = async (itemId) => {
        clearMessages();
        try {
            const res = await fetch(`/api/billing/sessions/${sessionId}/items/${itemId}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            const json = await res.json();
            if (res.ok && json.success) {
                setItems(json.data.items);
                setBillingPreview(json.data);
            } else {
                setError(json.detail || 'Failed to remove item');
            }
        } catch (e) {
            setError(e.message);
        }
    };

    // ── Close / Complete ─────────────────────────────────────────────────────
    const handleClose = async () => {
        if (!window.confirm('Confirm payment and close this bill?')) return;
        clearMessages();
        setLoading(true);
        try {
            const res = await fetch(`/api/billing/sessions/${sessionId}/close`, {
                method: 'POST',
                credentials: 'include',
            });
            const json = await res.json();
            if (res.ok && json.success) {
                setClosedSession(json.data);
                setStatus('closed');
                setSuccess(`Bill #${sessionId} closed. Total: ₹${json.data.net_total?.toFixed(2)}`);
            } else {
                setError(json.detail || 'Failed to close billing session');
            }
        } catch (e) {
            setError(e.message);
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
            const res = await fetch(`/api/billing/sessions/${sessionId}/cancel`, {
                method: 'POST',
                credentials: 'include',
            });
            const json = await res.json();
            if (res.ok && json.success) {
                setStatus('idle');
                setSessionId(null);
                setItems([]);
                setBillingPreview(null);
                setSuccess('Billing session cancelled.');
            } else {
                setError(json.detail || 'Failed to cancel session');
            }
        } catch (e) {
            setError(e.message);
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

    const fmtCur = (n) => `₹${parseFloat(n || 0).toFixed(2)}`;

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6 font-sans text-foreground">
            
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card border border-border p-5 rounded-lg shadow-xs">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary text-primary-foreground flex items-center justify-center rounded-md font-bold">
                        <ScanBarcode size={20} />
                    </div>
                    <div>
                        <h1 className="text-base sm:text-lg font-sans font-bold text-foreground tracking-tight">
                            Retail POS &amp; Billing Counter
                        </h1>
                        <p className="text-xs text-muted-foreground">
                            Scan medicine barcodes, apply batch discounts, and print bills in real time
                        </p>
                    </div>
                </div>

                {sessionId && (
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1.5 rounded-md text-xs font-mono font-bold bg-secondary text-secondary-foreground border border-border">
                            SESSION BILL #{sessionId}
                        </span>
                        {status === 'open' && (
                            <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-emerald-100/70 text-emerald-800 border border-emerald-300 rounded-md">
                                ACTIVE
                            </span>
                        )}
                    </div>
                )}
            </div>

            {/* Toast Alerts */}
            {error && (
                <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-md">
                    <AlertCircle size={14} className="shrink-0 text-destructive" />
                    <span>{error}</span>
                    <button onClick={clearMessages} className="ml-auto font-bold text-destructive cursor-pointer">✕</button>
                </div>
            )}
            {success && (
                <div className="flex items-center gap-2 p-3 bg-emerald-100/70 border border-emerald-300 text-emerald-800 text-xs rounded-md">
                    <CheckCircle2 size={14} className="shrink-0 text-emerald-700" />
                    <span>{success}</span>
                    <button onClick={clearMessages} className="ml-auto font-bold text-emerald-800 cursor-pointer">✕</button>
                </div>
            )}

            {/* ── IDLE STATE: Setup & Open Bill ─────────────────────────────── */}
            {status === 'idle' && (
                <div className="bg-card border border-border rounded-lg shadow-xs p-8 text-center space-y-6">
                    <div className="max-w-md mx-auto space-y-2">
                        <div className="w-12 h-12 bg-secondary border border-border text-foreground flex items-center justify-center mx-auto rounded-md">
                            <ShoppingCart size={24} />
                        </div>
                        <h2 className="text-base font-sans font-bold text-foreground">Initiate New Customer Bill</h2>
                        <p className="text-xs text-muted-foreground">
                            Select your retail shop counter to initialize the real-time stock allocation session.
                        </p>
                    </div>

                    <div className="max-w-sm mx-auto space-y-4 text-left">
                        <div>
                            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5 font-mono">
                                Select Shop Counter / Location <span className="text-destructive">*</span>
                            </label>
                            <div className="relative">
                                <MapPin className="absolute left-3 top-2.5 text-muted-foreground" size={15} />
                                <select
                                    value={locationId}
                                    onChange={e => setLocationId(e.target.value)}
                                    className="w-full pl-9 pr-3 py-2 text-xs bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-ring text-foreground font-medium cursor-pointer"
                                >
                                    <option value="">— Select Location Counter —</option>
                                    {locations.map(loc => (
                                        <option key={loc.id} value={loc.id}>
                                            {loc.name} ({loc.type || 'Retail Counter'})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <button
                            onClick={handleOpen}
                            disabled={loading || !locationId}
                            className="w-full py-2.5 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground font-bold text-xs uppercase tracking-wider rounded-md transition flex items-center justify-center gap-2 cursor-pointer shadow-xs"
                        >
                            {loading ? <Loader2 size={14} className="animate-spin" /> : <ScanBarcode size={14} />}
                            <span>Open Billing Session</span>
                        </button>
                    </div>
                </div>
            )}

            {/* ── OPEN STATE: Barcode Scanner & Real-Time Cart ──────────────── */}
            {status === 'open' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    
                    {/* Left 2 Cols: Scanner + Scanned Items List */}
                    <div className="lg:col-span-2 space-y-4">
                        
                        {/* Barcode Input Bar */}
                        <form onSubmit={handleScan} className="bg-card border border-border p-4 rounded-lg shadow-xs space-y-3">
                            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
                                Barcode Scanner &amp; SKU Lookup
                            </h3>
                            <div className="flex gap-2">
                                <div className="relative flex-1">
                                    <ScanBarcode className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
                                    <input
                                        ref={barcodeRef}
                                        type="text"
                                        placeholder="Scan barcode or type SKU (e.g. 890108600112)..."
                                        value={barcode}
                                        onChange={e => setBarcode(e.target.value)}
                                        className="w-full pl-9 pr-3 py-2 text-xs border border-input rounded-md bg-background text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                                    />
                                </div>
                                <div className="w-24">
                                    <input
                                        type="number"
                                        min="1"
                                        placeholder="Qty"
                                        value={qty}
                                        onChange={e => setQty(e.target.value)}
                                        className="w-full px-2 py-2 text-xs border border-input rounded-md text-center font-bold bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                                    />
                                </div>
                                <button
                                    type="submit"
                                    disabled={scanning || !barcode.trim()}
                                    className="px-4 py-2 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground text-xs font-bold uppercase rounded-md transition flex items-center gap-1.5 cursor-pointer shadow-xs"
                                >
                                    {scanning ? <Loader2 size={13} className="animate-spin" /> : <Plus size={14} />}
                                    <span>Add Item</span>
                                </button>
                            </div>
                        </form>

                        {/* Items Table */}
                        <div className="bg-card border border-border rounded-lg shadow-xs overflow-hidden">
                            <div className="p-3 border-b border-border bg-muted/20 flex items-center justify-between">
                                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
                                    Scanned Cart Items ({items.length})
                                </h3>
                                <button
                                    onClick={handleCancel}
                                    className="text-xs text-destructive hover:underline font-semibold cursor-pointer"
                                >
                                    Cancel Bill
                                </button>
                            </div>

                            {items.length === 0 ? (
                                <div className="p-12 text-center text-muted-foreground">
                                    <ScanBarcode size={32} className="mx-auto mb-2 text-muted-foreground/60" />
                                    <p className="text-xs font-semibold text-foreground">No items scanned yet</p>
                                    <p className="text-[11px] text-muted-foreground">Scan any medicine packaging barcode or SKU to add to cart.</p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-xs border-collapse">
                                        <thead>
                                            <tr className="bg-muted/40 text-muted-foreground font-bold uppercase text-[10px] border-b border-border font-mono">
                                                <th className="py-2.5 px-3">Medicine</th>
                                                <th className="py-2.5 px-3">Batch &amp; Expiry</th>
                                                <th className="py-2.5 px-3 text-right">MRP</th>
                                                <th className="py-2.5 px-3 text-center">Qty</th>
                                                <th className="py-2.5 px-3 text-right">Disc</th>
                                                <th className="py-2.5 px-3 text-right">Total</th>
                                                <th className="py-2.5 px-2 text-center">Del</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border/60 font-medium">
                                            {items.map(item => (
                                                <tr key={item.id} className="hover:bg-accent/30 transition-colors">
                                                    <td className="p-3">
                                                        <p className="font-bold text-foreground">{item.item_name}</p>
                                                        <span className="text-[10px] text-muted-foreground font-mono">{item.barcode || item.sku}</span>
                                                    </td>
                                                    <td className="p-3">
                                                        <span className="font-mono text-xs font-semibold text-foreground">{item.batch_number || 'BATCH-AUTO'}</span>
                                                        <p className="text-[10px] text-muted-foreground">{item.expiry_date || 'Standard'}</p>
                                                    </td>
                                                    <td className="p-3 text-right font-mono text-foreground">{fmtCur(item.mrp || item.unit_price)}</td>
                                                    <td className="p-3 text-center font-bold text-foreground">{item.quantity}</td>
                                                    <td className="p-3 text-right text-emerald-800 font-mono">
                                                        {item.discount_percent ? `${item.discount_percent}%` : '—'}
                                                    </td>
                                                    <td className="p-3 text-right font-mono font-bold text-foreground">
                                                        {fmtCur(item.line_total || (item.quantity * item.unit_price))}
                                                    </td>
                                                    <td className="p-3 text-center">
                                                        <button
                                                            onClick={() => handleRemove(item.id)}
                                                            className="text-muted-foreground hover:text-destructive transition cursor-pointer"
                                                            title="Remove line"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right 1 Col: Bill Summary Card */}
                    <div className="space-y-4">
                        <div className="bg-card border border-border rounded-lg shadow-xs p-5 space-y-4">
                            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider pb-2 border-b border-border font-mono">
                                Bill Computation Summary
                            </h3>

                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between text-muted-foreground">
                                    <span>Total Items:</span>
                                    <span className="font-bold text-foreground font-mono">{items.reduce((acc, i) => acc + (i.quantity || 1), 0)} Units</span>
                                </div>
                                <div className="flex justify-between text-muted-foreground">
                                    <span>Gross Total:</span>
                                    <span className="font-mono text-foreground">{fmtCur(billingPreview?.gross_total || 0)}</span>
                                </div>
                                <div className="flex justify-between text-emerald-800">
                                    <span>Total Discount:</span>
                                    <span className="font-mono font-bold">- {fmtCur(billingPreview?.discount_amount || 0)}</span>
                                </div>
                                <div className="pt-3 border-t border-border flex justify-between items-baseline">
                                    <span className="text-sm font-sans font-bold text-foreground">Net Payable:</span>
                                    <span className="text-xl font-bold font-mono text-foreground">
                                        {fmtCur(billingPreview?.net_total || 0)}
                                    </span>
                                </div>
                            </div>

                            <button
                                onClick={handleClose}
                                disabled={loading || items.length === 0}
                                className="w-full py-3 bg-primary hover:opacity-90 disabled:opacity-50 text-primary-foreground font-bold text-xs uppercase tracking-wider rounded-md transition flex items-center justify-center gap-2 cursor-pointer shadow-xs"
                            >
                                {loading ? <Loader2 size={14} className="animate-spin" /> : <Receipt size={15} />}
                                <span>Complete Bill &amp; Print</span>
                            </button>
                        </div>
                    </div>

                </div>
            )}

            {/* ── CLOSED STATE: Receipt & Bill Summary ──────────────────────── */}
            {status === 'closed' && closedSession && (
                <div className="bg-card border border-border rounded-lg p-8 max-w-lg mx-auto shadow-xs text-center space-y-5 text-card-foreground">
                    <div className="w-12 h-12 bg-emerald-100/70 border border-emerald-300 text-emerald-800 flex items-center justify-center mx-auto rounded-md">
                        <CheckCircle2 size={24} />
                    </div>

                    <div>
                        <h2 className="text-lg font-sans font-bold text-foreground">Transaction Completed</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Bill #{closedSession.session_id || sessionId} recorded and ledger updated.
                        </p>
                    </div>

                    <div className="bg-background border border-border rounded-md p-4 text-xs space-y-2 text-left font-mono">
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Gross Amount:</span>
                            <span className="font-bold text-foreground">{fmtCur(closedSession.gross_total)}</span>
                        </div>
                        <div className="flex justify-between text-emerald-800">
                            <span>Discount:</span>
                            <span className="font-bold">- {fmtCur(closedSession.discount_amount)}</span>
                        </div>
                        <div className="pt-2 border-t border-border flex justify-between text-sm font-bold text-foreground">
                            <span>Total Paid:</span>
                            <span>{fmtCur(closedSession.net_total)}</span>
                        </div>
                    </div>

                    <div className="flex gap-3 pt-2">
                        <button
                            onClick={() => window.print()}
                            className="flex-1 py-2.5 bg-background border border-border text-foreground hover:bg-accent text-xs font-bold uppercase rounded-md transition cursor-pointer"
                        >
                            Print Thermal Slip
                        </button>
                        <button
                            onClick={handleNewBill}
                            className="flex-1 py-2.5 bg-primary hover:opacity-90 text-primary-foreground text-xs font-bold uppercase rounded-md transition flex items-center justify-center gap-1.5 cursor-pointer shadow-xs"
                        >
                            <RotateCcw size={13} />
                            <span>Start Next Bill</span>
                        </button>
                    </div>
                </div>
            )}

        </div>
    );
}
