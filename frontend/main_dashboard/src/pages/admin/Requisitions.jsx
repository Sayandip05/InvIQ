import React, { useState, useEffect } from 'react';
import { requisition } from '../../services/api';
import { ClipboardCheck, ClipboardX, ChevronDown, ChevronUp, AlertTriangle, Clock, CheckCircle2, XCircle, Filter } from 'lucide-react';

const STATUS_STYLES = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    CANCELLED: 'bg-gray-100 text-gray-500',
};

const URGENCY_STYLES = {
    LOW: 'bg-slate-100 text-slate-600',
    NORMAL: 'bg-blue-100 text-blue-700',
    HIGH: 'bg-orange-100 text-orange-700',
    EMERGENCY: 'bg-red-100 text-red-700 font-bold',
};

const Requisitions = () => {
    const [requests, setRequests] = useState([]);
    const [stats, setStats] = useState(null);
    const [filter, setFilter] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const [approverName, setApproverName] = useState('');
    const [rejectReason, setRejectReason] = useState('');
    const [actionLoading, setActionLoading] = useState(null);
    const [showRejectModal, setShowRejectModal] = useState(null);

    useEffect(() => {
        loadData();
    }, [filter]);

    const loadData = async () => {
        try {
            const params = filter ? { status: filter } : {};
            const [reqRes, statsRes] = await Promise.all([
                requisition.list(params),
                requisition.stats(),
            ]);
            if (reqRes.data.success) setRequests(reqRes.data.data);
            if (statsRes.data.success) setStats(statsRes.data.data);
        } catch (err) {
            console.error('Failed to load requisitions', err);
        }
    };

    const handleApprove = async (id) => {
        if (!approverName.trim()) return alert('Enter your name first.');
        setActionLoading(id);
        try {
            const res = await requisition.approve(id, { approved_by: approverName.trim() });
            if (res.data.success) loadData();
        } catch (err) {
            alert(err.response?.data?.detail || 'Approval failed');
        } finally {
            setActionLoading(null);
        }
    };

    const handleReject = async (id) => {
        if (!approverName.trim()) return alert('Enter your name first.');
        if (!rejectReason.trim() || rejectReason.trim().length < 5) return alert('Provide a rejection reason (min 5 chars).');
        setActionLoading(id);
        try {
            const res = await requisition.reject(id, {
                rejected_by: approverName.trim(),
                reason: rejectReason.trim(),
            });
            if (res.data.success) {
                setShowRejectModal(null);
                setRejectReason('');
                loadData();
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Rejection failed');
        } finally {
            setActionLoading(null);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Requisitions</h1>
                    <p className="text-sm text-slate-500">Review and approve stock-out requests</p>
                </div>
                <div className="flex items-center gap-3">
                    <label className="text-sm text-slate-500">Your Name:</label>
                    <input
                        type="text"
                        placeholder="Store Manager"
                        className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-40"
                        value={approverName}
                        onChange={(e) => setApproverName(e.target.value)}
                    />
                </div>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <StatCard label="Total" value={stats.total} color="slate" />
                    <StatCard label="Pending" value={stats.pending} color="yellow" />
                    <StatCard label="Approved Today" value={stats.approved_today} color="green" />
                    <StatCard label="Rejected" value={stats.rejected} color="red" />
                    <StatCard label="🚨 Emergency" value={stats.emergency_pending} color="red" highlight />
                </div>
            )}

            {/* Filter Tabs */}
            <div className="flex gap-1 bg-white rounded-xl p-1 shadow-sm border border-slate-100">
                {['', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'].map(s => (
                    <button
                        key={s}
                        onClick={() => setFilter(s)}
                        className={`flex-1 py-2 rounded-lg text-xs font-medium transition ${filter === s ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50'}`}
                    >
                        {s || 'ALL'}
                    </button>
                ))}
            </div>

            {/* Requisition List */}
            <div className="space-y-3">
                {requests.length === 0 && (
                    <div className="bg-white rounded-xl shadow-sm p-12 text-center text-slate-400">
                        <ClipboardCheck size={40} className="mx-auto mb-3 text-slate-300" />
                        No requisitions found.
                    </div>
                )}

                {requests.map(req => {
                    const isExpanded = expandedId === req.id;
                    return (
                        <div key={req.id} className={`bg-white rounded-xl shadow-sm border transition ${req.urgency === 'EMERGENCY' && req.status === 'PENDING' ? 'border-red-300 ring-1 ring-red-100' : 'border-slate-100'}`}>
                            {/* Summary Row */}
                            <button
                                onClick={() => setExpandedId(isExpanded ? null : req.id)}
                                className="w-full p-4 flex items-center justify-between text-left"
                            >
                                <div className="flex items-center gap-3 flex-wrap">
                                    <span className="font-semibold text-slate-800 text-sm">{req.requisition_number}</span>
                                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_STYLES[req.status]}`}>{req.status}</span>
                                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${URGENCY_STYLES[req.urgency]}`}>{req.urgency}</span>
                                    <span className="text-xs text-slate-400">•</span>
                                    <span className="text-xs text-slate-500">{req.department}</span>
                                    <span className="text-xs text-slate-400">•</span>
                                    <span className="text-xs text-slate-500">{req.location_name}</span>
                                    <span className="text-xs text-slate-400">•</span>
                                    <span className="text-xs text-slate-500">by {req.requested_by}</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-xs text-slate-400">{new Date(req.created_at).toLocaleDateString()}</span>
                                    {isExpanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                                </div>
                            </button>

                            {/* Expanded Detail */}
                            {isExpanded && (
                                <div className="border-t border-slate-100 p-4 bg-slate-50/50">
                                    {/* Notes */}
                                    {req.notes && (
                                        <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
                                            <strong>Notes:</strong> {req.notes}
                                        </div>
                                    )}

                                    {/* Rejection reason */}
                                    {req.rejection_reason && (
                                        <div className="mb-4 p-3 bg-red-50 rounded-lg text-sm text-red-700 flex items-start gap-2">
                                            <XCircle size={16} className="mt-0.5 shrink-0" />
                                            <div><strong>Rejected by {req.approved_by}:</strong> {req.rejection_reason}</div>
                                        </div>
                                    )}

                                    {/* Items Table */}
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="text-xs text-slate-500 border-b border-slate-200">
                                                <th className="text-left py-2 font-medium">Item</th>
                                                <th className="text-center py-2 font-medium">Unit</th>
                                                <th className="text-center py-2 font-medium">Requested</th>
                                                <th className="text-center py-2 font-medium">Approved</th>
                                                <th className="text-left py-2 font-medium">Notes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {req.items.map(item => (
                                                <tr key={item.id} className="border-b border-slate-100 last:border-0">
                                                    <td className="py-2.5 font-medium text-slate-700">{item.item_name}</td>
                                                    <td className="py-2.5 text-center text-slate-500">{item.item_unit}</td>
                                                    <td className="py-2.5 text-center font-semibold">{item.quantity_requested}</td>
                                                    <td className="py-2.5 text-center font-semibold text-green-600">{item.quantity_approved ?? '—'}</td>
                                                    <td className="py-2.5 text-slate-400 text-xs">{item.notes || '—'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>

                                    {/* Actions (only for PENDING) */}
                                    {req.status === 'PENDING' && (
                                        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-slate-200">
                                            {showRejectModal === req.id ? (
                                                <div className="flex items-center gap-2 flex-1">
                                                    <input
                                                        type="text"
                                                        placeholder="Rejection reason (min 5 chars)..."
                                                        className="flex-1 px-3 py-2 border border-red-200 rounded-lg text-sm focus:ring-2 focus:ring-red-300 outline-none"
                                                        value={rejectReason}
                                                        onChange={(e) => setRejectReason(e.target.value)}
                                                    />
                                                    <button
                                                        onClick={() => handleReject(req.id)}
                                                        disabled={actionLoading === req.id}
                                                        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-70"
                                                    >
                                                        Confirm
                                                    </button>
                                                    <button
                                                        onClick={() => { setShowRejectModal(null); setRejectReason(''); }}
                                                        className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            ) : (
                                                <>
                                                    <button
                                                        onClick={() => handleApprove(req.id)}
                                                        disabled={actionLoading === req.id || !approverName.trim()}
                                                        className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition shadow-sm disabled:opacity-50"
                                                    >
                                                        <ClipboardCheck size={16} />
                                                        {actionLoading === req.id ? 'Processing...' : 'Approve & Deduct Stock'}
                                                    </button>
                                                    <button
                                                        onClick={() => setShowRejectModal(req.id)}
                                                        disabled={!approverName.trim()}
                                                        className="flex items-center gap-2 px-5 py-2.5 bg-white border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition disabled:opacity-50"
                                                    >
                                                        <ClipboardX size={16} /> Reject
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    )}

                                    {/* Approval info */}
                                    {req.status === 'APPROVED' && req.approved_by && (
                                        <div className="mt-3 text-xs text-green-600 flex items-center gap-1">
                                            <CheckCircle2 size={14} /> Approved by {req.approved_by}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// Stat Card Component
const StatCard = ({ label, value, color, highlight }) => {
    const colors = {
        slate: 'bg-white',
        yellow: 'bg-yellow-50 border-yellow-100',
        green: 'bg-green-50 border-green-100',
        red: highlight ? 'bg-red-50 border-red-200 ring-1 ring-red-100' : 'bg-red-50 border-red-100',
    };

    return (
        <div className={`rounded-xl p-4 border shadow-sm ${colors[color]}`}>
            <div className="text-2xl font-bold text-slate-800">{value}</div>
            <div className="text-xs text-slate-500 mt-1">{label}</div>
        </div>
    );
};

export default Requisitions;
