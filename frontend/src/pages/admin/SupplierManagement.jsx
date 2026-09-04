import React, { useState, useEffect } from 'react';
import { admin, inventory } from '../../services/api';
import {
    Truck, Plus, Search, CheckCircle, AlertCircle, Loader2,
    Building2, Mail, Phone, Calendar, RefreshCw, X, Shield, FileSpreadsheet
} from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

export default function SupplierManagement() {
    const [suppliers, setSuppliers] = useState([]);
    const [locations, setLocations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [modalOpen, setModalOpen] = useState(false);
    const [editingSupplier, setEditingSupplier] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);
    const [message, setMessage] = useState({ type: '', text: '' });

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        username: '',
        email: '',
        password: '',
        phone: '',
        location_ids: [],
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [supRes, locRes] = await Promise.all([
                admin.getSuppliers(),
                inventory.getLocations(),
            ]);
            setSuppliers(supRes.data?.data || []);
            setLocations(locRes.data?.data || []);
        } catch (err) {
            console.error('Failed to load suppliers:', err);
            setMessage({ type: 'error', text: 'Failed to fetch suppliers list' });
        } finally {
            setLoading(false);
        }
    };

    const handleOpenModal = (supplier = null) => {
        if (supplier) {
            setEditingSupplier(supplier);
            setFormData({
                name: supplier.name || '',
                username: supplier.username || '',
                email: supplier.email || '',
                password: '',
                phone: supplier.phone || '',
                location_ids: supplier.location_ids || [],
            });
        } else {
            setEditingSupplier(null);
            setFormData({
                name: '',
                username: '',
                email: '',
                password: '',
                phone: '',
                location_ids: [],
            });
        }
        setModalOpen(true);
    };

    const handleCloseModal = () => {
        setModalOpen(false);
        setEditingSupplier(null);
    };

    const handleSaveSupplier = async (e) => {
        e.preventDefault();
        setActionLoading(true);
        setMessage({ type: '', text: '' });

        try {
            if (editingSupplier) {
                const res = await admin.updateSupplier(editingSupplier.id, {
                    name: formData.name,
                    email: formData.email,
                    location_ids: formData.location_ids,
                });
                setMessage({ type: 'success', text: res.data?.message || 'Supplier updated successfully' });
            } else {
                const res = await admin.createSupplier(formData);
                setMessage({ type: 'success', text: res.data?.message || 'Supplier created successfully' });
            }
            handleCloseModal();
            loadData();
        } catch (err) {
            const errDetail = err.response?.data?.detail || err.response?.data?.message || 'Operation failed';
            setMessage({ type: 'error', text: errDetail });
        } finally {
            setActionLoading(false);
        }
    };

    const handleDeactivate = async (id, name) => {
        if (!window.confirm(`Are you sure you want to deactivate supplier "${name}"?`)) return;
        try {
            await admin.deleteSupplier(id);
            setMessage({ type: 'success', text: `Supplier "${name}" deactivated` });
            loadData();
        } catch (err) {
            setMessage({ type: 'error', text: 'Failed to deactivate supplier' });
        }
    };

    const filteredSuppliers = suppliers.filter((s) => {
        const query = searchQuery.toLowerCase();
        return (
            s.name?.toLowerCase().includes(query) ||
            s.username?.toLowerCase().includes(query) ||
            s.email?.toLowerCase().includes(query)
        );
    });

    return (
        <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
            {/* Full-Width Top Navbar */}
            <div className="sticky top-0 z-30 bg-card border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="font-sans text-xl font-bold text-foreground tracking-tight">Suppliers & Distributors</h2>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        <button
                            onClick={loadData}
                            className="p-2 bg-accent hover:bg-accent/80 text-foreground rounded-none transition-colors border border-border cursor-pointer"
                            title="Refresh list"
                        >
                            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        </button>
                        <button
                            onClick={() => handleOpenModal()}
                            className="flex items-center gap-1.5 px-3.5 py-2 bg-primary hover:bg-black text-primary-foreground text-xs font-semibold rounded-none border border-primary transition-colors cursor-pointer"
                        >
                            <Plus size={14} />
                            <span>Add Supplier</span>
                        </button>

                        {/* Notification Alerts Bell Dropdown */}
                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            {/* Page Content Container */}
            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">

            {/* Notification alert */}
            {message.text && (
                <div className={`p-4 text-xs font-medium border flex items-center justify-between ${
                    message.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-red-50 text-red-800 border-red-200'
                }`}>
                    <div className="flex items-center gap-2">
                        {message.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                        <span>{message.text}</span>
                    </div>
                    <button onClick={() => setMessage({ type: '', text: '' })} className="p-1 hover:opacity-75 cursor-pointer">
                        <X size={14} />
                    </button>
                </div>
            )}

            {/* Search Toolbar */}
            <div className="bg-card border border-border p-4 rounded-none flex items-center gap-3">
                <div className="relative flex-1">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search by distributor name, username, or email..."
                        className="w-full text-xs font-medium bg-background border border-border rounded-none pl-9 pr-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                    />
                </div>
                <span className="text-xs text-muted-foreground font-medium whitespace-nowrap font-mono">
                    {filteredSuppliers.length} of {suppliers.length} suppliers
                </span>
            </div>

            {/* Suppliers Grid */}
            {loading ? (
                <div className="p-12 text-center text-muted-foreground bg-card border border-border flex flex-col items-center gap-2">
                    <Loader2 size={24} className="animate-spin text-foreground" />
                    <span className="text-xs font-mono">Loading suppliers...</span>
                </div>
            ) : filteredSuppliers.length === 0 ? (
                <div className="p-12 text-center bg-card border border-border">
                    <Truck className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                    <h3 className="text-sm font-bold text-foreground font-sans">No Suppliers Found</h3>
                    <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                        Add your medicine distributors (e.g. Shree Pharma, Apollo Wholesale) to allow them to upload Excel delivery sheets.
                    </p>
                    <button
                        onClick={() => handleOpenModal()}
                        className="mt-4 px-4 py-2 bg-primary hover:bg-black text-primary-foreground text-xs font-semibold rounded-none transition-colors cursor-pointer"
                    >
                        Add First Supplier
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredSuppliers.map((supplier) => (
                        <div
                            key={supplier.id}
                            className="bg-card border border-border p-5 rounded-none flex flex-col justify-between hover:border-primary/40 transition-colors shadow-none"
                        >
                            <div>
                                <div className="flex items-start justify-between gap-2 pb-3 border-b border-border">
                                    <div>
                                        <h4 className="font-sans text-sm font-bold text-foreground">{supplier.name}</h4>
                                        <p className="text-xs text-muted-foreground font-mono mt-0.5">@{supplier.username}</p>
                                    </div>
                                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-none border font-mono ${
                                        supplier.is_active
                                            ? 'bg-accent text-foreground border-border'
                                            : 'bg-muted text-muted-foreground border-border'
                                    }`}>
                                        {supplier.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>

                                <div className="space-y-2 py-3 text-xs text-muted-foreground">
                                    <div className="flex items-center gap-2">
                                        <Mail size={13} className="text-muted-foreground shrink-0" />
                                        <span className="truncate text-foreground">{supplier.email}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <FileSpreadsheet size={13} className="text-muted-foreground shrink-0" />
                                        <span><strong className="text-foreground">{supplier.total_uploads || 0}</strong> Manifests Uploaded</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Calendar size={13} className="text-muted-foreground shrink-0" />
                                        <span>Added: {supplier.created_at ? new Date(supplier.created_at).toLocaleDateString() : 'N/A'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
                                <button
                                    onClick={() => handleOpenModal(supplier)}
                                    className="px-3 py-1.5 text-xs font-semibold text-foreground bg-accent hover:bg-accent/80 border border-border rounded-none transition-colors cursor-pointer"
                                >
                                    Edit
                                </button>
                                {supplier.is_active && (
                                    <button
                                        onClick={() => handleDeactivate(supplier.id, supplier.name)}
                                        className="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-none transition-colors cursor-pointer"
                                    >
                                        Deactivate
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add / Edit Supplier Modal */}
            {modalOpen && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border w-full max-w-lg p-6 shadow-2xl space-y-4 text-card-foreground">
                        <div className="flex items-center justify-between pb-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <Truck size={18} className="text-foreground" />
                                <h3 className="font-sans text-base font-bold text-foreground">
                                    {editingSupplier ? 'Edit Supplier' : 'Add New Medicine Supplier'}
                                </h3>
                            </div>
                            <button onClick={handleCloseModal} className="p-1 text-muted-foreground hover:text-foreground cursor-pointer">
                                <X size={18} />
                            </button>
                        </div>

                        <form onSubmit={handleSaveSupplier} className="space-y-3.5 text-xs">
                            <div>
                                <label className="block font-semibold text-foreground/80 mb-1">Distributor / Agency Name *</label>
                                <input
                                    type="text"
                                    required
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="e.g. Shree Pharma Distributors"
                                    className="w-full bg-background border border-border rounded-none px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-foreground/80 mb-1">Username (Login ID) *</label>
                                <input
                                    type="text"
                                    required
                                    disabled={Boolean(editingSupplier)}
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    placeholder="e.g. shreepharma"
                                    className="w-full bg-background border border-border rounded-none px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60 font-mono"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-foreground/80 mb-1">Email Address *</label>
                                <input
                                    type="email"
                                    required
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="e.g. orders@shreepharma.com"
                                    className="w-full bg-background border border-border rounded-none px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                />
                            </div>

                            {!editingSupplier && (
                                <div>
                                    <label className="block font-semibold text-foreground/80 mb-1">Initial Password</label>
                                    <input
                                        type="password"
                                        value={formData.password}
                                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                        placeholder="Defaults to vendor123"
                                        className="w-full bg-background border border-border rounded-none px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block font-semibold text-foreground/80 mb-1">Assigned Shop Branches</label>
                                <div className="space-y-1.5 max-h-32 overflow-y-auto p-2 bg-background border border-border">
                                    {locations.map((loc) => {
                                        const isChecked = formData.location_ids.includes(loc.id);
                                        return (
                                            <label key={loc.id} className="flex items-center gap-2 cursor-pointer text-foreground">
                                                <input
                                                    type="checkbox"
                                                    checked={isChecked}
                                                    onChange={() => {
                                                        const updated = isChecked
                                                            ? formData.location_ids.filter((id) => id !== loc.id)
                                                            : [...formData.location_ids, loc.id];
                                                        setFormData({ ...formData, location_ids: updated });
                                                    }}
                                                    className="rounded-none accent-primary"
                                                />
                                                <span>{loc.name}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
                                <button
                                    type="button"
                                    onClick={handleCloseModal}
                                    className="px-4 py-2 bg-accent hover:bg-accent/80 text-foreground border border-border font-semibold rounded-none transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={actionLoading}
                                    className="flex items-center gap-1.5 px-5 py-2 bg-primary hover:bg-black text-primary-foreground font-semibold rounded-none transition-colors disabled:opacity-50 cursor-pointer"
                                >
                                    {actionLoading && <Loader2 size={13} className="animate-spin" />}
                                    <span>{editingSupplier ? 'Save Changes' : 'Create Supplier'}</span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            </div>
        </div>
    );
}

