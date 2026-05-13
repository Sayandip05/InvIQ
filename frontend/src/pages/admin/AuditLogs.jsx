import React, { useState, useEffect } from 'react';
import { admin } from '../../services/api';
import { Search, Clock, User, Shield, AlertTriangle, CheckCircle, XCircle, LogIn, LogOut, Trash2, Edit, RefreshCw } from 'lucide-react';

// Maps the backend action strings to badge colours and icons
const ACTION_CONFIG = {
    LOGIN_SUCCESS:          { label: 'Login',         color: 'bg-blue-50 text-blue-700 ring-blue-200',     icon: LogIn },
    LOGOUT:                 { label: 'Logout',        color: 'bg-slate-100 text-slate-600 ring-slate-200', icon: LogOut },
    USER_CREATED:           { label: 'User Created',  color: 'bg-green-50 text-green-700 ring-green-200',  icon: User },
    USER_DELETED:           { label: 'User Deleted',  color: 'bg-red-50 text-red-700 ring-red-200',        icon: Trash2 },
    USER_ACTIVATED:         { label: 'Activated',     color: 'bg-emerald-50 text-emerald-700 ring-emerald-200', icon: CheckCircle },
    USER_DEACTIVATED:       { label: 'Deactivated',   color: 'bg-orange-50 text-orange-700 ring-orange-200', icon: XCircle },
    ROLE_CHANGED:           { label: 'Role Changed',  color: 'bg-purple-50 text-purple-700 ring-purple-200', icon: Shield },
    PASSWORD_CHANGED:       { label: 'Pwd Changed',   color: 'bg-yellow-50 text-yellow-700 ring-yellow-200', icon: Edit },
    PASSWORD_RESET_BY_ADMIN:{ label: 'Pwd Reset',     color: 'bg-yellow-50 text-yellow-700 ring-yellow-200', icon: RefreshCw },
    PROFILE_UPDATED:        { label: 'Profile Edit',  color: 'bg-sky-50 text-sky-700 ring-sky-200',        icon: Edit },
    ACCOUNT_LOCKED:         { label: 'Acct Locked',   color: 'bg-red-50 text-red-700 ring-red-200',        icon: AlertTriangle },
};

const FILTER_OPTIONS = [
    { value: '',                  label: 'All Actions' },
    { value: 'LOGIN_SUCCESS',     label: 'Login' },
    { value: 'LOGOUT',            label: 'Logout' },
    { value: 'USER_CREATED',      label: 'User Created' },
    { value: 'USER_DELETED',      label: 'User Deleted' },
    { value: 'ROLE_CHANGED',      label: 'Role Changed' },
    { value: 'PASSWORD_CHANGED',  label: 'Password Changed' },
    { value: 'ACCOUNT_LOCKED',    label: 'Account Locked' },
];

/** Safely serialize a log.details value (may be a JSON object or string) */
function formatDetails(details) {
    if (!details) return '-';
    if (typeof details === 'string') return details;
    // It's a JSON object — render key: value pairs as a readable string
    return Object.entries(details)
        .map(([k, v]) => `${k}: ${v}`)
        .join(' · ');
}

/** Safely convert a details value to a string for searching */
function detailsToString(details) {
    if (!details) return '';
    if (typeof details === 'string') return details.toLowerCase();
    return JSON.stringify(details).toLowerCase();
}

const AuditLogs = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');
    const [actionFilter, setActionFilter] = useState('');

    const loadLogs = async () => {
        setLoading(true);
        setError('');
        try {
            const params = { limit: 200 };
            if (actionFilter) params.action = actionFilter;
            const res = await admin.auditLogs(params);
            if (res.data.success) {
                setLogs(res.data.data);
            }
        } catch (err) {
            const msg =
                err.response?.data?.error?.message ||
                err.response?.data?.detail ||
                'Failed to load audit logs';
            setError(msg);
            console.error('Failed to load audit logs', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadLogs(); }, [actionFilter]);

    // Client-side search — safely handles details being an object or string
    const filteredLogs = logs.filter(log => {
        const term = searchTerm.toLowerCase();
        if (!term) return true;
        return (
            log.username?.toLowerCase().includes(term) ||
            log.action?.toLowerCase().includes(term) ||
            log.resource_type?.toLowerCase().includes(term) ||
            log.ip_address?.toLowerCase().includes(term) ||
            detailsToString(log.details).includes(term)
        );
    });

    const getActionBadge = (action) => {
        const cfg = ACTION_CONFIG[action];
        const Icon = cfg?.icon || Activity;
        const label = cfg?.label || action?.replace(/_/g, ' ') || '—';
        const color = cfg?.color || 'bg-slate-100 text-slate-600 ring-slate-200';
        return (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ring-1 ${color}`}>
                <Icon size={11} />
                {label}
            </span>
        );
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900">Audit Logs</h2>
                    <p className="text-slate-500 text-sm mt-1">Track all system activities and user actions</p>
                </div>
                <button
                    onClick={loadLogs}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition text-sm font-medium shadow-sm"
                >
                    <RefreshCw size={15} />
                    Refresh
                </button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                {/* Filters */}
                <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row gap-3">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            type="text"
                            placeholder="Search by user, action, IP..."
                            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <select
                        className="px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 text-sm text-slate-700"
                        value={actionFilter}
                        onChange={(e) => setActionFilter(e.target.value)}
                    >
                        {FILTER_OPTIONS.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>

                {/* Error state */}
                {error && (
                    <div className="m-4 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                        <AlertTriangle size={16} />
                        {error}
                    </div>
                )}

                {/* Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                            <tr>
                                <th className="px-6 py-3">Timestamp</th>
                                <th className="px-6 py-3">User</th>
                                <th className="px-6 py-3">Action</th>
                                <th className="px-6 py-3">Resource</th>
                                <th className="px-6 py-3">Details</th>
                                <th className="px-6 py-3">IP Address</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading ? (
                                <tr>
                                    <td colSpan="6" className="text-center py-16 text-slate-400">
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-blue-500" />
                                            <span className="text-sm">Loading logs...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : filteredLogs.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="text-center py-16 text-slate-400">
                                        <div className="flex flex-col items-center gap-2">
                                            <Shield size={32} className="opacity-30" />
                                            <span className="text-sm">No audit logs found</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredLogs.map((log) => (
                                    <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-3 text-xs text-slate-500 whitespace-nowrap">
                                            <div className="flex items-center gap-1.5">
                                                <Clock size={12} className="text-slate-400" />
                                                {log.created_at
                                                    ? new Date(log.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
                                                    : '—'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-2">
                                                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold uppercase">
                                                    {log.username?.[0] || '?'}
                                                </div>
                                                <span className="text-sm font-medium text-slate-700">{log.username || 'System'}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            {getActionBadge(log.action)}
                                        </td>
                                        <td className="px-6 py-3 text-xs text-slate-500">
                                            {log.resource_type
                                                ? <span className="capitalize">{log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}</span>
                                                : '—'}
                                        </td>
                                        <td className="px-6 py-3 text-xs text-slate-500 max-w-xs">
                                            <span className="truncate block" title={formatDetails(log.details)}>
                                                {formatDetails(log.details)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3 text-xs text-slate-400 font-mono">
                                            {log.ip_address || '—'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Footer count */}
                {!loading && !error && (
                    <div className="px-6 py-3 border-t border-slate-100 text-xs text-slate-400">
                        Showing {filteredLogs.length} of {logs.length} records
                    </div>
                )}
            </div>
        </div>
    );
};

// Fallback icon used if ACTION_CONFIG has no entry
function Activity({ size = 16 }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
}

export default AuditLogs;