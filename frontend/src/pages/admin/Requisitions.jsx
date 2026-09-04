import React, { useState, useEffect } from 'react';
import { requisition } from '../../services/api';
import { ClipboardCheck, ClipboardX, ChevronDown, ChevronUp, AlertTriangle, Clock, CheckCircle2, XCircle, Filter, Lock } from 'lucide-react';
import { useGuest } from '../../context/GuestContext';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

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
    const { isGuest, showAuthModal } = useGuest();
    const [requests, setRequests] = useState([]);
    const [stats, setStats] = useState(null);
    const [filter, setFilter] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const [approverName, setApproverName] = useState('');
    const [rejectReason, setRejectReason] = useState('');
    const [actionLoading, setActionLoading] = useState(null);
    const [showRejectModal, setShowRejectModal] = useState(null);

    const loadData = async () => {
        try {
            const [reqRes, statRes] = await Promise.all([
                requisition.list(),
                requisition.stats(),
            ]);
            if (reqRes.data.success) {
                setRequests(reqRes.data.data);
            }
            if (statRes.data.success) {
                setStats(statRes.data.data);
            }
        } catch (err) {
            console.error('Failed to load requisition data', err);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleApprove = async (id) => {
        if (isGuest) {
            showAuthModal('Sign in to approve stock requisitions.');
            return;
        }
        setActionLoading(id);
        try {
            const res = await requisition.approve(id, {
                approver_name: approverName || 'Store Admin',
            });
            if (res.data.success) {
                loadData();
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Approval failed');
        } finally {
            setActionLoading(null);
        }
    };

    const handleReject = async (id) => {
        if (isGuest) {
            showAuthModal('Sign in to reject stock requisitions.');
            return;
        }
        setActionLoading(id);
        try {
            const res = await requisition.reject(id, {
                approver_name: approverName || 'Store Admin',
                reason: rejectReason || 'Stock unavailable',
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
        <div className="flex flex-col min-h-full bg-background text-foreground">
            {/* Full-Width Top Navbar */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Requisitions & Orders</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">Manage dispensary stock fulfillment requests and approvals</p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <span className="font-semibold text-foreground">Approver:</span>
                            <input
                                type="text"
                                placeholder="Store Admin"
                                className="px-2.5 py-1.5 border border-input rounded-md text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring w-32"
                                value={approverName}
                                onChange={(e) => setApproverName(e.target.value)}
                            />
                        </div>

                        {/* Notification Alerts Bell Dropdown */}
                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            {/* Page Content Container */}
            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">
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
                <div className="flex gap-1 bg-card rounded-lg p-1 shadow-xs border border-border">
                    {['', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'].map(s => (
                        <button
                            key={s}
                            onClick={() => setFilter(s)}
                            className={`flex-1 py-2 rounded-md text-xs font-medium transition cursor-pointer ${filter === s ? 'bg-primary text-primary-foreground font-bold shadow-2xs' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}
                        >
                            {s || 'ALL'}
                        </button>
                    ))}
                </div>

                {/* Requisition List */}
                <div className="space-y-3">
                    {requests.length === 0 && (
                        <div className="bg-card border border-border rounded-lg shadow-xs p-12 text-center text-muted-foreground">
                            <ClipboardCheck size={40} className="mx-auto mb-3 text-muted-foreground/60" />
                            No requisitions found.
                        </div>
                    )}

                    {requests.map(req => {
                        const isExpanded = expandedId === req.id;
                        return (
                            <div key={req.id} className={`bg-card rounded-lg shadow-xs border transition ${req.urgency === 'EMERGENCY' && req.status === 'PENDING' ? 'border-destructive ring-1 ring-destructive/20' : 'border-border'}`}>
                                {/* Summary Row */}
                                <button
                                    onClick={() => setExpandedId(isExpanded ? null : req.id)}
                                    className="w-full p-4 flex items-center justify-between text-left cursor-pointer"
                                >
                                    <div className="flex items-center gap-3 flex-wrap">
                                        <span className="font-semibold text-foreground text-sm font-mono">{req.requisition_number}</span>
                                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_STYLES[req.status]}`}>{req.status}</span>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${URGENCY_STYLES[req.urgency]}`}>{req.urgency}</span>
                                        <span className="text-xs text-muted-foreground">•</span>
                                        <span className="text-xs text-muted-foreground">{req.department}</span>
                                        <span className="text-xs text-muted-foreground">•</span>
                                        <span className="text-xs text-muted-foreground">{req.location_name}</span>
                                        <span className="text-xs text-muted-foreground">•</span>
                                        <span className="text-xs text-muted-foreground">by {req.requested_by}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-xs text-muted-foreground font-mono">{new Date(req.created_at).toLocaleDateString()}</span>
                                        {isExpanded ? <ChevronUp size={16} className="text-muted-foreground" /> : <ChevronDown size={16} className="text-muted-foreground" />}
                                    </div>
                                </button>

                                {/* Expanded Detail */}
                                {isExpanded && (
                                    <div className="border-t border-border p-4 bg-muted/20">
                                        {/* Notes */}
                                        {req.notes && (
                                            <div className="mb-4 p-3 bg-accent border border-border rounded-md text-sm text-foreground">
                                                <strong>Notes:</strong> {req.notes}
                                            </div>
                                        )}

                                        {/* Rejection reason */}
                                        {req.rejection_reason && (
                                            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md text-sm text-destructive flex items-start gap-2">
                                                <XCircle size={16} className="mt-0.5 shrink-0" />
                                                <div><strong>Rejected by {req.approved_by}:</strong> {req.rejection_reason}</div>
                                            </div>
                                        )}

                                        {/* Items Table */}
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-xs text-muted-foreground border-b border-border font-mono">
                                                    <th className="text-left py-2 font-medium">Item</th>
                                                    <th className="text-center py-2 font-medium">Unit</th>
                                                    <th className="text-center py-2 font-medium">Requested</th>
                                                    <th className="text-center py-2 font-medium">Approved</th>
                                                    <th className="text-left py-2 font-medium">Notes</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {req.items.map(item => (
                                                    <tr key={item.id} className="border-b border-border/50 last:border-0">
                                                        <td className="py-2.5 font-medium text-foreground">{item.item_name}</td>
                                                        <td className="py-2.5 text-center text-muted-foreground">{item.item_unit}</td>
                                                        <td className="py-2.5 text-center font-semibold text-foreground">{item.quantity_requested}</td>
                                                        <td className="py-2.5 text-center font-semibold text-foreground">{item.quantity_approved ?? '—'}</td>
                                                        <td className="py-2.5 text-muted-foreground text-xs">{item.notes || '—'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>

                                        {/* Actions (only for PENDING) */}
                                        {req.status === 'PENDING' && (
                                            <div className="flex items-center gap-3 mt-4 pt-4 border-t border-border">
                                                {showRejectModal === req.id ? (
                                                    <div className="flex items-center gap-2 flex-1">
                                                        <input
                                                            type="text"
                                                            placeholder="Rejection reason (min 5 chars)..."
                                                            className="flex-1 px-3 py-2 border border-destructive/30 bg-background text-foreground rounded-none text-sm focus:ring-1 focus:ring-primary outline-none"
                                                            value={rejectReason}
                                                            onChange={(e) => setRejectReason(e.target.value)}
                                                        />
                                                        <button
                                                            onClick={() => handleReject(req.id)}
                                                            disabled={actionLoading === req.id}
                                                            className="px-4 py-2 bg-destructive text-destructive-foreground rounded-none text-sm font-medium hover:opacity-90 transition disabled:opacity-70 cursor-pointer"
                                                        >
                                                            Confirm
                                                        </button>
                                                        <button
                                                            onClick={() => { setShowRejectModal(null); setRejectReason(''); }}
                                                            className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground cursor-pointer"
                                                        >
                                                            Cancel
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <>
                                                        <button
                                                            onClick={() => handleApprove(req.id)}
                                                            disabled={actionLoading === req.id || !approverName.trim()}
                                                            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-none text-sm font-medium hover:bg-black transition shadow-sm disabled:opacity-50 cursor-pointer"
                                                        >
                                                            <ClipboardCheck size={16} />
                                                            {actionLoading === req.id ? 'Processing...' : 'Approve & Deduct Stock'}
                                                        </button>
                                                        <button
                                                            onClick={() => setShowRejectModal(req.id)}
                                                            disabled={!approverName.trim()}
                                                            className="flex items-center gap-2 px-5 py-2.5 bg-card border border-destructive/30 text-destructive rounded-none text-sm font-medium hover:bg-destructive/10 transition disabled:opacity-50 cursor-pointer"
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
