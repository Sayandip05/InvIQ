import React, { useState, useEffect } from 'react';
import { inventory } from '../../services/api';
import { Search, AlertCircle, CheckCircle, AlertTriangle, Building2 } from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

const formatCategory = (cat) => {
    if (!cat) return '';
    const map = {
        'analgesics': 'Pain Relief',
        'analgesic': 'Pain Relief',
        'cardiovascular': 'Heart Care',
        'cardiac': 'Heart Care',
        'respiratory': 'Breathing Care',
        'endocrine': 'Diabetes Care',
        'gastrointestinal': 'Stomach Care',
        'gastro': 'Stomach Care',
        'dermatology': 'Skin Care',
        'dermatological': 'Skin Care',
        'ophthalmic': 'Eye Care',
        'ophthalmology': 'Eye Care',
    };
    return map[cat.toLowerCase()] || cat;
};

const Inventory = () => {
    const [locations, setLocations] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

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

    const filteredItems = items.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.category.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const getStatusBadge = (status) => {
        switch (status) {
            case 'HEALTHY':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-accent text-foreground border border-border">
                        <CheckCircle size={12} className="mr-1 text-foreground" /> In Stock
                    </span>
                );
            case 'WARNING':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-[#7A7268]/15 text-foreground border border-[#7A7268]/30">
                        <AlertTriangle size={12} className="mr-1 text-[#7A7268]" /> Low Stock
                    </span>
                );
            case 'CRITICAL':
                return (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-[#F26A4B]/15 text-[#F26A4B] border border-[#F26A4B]/30">
                        <AlertCircle size={12} className="mr-1" /> Need Reorder
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
                        <p className="text-xs text-muted-foreground mt-0.5">Real-time medicine list and stock levels</p>
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
                <div className="bg-card border border-border rounded-none overflow-hidden shadow-xs">

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
                                <th className="px-6 py-3.5 text-right">Min Stock</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60 text-sm">
                            {loading ? (
                                <tr><td colSpan="5" className="text-center py-8 text-muted-foreground">Loading inventory...</td></tr>
                            ) : filteredItems.length === 0 ? (
                                <tr><td colSpan="5" className="text-center py-8 text-muted-foreground">No items found matching your filter.</td></tr>
                            ) : (
                                filteredItems.map((item) => (
                                    <tr key={item.id} className="hover:bg-accent/40 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-semibold text-foreground">{item.name}</div>
                                            <div className="text-xs text-muted-foreground">Base Unit: <span className="font-mono text-foreground">{item.base_unit || item.unit}</span></div>
                                        </td>
                                        <td className="px-6 py-4 text-muted-foreground capitalize">{formatCategory(item.category)}</td>
                                        <td className="px-6 py-4 text-center">{getStatusBadge(item.status)}</td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="font-bold text-foreground">
                                                {item.current_stock?.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">{item.base_unit || item.unit}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right text-muted-foreground font-mono font-medium">
                                            {item.min_stock} {item.base_unit || item.unit}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
            </div>
        </div>
    );
};

export default Inventory;
