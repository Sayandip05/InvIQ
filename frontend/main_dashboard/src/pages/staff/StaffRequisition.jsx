import React, { useState, useEffect } from 'react';
import { inventory, requisition } from '../../services/api';
import { Plus, Trash2, Send, ClipboardList, Clock, CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const URGENCY_OPTIONS = ['LOW', 'NORMAL', 'HIGH', 'EMERGENCY'];
const DEPARTMENTS = ['Cardiology', 'ICU', 'Emergency', 'Orthopedics', 'Pediatrics', 'Oncology', 'Pharmacy', 'General Ward', 'OT', 'Lab'];

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
    EMERGENCY: 'bg-red-100 text-red-700 animate-pulse',
};

const StaffRequisition = () => {
    const [locations, setLocations] = useState([]);
    const [items, setItems] = useState([]);
    const [myRequests, setMyRequests] = useState([]);
    const [activeTab, setActiveTab] = useState('form'); // 'form' | 'history'
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);

    const [form, setForm] = useState({
        location_id: '',
        department: '',
        urgency: 'NORMAL',
        requested_by: '',
        notes: '',
        items: [{ item_id: '', quantity: 1, notes: '' }],
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [locRes, itemRes] = await Promise.all([
                    inventory.getLocations(),
                    inventory.getItems(),
                ]);
                if (locRes.data.success) setLocations(locRes.data.data);
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
            items: [...prev.items, { item_id: '', quantity: 1, notes: '' }],
        }));
    };

    const removeItemRow = (index) => {
        setForm(prev => ({
            ...prev,
            items: prev.items.filter((_, i) => i !== index),
        }));
    };

    const updateItemRow = (index, field, value) => {
        setForm(prev => {
            const newItems = [...prev.items];
            newItems[index] = { ...newItems[index], [field]: value };
            return { ...prev, items: newItems };
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(null);

        const validItems = form.items.filter(i => i.item_id && i.quantity > 0);
        if (validItems.length === 0) {
            setError('Please add at least one item with quantity.');
            setLoading(false);
            return;
        }

        try {
            const payload = {
                location_id: parseInt(form.location_id),
                requested_by: form.requested_by.trim(),
                department: form.department,
                urgency: form.urgency,
                notes: form.notes || null,
                items: validItems.map(i => ({
                    item_id: parseInt(i.item_id),
                    quantity: parseInt(i.quantity),
                    notes: i.notes || null,
                })),
            };

            const res = await requisition.create(payload);
            if (res.data.success) {
                setSuccess(res.data.message);
                setForm(prev => ({
                    ...prev,
                    notes: '',
                    items: [{ item_id: '', quantity: 1, notes: '' }],
                }));
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Submission failed');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = async (id) => {
        try {
            await requisition.cancel(id, { cancelled_by: form.requested_by });
            loadHistory();
        } catch (err) {
            console.error('Cancel failed', err);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8 px-4">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Stock Requisition</h1>
                        <p className="text-slate-500 mt-1">Department Staff Portal</p>
                    </div>
                    <Link to="/admin" className="text-sm text-slate-400 hover:text-blue-600 flex items-center gap-1">
                        <ArrowLeft size={16} /> Admin Portal
                    </Link>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 bg-white rounded-xl p-1 shadow-sm border border-slate-100 mb-6">
                    <button
                        onClick={() => setActiveTab('form')}
                        className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition ${activeTab === 'form' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50'}`}
                    >
                        <Send size={16} className="inline mr-2" />New Request
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition ${activeTab === 'history' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50'}`}
                    >
                        <Clock size={16} className="inline mr-2" />My Requests
                    </button>
                </div>

                {/* ─── NEW REQUEST FORM ─── */}
                {activeTab === 'form' && (
                    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg border border-slate-100 overflow-hidden">
                        <div className="p-6 border-b border-slate-100 bg-slate-50/50 space-y-5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Your Name</label>
                                    <input
                                        required
                                        type="text"
                                        placeholder="e.g. Dr. Sharma"
                                        className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={form.requested_by}
                                        onChange={(e) => setForm({ ...form, requested_by: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Department</label>
                                    <select
                                        required
                                        className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={form.department}
                                        onChange={(e) => setForm({ ...form, department: e.target.value })}
                                    >
                                        <option value="">Select Department</option>
                                        {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Location</label>
                                    <select
                                        required
                                        className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={form.location_id}
                                        onChange={(e) => setForm({ ...form, location_id: e.target.value })}
                                    >
                                        <option value="">Select Location</option>
                                        {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Urgency</label>
                                    <div className="flex gap-2">
                                        {URGENCY_OPTIONS.map(u => (
                                            <button
                                                key={u}
                                                type="button"
                                                onClick={() => setForm({ ...form, urgency: u })}
                                                className={`flex-1 py-2 rounded-lg text-xs font-semibold transition border ${form.urgency === u ? URGENCY_STYLES[u] + ' border-current' : 'bg-white text-slate-400 border-slate-200 hover:border-slate-300'}`}
                                            >
                                                {u}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">Notes (optional)</label>
                                <textarea
                                    rows={2}
                                    placeholder="Additional notes for the store manager..."
                                    className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                />
                            </div>
                        </div>

                        {/* Items */}
                        <div className="p-6">
                            {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg border border-red-100 text-sm">{error}</div>}
                            {success && <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg border border-green-100 text-sm flex items-center gap-2"><CheckCircle2 size={18} />{success}</div>}

                            <div className="grid grid-cols-12 gap-3 text-xs font-medium text-slate-500 px-1 mb-2">
                                <div className="col-span-6">Item</div>
                                <div className="col-span-2 text-center">Qty</div>
                                <div className="col-span-3">Notes</div>
                                <div className="col-span-1"></div>
                            </div>

                            {form.items.map((row, index) => (
                                <div key={index} className="grid grid-cols-12 gap-3 items-center mb-2 p-2 hover:bg-slate-50 rounded-lg transition">
                                    <div className="col-span-6">
                                        <select
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                            value={row.item_id}
                                            onChange={(e) => updateItemRow(index, 'item_id', e.target.value)}
                                        >
                                            <option value="">Select Item</option>
                                            {items.map(item => (
                                                <option key={item.id} value={item.id}>{item.name} ({item.unit})</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="col-span-2">
                                        <input
                                            type="number"
                                            min="1"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-center text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                            value={row.quantity}
                                            onChange={(e) => updateItemRow(index, 'quantity', parseInt(e.target.value) || 1)}
                                        />
                                    </div>
                                    <div className="col-span-3">
                                        <input
                                            type="text"
                                            placeholder="Optional"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                            value={row.notes}
                                            onChange={(e) => updateItemRow(index, 'notes', e.target.value)}
                                        />
                                    </div>
                                    <div className="col-span-1 flex justify-center">
                                        <button type="button" onClick={() => removeItemRow(index)} disabled={form.items.length === 1} className="text-slate-300 hover:text-red-500 transition disabled:opacity-30">
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}

                            <button type="button" onClick={addItemRow} className="flex items-center gap-2 text-blue-600 font-medium text-sm hover:bg-blue-50 py-2 px-3 rounded-lg mt-3 transition">
                                <Plus size={16} /> Add Item
                            </button>
                        </div>

                        <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end">
                            <button type="submit" disabled={loading} className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition shadow-lg shadow-blue-200 disabled:opacity-70">
                                {loading ? 'Submitting...' : <><Send size={18} /> Submit Requisition</>}
                            </button>
                        </div>
                    </form>
                )}

                {/* ─── MY REQUESTS HISTORY ─── */}
                {activeTab === 'history' && (
                    <div className="space-y-3">
                        {!form.requested_by && (
                            <div className="p-8 bg-white rounded-xl text-center text-slate-400">
                                Enter your name in the form first to see your requests.
                            </div>
                        )}

                        {form.requested_by && myRequests.length === 0 && (
                            <div className="p-8 bg-white rounded-xl text-center text-slate-400">
                                <ClipboardList size={40} className="mx-auto mb-3 text-slate-300" />
                                No requisitions found.
                            </div>
                        )}

                        {myRequests.map(req => (
                            <div key={req.id} className="bg-white rounded-xl shadow-sm border border-slate-100 p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="font-semibold text-slate-800">{req.requisition_number}</span>
                                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_STYLES[req.status]}`}>{req.status}</span>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${URGENCY_STYLES[req.urgency]}`}>{req.urgency}</span>
                                    </div>
                                    <span className="text-xs text-slate-400">{new Date(req.created_at).toLocaleDateString()}</span>
                                </div>
                                <div className="text-sm text-slate-500 mb-2">
                                    {req.department} • {req.location_name} • {req.items.length} item(s)
                                </div>
                                {req.rejection_reason && (
                                    <div className="text-sm text-red-600 bg-red-50 rounded-lg p-2 mt-2 flex items-start gap-2">
                                        <XCircle size={16} className="mt-0.5 shrink-0" /> {req.rejection_reason}
                                    </div>
                                )}
                                {req.status === 'PENDING' && (
                                    <button onClick={() => handleCancel(req.id)} className="mt-2 text-xs text-slate-400 hover:text-red-500 transition">
                                        Cancel Request
                                    </button>
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
