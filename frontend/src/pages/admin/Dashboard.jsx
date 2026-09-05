import React, { useEffect, useState } from 'react';
import { analytics, inventory } from '../../services/api';
import AlertsDropdown from '../../components/layout/AlertsDropdown';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import {
    Activity, AlertTriangle, CheckCircle, Package,
    ArrowUpRight, ArrowDownRight, Filter, RotateCcw, Building2, Tag
} from 'lucide-react';


const THEME_CHART_COLORS = ['#F26A4B', '#2E2E2E', '#5E5A52', '#A89F8F', '#CFC8B8'];
const STATUS_COLORS = {
    HEALTHY: '#2E2E2E',
    WARNING: '#F59E0B',
    CRITICAL: '#F26A4B'
};

import { Skeleton } from '../../components/ui/skeleton';
import MonoRoundedDonut from '../../components/ui/mono-rounded-donut';

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
                <div className="bg-card border border-border rounded-lg grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border shadow-xs">
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
                <div className="bg-card border border-border rounded-lg grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border shadow-xs">
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
                                <Skeleton className="h-3 w-16 rounded-md" />
                                <Skeleton className="h-3 w-16 rounded-md" />
                                <Skeleton className="h-3 w-16 rounded-md" />
                            </div>
                        </div>
                    </div>

                    {/* Right Chart Skeleton (Horizontal Bar Chart) */}
                    <div className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-1.5">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-5 w-52 rounded-md" />
                                    <Skeleton className="h-4 w-24 rounded-md" />
                                </div>
                                <Skeleton className="h-3 w-64 rounded-md" />
                            </div>
                            <Skeleton className="h-4 w-16 rounded-md" />
                        </div>
                        <div className="h-64 flex flex-col justify-around pt-3 pr-2">
                            {[90, 75, 60, 45, 30].map((widthPct, idx) => (
                                <div key={idx} className="flex items-center gap-3">
                                    <Skeleton className="h-3 w-28 rounded-md shrink-0" />
                                    <Skeleton 
                                        className="h-5 rounded-md" 
                                        style={{ width: `${widthPct}%` }} 
                                    />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Top Critical Shortages Skeleton */}
                <div className="bg-card border border-border rounded-lg shadow-xs p-6 space-y-4">
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

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [locations, setLocations] = useState([]);
    const [categories, setCategories] = useState([]);
    const [selectedLocation, setSelectedLocation] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch available locations & category options on mount
    useEffect(() => {
        const fetchFilters = async () => {
            try {
                const [locRes, itemRes] = await Promise.all([
                    inventory.getLocations(),
                    inventory.getItems(),
                ]);
                if (locRes.data && locRes.data.data) {
                    setLocations(locRes.data.data);
                }
                if (itemRes.data && itemRes.data.data) {
                    const uniqueCats = Array.from(
                        new Set(itemRes.data.data.map((i) => i.category).filter(Boolean))
                    ).sort();
                    setCategories(uniqueCats);
                }
            } catch (err) {
                console.error("Failed to load filter options", err);
            }
        };
        fetchFilters();
    }, []);

    // Fetch dashboard stats whenever active filter changes
    useEffect(() => {
        const fetchStats = async () => {
            try {
                setLoading(true);
                const params = {};
                if (selectedLocation) params.location_id = selectedLocation;
                if (selectedCategory) params.category = selectedCategory;

                const response = await analytics.getStats(params);
                if (response.data && (response.data.success || response.data.data)) {
                    setStats(response.data.data || response.data);
                } else {
                    setError(response.data?.error?.message || response.data?.error || "Failed to load stats");
                }
            } catch (err) {
                setError("Network error. Is the backend running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, [selectedLocation, selectedCategory]);

    const handleResetFilters = () => {
        setSelectedLocation('');
        setSelectedCategory('');
    };

    const hasActiveFilters = Boolean(selectedLocation || selectedCategory);

    if (loading && !stats) {
        return <DashboardSkeleton />;
    }
    if (error && !stats) {
        return (
            <div className="p-8 max-w-7xl mx-auto w-full">
                <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg space-y-3">
                    <p className="font-semibold text-sm">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-destructive text-destructive-foreground text-xs font-semibold hover:opacity-90 transition-opacity rounded-md cursor-pointer"
                    >
                        Retry Loading
                    </button>
                </div>
            </div>
        );
    }
    if (!stats) return <DashboardSkeleton />;

    const category_distribution = stats.category_distribution || [];
    const low_stock_items = stats.low_stock_items || [];
    const location_stock = stats.location_stock || [];
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
                        <p className="text-xs text-muted-foreground mt-0.5">Real-time inventory intelligence & batch tracking</p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                        {/* Facility / Store Filter */}
                        <div className="relative flex items-center">
                            <Building2 size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                            <select
                                value={selectedLocation}
                                onChange={(e) => setSelectedLocation(e.target.value)}
                                className="text-xs font-medium bg-background border border-border text-foreground rounded-md pl-8 pr-7 py-2 hover:bg-accent/40 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
                            >
                                <option value="">All Facilities ({locations.length || 'Global'})</option>
                                {locations.map((loc) => (
                                    <option key={loc.id} value={loc.id}>
                                        {loc.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Category Filter */}
                        <div className="relative flex items-center">
                            <Tag size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                            <select
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                                className="text-xs font-medium bg-background border border-border text-foreground rounded-md pl-8 pr-7 py-2 hover:bg-accent/40 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
                            >
                                <option value="">All Categories ({categories.length || 'All'})</option>
                                {categories.map((cat) => (
                                    <option key={cat} value={cat}>
                                        {cat}
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
                <div className="bg-card border border-border rounded-lg grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border shadow-xs">

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Active SKUs</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">{totalItems}</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-muted-foreground">
                        <span>Total catalog volume</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Inventory Valuation</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">₹0</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-muted-foreground">
                        <span>Live purchase evaluation</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Stock Fulfillment Rate</p>
                        <h3 className="text-3xl font-sans font-bold text-foreground mt-2 tracking-tight">
                            {totalItems > 0 ? (((totalItems - criticalItems) / totalItems) * 100).toFixed(1) + '%' : '—'}
                        </h3>
                    </div>
                    <div className="mt-4 flex items-center text-muted-foreground text-xs font-medium">
                        <span>Across active store locations</span>
                    </div>
                </div>

                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <p className="text-[11px] font-bold text-muted-foreground tracking-wider font-mono uppercase">Critical Stock Alerts</p>
                        <h3 className="text-3xl font-sans font-bold text-destructive mt-2 tracking-tight">{criticalItems} Critical</h3>
                    </div>
                    <div className="mt-4 flex items-center text-xs font-medium text-amber-700">
                        <span>⚠️ {warningItems} Near Minimum</span>
                    </div>
                </div>
            </div>

            {/* Connected Charts Grid Matrix */}
            <div className="bg-card border border-border rounded-lg grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border shadow-xs">
                {/* Status Distribution - "Mono Rounded" Style */}
                <div className="p-6 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-base font-sans font-bold text-foreground">Inventory Health Breakdown</h3>
                            {totalItems > 0 && (
                                <span className="text-xs font-semibold text-emerald-800 bg-emerald-100/70 px-2 py-0.5 border border-emerald-300 rounded-md flex items-center gap-0.5">
                                    <ArrowUpRight size={12} /> {totalItems > 0 ? (((totalItems - criticalItems) / totalItems) * 100).toFixed(1) : 0}% Healthy
                                </span>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground mb-4">Real-time batch stock status across warehouse locations.</p>
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

                {/* Category Distribution with Adaptive Scroll */}
                <div className="p-6">
                    <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-sans font-bold text-foreground">Therapeutic Category Volume</h3>
                            <span className="text-xs font-semibold text-foreground bg-accent px-2 py-0.5 border border-border rounded-md flex items-center gap-0.5">
                                {category_distribution.length} Categories
                            </span>
                        </div>
                        <span className="text-xs font-bold text-foreground">
                            {totalItems} Units
                        </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-4">Current units in stock by therapeutic medicine category.</p>
                    <div className="max-h-[300px] overflow-y-auto pr-2">
                        <div style={{ height: Math.max(260, category_distribution.length * 34) }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={category_distribution}
                                    layout="vertical"
                                    margin={{ top: 8, right: 20, left: 10, bottom: 8 }}
                                    barCategoryGap="20%"
                                >
                                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5DFD5" opacity={0.6} />
                                    <XAxis type="number" tick={{ fontSize: 11, fill: '#5E5A52' }} axisLine={{ stroke: '#D2CBBB' }} />
                                    <YAxis
                                        dataKey="name"
                                        type="category"
                                        width={140}
                                        interval={0}
                                        tick={{ fontSize: 11, fill: '#1E1E1E' }}
                                        axisLine={{ stroke: '#D2CBBB' }}
                                    />
                                    <Tooltip
                                        cursor={{ fill: 'rgba(0, 0, 0, 0.03)', radius: [999, 999, 999, 999] }}
                                        content={({ active, payload, label }) => {
                                            if (!active || !payload || !payload.length) return null;
                                            return (
                                                <div className="bg-card border border-border rounded-xl p-3 shadow-lg min-w-[130px]">
                                                    <p className="text-xs font-semibold text-foreground">{label}</p>
                                                    <div className="h-[1px] bg-border my-1.5" />
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <span className="w-2 h-2 rounded-full bg-[#F26A4B] shrink-0" />
                                                        <span>Volume: <strong className="text-foreground font-bold font-mono">{payload[0].value}</strong></span>
                                                    </div>
                                                </div>
                                            );
                                        }}
                                    />
                                    <Bar
                                        dataKey="value"
                                        fill="#F26A4B"
                                        radius={[999, 999, 999, 999]}
                                        barSize={14}
                                        background={{ fill: 'rgba(0, 0, 0, 0.04)', radius: [999, 999, 999, 999] }}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            </div>

            {/* Top Critical Shortages — Full Width */}
            <div className="bg-card border border-border rounded-lg shadow-xs">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h3 className="text-base font-sans font-bold text-foreground">Top Critical Shortages</h3>
                            <p className="text-xs text-muted-foreground">Items requiring immediate reorder.</p>
                        </div>
                        <span className="text-xs font-semibold text-destructive bg-destructive/10 border border-destructive/20 px-2 py-0.5 rounded-md">
                            {low_stock_items.length} Critical
                        </span>
                    </div>
                    <div className="divide-y divide-border/60">
                        {low_stock_items.length === 0 ? (
                            <p className="text-muted-foreground text-sm text-center py-10">No critical shortages found.</p>
                        ) : (
                            low_stock_items.slice(0, 8).map((item, index) => (
                                <div key={index} className="py-3 flex items-center justify-between">
                                    <div>
                                        <p className="font-semibold text-foreground text-sm">{item.name}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {item.location || 'Central Warehouse'}{item.category ? ` • ${item.category}` : ''}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-bold text-destructive">
                                            {item.days_remaining != null ? `${item.days_remaining}d left` : `${item.stock || item.current_stock || 0} left`}
                                        </p>
                                        <p className="text-[11px] text-muted-foreground">Min: {item.min_stock ?? '—'}</p>
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


