import React, { useState, useEffect } from 'react';
import {
    Building2,
    Store,
    Plus,
    Edit3,
    Trash2,
    CheckCircle2,
    AlertCircle,
    Save,
    RefreshCw,
    Shield,
    MapPin,
    Phone,
    Mail,
    FileBadge,
    FileCheck2,
    Power,
    Percent,
    Tag,
    X,
    Loader2
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useGuest } from '../../context/GuestContext';

export default function OrganizationSettings() {
    const { user } = useAuth();
    const { isGuest, showAuthModal } = useGuest();

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);

    // Organization details state
    const [orgData, setOrgData] = useState({
        name: '',
        slug: '',
        plan: 'single_pharmacy',
        address: '',
        phone: '',
        email: '',
        gstin: '',
        dl_number: '',
        settings: {},
        branches: [],
        total_branches: 0,
        active_branches: 0,
    });

    // Branch modal state
    const [isBranchModalOpen, setIsBranchModalOpen] = useState(false);
    const [editingBranch, setEditingBranch] = useState(null);
    const [branchForm, setBranchForm] = useState({
        name: '',
        type: 'retail_counter',
        region: 'North',
        address: '',
        phone: '',
        pincode: '',
        radius_meters: 500,
    });
    const [branchSaving, setBranchSaving] = useState(false);

    // Delete confirmation state
    const [deleteCandidate, setDeleteCandidate] = useState(null);
    const [deleting, setDeleting] = useState(false);

    // Discount policy state
    const [discountModel, setDiscountModel] = useState('none');
    const [flatPct, setFlatPct] = useState('');
    const [tieredSlabs, setTieredSlabs] = useState([
        { min_bill: 0,    max_bill: 499,  discount_pct: 0  },
        { min_bill: 500,  max_bill: 1999, discount_pct: 5  },
        { min_bill: 2000, max_bill: 9999, discount_pct: 10 },
        { min_bill: 10000, max_bill: null, discount_pct: 15 },
    ]);
    const [discountSaving, setDiscountSaving] = useState(false);
    const [discountMsg, setDiscountMsg] = useState(null);
    const [discountErr, setDiscountErr] = useState(null);

    const fetchOrgData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/admin/organization', {
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });
            if (res.ok) {
                const json = await res.json();
                if (json.success && json.data) {
                    setOrgData({
                        name: json.data.name || '',
                        slug: json.data.slug || '',
                        plan: json.data.plan || 'single_pharmacy',
                        address: json.data.address || '',
                        phone: json.data.phone || '',
                        email: json.data.email || '',
                        gstin: json.data.gstin || '',
                        dl_number: json.data.dl_number || '',
                        settings: json.data.settings || {},
                        branches: json.data.branches || [],
                        total_branches: json.data.total_branches || 0,
                        active_branches: json.data.active_branches || 0,
                    });
                    // Hydrate discount state from org.settings
                    const s = json.data.settings || {};
                    setDiscountModel(s.discount_model || 'none');
                    setFlatPct(s.flat_discount_pct != null ? String(s.flat_discount_pct) : '');
                    if (s.tiered_discount_config && s.tiered_discount_config.length > 0) {
                        setTieredSlabs(s.tiered_discount_config);
                    }
                }
            } else if (res.status === 401 || res.status === 403) {
                if (isGuest) {
                    // Provide fallback demo view for guests
                    setOrgData({
                        name: 'Apollo Chemist & Healthcare Store',
                        slug: 'apollo-chemist-demo',
                        plan: 'single_pharmacy',
                        address: 'Shop 12, Main Market, Connaught Place, New Delhi',
                        phone: '+91 98765 43210',
                        email: 'contact@apollopharmacy.example.com',
                        gstin: '07AAAAA0000A1Z5',
                        dl_number: 'DL-20B-12345/21B-67890',
                        settings: { auto_reorder: true, fefo_warning_days: 60 },
                        branches: [
                            {
                                id: 1,
                                name: 'Main Retail Counter',
                                type: 'retail_counter',
                                region: 'Delhi NCR',
                                address: 'Shop 12, Main Market',
                                phone: '+91 98765 43210',
                                pincode: '110001',
                                radius_meters: 500,
                                is_active: true,
                            },
                            {
                                id: 2,
                                name: 'Cold Storage Vault (Biologics)',
                                type: 'cold_storage',
                                region: 'Delhi NCR',
                                address: 'Basement Storage A',
                                phone: '+91 98765 43211',
                                pincode: '110001',
                                radius_meters: 100,
                                is_active: true,
                            },
                        ],
                        total_branches: 2,
                        active_branches: 2,
                    });
                } else {
                    setError('Unauthorized. Please log in as an administrator.');
                }
            } else {
                setError('Failed to load store organization settings.');
            }
        } catch (err) {
            setError(err.message || 'Network error loading store settings.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrgData();
    }, [isGuest]);

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        if (isGuest) {
            showAuthModal('Sign in as Admin to update store profile.');
            return;
        }

        setSaving(true);
        setMessage(null);
        setError(null);

        try {
            const res = await fetch('/api/admin/organization', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    name: orgData.name,
                    address: orgData.address,
                    phone: orgData.phone,
                    email: orgData.email,
                    gstin: orgData.gstin,
                    dl_number: orgData.dl_number,
                }),
            });

            const json = await res.json();
            if (res.ok && json.success) {
                setMessage('Store profile updated successfully.');
                setTimeout(() => setMessage(null), 3000);
            } else {
                setError(json.detail || json.message || 'Failed to update store profile.');
            }
        } catch (err) {
            setError(err.message || 'Network error saving store profile.');
        } finally {
            setSaving(false);
        }
    };

    const handleOpenAddBranch = () => {
        if (isGuest) {
            showAuthModal('Sign in to add new branch counters.');
            return;
        }
        setEditingBranch(null);
        setBranchForm({
            name: '',
            type: 'retail_counter',
            region: 'Default Region',
            address: '',
            phone: '',
            pincode: '',
            radius_meters: 500,
        });
        setIsBranchModalOpen(true);
    };

    const handleOpenEditBranch = (branch) => {
        if (isGuest) {
            showAuthModal('Sign in to edit branch locations.');
            return;
        }
        setEditingBranch(branch);
        setBranchForm({
            name: branch.name || '',
            type: branch.type || 'retail_counter',
            region: branch.region || 'Default Region',
            address: branch.address || '',
            phone: branch.phone || '',
            pincode: branch.pincode || '',
            radius_meters: branch.radius_meters || 500,
        });
        setIsBranchModalOpen(true);
    };

    const handleSaveBranch = async (e) => {
        e.preventDefault();
        setBranchSaving(true);
        setError(null);

        try {
            const url = editingBranch
                ? `/api/inventory/locations/${editingBranch.id}`
                : '/api/inventory/locations';
            const method = editingBranch ? 'PATCH' : 'POST';

            const res = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(branchForm),
            });

            const json = await res.json();
            if (res.ok && json.success) {
                setMessage(editingBranch ? 'Branch updated successfully.' : 'New branch created successfully.');
                setIsBranchModalOpen(false);
                fetchOrgData();
                setTimeout(() => setMessage(null), 3000);
            } else {
                setError(json.detail || json.message || 'Failed to save branch counter.');
            }
        } catch (err) {
            setError(err.message || 'Error saving branch counter.');
        } finally {
            setBranchSaving(false);
        }
    };

    const handleToggleBranchActive = async (branch) => {
        if (isGuest) {
            showAuthModal('Sign in to manage branch counter status.');
            return;
        }
        try {
            const res = await fetch(`/api/inventory/locations/${branch.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ is_active: !branch.is_active }),
            });
            const json = await res.json();
            if (res.ok && json.success) {
                fetchOrgData();
            } else {
                setError(json.detail || json.message || 'Failed to update branch status.');
            }
        } catch (err) {
            setError(err.message || 'Error updating branch status.');
        }
    };

    const handleConfirmDelete = async () => {
        if (!deleteCandidate) return;
        setDeleting(true);
        setError(null);
        try {
            const res = await fetch(`/api/inventory/locations/${deleteCandidate.id}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            const json = await res.json();
            if (res.ok && json.success) {
                setMessage(json.message);
                setDeleteCandidate(null);
                fetchOrgData();
                setTimeout(() => setMessage(null), 3000);
            } else {
                setError(json.detail || json.message || 'Failed to delete/archive branch.');
            }
        } catch (err) {
            setError(err.message || 'Error deleting branch.');
        } finally {
            setDeleting(false);
        }
    };

    // ── Discount helpers ──────────────────────────────────────────────────
    const handleSaveDiscount = async () => {
        if (isGuest) { showAuthModal('Sign in to update discount settings'); return; }
        setDiscountSaving(true);
        setDiscountMsg(null);
        setDiscountErr(null);
        try {
            const body = {
                discount_model: discountModel,
                flat_discount_pct: parseFloat(flatPct) || 0,
                tiered_discount_config: tieredSlabs.map(s => ({
                    min_bill:     parseFloat(s.min_bill)     || 0,
                    max_bill:     s.max_bill != null && s.max_bill !== '' ? parseFloat(s.max_bill) : null,
                    discount_pct: parseFloat(s.discount_pct) || 0,
                })),
                manual_discount_cap_pct: 20,
            };
            const res = await fetch('/api/admin/discount-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(body),
            });
            const json = await res.json();
            if (res.ok && json.success) {
                setDiscountMsg('Discount policy saved successfully.');
                setTimeout(() => setDiscountMsg(null), 3000);
            } else {
                const errs = json.detail?.errors || [json.detail || json.message || 'Failed to save'];
                setDiscountErr(Array.isArray(errs) ? errs.join(' • ') : String(errs));
            }
        } catch (e) {
            setDiscountErr(e.message || 'Error saving discount policy.');
        } finally {
            setDiscountSaving(false);
        }
    };

    const addSlab = () => setTieredSlabs(prev => [
        ...prev,
        { min_bill: '', max_bill: '', discount_pct: '' }
    ]);

    const removeSlab = (idx) => setTieredSlabs(prev => prev.filter((_, i) => i !== idx));

    const updateSlab = (idx, field, val) => {
        setTieredSlabs(prev => prev.map((s, i) =>
            i === idx ? { ...s, [field]: val } : s
        ));
    };

    return (
        <div className="p-6 md:p-8 max-w-[1560px] mx-auto space-y-6 animate-in fade-in duration-150">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
                <div>
                    <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 font-mono">
                        <Store size={14} className="text-foreground" />
                        <span>Pharmacy Business & Branches</span>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                        <h1 className="font-sans text-2xl font-bold text-foreground tracking-tight">
                            Store Profile & Counter Setup
                        </h1>
                        {/* Brand / Branch Summary in small text in header */}
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-accent/60 border border-border rounded-none text-xs font-mono text-muted-foreground">
                            <span><strong className="text-foreground font-bold">{orgData.total_branches}</strong> Total Branches</span>
                            <span>•</span>
                            <span><strong className="text-emerald-700 font-bold">{orgData.active_branches}</strong> Active Counters</span>
                        </div>
                    </div>
                    <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                        Manage your chemist legal profile, drug licenses, GSTIN, and branch locations.
                    </p>
                </div>

                <div className="flex items-center gap-2.5">
                    <button
                        onClick={fetchOrgData}
                        disabled={loading}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-foreground bg-accent border border-border rounded-none hover:bg-accent/80 transition-colors cursor-pointer"
                    >
                        <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        <span>Refresh</span>
                    </button>
                    <button
                        onClick={handleOpenAddBranch}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-primary-foreground bg-primary border border-primary rounded-none hover:bg-black transition-all cursor-pointer"
                    >
                        <Plus size={14} />
                        <span>Add Branch Counter</span>
                    </button>
                </div>
            </div>

            {/* Notification messages */}
            {message && (
                <div className="p-3.5 rounded-none bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-medium flex items-center justify-between animate-in fade-in">
                    <div className="flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-emerald-700 shrink-0" />
                        <span>{message}</span>
                    </div>
                    <button onClick={() => setMessage(null)} className="text-xs font-bold text-emerald-800 hover:underline">
                        Dismiss
                    </button>
                </div>
            )}

            {error && (
                <div className="p-3.5 rounded-none bg-rose-50 border border-rose-300 text-rose-900 text-xs font-medium flex items-center justify-between animate-in fade-in">
                    <div className="flex items-center gap-2">
                        <AlertCircle size={16} className="text-rose-700 shrink-0" />
                        <span>{error}</span>
                    </div>
                    <button onClick={() => setError(null)} className="text-xs font-bold text-rose-800 hover:underline">
                        Dismiss
                    </button>
                </div>
            )}

            {/* Main Content Grid: 3 Cards Side by Side */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                {/* ── 1. Store Profile ── */}
                <div className="bg-card border border-border rounded-none p-6 space-y-5">
                        <div className="flex items-center justify-between border-b border-border pb-3">
                            <div className="flex items-center gap-2">
                                <Building2 size={16} className="text-foreground" />
                                <h2 className="text-sm font-bold text-foreground uppercase tracking-wider font-mono">Store Profile</h2>
                            </div>
                            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-none bg-accent text-foreground border border-border font-mono">
                                {orgData.plan.replace('_', ' ')}
                            </span>
                        </div>

                        <form onSubmit={handleSaveProfile} className="space-y-4">
                            <div>
                                <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                    Pharmacy / Store Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={orgData.name}
                                    onChange={(e) => setOrgData({ ...orgData, name: e.target.value })}
                                    placeholder="e.g. Sharma Medicos & Chemist"
                                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                    Drug License No. (DL No.)
                                </label>
                                <div className="relative">
                                    <FileBadge className="absolute left-3 top-2.5 text-muted-foreground" size={15} />
                                    <input
                                        type="text"
                                        value={orgData.dl_number}
                                        onChange={(e) => setOrgData({ ...orgData, dl_number: e.target.value })}
                                        placeholder="e.g. DL-20B-12345 / 21B-67890"
                                        className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground font-mono text-xs"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                    GSTIN / Tax ID
                                </label>
                                <div className="relative">
                                    <FileCheck2 className="absolute left-3 top-2.5 text-muted-foreground" size={15} />
                                    <input
                                        type="text"
                                        value={orgData.gstin}
                                        onChange={(e) => setOrgData({ ...orgData, gstin: e.target.value })}
                                        placeholder="e.g. 07AAAAA0000A1Z5"
                                        className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground font-mono text-xs uppercase"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                        Contact Phone
                                    </label>
                                    <div className="relative">
                                        <Phone className="absolute left-3 top-2.5 text-muted-foreground" size={14} />
                                        <input
                                            type="text"
                                            value={orgData.phone}
                                            onChange={(e) => setOrgData({ ...orgData, phone: e.target.value })}
                                            placeholder="+91 98765..."
                                            className="w-full pl-8 pr-2 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                        Store Email
                                    </label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-2.5 text-muted-foreground" size={14} />
                                        <input
                                            type="email"
                                            value={orgData.email}
                                            onChange={(e) => setOrgData({ ...orgData, email: e.target.value })}
                                            placeholder="store@domain..."
                                            className="w-full pl-8 pr-2 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-foreground/80 mb-1">
                                    Headquarters / Main Store Address
                                </label>
                                <div className="relative">
                                    <MapPin className="absolute left-3 top-2.5 text-muted-foreground" size={15} />
                                    <textarea
                                        rows={3}
                                        value={orgData.address}
                                        onChange={(e) => setOrgData({ ...orgData, address: e.target.value })}
                                        placeholder="Full street address, market name, city, state"
                                        className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={saving}
                                className="w-full py-2.5 px-4 bg-primary hover:bg-black text-primary-foreground font-bold text-xs rounded-none transition-all flex items-center justify-center gap-2 cursor-pointer"
                            >
                                {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={14} />}
                                <span>{saving ? 'Saving Profile...' : 'Save Store Profile'}</span>
                            </button>
                        </form>
                    </div>

                    {/* ── 2. Customer Discount Policy ── */}
                    <div className="bg-card border border-border rounded-none p-6 space-y-4">
                        <div className="flex items-center gap-2 border-b border-border pb-3">
                            <Tag size={16} className="text-foreground" />
                            <h2 className="text-sm font-bold text-foreground uppercase tracking-wider font-mono">Customer Discount Policy</h2>
                        </div>

                        {discountMsg && (
                            <div className="p-3 rounded-none bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs flex items-center gap-2 animate-in fade-in">
                                <CheckCircle2 size={14} className="text-emerald-700 shrink-0" />
                                <span>{discountMsg}</span>
                                <button onClick={() => setDiscountMsg(null)} className="ml-auto text-emerald-800 font-bold">✕</button>
                            </div>
                        )}
                        {discountErr && (
                            <div className="p-3 rounded-none bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2 animate-in fade-in">
                                <AlertCircle size={14} className="text-rose-700 shrink-0" />
                                <span>{discountErr}</span>
                                <button onClick={() => setDiscountErr(null)} className="ml-auto text-rose-800 font-bold">✕</button>
                            </div>
                        )}

                        {/* Model selector */}
                        <div className="space-y-2">
                            <p className="text-xs font-semibold text-foreground/80 uppercase tracking-wider font-mono">Discount Model</p>
                            {[
                                ['none',   'No Discount (Full MRP always)'],
                                ['flat',   'Flat % — same % off every bill'],
                                ['tiered', 'Tiered Slabs — % based on bill total'],
                            ].map(([val, label]) => (
                                <label key={val} className={`flex items-center gap-3 p-2.5 rounded-none border cursor-pointer transition-all ${
                                    discountModel === val
                                        ? 'border-primary bg-accent font-semibold text-foreground'
                                        : 'border-border hover:border-border/80 bg-background text-foreground'
                                }`}>
                                    <input
                                        type="radio" name="discount_model" value={val}
                                        checked={discountModel === val}
                                        onChange={() => setDiscountModel(val)}
                                        className="accent-primary"
                                    />
                                    <span className="text-xs text-foreground">{label}</span>
                                </label>
                            ))}
                        </div>

                        {/* Flat model: single pct input */}
                        {discountModel === 'flat' && (
                            <div>
                                <label className="block text-xs font-semibold text-foreground/80 mb-1.5">
                                    Flat Discount Percentage
                                </label>
                                <div className="relative">
                                    <Percent className="absolute left-3 top-2.5 text-muted-foreground" size={13} />
                                    <input
                                        type="number" min="0.1" max="100" step="0.5"
                                        value={flatPct}
                                        onChange={e => setFlatPct(e.target.value)}
                                        placeholder="e.g. 10"
                                        className="w-full pl-8 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground font-mono"
                                    />
                                </div>
                                <p className="text-[11px] text-muted-foreground mt-1.5">
                                    Every bill gets this % off regardless of total amount.
                                </p>
                            </div>
                        )}

                        {/* Tiered model: slab table */}
                        {discountModel === 'tiered' && (
                            <div className="space-y-3">
                                <p className="text-xs font-semibold text-foreground/80 uppercase tracking-wider font-mono">Discount Slabs</p>
                                <div className="space-y-2">
                                    {tieredSlabs.map((slab, idx) => (
                                        <div key={idx} className="flex items-center gap-1.5 bg-background border border-border rounded-none p-2">
                                            <span className="text-[11px] font-bold text-muted-foreground shrink-0">₹</span>
                                            <input
                                                type="number" placeholder="Min"
                                                value={slab.min_bill ?? ''}
                                                onChange={e => updateSlab(idx, 'min_bill', e.target.value)}
                                                className="w-20 px-2 py-1 text-xs border border-border rounded-none text-foreground bg-card focus:outline-none focus:border-primary font-mono"
                                            />
                                            <span className="text-[11px] text-muted-foreground">–</span>
                                            <input
                                                type="number" placeholder="Max (∞)"
                                                value={slab.max_bill ?? ''}
                                                onChange={e => updateSlab(idx, 'max_bill', e.target.value === '' ? null : e.target.value)}
                                                className="w-24 px-2 py-1 text-xs border border-border rounded-none text-foreground bg-card focus:outline-none focus:border-primary font-mono"
                                            />
                                            <span className="text-[11px] text-muted-foreground">→</span>
                                            <input
                                                type="number" min="0" max="100" step="0.5" placeholder="%"
                                                value={slab.discount_pct ?? ''}
                                                onChange={e => updateSlab(idx, 'discount_pct', e.target.value)}
                                                className="w-14 px-2 py-1 text-xs border border-border rounded-none text-foreground bg-card focus:outline-none focus:border-primary font-mono"
                                            />
                                            <span className="text-[11px] text-foreground font-bold">%</span>
                                            <button
                                                onClick={() => removeSlab(idx)}
                                                disabled={tieredSlabs.length === 1}
                                                className="ml-auto p-1 text-muted-foreground hover:text-rose-600 transition-colors disabled:opacity-30 cursor-pointer"
                                                title="Remove slab"
                                            ><Trash2 size={12} /></button>
                                        </div>
                                    ))}
                                </div>
                                <button
                                    onClick={addSlab}
                                    className="flex items-center gap-1.5 text-xs font-bold text-foreground hover:text-[#F26A4B] transition-colors cursor-pointer"
                                >
                                    <Plus size={13} /> Add Slab
                                </button>
                                <p className="text-[11px] text-muted-foreground">
                                    Leave Max blank for highest slab (no ceiling). Slabs are evaluated top-to-bottom.
                                </p>
                            </div>
                        )}

                        {discountModel === 'none' && (
                            <p className="text-xs text-muted-foreground bg-background rounded-none px-3.5 py-3 border border-border">
                                No discount applied. Customers pay full MRP on every bill.
                            </p>
                        )}

                        <button
                            onClick={handleSaveDiscount}
                            disabled={discountSaving}
                            className="w-full py-2.5 px-4 bg-primary hover:bg-black text-primary-foreground font-bold text-xs rounded-none transition-all flex items-center justify-center gap-2 cursor-pointer"
                        >
                            {discountSaving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                            <span>{discountSaving ? 'Saving Policy...' : 'Save Discount Policy'}</span>
                        </button>
                    </div>

                {/* ── 3. Branch & Counter Locations ── */}
                <div className="bg-card border border-border rounded-none p-6 space-y-5">
                        <div className="flex items-center justify-between border-b border-border pb-4">
                            <div>
                                <h2 className="font-mono text-sm font-bold text-foreground uppercase tracking-wider">Branch & Counter Locations</h2>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    Counter staff and medicine stocks are strictly partitioned across these locations.
                                </p>
                            </div>
                            <button
                                onClick={handleOpenAddBranch}
                                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-foreground bg-accent border border-border rounded-none hover:bg-accent/80 transition-colors cursor-pointer"
                            >
                                <Plus size={14} />
                                <span>Add Branch</span>
                            </button>
                        </div>

                        {loading ? (
                            <div className="p-8 text-center text-muted-foreground text-xs font-mono">
                                Loading branches...
                            </div>
                        ) : orgData.branches.length === 0 ? (
                            <div className="p-8 text-center border-2 border-dashed border-border rounded-none space-y-3">
                                <Store className="w-8 h-8 text-muted-foreground mx-auto" />
                                <div>
                                    <p className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">No branch counters configured</p>
                                    <p className="text-xs text-muted-foreground mt-1">Add your main pharmacy counter to begin dispensing medicines.</p>
                                </div>
                                <button
                                    onClick={handleOpenAddBranch}
                                    className="px-4 py-2 text-xs font-bold text-primary-foreground bg-primary rounded-none hover:bg-black cursor-pointer"
                                >
                                    Create Primary Counter
                                </button>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-3.5">
                                {orgData.branches.map((b) => (
                                    <div
                                        key={b.id}
                                        className={`p-4 rounded-none border transition-all flex flex-col justify-between ${
                                            b.is_active
                                                ? 'bg-background border-border hover:border-primary/40'
                                                : 'bg-accent/50 border-border opacity-70'
                                        }`}
                                    >
                                        <div className="space-y-2">
                                            <div className="flex items-start justify-between gap-2">
                                                <div>
                                                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground font-mono">
                                                        ID: #{b.id} • {b.region}
                                                    </span>
                                                    <h3 className="font-sans text-sm font-bold text-foreground leading-tight">
                                                        {b.name}
                                                    </h3>
                                                </div>
                                                <span
                                                    className={`px-2 py-0.5 rounded-none text-[10px] font-bold uppercase tracking-wider font-mono ${
                                                        b.is_active
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted text-foreground'
                                                    }`}
                                                >
                                                    {b.is_active ? 'Active' : 'Archived'}
                                                </span>
                                            </div>

                                            <div className="text-xs text-muted-foreground space-y-1 pt-1 font-sans">
                                                <p className="flex items-center gap-1.5">
                                                    <span className="font-semibold text-foreground">Type:</span>
                                                    <span className="capitalize">{b.type.replace('_', ' ')}</span>
                                                </p>
                                                {b.address && (
                                                    <p className="truncate" title={b.address}>
                                                        <span className="font-semibold text-foreground">Address:</span> {b.address}
                                                    </p>
                                                )}
                                                {b.phone && (
                                                    <p>
                                                        <span className="font-semibold text-foreground">Phone:</span> {b.phone}
                                                    </p>
                                                )}
                                                <p>
                                                    <span className="font-semibold text-foreground">Radius:</span> {b.radius_meters || 500}m counter boundary
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between pt-3 mt-3 border-t border-border">
                                            <button
                                                onClick={() => handleToggleBranchActive(b)}
                                                className={`text-[11px] font-bold flex items-center gap-1 hover:underline cursor-pointer ${
                                                    b.is_active ? 'text-amber-700' : 'text-foreground'
                                                }`}
                                            >
                                                <Power size={12} />
                                                <span>{b.is_active ? 'Deactivate' : 'Activate'}</span>
                                            </button>

                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => handleOpenEditBranch(b)}
                                                    className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded-none transition-colors cursor-pointer"
                                                    title="Edit branch"
                                                >
                                                    <Edit3 size={14} />
                                                </button>
                                                <button
                                                    onClick={() => setDeleteCandidate(b)}
                                                    className="p-1.5 text-muted-foreground hover:text-rose-600 hover:bg-rose-50 rounded-none transition-colors cursor-pointer"
                                                    title="Delete or archive branch"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
            </div>

            {/* ── Modal: Add / Edit Branch ──────────────────────────────────────── */}
            {isBranchModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
                    <div className="bg-card border border-border rounded-none shadow-2xl max-w-lg w-full p-6 space-y-4 text-card-foreground">
                        <div className="flex items-center justify-between pb-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <Store size={18} className="text-foreground" />
                                <h3 className="font-sans text-sm font-bold text-foreground uppercase tracking-wider">
                                    {editingBranch ? 'Edit Branch Counter' : 'Add New Pharmacy Counter'}
                                </h3>
                            </div>
                            <button
                                onClick={() => setIsBranchModalOpen(false)}
                                className="p-1 text-muted-foreground hover:text-foreground hover:bg-accent rounded-none"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <form onSubmit={handleSaveBranch} className="space-y-3.5">
                            <div>
                                <label className="block text-xs font-semibold text-foreground mb-1">
                                    Branch / Counter Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={branchForm.name}
                                    onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
                                    placeholder="e.g. Durgapur Station Road Branch"
                                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs font-semibold text-foreground mb-1">
                                        Counter Type
                                    </label>
                                    <select
                                        value={branchForm.type}
                                        onChange={(e) => setBranchForm({ ...branchForm, type: e.target.value })}
                                        className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                    >
                                        <option value="retail_counter">Retail Counter</option>
                                        <option value="hospital_pharmacy">Hospital Pharmacy</option>
                                        <option value="warehouse">Storage Godown</option>
                                        <option value="clinic_dispensary">Clinic Dispensary</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-foreground mb-1">
                                        Region / District
                                    </label>
                                    <input
                                        type="text"
                                        value={branchForm.region}
                                        onChange={(e) => setBranchForm({ ...branchForm, region: e.target.value })}
                                        placeholder="e.g. West Bengal"
                                        className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs font-semibold text-foreground mb-1">
                                        Phone Number
                                    </label>
                                    <input
                                        type="text"
                                        value={branchForm.phone}
                                        onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
                                        placeholder="+91..."
                                        className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-foreground mb-1">
                                        PIN Code
                                    </label>
                                    <input
                                        type="text"
                                        value={branchForm.pincode}
                                        onChange={(e) => setBranchForm({ ...branchForm, pincode: e.target.value })}
                                        placeholder="110001"
                                        className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs font-mono"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-foreground mb-1">
                                    Address
                                </label>
                                <input
                                    type="text"
                                    value={branchForm.address}
                                    onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
                                    placeholder="Shop number, street, landmark"
                                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground text-xs"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-foreground mb-1">
                                    Geofence Radius (meters)
                                </label>
                                <input
                                    type="number"
                                    min="50"
                                    max="50000"
                                    value={branchForm.radius_meters}
                                    onChange={(e) => setBranchForm({ ...branchForm, radius_meters: parseInt(e.target.value) || 500 })}
                                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary text-foreground font-mono"
                                />
                            </div>

                            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                                <button
                                    type="button"
                                    onClick={() => setIsBranchModalOpen(false)}
                                    className="px-4 py-2 text-xs font-semibold text-foreground bg-accent border border-border rounded-none hover:bg-accent/80 cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={branchSaving}
                                    className="px-5 py-2 text-xs font-bold text-primary-foreground bg-primary rounded-none hover:bg-black transition-all flex items-center gap-1.5 cursor-pointer"
                                >
                                    {branchSaving && <Loader2 size={12} className="animate-spin" />}
                                    <span>{branchSaving ? 'Saving...' : editingBranch ? 'Update Branch' : 'Add Branch'}</span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ── Modal: Safe Delete/Archive Confirmation ──────────────────────── */}
            {deleteCandidate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
                    <div className="bg-card border border-border rounded-none shadow-2xl max-w-md w-full p-6 space-y-4 text-card-foreground">
                        <div className="flex items-center gap-3 text-amber-700">
                            <AlertCircle size={22} />
                            <h3 className="font-sans text-sm font-bold text-foreground uppercase tracking-wider">Remove Branch Counter?</h3>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                            Are you sure you want to remove <strong className="text-foreground">{deleteCandidate.name}</strong>?
                            <br /><br />
                            <strong>Business rule:</strong> If historical stock or dispense transactions exist for this branch, it will be <strong>safely archived</strong> (deactivated) to preserve audit trails. If no transaction history exists, it will be permanently deleted.
                        </p>
                        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                            <button
                                type="button"
                                disabled={deleting}
                                onClick={() => setDeleteCandidate(null)}
                                className="px-4 py-2 text-xs font-semibold text-foreground bg-accent border border-border rounded-none hover:bg-accent/80 cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                disabled={deleting}
                                onClick={handleConfirmDelete}
                                className="px-4 py-2 text-xs font-bold text-white bg-rose-700 hover:bg-rose-800 rounded-none transition-all flex items-center gap-1.5 cursor-pointer"
                            >
                                {deleting && <Loader2 size={12} className="animate-spin" />}
                                <span>{deleting ? 'Processing...' : 'Confirm Removal'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
