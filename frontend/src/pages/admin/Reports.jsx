import React, { useState, useEffect } from 'react';
import { admin, inventory } from '../../services/api';
import {
    Download,
    MapPin,
    Calendar,
    Loader2,
    ChevronRight,
} from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

const LOCATION_TYPE_LABELS = {
    central_warehouse: 'Warehouse',
    retail_pharmacy:   'Retail Pharmacy',
    hospital_client:   'Hospital',
    retail_counter:    'Retail Counter',
};

const REPORT_TYPES = [
    { value: 'inventory',     label: 'Inventory Report',       desc: 'Current stock levels across all locations' },
    { value: 'monthly_sales', label: 'Monthly Sales & Profit', desc: 'Gross revenue, discounts, COGS & profit margin' },
    { value: 'requisitions',  label: 'Requisition Report',     desc: 'All requisitions and approvals' },
    { value: 'low_stock',     label: 'Low Stock Report',       desc: 'Items below minimum threshold' },
];

const Reports = () => {
    const [loading, setLoading]       = useState(false);
    const [reportType, setReportType] = useState('inventory');
    const [locationId, setLocationId] = useState('');
    const [dateFrom, setDateFrom]     = useState('');
    const [dateTo, setDateTo]         = useState('');
    const [locations, setLocations]   = useState([]);
    const [locLoading, setLocLoading] = useState(true);

    const currentMonthKey = new Date().toISOString().slice(0, 7);
    const [selectedMonth, setSelectedMonth] = useState(currentMonthKey);
    const [monthlyData, setMonthlyData]     = useState(null);
    const [monthlyLoading, setMonthlyLoading] = useState(false);

    useEffect(() => {
        const fetchLocations = async () => {
            try {
                const res = await inventory.getLocations();
                const data = res.data?.data ?? res.data ?? [];
                setLocations(Array.isArray(data) ? data : (data.items ?? []));
            } catch {
                // silent fail
            } finally {
                setLocLoading(false);
            }
        };
        fetchLocations();
    }, []);

    useEffect(() => {
        if (reportType !== 'monthly_sales' || !selectedMonth) return;
        const fetchMonthly = async () => {
            setMonthlyLoading(true);
            try {
                const [year, month] = selectedMonth.split('-');
                const res = await admin.getMonthlySalesReport(parseInt(year, 10), parseInt(month, 10));
                if (res.data?.success && res.data?.data) setMonthlyData(res.data.data);
            } catch {
                // silent fail
            } finally {
                setMonthlyLoading(false);
            }
        };
        fetchMonthly();
    }, [reportType, selectedMonth]);

    const handleDownload = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (reportType === 'monthly_sales') {
                if (selectedMonth) params.append('date_from', `${selectedMonth}-01`);
            } else {
                if (locationId) params.append('location_id', locationId);
                if (dateFrom)   params.append('date_from', dateFrom);
                if (dateTo)     params.append('date_to', dateTo);
            }
            const response = await admin.generateReport(reportType, params.toString());
            const blob = new Blob([response.data], { type: 'application/pdf' });
            const url  = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href     = url;
            link.download = `inviq_${reportType}_report_${new Date().toISOString().slice(0,10)}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch {
            alert('Failed to generate report. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const grouped = locations.reduce((acc, loc) => {
        const key = loc.location_type || loc.type || 'other';
        if (!acc[key]) acc[key] = [];
        acc[key].push(loc);
        return acc;
    }, {});

    const fmtCurrency = (n) =>
        `₹${parseFloat(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const inputCls = "w-full px-3 py-2 border border-border rounded-none focus:outline-none focus:border-primary text-sm bg-background text-foreground";
    const labelCls = "flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 font-mono";

    return (
        <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
            {/* Top Navbar */}
            <div className="sticky top-0 z-30 bg-card border-b border-border px-6 py-3.5">
                <div className="flex items-center justify-between">
                    <h2 className="font-sans text-base font-bold text-foreground tracking-tight">Reports &amp; Analytics</h2>
                    <AlertsDropdown />
                </div>
            </div>

            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">

                {/* Generate Report Card */}
                <div className="bg-card border border-border rounded-none shadow-none">

                    {/* Card Header */}
                    <div className="px-6 py-4 border-b border-border">
                        <h3 className="font-sans text-sm font-bold text-foreground">Generate Report</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Select a report type and time period to export PDF</p>
                    </div>

                    <div className="p-6 space-y-6">
                        {/* Report Type Selection */}
                        <div>
                            <p className={labelCls}>Report Type</p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                                {REPORT_TYPES.map((type) => (
                                    <button
                                        key={type.value}
                                        onClick={() => setReportType(type.value)}
                                        className={[
                                            "p-4 text-left transition-all border rounded-none focus:outline-none flex flex-col justify-between min-h-[96px] cursor-pointer",
                                            reportType === type.value
                                                ? "bg-accent border-primary border-l-4 border-l-primary"
                                                : "bg-card border-border hover:border-primary/40 hover:bg-accent/40",
                                        ].join(" ")}
                                    >
                                        <div className="flex items-center justify-between gap-1 w-full">
                                            <span className={`text-sm font-bold ${reportType === type.value ? 'text-foreground' : 'text-foreground/80'}`}>
                                                {type.label}
                                            </span>
                                            {reportType === type.value && <ChevronRight size={14} className="text-foreground shrink-0" />}
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">{type.desc}</p>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Filters */}
                        {reportType === 'monthly_sales' ? (
                            <div className="space-y-4">
                                <div className="max-w-xs">
                                    <label className={labelCls}>
                                        <Calendar size={12} /> Calendar Month
                                    </label>
                                    <input
                                        type="month"
                                        className={inputCls}
                                        value={selectedMonth}
                                        onChange={(e) => setSelectedMonth(e.target.value)}
                                    />
                                </div>

                                {/* Monthly summary metrics */}
                                {monthlyLoading ? (
                                    <div className="flex items-center gap-2 py-4 text-muted-foreground text-xs font-mono">
                                        <Loader2 size={14} className="animate-spin" /> Loading financial data…
                                    </div>
                                ) : monthlyData ? (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border">
                                        {[
                                            { label: 'Gross Sales', value: fmtCurrency(monthlyData.gross_total), sub: `${monthlyData.session_count} bill(s)`, color: 'text-foreground' },
                                            { label: 'Discounts', value: `−${fmtCurrency(monthlyData.discount_amount)}`, sub: 'Applied', color: 'text-[#F26A4B]' },
                                            { label: 'Net Revenue', value: fmtCurrency(monthlyData.net_total), sub: 'Collected', color: 'text-foreground' },
                                            { label: 'Gross Profit', value: fmtCurrency(monthlyData.gross_profit), sub: `${monthlyData.margin_pct}% margin`, color: 'text-foreground' },
                                        ].map((m) => (
                                            <div key={m.label} className="bg-card p-4">
                                                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide font-mono">{m.label}</p>
                                                <p className={`font-mono text-base font-bold mt-1 ${m.color}`}>{m.value}</p>
                                                <p className="text-[10px] text-muted-foreground mt-0.5">{m.sub}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : null}
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div>
                                    <label className={labelCls}>
                                        <MapPin size={12} /> Location
                                    </label>
                                    <select
                                        className={inputCls}
                                        value={locationId}
                                        onChange={(e) => setLocationId(e.target.value)}
                                        disabled={locLoading}
                                    >
                                        <option value="">
                                            {locLoading ? 'Loading…' : 'All Locations'}
                                        </option>
                                        {Object.entries(grouped).map(([type, locs]) => (
                                            <optgroup key={type} label={LOCATION_TYPE_LABELS[type] ?? type}>
                                                {locs.map(loc => (
                                                    <option key={loc.id} value={loc.id}>{loc.name}</option>
                                                ))}
                                            </optgroup>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className={labelCls}>
                                        <Calendar size={12} /> From Date
                                    </label>
                                    <input
                                        type="date"
                                        className={inputCls}
                                        value={dateFrom}
                                        onChange={(e) => setDateFrom(e.target.value)}
                                    />
                                </div>

                                <div>
                                    <label className={labelCls}>
                                        <Calendar size={12} /> To Date
                                    </label>
                                    <input
                                        type="date"
                                        className={inputCls}
                                        value={dateTo}
                                        onChange={(e) => setDateTo(e.target.value)}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Download Button */}
                        <div className="pt-2 border-t border-border">
                            <button
                                onClick={handleDownload}
                                disabled={loading}
                                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-black text-primary-foreground text-sm font-semibold rounded-none border border-primary transition disabled:opacity-40 cursor-pointer"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 size={15} className="animate-spin" />
                                        <span>Generating…</span>
                                    </>
                                ) : (
                                    <>
                                        <Download size={15} />
                                        <span>Generate &amp; Download PDF</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Report Delivery Info */}
                <div className="bg-card border border-border rounded-none px-6 py-4">
                    <h3 className="font-sans text-sm font-bold text-foreground mb-1">Report Delivery &amp; Archiving</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        All compiled PDF audit reports are cryptographically timestamped and archived for compliance.
                        Monthly reports aggregate closed billing sessions in real time.
                    </p>
                </div>

            </div>
        </div>
    );
};

export default Reports;