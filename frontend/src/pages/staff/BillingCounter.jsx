import React from 'react';
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
import { useBillingCounter } from '@/features/billing/hooks/useBillingCounter';
import AlertsDropdown from '@/components/layout/AlertsDropdown';

export default function BillingCounter() {
    const {
        sessionId,
        status,
        items,
        billingPreview,
        closedSession,
        locations,
        locationId,
        setLocationId,
        loading,
        error,
        success,
        clearMessages,
        handleOpen,
        handleRemove,
        handleClose,
        handleCancel,
        handleNewBill,
    } = useBillingCounter();

    const fmtCur = (n) => `₹${parseFloat(n || 0).toFixed(2)}`;

    return (
        <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
            {/* ── Full-Width Sticky Top Navbar (Identical to Dashboard / Inventory) ── */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Retail POS &amp; Billing Counter</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Scan medicine barcodes, apply batch discounts, and print bills in real time
                        </p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        {sessionId && (
                            <div className="flex items-center gap-2">
                                <span className="px-3 py-1.5 rounded-md text-xs font-mono font-bold bg-secondary text-secondary-foreground border border-border">
                                    BILL #{sessionId}
                                </span>
                                {status === 'open' && (
                                    <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 rounded-md">
                                        ACTIVE
                                    </span>
                                )}
                            </div>
                        )}

                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            <div className="p-6 md:p-8 max-w-6xl mx-auto w-full space-y-6 flex-1">

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
                        
                        {/* Barcode Scanner Section (Placeholder / Non-functional) */}
                        <div className="bg-card border border-border p-4 rounded-lg shadow-xs space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono flex items-center gap-2">
                                    <ScanBarcode size={15} className="text-muted-foreground" />
                                    Barcode Scanner (Hardware Placeholder)
                                </h3>
                                <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-muted text-muted-foreground border border-border rounded">
                                    Placeholder
                                </span>
                            </div>
                            <div className="flex gap-2">
                                <div className="relative flex-1">
                                    <ScanBarcode className="absolute left-3 top-2.5 text-muted-foreground opacity-50" size={16} />
                                    <input
                                        type="text"
                                        disabled
                                        placeholder="Barcode scanner placeholder (connect handheld scanner device)..."
                                        className="w-full pl-9 pr-3 py-2 text-xs border border-input rounded-md bg-muted/40 text-muted-foreground font-mono cursor-not-allowed select-none"
                                    />
                                </div>
                                <div className="w-24">
                                    <input
                                        type="text"
                                        disabled
                                        placeholder="Qty: 1"
                                        className="w-full px-2 py-2 text-xs border border-input rounded-md text-center bg-muted/40 text-muted-foreground font-mono cursor-not-allowed select-none"
                                    />
                                </div>
                                <button
                                    type="button"
                                    disabled
                                    className="px-4 py-2 bg-muted border border-border text-muted-foreground text-xs font-semibold uppercase rounded-md cursor-not-allowed select-none flex items-center gap-1.5 opacity-60"
                                    title="Barcode scanning is a hardware placeholder"
                                >
                                    <ScanBarcode size={14} />
                                    <span>Scan (Placeholder)</span>
                                </button>
                            </div>
                        </div>

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
                                    <p className="text-xs font-semibold text-foreground">No items in cart</p>
                                    <p className="text-[11px] text-muted-foreground">Items will appear here once registered.</p>
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
        </div>
    );
}
