import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { admin as adminApi, auth as authApi, inventory as inventoryApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import {
    Users, Truck, Plus, Search, Edit2, Trash2, Building2,
    RefreshCw, MapPin, Mail, Calendar, FileSpreadsheet,
    AlertCircle, CheckCircle, X, Loader2
} from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

export default function SuppliersAndStaff({ initialTab = 'staff' }) {
    const { user: currentUser } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();

    // Tab state: 'staff' or 'suppliers'
    const paramTab = searchParams.get('tab');
    const [activeTab, setActiveTab] = useState(paramTab || initialTab);

    // Sync tab with URL search parameter
    const handleTabChange = (newTab) => {
        setActiveTab(newTab);
        setSearchParams({ tab: newTab });
    };

    // Shared / domain state
    const [loading, setLoading] = useState(true);
    const [locations, setLocations] = useState([]);
    const [users, setUsers] = useState([]);
    const [suppliers, setSuppliers] = useState([]);
    const [message, setMessage] = useState({ type: '', text: '' });

    // Search queries
    const [userSearch, setUserSearch] = useState('');
    const [supplierSearch, setSupplierSearch] = useState('');

    // User / Staff modal state
    const [userModalOpen, setUserModalOpen] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [userSaving, setUserSaving] = useState(false);
    const [userForm, setUserForm] = useState({
        username: '',
        email: '',
        full_name: '',
        role: 'staff',
        password: '',
        location_ids: [],
    });

    // Supplier modal state
    const [supplierModalOpen, setSupplierModalOpen] = useState(false);
    const [editingSupplier, setEditingSupplier] = useState(null);
    const [supplierSaving, setSupplierSaving] = useState(false);
    const [supplierForm, setSupplierForm] = useState({
        name: '',
        username: '',
        email: '',
        password: '',
        phone: '',
        location_ids: [],
    });

    // Load data for both staff & suppliers
    const loadAllData = useCallback(async () => {
        setLoading(true);
        setMessage({ type: '', text: '' });
        try {
            const [usersRes, supRes, locRes] = await Promise.all([
                authApi.list().catch(() => ({ data: { success: false, data: [] } })),
                adminApi.getSuppliers().catch(() => ({ data: { success: false, data: [] } })),
                inventoryApi.getLocations().catch(() => ({ data: { success: false, data: [] } })),
            ]);

            if (usersRes.data?.success) {
                setUsers(usersRes.data.data || []);
            }
            if (supRes.data?.success || Array.isArray(supRes.data?.data)) {
                setSuppliers(supRes.data.data || []);
            }
            if (locRes.data?.success || Array.isArray(locRes.data?.data)) {
                setLocations(locRes.data.data || []);
            }
        } catch (err) {
            console.error('Failed to load roster data:', err);
            setMessage({ type: 'error', text: 'Failed to refresh directory records.' });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAllData();
    }, [loadAllData]);

    // Keep active tab synced if prop changes
    useEffect(() => {
        if (paramTab && (paramTab === 'staff' || paramTab === 'suppliers')) {
            setActiveTab(paramTab);
        } else if (initialTab) {
            setActiveTab(initialTab);
        }
    }, [paramTab, initialTab]);

    // ── Staff Handlers ────────────────────────────────────────────────────────
    const handleOpenUserModal = (userToEdit = null) => {
        if (userToEdit) {
            setEditingUser(userToEdit);
            setUserForm({
                username: userToEdit.username,
                email: userToEdit.email || '',
                full_name: userToEdit.full_name || '',
                role: userToEdit.role || 'staff',
                password: '',
                location_ids: userToEdit.location_ids || [],
            });
        } else {
            setEditingUser(null);
            setUserForm({
                username: '',
                email: '',
                full_name: '',
                role: 'staff',
                password: '',
                location_ids: locations.length > 0 ? [locations[0].id] : [],
            });
        }
        setUserModalOpen(true);
    };

    const handleSaveUser = async (e) => {
        e.preventDefault();
        setUserSaving(true);
        try {
            if (editingUser) {
                await authApi.update(editingUser.id, userForm);
                setMessage({ type: 'success', text: `Staff member "${userForm.username}" updated.` });
            } else {
                await authApi.register(userForm);
                setMessage({ type: 'success', text: `New staff member "${userForm.username}" allocated successfully.` });
            }
            setUserModalOpen(false);
            setEditingUser(null);
            loadAllData();
        } catch (err) {
            const msg =
                err.response?.data?.error?.message ||
                err.response?.data?.detail ||
                'Operation failed. Please verify the input values.';
            alert(msg);
        } finally {
            setUserSaving(false);
        }
    };

    const handleDeleteUser = async (id, username) => {
        if (!window.confirm(`Are you sure you want to remove staff member "${username}"?`)) return;
        try {
            await authApi.delete(id);
            setMessage({ type: 'success', text: `Staff member "${username}" removed.` });
            loadAllData();
        } catch {
            alert('Failed to remove staff member');
        }
    };

    // ── Supplier Handlers ─────────────────────────────────────────────────────
    const handleOpenSupplierModal = (supplierToEdit = null) => {
        if (supplierToEdit) {
            setEditingSupplier(supplierToEdit);
            setSupplierForm({
                name: supplierToEdit.name || '',
                username: supplierToEdit.username || '',
                email: supplierToEdit.email || '',
                password: '',
                phone: supplierToEdit.phone || '',
                location_ids: supplierToEdit.location_ids || [],
            });
        } else {
            setEditingSupplier(null);
            setSupplierForm({
                name: '',
                username: '',
                email: '',
                password: '',
                phone: '',
                location_ids: [],
            });
        }
        setSupplierModalOpen(true);
    };

    const handleSaveSupplier = async (e) => {
        e.preventDefault();
        setSupplierSaving(true);
        try {
            if (editingSupplier) {
                const res = await adminApi.updateSupplier(editingSupplier.id, {
                    name: supplierForm.name,
                    email: supplierForm.email,
                    location_ids: supplierForm.location_ids,
                });
                setMessage({ type: 'success', text: res.data?.message || 'Supplier details updated.' });
            } else {
                const res = await adminApi.createSupplier(supplierForm);
                setMessage({ type: 'success', text: res.data?.message || 'New medicine supplier registered.' });
            }
            setSupplierModalOpen(false);
            setEditingSupplier(null);
            loadAllData();
        } catch (err) {
            const errDetail = err.response?.data?.detail || err.response?.data?.message || 'Failed to save supplier';
            alert(errDetail);
        } finally {
            setSupplierSaving(false);
        }
    };

    const handleDeactivateSupplier = async (id, name) => {
        if (!window.confirm(`Are you sure you want to deactivate supplier "${name}"?`)) return;
        try {
            await adminApi.deleteSupplier(id);
            setMessage({ type: 'success', text: `Supplier "${name}" deactivated.` });
            loadAllData();
        } catch {
            alert('Failed to deactivate supplier');
        }
    };

    // Helpers
    const getLocationNames = (locIds) => {
        if (!locIds || locIds.length === 0) return 'All Branches';
        const matched = locations.filter((l) => locIds.includes(l.id));
        if (matched.length === 0) return `${locIds.length} Branch(es)`;
        return matched.map((l) => l.name).join(', ');
    };

    const getRoleBadge = (role) => {
        const colors = {
            admin: 'bg-red-50 text-red-700 border-red-200',
            manager: 'bg-amber-50 text-amber-700 border-amber-200',
            staff: 'bg-blue-50 text-blue-700 border-blue-200',
            vendor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        };
        return (
            <span className={`px-2 py-0.5 border rounded-none text-[10px] font-bold uppercase tracking-wider font-mono ${colors[role] || 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                {role}
            </span>
        );
    };

    // Filtered data
    const filteredUsers = users.filter((u) => {
        const query = userSearch.toLowerCase();
        return (
            u.username?.toLowerCase().includes(query) ||
            u.email?.toLowerCase().includes(query) ||
            u.full_name?.toLowerCase().includes(query) ||
            u.role?.toLowerCase().includes(query)
        );
    });

    const filteredSuppliers = suppliers.filter((s) => {
        const query = supplierSearch.toLowerCase();
        return (
            s.name?.toLowerCase().includes(query) ||
            s.username?.toLowerCase().includes(query) ||
            s.email?.toLowerCase().includes(query)
        );
    });

    return (
        <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
            {/* ── Full-Width Sticky Top Navbar (Identical to Dashboard / Inventory) ── */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Suppliers &amp; Staff</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Directory of your store staff and medicine suppliers
                        </p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        {/* Tab Switcher */}
                        <div className="inline-flex items-center bg-accent/60 p-0.5 border border-border rounded-md text-xs">
                            <button
                                onClick={() => handleTabChange('staff')}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
                                    activeTab === 'staff'
                                        ? 'bg-background text-foreground shadow-xs font-bold'
                                        : 'text-muted-foreground hover:text-foreground'
                                }`}
                            >
                                <Users size={13} />
                                <span>Staff ({users.length})</span>
                            </button>
                            <button
                                onClick={() => handleTabChange('suppliers')}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
                                    activeTab === 'suppliers'
                                        ? 'bg-background text-foreground shadow-xs font-bold'
                                        : 'text-muted-foreground hover:text-foreground'
                                }`}
                            >
                                <Truck size={13} />
                                <span>Suppliers ({suppliers.length})</span>
                            </button>
                        </div>

                        <button
                            onClick={loadAllData}
                            className="p-2 bg-accent/50 hover:bg-accent text-foreground rounded-md transition-colors border border-border cursor-pointer"
                            title="Refresh directory"
                        >
                            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        </button>

                        {/* Dynamic Action Button based on active tab */}
                        {activeTab === 'staff' ? (
                            <button
                                onClick={() => handleOpenUserModal()}
                                className="flex items-center gap-1.5 px-3.5 py-2 bg-primary hover:bg-black text-primary-foreground text-xs font-semibold rounded-md border border-primary transition-colors cursor-pointer shadow-2xs"
                            >
                                <Plus size={14} />
                                <span>Allocate Staff</span>
                            </button>
                        ) : (
                            <button
                                onClick={() => handleOpenSupplierModal()}
                                className="flex items-center gap-1.5 px-3.5 py-2 bg-primary hover:bg-black text-primary-foreground text-xs font-semibold rounded-md border border-primary transition-colors cursor-pointer shadow-2xs"
                            >
                                <Plus size={14} />
                                <span>Add Supplier</span>
                            </button>
                        )}

                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Main Content Area ────────────────────────────────────────── */}
            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">
                {/* Notification toast */}
                {message.text && (
                    <div className={`p-3 text-xs font-medium border flex items-center justify-between animate-in fade-in ${message.type === 'success'
                            ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                            : 'bg-rose-50 text-rose-900 border-rose-300'
                        }`}>
                        <div className="flex items-center gap-2">
                            {message.type === 'success' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
                            <span>{message.text}</span>
                        </div>
                        <button onClick={() => setMessage({ type: '', text: '' })} className="text-xs hover:underline cursor-pointer font-bold">
                            Dismiss
                        </button>
                    </div>
                )}

                {/* ══════════════ TAB 1: USERS & STAFF ══════════════ */}
                {activeTab === 'staff' && (
                    <div className="space-y-4 animate-in fade-in duration-150">
                        {/* Store isolation info bar */}
                        <div className="bg-card border border-border p-4 rounded-lg shadow-xs flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2.5">
                                <Building2 size={16} className="text-foreground shrink-0" />
                                <div>
                                    <span className="font-mono font-bold text-foreground">
                                        Active Organization: <span className="underline">{currentUser?.organization_name || 'Your Pharmacy Network'}</span>
                                    </span>
                                    <span className="text-muted-foreground ml-2 hidden sm:inline">
                                        (Staff accounts can only access branches allocated to them)
                                    </span>
                                </div>
                            </div>
                            <span className="font-mono font-bold text-foreground px-2.5 py-1 bg-accent/60 border border-border rounded-md text-[11px]">
                                {users.length} Account(s)
                            </span>
                        </div>

                        {/* Search Toolbar */}
                        <div className="bg-card border border-border p-4 rounded-lg shadow-xs flex items-center gap-3">
                            <div className="relative flex-1">
                                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                <input
                                    type="text"
                                    value={userSearch}
                                    onChange={(e) => setUserSearch(e.target.value)}
                                    placeholder="Search staff by username, name, email, or role..."
                                    className="w-full text-xs font-medium bg-background border border-border rounded-md pl-9 pr-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                                />
                            </div>
                            <span className="text-xs text-muted-foreground font-mono whitespace-nowrap">
                                {filteredUsers.length} of {users.length} staff
                            </span>
                        </div>

                        {/* Staff Table */}
                        <div className="bg-card border border-border rounded-lg overflow-hidden shadow-xs">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse text-xs">
                                    <thead className="bg-accent/40 text-muted-foreground font-bold text-[11px] uppercase tracking-wider border-b border-border font-mono">
                                        <tr>
                                            <th className="px-4 py-2.5">Staff / User</th>
                                            <th className="px-4 py-2.5">Email</th>
                                            <th className="px-4 py-2.5">Role</th>
                                            <th className="px-4 py-2.5">Branch Counter</th>
                                            <th className="px-4 py-2.5">Status</th>
                                            <th className="px-4 py-2.5 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border text-foreground">
                                        {loading ? (
                                            <tr>
                                                <td colSpan="6" className="text-center py-10 text-muted-foreground font-mono">
                                                    <Loader2 size={16} className="animate-spin inline-block mr-2" />
                                                    Loading staff roster...
                                                </td>
                                            </tr>
                                        ) : filteredUsers.length === 0 ? (
                                            <tr>
                                                <td colSpan="6" className="text-center py-10 text-muted-foreground font-mono">
                                                    No staff members match the query
                                                </td>
                                            </tr>
                                        ) : (
                                            filteredUsers.map((u) => (
                                                <tr key={u.id} className="hover:bg-accent/30 transition-colors">
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-2.5">
                                                            <div className="w-7 h-7 rounded-none bg-accent border border-border text-foreground flex items-center justify-center text-xs font-bold font-mono">
                                                                {u.username?.[0]?.toUpperCase() || 'U'}
                                                            </div>
                                                            <div>
                                                                <p className="font-bold text-foreground">{u.username}</p>
                                                                <p className="text-[10px] text-muted-foreground">{u.full_name || 'No full name'}</p>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3 text-muted-foreground font-mono">{u.email || '—'}</td>
                                                    <td className="px-4 py-3 font-mono">{getRoleBadge(u.role)}</td>
                                                    <td className="px-4 py-3 text-foreground">
                                                        <div className="flex items-center gap-1 text-xs">
                                                            <MapPin size={12} className="text-muted-foreground shrink-0" />
                                                            <span className="truncate max-w-xs">{getLocationNames(u.location_ids)}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-0.5 border rounded-none text-[10px] font-bold uppercase tracking-wider font-mono ${u.is_active ? 'bg-accent text-foreground border-border' : 'bg-muted text-muted-foreground border-border'
                                                            }`}>
                                                            {u.is_active ? 'Active' : 'Inactive'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        <div className="flex items-center justify-end gap-1.5">
                                                            <button
                                                                onClick={() => handleOpenUserModal(u)}
                                                                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent border border-border rounded-none transition-colors cursor-pointer"
                                                                title="Edit staff member"
                                                            >
                                                                <Edit2 size={12} />
                                                            </button>
                                                            <button
                                                                onClick={() => handleDeleteUser(u.id, u.username)}
                                                                className="p-1.5 text-muted-foreground hover:text-rose-600 hover:bg-rose-50 border border-border rounded-none transition-colors cursor-pointer"
                                                                title="Remove staff member"
                                                            >
                                                                <Trash2 size={12} />
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}

                {/* ══════════════ TAB 2: SUPPLIERS & VENDORS ══════════════ */}
                {activeTab === 'suppliers' && (
                    <div className="space-y-4 animate-in fade-in duration-150">
                        {/* Search Toolbar */}
                        <div className="bg-card border border-border p-4 rounded-lg shadow-xs flex items-center gap-3">
                            <div className="relative flex-1">
                                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                <input
                                    type="text"
                                    value={supplierSearch}
                                    onChange={(e) => setSupplierSearch(e.target.value)}
                                    placeholder="Search by distributor name, username, or email..."
                                    className="w-full text-xs font-medium bg-background border border-border rounded-md pl-9 pr-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                                />
                            </div>
                            <span className="text-xs text-muted-foreground font-mono whitespace-nowrap">
                                {filteredSuppliers.length} of {suppliers.length} distributors
                            </span>
                        </div>

                        {/* Suppliers Grid */}
                        {loading ? (
                            <div className="p-12 text-center text-muted-foreground bg-card border border-border rounded-lg shadow-xs flex flex-col items-center gap-2">
                                <Loader2 size={20} className="animate-spin text-foreground" />
                                <span className="text-xs font-mono">Loading distributor accounts...</span>
                            </div>
                        ) : filteredSuppliers.length === 0 ? (
                            <div className="p-10 text-center bg-card border border-border rounded-lg shadow-xs">
                                <Truck className="w-10 h-10 text-muted-foreground mx-auto mb-2" />
                                <h3 className="text-sm font-bold text-foreground font-sans">No Medicine Suppliers Found</h3>
                                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                                    Register your wholesale distributors to permit bulk Excel delivery uploads and PO matching.
                                </p>
                                <button
                                    onClick={() => handleOpenSupplierModal()}
                                    className="mt-3 px-4 py-1.5 bg-primary hover:bg-black text-primary-foreground text-xs font-bold rounded-md transition-colors cursor-pointer"
                                >
                                    Add First Supplier
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {filteredSuppliers.map((supplier) => (
                                    <div
                                        key={supplier.id}
                                        className="bg-card border border-border p-5 rounded-lg shadow-xs flex flex-col justify-between hover:border-primary/40 transition-colors"
                                    >
                                        <div>
                                            <div className="flex items-start justify-between gap-2 pb-2.5 border-b border-border">
                                                <div>
                                                    <h4 className="font-sans text-sm font-bold text-foreground">{supplier.name}</h4>
                                                    <p className="text-[11px] text-muted-foreground font-mono mt-0.5">@{supplier.username}</p>
                                                </div>
                                                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-none border font-mono ${supplier.is_active
                                                        ? 'bg-accent text-foreground border-border'
                                                        : 'bg-muted text-muted-foreground border-border'
                                                    }`}>
                                                    {supplier.is_active ? 'Active' : 'Inactive'}
                                                </span>
                                            </div>

                                            <div className="space-y-1.5 py-3 text-xs text-muted-foreground">
                                                <div className="flex items-center gap-2">
                                                    <Mail size={12} className="text-muted-foreground shrink-0" />
                                                    <span className="truncate text-foreground font-mono">{supplier.email}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <FileSpreadsheet size={12} className="text-muted-foreground shrink-0" />
                                                    <span><strong className="text-foreground">{supplier.total_uploads || 0}</strong> Delivery Sheets</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Calendar size={12} className="text-muted-foreground shrink-0" />
                                                    <span>Registered: {supplier.created_at ? new Date(supplier.created_at).toLocaleDateString() : 'N/A'}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="pt-2.5 border-t border-border flex items-center justify-end gap-1.5">
                                            <button
                                                onClick={() => handleOpenSupplierModal(supplier)}
                                                className="px-2.5 py-1 text-xs font-semibold text-foreground bg-accent hover:bg-accent/80 border border-border rounded-none transition-colors cursor-pointer"
                                            >
                                                Edit
                                            </button>
                                            {supplier.is_active && (
                                                <button
                                                    onClick={() => handleDeactivateSupplier(supplier.id, supplier.name)}
                                                    className="px-2.5 py-1 text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-border rounded-none transition-colors cursor-pointer"
                                                >
                                                    Deactivate
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* ── User / Staff Modal ───────────────────────────────────────── */}
            {userModalOpen && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in">
                    <div className="bg-card border border-border rounded-none shadow-xl w-full max-w-md p-5 space-y-3.5 text-card-foreground">
                        <div className="flex items-center justify-between pb-2.5 border-b border-border">
                            <div>
                                <h3 className="font-sans text-sm font-bold text-foreground">
                                    {editingUser ? 'Edit Staff Allocation' : 'Allocate New Staff Member'}
                                </h3>
                                <p className="text-[11px] text-muted-foreground">Assign credentials, role, and branch location</p>
                            </div>
                            <button onClick={() => setUserModalOpen(false)} className="text-muted-foreground hover:text-foreground cursor-pointer">
                                <X size={16} />
                            </button>
                        </div>
                        <form onSubmit={handleSaveUser} className="space-y-3 text-xs">
                            <div>
                                <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">Username *</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full px-3 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                                    value={userForm.username}
                                    onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">Email Address *</label>
                                <input
                                    type="email"
                                    required
                                    className="w-full px-3 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                                    value={userForm.email}
                                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">Full Name</label>
                                <input
                                    type="text"
                                    className="w-full px-3 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                                    value={userForm.full_name}
                                    onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-2.5">
                                <div>
                                    <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">Role *</label>
                                    <select
                                        required
                                        className="w-full px-2.5 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                                        value={userForm.role}
                                        onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                                    >
                                        <option value="staff">Store Staff</option>
                                        <option value="vendor">Medicine Supplier</option>
                                        <option value="manager">Branch Manager</option>
                                        <option value="admin">Store Admin</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">Branch Counter</label>
                                    <select
                                        className="w-full px-2.5 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                                        value={userForm.location_ids?.[0] || ''}
                                        onChange={(e) => setUserForm({ ...userForm, location_ids: e.target.value ? [parseInt(e.target.value)] : [] })}
                                    >
                                        <option value="">All Branches</option>
                                        {locations.map((loc) => (
                                            <option key={loc.id} value={loc.id}>{loc.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-foreground/80 uppercase tracking-wider mb-1 font-mono">
                                    {editingUser ? 'New Password (blank to keep current)' : 'Initial Password *'}
                                </label>
                                <input
                                    type="password"
                                    required={!editingUser}
                                    minLength={8}
                                    className="w-full px-3 py-1.5 text-xs bg-background border border-border rounded-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                                    value={userForm.password}
                                    onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-2.5 border-t border-border">
                                <button
                                    type="button"
                                    onClick={() => setUserModalOpen(false)}
                                    className="px-3 py-1.5 text-xs font-semibold text-foreground bg-accent hover:bg-accent/80 border border-border rounded-none transition cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={userSaving}
                                    className="px-4 py-1.5 text-xs font-bold bg-primary text-primary-foreground hover:bg-black rounded-none transition disabled:opacity-50 cursor-pointer shadow-2xs"
                                >
                                    {userSaving ? 'Saving...' : (editingUser ? 'Update Staff' : 'Allocate Staff')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ── Supplier Modal ───────────────────────────────────────────── */}
            {supplierModalOpen && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in">
                    <div className="bg-card border border-border rounded-none shadow-2xl w-full max-w-md p-5 space-y-3.5 text-card-foreground">
                        <div className="flex items-center justify-between pb-2.5 border-b border-border">
                            <div className="flex items-center gap-2">
                                <Truck size={16} className="text-foreground" />
                                <h3 className="font-sans text-sm font-bold text-foreground">
                                    {editingSupplier ? 'Edit Medicine Distributor' : 'Register Medicine Supplier'}
                                </h3>
                            </div>
                            <button onClick={() => setSupplierModalOpen(false)} className="text-muted-foreground hover:text-foreground cursor-pointer">
                                <X size={16} />
                            </button>
                        </div>

                        <form onSubmit={handleSaveSupplier} className="space-y-3 text-xs">
                            <div>
                                <label className="block font-bold uppercase tracking-wider text-[11px] font-mono text-foreground/80 mb-1">
                                    Distributor Agency Name *
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={supplierForm.name}
                                    onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                                    placeholder="e.g. Shree Pharma Distributors"
                                    className="w-full bg-background border border-border rounded-none px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                />
                            </div>

                            <div>
                                <label className="block font-bold uppercase tracking-wider text-[11px] font-mono text-foreground/80 mb-1">
                                    Username (Portal Login) *
                                </label>
                                <input
                                    type="text"
                                    required
                                    disabled={Boolean(editingSupplier)}
                                    value={supplierForm.username}
                                    onChange={(e) => setSupplierForm({ ...supplierForm, username: e.target.value })}
                                    placeholder="e.g. shreepharma"
                                    className="w-full bg-background border border-border rounded-none px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60 font-mono"
                                />
                            </div>

                            <div>
                                <label className="block font-bold uppercase tracking-wider text-[11px] font-mono text-foreground/80 mb-1">
                                    Official Email Address *
                                </label>
                                <input
                                    type="email"
                                    required
                                    value={supplierForm.email}
                                    onChange={(e) => setSupplierForm({ ...supplierForm, email: e.target.value })}
                                    placeholder="e.g. orders@shreepharma.com"
                                    className="w-full bg-background border border-border rounded-none px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                                />
                            </div>

                            {!editingSupplier && (
                                <div>
                                    <label className="block font-bold uppercase tracking-wider text-[11px] font-mono text-foreground/80 mb-1">
                                        Initial Password (defaults to vendor123)
                                    </label>
                                    <input
                                        type="password"
                                        value={supplierForm.password}
                                        onChange={(e) => setSupplierForm({ ...supplierForm, password: e.target.value })}
                                        placeholder="vendor123"
                                        className="w-full bg-background border border-border rounded-none px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block font-bold uppercase tracking-wider text-[11px] font-mono text-foreground/80 mb-1">
                                    Authorized Branch Counters
                                </label>
                                <div className="space-y-1 max-h-28 overflow-y-auto p-2 bg-background border border-border">
                                    {locations.map((loc) => {
                                        const isChecked = supplierForm.location_ids.includes(loc.id);
                                        return (
                                            <label key={loc.id} className="flex items-center gap-2 cursor-pointer text-foreground text-[11px]">
                                                <input
                                                    type="checkbox"
                                                    checked={isChecked}
                                                    onChange={() => {
                                                        const updated = isChecked
                                                            ? supplierForm.location_ids.filter((id) => id !== loc.id)
                                                            : [...supplierForm.location_ids, loc.id];
                                                        setSupplierForm({ ...supplierForm, location_ids: updated });
                                                    }}
                                                    className="rounded-none accent-primary"
                                                />
                                                <span>{loc.name}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="pt-2.5 border-t border-border flex items-center justify-end gap-2">
                                <button
                                    type="button"
                                    onClick={() => setSupplierModalOpen(false)}
                                    className="px-3 py-1.5 bg-accent hover:bg-accent/80 text-foreground border border-border font-semibold rounded-none transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={supplierSaving}
                                    className="flex items-center gap-1.5 px-4 py-1.5 bg-primary hover:bg-black text-primary-foreground font-bold rounded-none transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
                                >
                                    {supplierSaving && <Loader2 size={12} className="animate-spin" />}
                                    <span>{editingSupplier ? 'Save Changes' : 'Register Supplier'}</span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
