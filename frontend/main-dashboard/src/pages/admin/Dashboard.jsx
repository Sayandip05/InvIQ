import React, { useEffect, useState } from 'react';
import { analytics } from '../../services/api';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import { Activity, AlertTriangle, CheckCircle, Package } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];
const STATUS_COLORS = {
    HEALTHY: '#22c55e',
    WARNING: '#f59e0b',
    CRITICAL: '#ef4444'
};

const StatCard = ({ title, value, icon: Icon, color }) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-center space-x-4">
        <div className={`p-3 rounded-lg ${color}`}>
            <Icon className="text-white" size={24} />
        </div>
        <div>
            <p className="text-slate-500 text-sm font-medium">{title}</p>
            <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
        </div>
    </div>
);

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await analytics.getStats();
                if (response.data.success) {
                    setStats(response.data.data);
                } else {
                    setError(response.data.error || "Failed to load stats");
                }
            } catch (err) {
                setError("Network error. Is the backend running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, []);

    if (loading) return <div className="flex h-full items-center justify-center text-slate-400">Loading analytics...</div>;
    if (error) return <div className="p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>;
    if (!stats) return null;

    const { category_distribution, low_stock_items, location_stock, status_distribution } = stats;

    // Calculate totals for cards
    const totalItems = category_distribution.reduce((acc, curr) => acc + curr.value, 0);
    const criticalItems = status_distribution.find(i => i.name === 'CRITICAL')?.value || 0;
    const warningItems = status_distribution.find(i => i.name === 'WARNING')?.value || 0;

    return (
        <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-800">Dashboard Overview</h2>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Stock Items"
                    value={totalItems}
                    icon={Package}
                    color="bg-blue-500"
                />
                <StatCard
                    title="Healthy Items"
                    value={status_distribution.find(i => i.name === 'HEALTHY')?.value || 0}
                    icon={CheckCircle}
                    color="bg-green-500"
                />
                <StatCard
                    title="Critical Shortages"
                    value={criticalItems}
                    icon={AlertTriangle}
                    color="bg-red-500"
                />
                <StatCard
                    title="Low Stock Warnings"
                    value={warningItems}
                    icon={Activity}
                    color="bg-amber-500"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Status Distribution */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 className="text-lg font-semibold text-slate-700 mb-4">Stock Health Status</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={status_distribution}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {status_distribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Category Distribution */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 className="text-lg font-semibold text-slate-700 mb-4">Inventory by Category</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={category_distribution} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={100} />
                                <Tooltip />
                                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Location Stock Levels */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 className="text-lg font-semibold text-slate-700 mb-4">Stock Volume by Location</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={location_stock}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top Critical Items */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 className="text-lg font-semibold text-slate-700 mb-4">Top Critical Shortages</h3>
                    <div className="space-y-4">
                        {low_stock_items.length === 0 ? (
                            <p className="text-slate-400 text-sm text-center py-8">No critical shortages found.</p>
                        ) : (
                            low_stock_items.map((item, index) => (
                                <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                                    <div>
                                        <p className="font-medium text-slate-800">{item.name}</p>
                                        <p className="text-xs text-red-600">Shortage: -{item.shortage}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-bold text-slate-700">{item.stock} / {item.min_stock}</p>
                                        <p className="text-xs text-slate-500">Current / Min</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
