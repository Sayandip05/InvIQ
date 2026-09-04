import React, { useState, useEffect } from 'react';
import { inventory } from '../../services/api';
import { Search, Filter, AlertCircle, CheckCircle, AlertTriangle, Building2, Layers, Plus, Trash2, X, Tag } from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

const Inventory = () => {
    const [locations, setLocations] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // Modal state for Packaging Management
    const [selectedItemForPkg, setSelectedItemForPkg] = useState(null);
    const [packagings, setPackagings] = useState([]);
    const [loadingPkg, setLoadingPkg] = useState(false);
    const [pkgForm, setPkgForm] = useState({
        unit_name: '',
        multiplier: 10,
        barcode: '',
        mrp: '',
        purchase_rate: '',
        is_default_dispense: false,
        is_default_purchase: false,
    });
    const [pkgError, setPkgError] = useState('');
    const [pkgSuccess, setPkgSuccess] = useState('');

    const fetchLocations = async () => {
        try {
            const response = await inventory.getLocations();
            if (response.data.success) {
                setLocations(response.data.data);
                if (response.data.data.length > 0 && !selectedLocation) {
                    setSelectedLocation(response.data.data[0].id);
                }
            }
        } catch (err) {
            console.error("Failed to fetch locations", err);
        }
    };

    useEffect(() => {
        fetchLocations();
    }, []);

    const fetchItems = async () => {
        if (!selectedLocation) return;
        setLoading(true);
        try {
            const response = await inventory.getLocationItems(selectedLocation);
            if (response.data.success) {
                setItems(response.data.data);
            }
        } catch (err) {
            console.error("Failed to fetch items", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchItems();
    }, [selectedLocation]);

    const openPackagingModal = async (item) => {
        setSelectedItemForPkg(item);
        setPkgError('');
        setPkgSuccess('');
        setPkgForm({
            unit_name: '',
            multiplier: 10,
            barcode: '',
            mrp: '',
            purchase_rate: '',
            is_default_dispense: false,
            is_default_purchase: false,
        });
        setLoadingPkg(true);
        try {
            const res = await inventory.getPackagings(item.id);
            if (res.data.success) {
                setPackagings(res.data.data || []);
            }
        } catch (err) {
            setPkgError('Failed to load packaging tiers');
        } finally {
            setLoadingPkg(false);
        }
    };

    const handleAddPackaging = async (e) => {
        e.preventDefault();
        if (!pkgForm.unit_name.trim()) {
            setPkgError('Unit name is required (e.g. Strip, Box)');
            return;
        }
        if (pkgForm.multiplier < 1) {
            setPkgError('Multiplier must be at least 1');
            return;
        }
        setPkgError('');
        setPkgSuccess('');
        try {
            const payload = {
                unit_name: pkgForm.unit_name.trim().toLowerCase(),
                multiplier: parseInt(pkgForm.multiplier),
                barcode: pkgForm.barcode.trim() || null,
                mrp: pkgForm.mrp ? parseFloat(pkgForm.mrp) : null,
                purchase_rate: pkgForm.purchase_rate ? parseFloat(pkgForm.purchase_rate) : null,
                is_default_dispense: pkgForm.is_default_dispense,
                is_default_purchase: pkgForm.is_default_purchase,
            };
            const res = await inventory.addPackaging(selectedItemForPkg.id, payload);
            if (res.data.success) {
                setPkgSuccess(`Added ${pkgForm.unit_name}`);
                setPackagings(prev => [...prev, res.data.data]);
                setPkgForm({
                    unit_name: '',
                    multiplier: 10,
                    barcode: '',
                    mrp: '',
                    purchase_rate: '',
                    is_default_dispense: false,
                    is_default_purchase: false,
                });
                fetchItems();
            }
        } catch (err) {
            setPkgError(err.response?.data?.detail || err.message || 'Failed to add packaging tier');
        }
    };

    const handleDeletePackaging = async (pkgId) => {
        if (!confirm('Are you sure you want to remove this packaging tier?')) return;
        try {
            const res = await inventory.deletePackaging(selectedItemForPkg.id, pkgId);
            if (res.data.success) {
                setPackagings(prev => prev.filter(p => p.id !== pkgId));
                fetchItems();
            }
        } catch (err) {
            setPkgError('Failed to delete packaging tier');
        }
    };

    const filteredItems = items.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.category.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const getStatusBadge = (status) => {
        switch (status) {
            case 'HEALTHY':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-none text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle size={12} className="mr-1" /> Healthy
                    </span>
                );
            case 'WARNING':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-none text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <AlertTriangle size={12} className="mr-1" /> Low Stock
                    </span>
                );
            case 'CRITICAL':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-none text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
                        <AlertCircle size={12} className="mr-1" /> Critical
                    </span>
                );
            default:
                return null;
        }
    };

    return (
        <div className="flex flex-col min-h-full bg-background text-foreground">
            {/* Full-Width Top Navbar */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Inventory Management</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">Real-time SKU catalog and packaging unit configurations</p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        {/* Facility / Location Selector */}
                        <div className="relative flex items-center">
                            <Building2 size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                            <select
                                className="text-xs font-medium bg-background border border-border text-foreground rounded-md pl-8 pr-7 py-2 hover:bg-accent/40 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
                                value={selectedLocation}
                                onChange={(e) => setSelectedLocation(e.target.value)}
                            >
                                {locations.map(loc => (
                                    <option key={loc.id} value={loc.id}>{loc.name}</option>
                                ))}
                            </select>
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
                <div className="bg-card border border-border rounded-lg overflow-hidden shadow-xs">

                <div className="p-4 border-b border-border flex items-center justify-between gap-4">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={18} />
                        <input
                            type="text"
                            placeholder="Search by medicine name or category..."
                            className="w-full pl-10 pr-4 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring bg-background text-foreground text-sm"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="text-xs text-muted-foreground font-mono font-medium">
                        Showing {filteredItems.length} items
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-muted/40 text-muted-foreground font-semibold text-[11px] uppercase tracking-wider font-mono">
                            <tr>
                                <th className="px-6 py-3.5">Medicine Name</th>
                                <th className="px-6 py-3.5">Category</th>
                                <th className="px-6 py-3.5 text-center">Status</th>
                                <th className="px-6 py-3.5 text-right">Available Stock</th>
                                <th className="px-6 py-3.5">Packaging Hierarchy</th>
                                <th className="px-6 py-3.5 text-right">Min Stock</th>
                                <th className="px-6 py-3.5 text-center">UOM Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60 text-sm">
                            {loading ? (
                                <tr><td colSpan="7" className="text-center py-8 text-muted-foreground">Loading inventory...</td></tr>
                            ) : filteredItems.length === 0 ? (
                                <tr><td colSpan="7" className="text-center py-8 text-muted-foreground">No items found matching your filter.</td></tr>
                            ) : (
                                filteredItems.map((item) => (
                                    <tr key={item.id} className="hover:bg-accent/40 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-semibold text-foreground">{item.name}</div>
                                            <div className="text-xs text-muted-foreground">Base Unit: <span className="font-mono text-foreground">{item.base_unit || item.unit}</span></div>
                                        </td>
                                        <td className="px-6 py-4 text-muted-foreground capitalize">{item.category}</td>
                                        <td className="px-6 py-4 text-center">{getStatusBadge(item.status)}</td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="font-bold text-foreground">
                                                {item.current_stock?.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">{item.base_unit || item.unit}</span>
                                            </div>
                                            {item.stock_breakdown && (
                                                <div className="text-xs text-amber-700 font-medium mt-0.5">
                                                    {item.stock_breakdown}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-wrap gap-1">
                                                {item.packagings && item.packagings.length > 0 ? (
                                                    item.packagings.map(p => (
                                                        <span key={p.id} className="inline-flex items-center px-2 py-0.5 text-xs bg-secondary text-secondary-foreground border border-border rounded font-mono">
                                                            {p.unit_name} ({p.multiplier}x)
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="text-xs text-muted-foreground italic">Base unit only</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right text-muted-foreground font-mono font-medium">
                                            {item.min_stock} {item.base_unit || item.unit}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <button
                                                onClick={() => openPackagingModal(item)}
                                                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-secondary-foreground bg-secondary border border-border rounded-md hover:bg-accent transition-colors cursor-pointer"
                                            >
                                                <Layers size={13} />
                                                Packaging
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
            </div>

            {/* Packaging Configuration Modal */}
            {selectedItemForPkg && (
                <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-card text-card-foreground rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-border animate-in fade-in zoom-in-95 duration-150">
                        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
                            <div>
                                <h3 className="text-base font-sans font-bold text-foreground flex items-center gap-2">
                                    <Layers className="text-primary" size={18} />
                                    Packaging Tiers for {selectedItemForPkg.name}
                                </h3>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    Base Unit: <span className="font-semibold text-foreground font-mono">{selectedItemForPkg.base_unit || selectedItemForPkg.unit}</span> (Atomic Count)
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedItemForPkg(null)}
                                className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-accent cursor-pointer"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="p-5 overflow-y-auto space-y-6 flex-1">
                            {pkgError && (
                                <div className="p-3 text-xs bg-destructive/10 text-destructive border border-destructive/20 rounded-md">
                                    {pkgError}
                                </div>
                            )}
                            {pkgSuccess && (
                                <div className="p-3 text-xs bg-emerald-100/70 text-emerald-800 border border-emerald-300 rounded-md">
                                    {pkgSuccess}
                                </div>
                            )}

                            {/* Existing Tiers List */}
                            <div>
                                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider mb-2 font-mono">Registered Packaging Tiers</h4>
                                {loadingPkg ? (
                                    <div className="text-xs text-muted-foreground py-3">Loading packaging tiers...</div>
                                ) : packagings.length === 0 ? (
                                    <div className="text-xs text-muted-foreground italic p-3 bg-background rounded-md border border-border">
                                        No secondary packaging defined. This medicine is currently tracked solely in loose <span className="font-semibold">{selectedItemForPkg.base_unit || selectedItemForPkg.unit}</span>.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {packagings.map(pkg => (
                                            <div key={pkg.id} className="flex items-center justify-between p-3 bg-background border border-border rounded-md text-xs">
                                                <div>
                                                    <div className="font-bold text-foreground capitalize">
                                                        1 {pkg.unit_name} = {pkg.multiplier} {selectedItemForPkg.base_unit || selectedItemForPkg.unit}
                                                    </div>
                                                    <div className="text-muted-foreground flex items-center gap-3 mt-1 font-mono">
                                                        {pkg.barcode && <span>Barcode: <code className="bg-accent px-1 py-0.5 rounded text-foreground">{pkg.barcode}</code></span>}
                                                        {pkg.mrp != null && <span>MRP: ₹{parseFloat(pkg.mrp).toFixed(2)}</span>}
                                                        {pkg.purchase_rate != null && <span>Purchase: ₹{parseFloat(pkg.purchase_rate).toFixed(2)}</span>}
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleDeletePackaging(pkg.id)}
                                                    className="p-1.5 text-destructive hover:bg-destructive/10 rounded cursor-pointer"
                                                    title="Delete tier"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Add New Packaging Tier Form */}
                            <form onSubmit={handleAddPackaging} className="p-4 bg-muted/30 border border-border rounded-lg space-y-3">
                                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5 font-mono">
                                    <Plus size={14} /> Add Packaging Tier (e.g. Strip = 10, Box = 100)
                                </h4>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div>
                                        <label className="block text-[11px] font-semibold text-foreground mb-1">Packaging Name *</label>
                                        <input
                                            type="text"
                                            placeholder="strip, box, vial..."
                                            value={pkgForm.unit_name}
                                            onChange={e => setPkgForm({...pkgForm, unit_name: e.target.value})}
                                            className="w-full text-xs p-2 bg-background border border-input rounded-md text-foreground focus:ring-1 focus:ring-ring"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-semibold text-foreground mb-1">Multiplier ({selectedItemForPkg.base_unit || 'base units'}) *</label>
                                        <input
                                            type="number"
                                            min="1"
                                            placeholder="e.g. 10"
                                            value={pkgForm.multiplier}
                                            onChange={e => setPkgForm({...pkgForm, multiplier: e.target.value})}
                                            className="w-full text-xs p-2 bg-background border border-input rounded-md text-foreground focus:ring-1 focus:ring-ring"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-semibold text-foreground mb-1">Package Barcode (EAN)</label>
                                        <input
                                            type="text"
                                            placeholder="EAN printed on pack"
                                            value={pkgForm.barcode}
                                            onChange={e => setPkgForm({...pkgForm, barcode: e.target.value})}
                                            className="w-full text-xs p-2 bg-background border border-input rounded-md text-foreground focus:ring-1 focus:ring-ring"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-semibold text-foreground mb-1">Package MRP (₹)</label>
                                        <input
                                            type="number"
                                            step="0.01"
                                            placeholder="Auto if empty"
                                            value={pkgForm.mrp}
                                            onChange={e => setPkgForm({...pkgForm, mrp: e.target.value})}
                                            className="w-full text-xs p-2 bg-background border border-input rounded-md text-foreground focus:ring-1 focus:ring-ring"
                                        />
                                    </div>
                                </div>
                                <div className="flex justify-end pt-2">
                                    <button
                                        type="submit"
                                        className="px-4 py-2 text-xs font-semibold text-primary-foreground bg-primary hover:opacity-90 rounded-md transition-opacity flex items-center gap-1.5 shadow-xs cursor-pointer"
                                    >
                                        <Plus size={14} /> Add Packaging Tier
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Inventory;

