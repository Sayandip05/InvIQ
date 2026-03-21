import React, { useState, useEffect } from 'react';
import { inventory } from '../../services/api';
import { Search, Filter, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

const Inventory = () => {
    const [locations, setLocations] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const fetchLocations = async () => {
            try {
                const response = await inventory.getLocations();
                if (response.data.success) {
                    setLocations(response.data.data);
                    if (response.data.data.length > 0) {
                        setSelectedLocation(response.data.data[0].id);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch locations", err);
            }
        };
        fetchLocations();
    }, []);

    useEffect(() => {
        if (!selectedLocation) return;

        const fetchItems = async () => {
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
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle size={12} className="mr-1" /> Healthy
                    </span>
                );
            case 'WARNING':
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        <AlertTriangle size={12} className="mr-1" /> Low Stock
                    </span>
                );
            case 'CRITICAL':
                return (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <AlertCircle size={12} className="mr-1" /> Critical
                    </span>
                );
            default:
                return null;
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">Inventory Management</h2>
                    <p className="text-slate-500">View and manage stock levels per location</p>
                </div>

                <div className="flex items-center space-x-4 w-full md:w-auto">
                    <select
                        className="bg-white border border-slate-300 text-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={selectedLocation}
                        onChange={(e) => setSelectedLocation(e.target.value)}
                    >
                        {locations.map(loc => (
                            <option key={loc.id} value={loc.id}>{loc.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="p-4 border-b border-slate-100 flex items-center space-x-4">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search items..."
                            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-lg">
                        <Filter size={20} />
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 text-slate-600 font-medium text-sm">
                            <tr>
                                <th className="px-6 py-4">Item Name</th>
                                <th className="px-6 py-4">Category</th>
                                <th className="px-6 py-4 text-center">Status</th>
                                <th className="px-6 py-4 text-right">Current Stock</th>
                                <th className="px-6 py-4 text-right">Min Required</th>
                                <th className="px-6 py-4">Unit</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading ? (
                                <tr><td colSpan="6" className="text-center py-8 text-slate-400">Loading inventory...</td></tr>
                            ) : filteredItems.length === 0 ? (
                                <tr><td colSpan="6" className="text-center py-8 text-slate-400">No items found matching your filter.</td></tr>
                            ) : (
                                filteredItems.map((item) => (
                                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-4 font-medium text-slate-800">{item.name}</td>
                                        <td className="px-6 py-4 text-slate-500">{item.category}</td>
                                        <td className="px-6 py-4 text-center">{getStatusBadge(item.status)}</td>
                                        <td className="px-6 py-4 text-right font-medium text-slate-700">{item.current_stock}</td>
                                        <td className="px-6 py-4 text-right text-slate-500">{item.min_stock}</td>
                                        <td className="px-6 py-4 text-slate-400 text-sm">{item.unit}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Inventory;
