import React, { useState, useEffect } from 'react';
import { admin, inventory } from '../../services/api';
import { Download, FileText, MapPin, Calendar } from 'lucide-react';

const LOCATION_TYPE_LABELS = {
    central_warehouse: '🏭 Warehouse',
    retail_pharmacy:   '💊 Retail Pharmacy',
    hospital_client:   '🏥 Hospital',
};

const Reports = () => {
    const [loading, setLoading]       = useState(false);
    const [reportType, setReportType] = useState('inventory');
    const [locationId, setLocationId] = useState('');
    const [dateFrom, setDateFrom]     = useState('');
    const [dateTo, setDateTo]         = useState('');
    const [locations, setLocations]   = useState([]);
    const [locLoading, setLocLoading] = useState(true);

    // ── Fetch real locations from the database ────────────────────────────────
    useEffect(() => {
        const fetchLocations = async () => {
            try {
                const res = await inventory.getLocations();
                const data = res.data?.data ?? res.data ?? [];
                // Support both array and paginated {items:[]} shapes
                setLocations(Array.isArray(data) ? data : (data.items ?? []));
            } catch (err) {
                console.error('Failed to load locations', err);
            } finally {
                setLocLoading(false);
            }
        };
        fetchLocations();
    }, []);

    const handleDownload = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (locationId) params.append('location_id', locationId);
            if (dateFrom)   params.append('date_from', dateFrom);
            if (dateTo)     params.append('date_to', dateTo);

            // Backend streams the PDF directly as a blob — don't parse as JSON
            const response = await admin.generateReport(reportType, params.toString());

            // Create a temporary object URL and trigger browser download
            const blob = new Blob([response.data], { type: 'application/pdf' });
            const url  = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href     = url;
            link.download = `inviq_${reportType}_report_${new Date().toISOString().slice(0,10)}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Report generation failed', err);
            alert('Failed to generate report. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const reportTypes = [
        { value: 'inventory',     label: 'Inventory Report',    desc: 'Current stock levels across all locations' },
        { value: 'transactions',  label: 'Transaction Report',  desc: 'All stock movements and transactions' },
        { value: 'requisitions',  label: 'Requisition Report',  desc: 'All requisitions and approvals' },
        { value: 'low_stock',     label: 'Low Stock Report',    desc: 'Items below minimum threshold' },
    ];

    // Group locations by type for the optgroup dropdown
    const grouped = locations.reduce((acc, loc) => {
        const key = loc.location_type || loc.type || 'other';
        if (!acc[key]) acc[key] = [];
        acc[key].push(loc);
        return acc;
    }, {});

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-slate-900">Reports</h2>
                <p className="text-slate-500">Generate and download various inventory reports</p>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Generate Report</h3>

                <div className="space-y-4">
                    {/* Report Type */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Report Type</label>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {reportTypes.map(type => (
                                <button
                                    key={type.value}
                                    onClick={() => setReportType(type.value)}
                                    className={`p-4 rounded-xl border text-left transition ${
                                        reportType === type.value
                                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                                            : 'border-slate-200 hover:border-slate-300'
                                    }`}
                                >
                                    <div className="font-medium">{type.label}</div>
                                    <div className="text-xs text-slate-500 mt-1">{type.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Location dropdown — fetched from DB */}
                        <div>
                            <label className="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                                <MapPin size={13} /> Location (optional)
                            </label>
                            <select
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                value={locationId}
                                onChange={(e) => setLocationId(e.target.value)}
                                disabled={locLoading}
                            >
                                <option value="">
                                    {locLoading ? 'Loading locations…' : 'All Locations'}
                                </option>

                                {Object.entries(grouped).map(([type, locs]) => (
                                    <optgroup
                                        key={type}
                                        label={LOCATION_TYPE_LABELS[type] ?? type}
                                    >
                                        {locs.map(loc => (
                                            <option key={loc.id} value={loc.id}>
                                                {loc.name}
                                            </option>
                                        ))}
                                    </optgroup>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                                <Calendar size={13} /> From Date
                            </label>
                            <input
                                type="date"
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                value={dateFrom}
                                onChange={(e) => setDateFrom(e.target.value)}
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                                <Calendar size={13} /> To Date
                            </label>
                            <input
                                type="date"
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                value={dateTo}
                                onChange={(e) => setDateTo(e.target.value)}
                            />
                        </div>
                    </div>

                    <button
                        onClick={handleDownload}
                        disabled={loading}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                    >
                        {loading ? (
                            <span className="animate-pulse">Generating PDF…</span>
                        ) : (
                            <>
                                <Download size={18} />
                                Generate &amp; Download PDF
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Recent Reports</h3>
                <p className="text-slate-400 text-sm">No recent reports. Generate your first report above.</p>
            </div>
        </div>
    );
};

export default Reports;