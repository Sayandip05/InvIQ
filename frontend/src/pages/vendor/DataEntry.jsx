import React, { useState, useEffect } from 'react';
import { inventory } from '../../services/api';
import { Plus, Trash2, Save, ArrowLeft, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

const DataEntry = () => {
    const [locations, setLocations] = useState([]);
    const [items, setItems] = useState([]);
    const [formData, setFormData] = useState({
        location_id: '',
        date: new Date().toISOString().split('T')[0],
        entered_by: 'vendor', // default
        items: []
    });
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [locRes, itemRes] = await Promise.all([
                    inventory.getLocations(),
                    inventory.getItems()
                ]);

                if (locRes.data.success) setLocations(locRes.data.data);
                if (itemRes.data.success) setItems(itemRes.data.data);

                // Set default location if available
                if (locRes.data.data.length > 0) {
                    setFormData(prev => ({ ...prev, location_id: locRes.data.data[0].id }));
                }

                // Initialize with one empty row
                addItemRow();
            } catch (err) {
                console.error("Failed to fetch initial data", err);
            }
        };
        fetchData();
    }, []);

    const addItemRow = () => {
        setFormData(prev => ({
            ...prev,
            items: [...prev.items, { item_id: '', received: 0, issued: 0, notes: '' }]
        }));
    };

    const removeItemRow = (index) => {
        setFormData(prev => ({
            ...prev,
            items: prev.items.filter((_, i) => i !== index)
        }));
    };

    const updateItemRow = (index, field, value) => {
        setFormData(prev => {
            const newItems = [...prev.items];
            newItems[index] = { ...newItems[index], [field]: value };
            return { ...prev, items: newItems };
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        // Filter out invalid rows (no item selected)
        const validItems = formData.items.filter(item => item.item_id);

        if (validItems.length === 0) {
            setError("Please add at least one item.");
            setLoading(false);
            return;
        }

        try {
            const payload = {
                ...formData,
                items: validItems
            };

            const response = await inventory.addBulkTransaction(payload);

            if (response.data.success) {
                setSuccess(true);
                // Reset form items but keep location/date
                setFormData(prev => ({
                    ...prev,
                    items: [{ item_id: '', received: 0, issued: 0, notes: '' }]
                }));
            } else {
                setError(response.data.message || "Submission failed");
            }
        } catch (err) {
            setError(err.response?.data?.detail || "Network error");
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full text-center">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle className="text-green-600" size={32} />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">Success!</h2>
                    <p className="text-slate-500 mb-6">Inventory data has been submitted successfully.</p>
                    <button
                        onClick={() => setSuccess(false)}
                        className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
                    >
                        Submit More Data
                    </button>
                    <div className="mt-4">
                        <Link to="/admin" className="text-sm text-slate-400 hover:text-blue-500">Go to Admin Portal</Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Vendor Portal</h1>
                        <p className="mt-2 text-slate-600">Daily Stock Entry</p>
                    </div>
                    <Link to="/admin" className="text-slate-400 hover:text-blue-600 font-medium text-sm flex items-center gap-1">
                        Admin Access
                    </Link>
                </div>

                <form onSubmit={handleSubmit} className="bg-white shadow-xl rounded-2xl overflow-hidden border border-slate-100">
                    <div className="p-6 md:p-8 border-b border-slate-100 bg-slate-50/50 space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Location</label>
                                <select
                                    required
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    value={formData.location_id}
                                    onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                                >
                                    {locations.map(loc => (
                                        <option key={loc.id} value={loc.id}>{loc.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Date</label>
                                <input
                                    type="date"
                                    required
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    value={formData.date}
                                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="p-6 md:p-8">
                        {error && (
                            <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg border border-red-100 flex items-center gap-2">
                                <AlertTriangle size={20} />
                                {error}
                            </div>
                        )}

                        <div className="space-y-4">
                            <div className="grid grid-cols-12 gap-4 text-sm font-medium text-slate-500 px-2">
                                <div className="col-span-5 md:col-span-4">Item</div>
                                <div className="col-span-3 md:col-span-2 text-center">Received</div>
                                <div className="col-span-3 md:col-span-2 text-center">Issued</div>
                                <div className="hidden md:block col-span-3">Notes</div>
                                <div className="col-span-1"></div>
                            </div>

                            {formData.items.map((row, index) => (
                                <div key={index} className="grid grid-cols-12 gap-4 items-start p-2 hover:bg-slate-50 rounded-lg transition-colors">
                                    <div className="col-span-5 md:col-span-4">
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
                                    <div className="col-span-3 md:col-span-2">
                                        <input
                                            type="number"
                                            min="0"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-center text-sm"
                                            value={row.received}
                                            onChange={(e) => updateItemRow(index, 'received', parseInt(e.target.value) || 0)}
                                        />
                                    </div>
                                    <div className="col-span-3 md:col-span-2">
                                        <input
                                            type="number"
                                            min="0"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-center text-sm"
                                            value={row.issued}
                                            onChange={(e) => updateItemRow(index, 'issued', parseInt(e.target.value) || 0)}
                                        />
                                    </div>
                                    <div className="hidden md:block col-span-3">
                                        <input
                                            type="text"
                                            placeholder="Optional notes"
                                            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                            value={row.notes}
                                            onChange={(e) => updateItemRow(index, 'notes', e.target.value)}
                                        />
                                    </div>
                                    <div className="col-span-1 flex justify-center pt-2">
                                        <button
                                            type="button"
                                            onClick={() => removeItemRow(index)}
                                            className="text-slate-300 hover:text-red-500 transition-colors"
                                            disabled={formData.items.length === 1}
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6">
                            <button
                                type="button"
                                onClick={addItemRow}
                                className="flex items-center gap-2 text-blue-600 font-medium hover:text-blue-700 py-2 px-4 rounded-lg hover:bg-blue-50 transition-colors"
                            >
                                <Plus size={18} />
                                Add Another Item
                            </button>
                        </div>
                    </div>

                    <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end">
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-slate-800 transition-colors shadow-lg shadow-slate-200 disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                'Submitting...'
                            ) : (
                                <>
                                    <Save size={20} />
                                    Submit Inventory Data
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default DataEntry;
