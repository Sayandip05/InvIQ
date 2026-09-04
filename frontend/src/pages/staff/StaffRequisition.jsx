import React, { useState, useEffect } from 'react';
import { inventory, requisition } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import {
  Plus, Trash2, Send, ClipboardList, Clock, CheckCircle2, XCircle,
  Building2, User, LogOut, ScanBarcode, AlertTriangle, ShieldCheck
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

const URGENCY_OPTIONS = ['LOW', 'NORMAL', 'HIGH', 'EMERGENCY'];
const DEPARTMENTS = ['Pharmacy Counter', 'Emergency', 'ICU', 'Cardiology', 'General Ward', 'OT', 'Pediatrics', 'Oncology', 'Lab'];

const STATUS_STYLES = {
    PENDING: 'bg-amber-500/10 text-amber-800 border border-amber-500/30 font-semibold',
    APPROVED: 'bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 font-semibold',
    REJECTED: 'bg-destructive/10 text-destructive border border-destructive/30 font-semibold',
    CANCELLED: 'bg-accent/50 text-muted-foreground border border-border',
};

const URGENCY_STYLES = {
    LOW: 'bg-accent/50 text-foreground border border-border',
    NORMAL: 'bg-primary text-primary-foreground border border-primary',
    HIGH: 'bg-amber-500/20 text-amber-900 border border-amber-500/40 font-bold',
    EMERGENCY: 'bg-[#F26A4B] text-white border border-[#F26A4B] font-bold animate-pulse',
};

const StaffRequisition = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [locations, setLocations] = useState([]);
    const [items, setItems] = useState([]);
    const [myRequests, setMyRequests] = useState([]);
    const [activeTab, setActiveTab] = useState('form'); // 'form' | 'history'
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);

    const [form, setForm] = useState({
        location_id: '',
        department: 'Pharmacy Counter',
        urgency: 'NORMAL',
        requested_by: user?.full_name || user?.username || 'Staff Pharmacist',
        notes: '',
        items: [{ item_id: '', quantity: 1, packaging_unit: '', notes: '' }],
    });

    useEffect(() => {
        if (user) {
            setForm(prev => ({
                ...prev,
                requested_by: user.full_name || user.username || 'Staff Pharmacist'
            }));
        }
    }, [user]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [locRes, itemRes] = await Promise.all([
                    inventory.getLocations(),
                    inventory.getItems(),
                ]);
                if (locRes.data.success) {
                    const locs = locRes.data.data;
                    setLocations(locs);
                    if (locs.length > 0 && !form.location_id) {
                        setForm(prev => ({ ...prev, location_id: locs[0].id }));
                    }
                }
                if (itemRes.data.success) setItems(itemRes.data.data);
            } catch (err) {
                console.error('Failed to fetch data', err);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        if (activeTab === 'history' && form.requested_by) {
            loadHistory();
        }
    }, [activeTab]);

    const loadHistory = async () => {
        try {
            const res = await requisition.list({ requested_by: form.requested_by });
            if (res.data.success) setMyRequests(res.data.data);
        } catch (err) {
            console.error('Failed to load history', err);
        }
    };

    const addItemRow = () => {
        setForm(prev => ({
            ...prev,
            items: [...prev.items, { item_id: '', quantity: 1, packaging_unit: '', notes: '' }],
        }));
    };

    const removeItemRow = (index) => {
        if (form.items.length === 1) return;
        setForm(prev => ({
            ...prev,
            items: prev.items.filter((_, idx) => idx !== index),
        }));
    };

    const updateItemRow = (index, field, value) => {
        const newItems = [...form.items];
        newItems[index][field] = value;
        setForm(prev => ({ ...prev, items: newItems }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(null);

        // Validation
        const validItems = form.items.filter(i => i.item_id && i.quantity > 0);
        if (validItems.length === 0) {
            setError('Please add at least one valid item with a quantity.');
            setLoading(false);
            return;
        }

        try {
            const payload = {
                ...form,
                location_id: parseInt(form.location_id),
                items: validItems.map(i => ({
                    item_id: parseInt(i.item_id),
                    quantity: parseInt(i.quantity),
                    packaging_unit: i.packaging_unit ? String(i.packaging_unit).trim() : null,
                    notes: i.notes,
                })),
            };

            const res = await requisition.create(payload);
            if (res.data.success) {
                setSuccess(`Requisition ${res.data.data.requisition_number} submitted successfully!`);
                setForm({
                    location_id: locations[0]?.id || '',
                    department: 'Pharmacy Counter',
                    urgency: 'NORMAL',
                    requested_by: user?.full_name || user?.username || 'Staff Pharmacist',
                    notes: '',
                    items: [{ item_id: '', quantity: 1, packaging_unit: '', notes: '' }],
                });
                setTimeout(() => setSuccess(null), 5000);
            }
        } catch (err) {
            setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to submit requisition.');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = async (id) => {
        if (!window.confirm('Are you sure you want to cancel this requisition?')) return;
        try {
            const res = await requisition.cancel(id);
            if (res.data.success) {
                loadHistory();
            }
        } catch (err) {
            alert(err.response?.data?.error?.message || 'Failed to cancel requisition');
        }
    };

    const handleLogout = async () => {
        await logout();
        navigate('/signin');
    };

    return (
        <div className="min-h-screen bg-background text-foreground p-4 md:p-8 font-sans">
            <div className="max-w-5xl mx-auto space-y-6">

                {/* ── Top Header / User Context Bar (Warm Editorial Theme) ──────────────── */}
                <div className="bg-card border border-border p-5 rounded-none shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <img
                            src="/logo.png"
                            alt="InvIQ Logo"
                            className="w-9 h-9 object-contain shrink-0"
                        />
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 bg-primary text-primary-foreground text-[10px] font-bold uppercase tracking-wider rounded-none">
                                    Staff Portal
                                </span>
                                <span className="text-xs text-border">|</span>
                                <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                                    <Building2 size={13} className="text-foreground" />
                                    <span>{user?.organization_name || 'Assigned Pharmacy Network'}</span>
                                </div>
                            </div>
                            <h1 className="text-base sm:text-lg font-sans font-bold text-foreground tracking-tight mt-0.5">
                                Medicine Requisition &amp; Stock Intake
                            </h1>
                            <p className="text-xs text-muted-foreground">
                                Operator: <strong className="text-foreground">{user?.full_name || user?.username}</strong>
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Link
                            to="/staff/billing"
                            className="flex items-center gap-1.5 px-3.5 py-2 bg-card hover:bg-accent text-foreground text-xs font-bold border border-border rounded-none transition"
                        >
                            <ScanBarcode size={14} className="text-foreground" />
                            <span>Billing Counter</span>
                        </Link>

                        <button
                            onClick={handleLogout}
                            className="flex items-center gap-1.5 px-3.5 py-2 bg-card hover:bg-destructive/10 hover:text-destructive text-muted-foreground text-xs font-semibold border border-border rounded-none transition cursor-pointer"
                        >
                            <LogOut size={14} />
                            <span>Sign Out</span>
                        </button>
                    </div>
                </div>

                {/* ── Unassigned Warning (If no org) ────────────────────── */}
                {!user?.org_id && (
                    <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-none flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                        <div>
                            <h4 className="text-xs font-bold text-amber-900">Unallocated Staff Account</h4>
                            <p className="text-xs text-amber-800 mt-0.5">
                                Your account is not yet allocated to an active Chemist Store Admin. Please ask your Pharmacy Store Owner / Admin to allocate your username (<strong>{user?.username}</strong>) in their User Management panel.
                            </p>
                        </div>
                    </div>
                )}

                {/* Navigation Tabs */}
                <div className="flex bg-card border border-border rounded-none p-1 shadow-2xs">
                    <button
                        onClick={() => setActiveTab('form')}
                        className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider transition rounded-none cursor-pointer ${
                            activeTab === 'form'
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:bg-accent/40'
                        }`}
                    >
                        <Send size={13} className="inline mr-1.5" /> New Requisition
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider transition rounded-none cursor-pointer ${
                            activeTab === 'history'
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:bg-accent/40'
                        }`}
                    >
                        <Clock size={13} className="inline mr-1.5" /> My Request History
                    </button>
                </div>

                {/* ─── NEW REQUEST FORM (Warm Editorial Theme) ─── */}
                {activeTab === 'form' && (
                    <form onSubmit={handleSubmit} className="bg-card rounded-none border border-border shadow-xs overflow-hidden">
                        <div className="p-6 border-b border-border bg-accent/20 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                                        Requester Name <span className="text-destructive">*</span>
                                    </label>
                                    <input
                                        required
                                        type="text"
                                        placeholder="e.g. Pharmacist Rahul"
                                        className="w-full px-3 py-2 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                        value={form.requested_by}
                                        onChange={(e) => setForm({ ...form, requested_by: e.target.value })}
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                                        Department <span className="text-destructive">*</span>
                                    </label>
                                    <select
                                        required
                                        className="w-full px-3 py-2 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                        value={form.department}
                                        onChange={(e) => setForm({ ...form, department: e.target.value })}
                                    >
                                        <option value="">Select Department</option>
                                        {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                                        Location / Counter <span className="text-destructive">*</span>
                                    </label>
                                    <select
                                        required
                                        className="w-full px-3 py-2 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                        value={form.location_id}
                                        onChange={(e) => setForm({ ...form, location_id: e.target.value })}
                                    >
                                        <option value="">Select Location</option>
                                        {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                                        Urgency Level
                                    </label>
                                    <div className="grid grid-cols-4 gap-1.5">
                                        {URGENCY_OPTIONS.map(u => (
                                             <button
                                                key={u}
                                                type="button"
                                                onClick={() => setForm({ ...form, urgency: u })}
                                                className={`py-2 rounded-none text-[11px] font-bold uppercase transition border cursor-pointer ${
                                                    form.urgency === u
                                                        ? URGENCY_STYLES[u]
                                                        : 'bg-card text-muted-foreground border-border hover:border-foreground/40'
                                                }`}
                                            >
                                                {u}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
                                    Notes (Optional)
                                </label>
                                <textarea
                                    rows={2}
                                    placeholder="Add batch preference, cold-chain handling note, or urgent requirements..."
                                    className="w-full px-3 py-2 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary resize-none"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                />
                            </div>
                        </div>

                        {/* Items Section */}
                        <div className="p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
                                    Requisition Medicine List
                                </h3>
                                <span className="text-[11px] text-muted-foreground">
                                    {form.items.length} Item line(s)
                                </span>
                            </div>

                            {error && (
                                <div className="p-3 bg-destructive/10 border border-destructive/30 text-destructive text-xs rounded-none">
                                    {error}
                                </div>
                            )}

                            {success && (
                                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 text-xs rounded-none flex items-center gap-2">
                                    <CheckCircle2 size={16} className="text-emerald-700 shrink-0" />
                                    <span>{success}</span>
                                </div>
                            )}

                            <div className="border border-border overflow-x-auto">
                                <table className="w-full text-left text-xs border-collapse">
                                    <thead>
                                        <tr className="bg-accent/40 border-b border-border text-foreground font-bold uppercase text-[10px]">
                                            <th className="py-2.5 px-3">Medicine / Item</th>
                                            <th className="py-2.5 px-3 w-28 text-center">Quantity</th>
                                            <th className="py-2.5 px-3 w-36">Unit (e.g. strip/box)</th>
                                            <th className="py-2.5 px-3">Line Notes</th>
                                            <th className="py-2.5 px-3 w-12 text-center">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border/50">
                                        {form.items.map((row, index) => (
                                            <tr key={index} className="hover:bg-accent/20">
                                                <td className="p-2">
                                                    <select
                                                        required
                                                        className="w-full px-2.5 py-1.5 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                                        value={row.item_id}
                                                        onChange={(e) => updateItemRow(index, 'item_id', e.target.value)}
                                                    >
                                                        <option value="">Select Medicine Item</option>
                                                        {items.map(item => (
                                                            <option key={item.id} value={item.id}>
                                                                {item.name} ({item.unit}) - SKU: {item.sku || 'N/A'}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </td>
                                                <td className="p-2">
                                                    <input
                                                        type="number"
                                                        min="1"
                                                        required
                                                        className="w-full px-2 py-1.5 border border-border rounded-none text-center text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                                        value={row.quantity}
                                                        onChange={(e) => updateItemRow(index, 'quantity', parseInt(e.target.value) || 1)}
                                                    />
                                                </td>
                                                <td className="p-2">
                                                    <input
                                                        type="text"
                                                        placeholder="strip, box, vial"
                                                        className="w-full px-2.5 py-1.5 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                                        value={row.packaging_unit || ''}
                                                        onChange={(e) => updateItemRow(index, 'packaging_unit', e.target.value)}
                                                    />
                                                </td>
                                                <td className="p-2">
                                                    <input
                                                        type="text"
                                                        placeholder="Optional item note"
                                                        className="w-full px-2.5 py-1.5 border border-border rounded-none text-xs bg-background text-foreground focus:outline-none focus:border-primary"
                                                        value={row.notes}
                                                        onChange={(e) => updateItemRow(index, 'notes', e.target.value)}
                                                    />
                                                </td>
                                                <td className="p-2 text-center">
                                                    <button
                                                        type="button"
                                                        onClick={() => removeItemRow(index)}
                                                        disabled={form.items.length === 1}
                                                        className="text-muted-foreground hover:text-destructive disabled:opacity-20 transition cursor-pointer"
                                                        title="Remove Row"
                                                    >
                                                        <Trash2 size={15} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <button
                                type="button"
                                onClick={addItemRow}
                                className="inline-flex items-center gap-1.5 text-xs font-bold text-foreground bg-accent/40 hover:bg-accent border border-border px-3 py-1.5 rounded-none transition cursor-pointer"
                            >
                                <Plus size={14} />
                                <span>Add Another Medicine</span>
                            </button>
                        </div>

                        <div className="p-5 bg-accent/20 border-t border-border flex justify-end">
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex items-center gap-2 bg-primary hover:bg-black text-primary-foreground px-6 py-2.5 rounded-none font-bold text-xs uppercase tracking-wider transition disabled:opacity-50 cursor-pointer"
                            >
                                {loading ? 'Submitting Requisition...' : (
                                    <>
                                        <Send size={14} />
                                        <span>Submit Requisition Request</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}

                {/* ─── MY REQUESTS HISTORY (Warm Editorial Theme) ─── */}
                {activeTab === 'history' && (
                    <div className="space-y-3">
                        {!form.requested_by && (
                            <div className="p-8 bg-card border border-border rounded-none text-center text-muted-foreground text-xs">
                                Enter your requester name in the form first to view your requisitions.
                            </div>
                        )}

                        {form.requested_by && myRequests.length === 0 && (
                            <div className="p-10 bg-card border border-border rounded-none text-center text-muted-foreground">
                                <ClipboardList size={36} className="mx-auto mb-2 text-muted-foreground/50" />
                                <p className="text-xs font-semibold text-foreground">No requisitions recorded yet.</p>
                                <p className="text-[11px] text-muted-foreground mt-0.5">Submit your first medicine requisition above.</p>
                            </div>
                        )}

                        {myRequests.map(req => (
                            <div key={req.id} className="bg-card rounded-none border border-border p-4 shadow-2xs space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <span className="font-mono text-xs font-bold text-foreground">{req.requisition_number}</span>
                                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-none ${STATUS_STYLES[req.status]}`}>
                                            {req.status}
                                        </span>
                                        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-none ${URGENCY_STYLES[req.urgency]}`}>
                                            {req.urgency}
                                        </span>
                                    </div>
                                    <span className="text-[11px] text-muted-foreground">{new Date(req.created_at).toLocaleDateString()}</span>
                                </div>
                                
                                <div className="text-xs text-muted-foreground">
                                    <span className="font-semibold text-foreground">{req.department}</span> • Counter: {req.location_name} • {req.items?.length || 0} Line item(s)
                                </div>

                                {req.rejection_reason && (
                                    <div className="text-xs text-destructive bg-destructive/10 border border-destructive/30 p-2.5 flex items-start gap-2 rounded-none">
                                        <XCircle size={15} className="mt-0.5 shrink-0 text-destructive" />
                                        <span>Rejection Reason: {req.rejection_reason}</span>
                                    </div>
                                )}

                                {req.status === 'PENDING' && (
                                    <div className="pt-1">
                                        <button
                                            onClick={() => handleCancel(req.id)}
                                            className="text-xs text-destructive hover:underline font-semibold transition cursor-pointer"
                                        >
                                            Cancel Request
                                        </button>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default StaffRequisition;
