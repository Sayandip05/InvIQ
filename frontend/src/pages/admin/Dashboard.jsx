import React, { useEffect, useState } from 'react';
import { analytics, inventory } from '../../services/api';
import AlertsDropdown from '../../components/layout/AlertsDropdown';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import {
    Activity, AlertTriangle, CheckCircle, Package,
    ArrowUpRight, ArrowDownRight, Filter, RotateCcw, Building2
} from 'lucide-react';


const THEME_CHART_COLORS = ['#F26A4B', '#2E2E2E', '#5E5A52', '#A89F8F', '#CFC8B8'];
const STATUS_COLORS = {
    HEALTHY: '#2E2E2E',
    WARNING: '#F59E0B',
    CRITICAL: '#F26A4B'
};

import { Skeleton } from '../../components/ui/skeleton';
import MonoRoundedDonut from '../../components/ui/mono-rounded-donut';
import ExpiryLineChart from '../../components/ui/ExpiryLineChart';

export const DashboardSkeleton = () => {
    return (
        <div className="flex flex-col min-h-full">
            {/* Top Bar Skeleton */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <Skeleton className="h-7 w-48 rounded-md" />
                    <div className="flex items-center gap-2.5 flex-wrap">
                        <Skeleton className="h-8 w-40 rounded-md" />
                        <Skeleton className="h-8 w-36 rounded-md" />
                        <div className="pl-1 border-l border-border">
                            <Skeleton className="h-8 w-8 rounded-md" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Page Content Skeleton Container */}
            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">
                {/* 4 KPI Matrix Skeleton */}
                <div className="bg-card border border-border rounded-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border shadow-xs">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="p-6 flex flex-col justify-between space-y-4">
                            <div className="space-y-2">
                                <Skeleton className="h-3 w-36 rounded-md" />
                                <Skeleton className="h-8 w-24 rounded-md mt-2" />
                            </div>
                            <Skeleton className="h-3.5 w-28 rounded-md mt-2" />
                        </div>
                    ))}
                </div>

                {/* Connected Charts Grid Matrix Skeleton */}
                <div className="bg-card border border-border rounded-xl grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border shadow-xs">
                    {/* Left Chart Skeleton (Donut / Pie Chart) */}
                    <div className="p-6 space-y-4">
                        <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                                <Skeleton className="h-5 w-48 rounded-md" />
                                <Skeleton className="h-4 w-20 rounded-md" />
                            </div>
                            <Skeleton className="h-3 w-72 rounded-md" />
                        </div>
                        <div className="h-64 flex flex-col items-center justify-center space-y-4 pt-2">
                            <div className="relative flex items-center justify-center">
                                <Skeleton className="w-40 h-40 rounded-full" />
                                <div className="absolute w-24 h-24 bg-card rounded-full" />
                            </div>
                            <div className="flex items-center gap-4 pt-2">
                                <Skeleton className="h-3 w-16 rounded-full" />
                                <Skeleton className="h-3 w-16 rounded-full" />
                                <Skeleton className="h-3 w-16 rounded-full" />
                            </div>
                        </div>
                    </div>

                    {/* Right Chart Skeleton (Dynamic Expiry Line Chart) */}
                    <div className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-1.5">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-5 w-52 rounded-md" />
                                    <Skeleton className="h-4 w-24 rounded-md" />
                                </div>
                                <Skeleton className="h-3 w-64 rounded-md" />
                            </div>
                            <Skeleton className="h-4 w-28 rounded-md" />
                        </div>
                        <div className="h-64 rounded-xl bg-accent/20 p-4 flex flex-col justify-between border border-border">
                            <div className="flex justify-end gap-3">
                                <Skeleton className="h-3 w-20 rounded" />
                                <Skeleton className="h-3 w-20 rounded" />
                            </div>
                            <div className="h-40 flex items-center justify-center">
                                <Skeleton className="h-28 w-full rounded-lg" />
                            </div>
                            <div className="flex justify-between">
                                {[1, 2, 3, 4, 5, 6].map((i) => (
                                    <Skeleton key={i} className="h-2.5 w-8 rounded" />
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Top Critical Shortages Skeleton */}
                <div className="bg-card border border-border rounded-xl shadow-xs p-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="space-y-1.5">
                            <Skeleton className="h-5 w-44 rounded-md" />
                            <Skeleton className="h-3 w-56 rounded-md" />
                        </div>
                        <Skeleton className="h-5 w-20 rounded-md" />
                    </div>
                    <div className="divide-y divide-border/60">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="py-3.5 flex items-center justify-between">
                                <div className="space-y-1.5">
                                    <Skeleton className="h-4 w-48 rounded-md" />
                                    <Skeleton className="h-3 w-36 rounded-md" />
                                </div>
                                <div className="space-y-1.5 flex flex-col items-end">
                                    <Skeleton className="h-4 w-16 rounded-md" />
                                    <Skeleton className="h-2.5 w-12 rounded-md" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

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

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [locations, setLocations] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch available locations on mount
    useEffect(() => {
        const fetchFilters = async () => {
            try {
                const locRes = await inventory.getLocations();
                if (locRes.data && locRes.data.data) {
                    setLocations(locRes.data.data);
                }
            } catch (err) {
                console.error("Failed to load filter options", err);
            }
        };
        fetchFilters();
    }, []);

    // Fetch dashboard stats whenever active location filter changes
    useEffect(() => {
        const fetchStats = async () => {
            try {
                setLoading(true);
                const params = {};
                if (selectedLocation) params.location_id = selectedLocation;

                const response = await analytics.getStats(params);
                if (response.data && (response.data.success || response.data.data)) {
                    setStats(response.data.data || response.data);
                } else {
                    setError("Unable to load dashboard details right now.");
                }
            } catch (err) {
                setError("Unable to connect to the server. Please check your internet connection and try again.");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, [selectedLocation]);

    const handleResetFilters = () => {
        setSelectedLocation('');
    };

    const hasActiveFilters = Boolean(selectedLocation);

    if (loading && !stats) {
        return <DashboardSkeleton />;
    }
    if (error && !stats) {
        return (
            <div className="p-8 max-w-7xl mx-auto w-full">
                <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl space-y-3">
                    <p className="font-semibold text-sm">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-destructive text-destructive-foreground text-xs font-semibold hover:opacity-90 transition-opacity rounded-md cursor-pointer"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }
    if (!stats) return <DashboardSkeleton />;

    const category_distribution = stats.category_distribution || [];
    const low_stock_items = stats.low_stock_items || [];
    const status_distribution = stats.status_distribution || [];

    // Calculate totals for cards
    const totalItems = category_distribution.reduce((acc, curr) => acc + (curr.value || 0), 0);
    const criticalItems = status_distribution.find(i => i.name === 'CRITICAL')?.value || 0;
    const warningItems = status_distribution.find(i => i.name === 'WARNING')?.value || 0;

    return (
        <div className="flex flex-col min-h-full bg-background text-foreground">
            {/* Full-Width Top Navbar */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Dashboard Overview</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">Overview of stock levels, reorder alerts, and expiring medicines</p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        {/* Location Filter */}
                        <div className="relative flex items-center">
                            <Building2 size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                            <select
                                value={selectedLocation}
                                onChange={(e) => setSelectedLocation(e.target.value)}
                                className="text-xs font-medium bg-background border border-border text-foreground rounded-md pl-8 pr-7 py-2 hover:bg-accent/40 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
                            >
                                <option value="">All Locations ({locations.length || 'All'})</option>
                                {locations.map((loc) => (
                                    <option key={loc.id} value={loc.id}>
                                        {loc.name}
                                    </option>
                                ))}
                            </select>
                        </div>


                        {/* Reset Button */}
                        {hasActiveFilters && (
                            <button
                                onClick={handleResetFilters}
                                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-secondary-foreground bg-secondary hover:bg-accent border border-border rounded-md transition-colors cursor-pointer"
                                title="Reset all filters"
                            >
                                <RotateCcw size={12} />
                                <span>Reset</span>
                            </button>
                        )}

                        {/* Notification Alerts Bell Dropdown */}
                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            {/* Page Content Container with Standard Spacious Layout */}
            <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">
                {/* 4 KPI Matrix with Warm Parchment Cards */}
                <div className="bg-card border border-border rounded-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border shadow-xs">

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Total Medicines</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">{totalItems}</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-muted-foreground">
                        <span>Total medicines in system</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Total Stock Value</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">₹0</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-muted-foreground">
                        <span>Estimated total inventory value</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">In-Stock Rate</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">
                            {totalItems > 0 ? (((totalItems - criticalItems) / totalItems) * 100).toFixed(1) + '%' : '—'}
                        </h3>
                    </div>
                    <div className="mt-4 flex items-center text-muted-foreground text-xs font-medium">
                        <span>Medicines in healthy supply</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Low Stock Alerts</p>
                        <h3 className="text-3xl font-sans font-bold text-destructive mt-2 tracking-tight">{criticalItems} Need Reorder</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-amber-700">
                        <span>⚠️ {warningItems} Running Low</span>
                    </div>
                </div>
            </div>

            {/* Connected Charts Grid Matrix */}
            <div className="bg-card border border-border rounded-xl grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border shadow-xs">
                {/* Status Distribution - "Mono Rounded" Style */}
                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-base font-sans font-bold text-foreground">Stock Health Overview</h3>
                            {totalItems > 0 && (
                                <span className="text-xs font-semibold text-foreground bg-accent px-2 py-0.5 border border-border rounded-md flex items-center gap-0.5">
                                    <ArrowUpRight size={12} className="text-[#F26A4B]" /> {totalItems > 0 ? (((totalItems - criticalItems) / totalItems) * 100).toFixed(1) : 0}% Well Stocked
                                </span>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground mb-4">Overview of current stock across all storage locations.</p>
                    </div>

                    <MonoRoundedDonut
                        data={status_distribution}
                        title="Stock Health"
                        height={240}
                        innerRadius={68}
                        outerRadius={92}
                        cornerRadius={8}
                        paddingAngle={6}
                    />
                </div>

                {/* Expiry Risk Trajectory - Dynamic Spline Lines */}
                <div className="p-6 flex flex-col justify-between">
                    <ExpiryLineChart data={stats.expiry_timeline} height={240} />
                </div>
            </div>

            {/* Low Stock Medicines — Full Width */}
            <div className="bg-card border border-border rounded-xl shadow-xs">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h3 className="text-base font-sans font-bold text-foreground">Medicines Running Low</h3>
                            <p className="text-xs text-muted-foreground">Medicines that need to be reordered soon.</p>
                        </div>
                        <span className="text-xs font-semibold text-destructive bg-destructive/10 border border-destructive/20 px-2 py-0.5 rounded-md">
                            {low_stock_items.length} Need Reorder
                        </span>
                    </div>
                    <div className="divide-y divide-border/60">
                        {low_stock_items.length === 0 ? (
                            <p className="text-muted-foreground text-sm text-center py-10">Great news! All medicines have sufficient stock.</p>
                        ) : (
                            low_stock_items.slice(0, 8).map((item, index) => (
                                <div key={index} className="py-3 flex items-center justify-between">
                                    <div>
                                        <p className="font-semibold text-foreground text-sm">{item.name}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {item.location || 'Central Location'}{item.category ? ` • ${formatCategory(item.category)}` : ''}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-bold text-destructive">
                                            {item.days_remaining != null ? `${item.days_remaining} days left` : `${item.stock || item.current_stock || 0} units left`}
                                        </p>
                                        <p className="text-[11px] text-muted-foreground">Minimum needed: {item.min_stock ?? '—'}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
        </div>
    );
};

export default Dashboard;


