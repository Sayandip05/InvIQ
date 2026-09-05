import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AIAssistantInterface from '../../components/ui/ai-assistant-interface';
import MonoRoundedDonut from '../../components/ui/mono-rounded-donut';
import {
    LayoutDashboard, Package, ClipboardList, MessageSquare,
    PanelLeftClose, Bell, Search, LogIn, UserPlus,
    ArrowUpRight, MapPin, X, HelpCircle, Menu
} from 'lucide-react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import {
    MOCK_STATS,
    MOCK_LOCATIONS,
    MOCK_ITEMS,
    MOCK_REQUISITIONS,
    MOCK_CHATBOT_REPLIES
} from '../../services/mockData';

const STATUS_COLORS = {
    HEALTHY: '#2E2E2E',
    WARNING: '#A89F8F',
    CRITICAL: '#F26A4B'
};

const PIE_COLORS = ['#F26A4B', '#2E2E2E', '#5E5A52'];

export default function PreviewDashboard() {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('dashboard');
    const [collapsed, setCollapsed] = useState(false);
    const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
    const [selectedLocation, setSelectedLocation] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [requisitions, setRequisitions] = useState(MOCK_REQUISITIONS);
    const [showHelp, setShowHelp] = useState(false);

    const handleApproveReq = (id) => {
        setRequisitions(prev => prev.map(r => r.id === id ? { ...r, status: 'APPROVED' } : r));
    };

    const handleRejectReq = (id) => {
        setRequisitions(prev => prev.map(r => r.id === id ? { ...r, status: 'REJECTED' } : r));
    };

    const filteredItems = MOCK_ITEMS.filter(item => {
        const matchesLocation = selectedLocation === 'all' || item.location_name === selectedLocation;
        const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.batch_number.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesLocation && matchesSearch;
    });

    return (
        <div className="flex h-screen w-screen bg-background font-sans text-foreground overflow-hidden">
            {/* Mobile Backdrop */}
            {mobileSidebarOpen && (
                <div
                    onClick={() => setMobileSidebarOpen(false)}
                    className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 md:hidden transition-opacity"
                />
            )}

            {/* ── 1. Left Collapsible / Mobile Responsive Sidebar ─────────── */}
            <aside className={`fixed inset-y-0 left-0 md:static h-screen bg-sidebar border-r border-sidebar-border text-sidebar-foreground flex flex-col transition-all duration-300 ease-in-out shrink-0 z-50 md:z-30 ${
                mobileSidebarOpen ? 'translate-x-0 w-64 shadow-2xl' : '-translate-x-full md:translate-x-0'
            } ${collapsed ? 'md:w-20' : 'md:w-64'}`}>
                {/* Brand Header */}
                <div className="h-16 px-4 flex items-center justify-between border-b border-sidebar-border">
                    {!collapsed ? (
                        <>
                            <div className="flex items-center gap-3">
                                <img src="/logo.png" alt="InvIQ Logo" className="w-8 h-8 object-contain shrink-0" />
                                <div className="flex flex-col justify-center">
                                    <h1 className="font-sans text-xl font-bold text-sidebar-foreground tracking-tight leading-none">InvIQ</h1>
                                    <span className="inline-block mt-1 text-[10px] uppercase font-bold tracking-wider text-muted-foreground bg-accent px-1.5 py-0.5 rounded border border-border w-fit font-mono">
                                        Demo Preview
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setCollapsed(true)}
                                    className="hidden md:flex p-1.5 rounded-md text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors"
                                    title="Collapse Sidebar"
                                >
                                    <PanelLeftClose size={18} />
                                </button>
                                <button
                                    onClick={() => setMobileSidebarOpen(false)}
                                    className="md:hidden p-1.5 rounded-md text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors"
                                    title="Close Sidebar"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        </>
                    ) : (
                        <div className="w-full flex justify-center items-center">
                            <button
                                onClick={() => setCollapsed(false)}
                                className="group p-2 rounded-md hover:bg-sidebar-accent transition-all cursor-pointer flex items-center justify-center"
                                title="Click Logo to Expand Sidebar"
                                aria-label="Expand Sidebar"
                            >
                                <img
                                    src="/logo.png"
                                    alt="InvIQ Logo"
                                    className="w-8 h-8 object-contain group-hover:scale-110 transition-transform"
                                />
                            </button>
                        </div>
                    )}
                </div>

                {/* Navigation Items */}
                <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
                    {[
                        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
                        { id: 'inventory', label: 'Inventory', icon: Package },
                        { id: 'requisitions', label: 'Requisitions', icon: ClipboardList, badge: requisitions.filter(r => r.status === 'PENDING').length },
                        { id: 'chat', label: 'AI Assistant', icon: MessageSquare, badge: 'AI' },
                    ].map((tab) => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => {
                                    setActiveTab(tab.id);
                                    setMobileSidebarOpen(false);
                                }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all cursor-pointer ${
                                    isActive
                                        ? 'bg-sidebar-accent text-sidebar-primary border-l-2 border-primary font-semibold'
                                        : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                                } ${collapsed ? 'md:justify-center md:px-2' : ''}`}
                            >
                                <Icon size={18} className="shrink-0" />
                                {(!collapsed || mobileSidebarOpen) && (
                                    <span className="flex-1 text-left truncate">{tab.label}</span>
                                )}
                                {tab.badge && (!collapsed || mobileSidebarOpen) && (
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                        isActive ? 'bg-primary text-primary-foreground' : 'bg-accent text-foreground'
                                    }`}>
                                        {tab.badge}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </nav>

                {/* Help & Support Button */}
                <div className="p-3 border-t border-sidebar-border">
                    <button
                        onClick={() => setShowHelp(true)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors cursor-pointer ${
                            collapsed ? 'justify-center' : ''
                        }`}
                        title="Help & Support"
                    >
                        <HelpCircle size={18} className="shrink-0 text-foreground" />
                        {!collapsed && <span>Help &amp; Support</span>}
                    </button>
                </div>

                {/* Sidebar Bottom Status */}
                <div className="p-3 border-t border-sidebar-border bg-sidebar/50">
                    {!collapsed ? (
                        <div className="p-3 bg-card border border-border rounded-md">
                            <div className="flex items-center gap-2 mb-1.5">
                                <span className="w-2 h-2 rounded-full bg-[#F26A4B] animate-pulse" />
                                <span className="text-xs font-semibold text-foreground">Demo Mode Active</span>
                            </div>
                            <p className="text-[11px] text-muted-foreground leading-snug">
                                Exploring live simulated pharmacy data.
                            </p>
                        </div>
                    ) : (
                        <div className="flex justify-center py-1" title="Demo Mode Active">
                            <span className="w-2.5 h-2.5 rounded-full bg-[#F26A4B]" />
                        </div>
                    )}
                </div>
            </aside>

            {/* Help & Support Modal */}
            {showHelp && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border w-full max-w-md p-6 shadow-2xl space-y-4 rounded-lg text-card-foreground">
                        <div className="flex items-center justify-between pb-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-primary text-primary-foreground flex items-center justify-center rounded">
                                    <HelpCircle size={18} />
                                </div>
                                <div>
                                    <h3 className="font-sans text-base font-bold text-foreground">Help &amp; Support</h3>
                                    <p className="text-xs text-muted-foreground">InvIQ Pharmacy &amp; Supply Chain Desk</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowHelp(false)}
                                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs sm:text-sm">
                            <div className="p-3 bg-background border border-border rounded space-y-1">
                                <p className="font-semibold text-foreground">Enterprise Hotline</p>
                                <p className="text-muted-foreground">Call 24/7 Supply Chain Support: <span className="font-mono text-foreground">+1 (800) 555-INVIQ</span></p>
                            </div>

                            <div className="p-3 bg-background border border-border rounded space-y-1">
                                <p className="font-semibold text-foreground">Direct Email Desk</p>
                                <p className="text-muted-foreground">Technical &amp; Batch Queries: <span className="font-mono text-foreground">support@inviq.ai</span></p>
                            </div>

                            <div className="p-3 bg-background border border-border rounded space-y-1">
                                <p className="font-semibold text-foreground">Documentation &amp; Guides</p>
                                <p className="text-muted-foreground">Access cold-chain SOPs, FEFO guides, and automated requisition walkthroughs.</p>
                            </div>
                        </div>

                        <div className="pt-2">
                            <button
                                onClick={() => setShowHelp(false)}
                                className="w-full py-2.5 bg-primary hover:bg-black text-primary-foreground font-semibold text-sm rounded transition-colors cursor-pointer"
                            >
                                OK, Got It
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── 2. Main Viewport & Fixed Top Bar ──────────────────────────── */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0 bg-background">
                {/* Top Header Bar */}
                <header className="h-16 px-4 sm:px-6 bg-card border-b border-border flex items-center justify-between shrink-0 z-20">
                    {/* Left: Hamburger (mobile) + Title */}
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setMobileSidebarOpen(true)}
                            className="md:hidden p-2 rounded-lg text-foreground hover:bg-accent transition-colors"
                            aria-label="Open Navigation Menu"
                        >
                            <Menu size={20} />
                        </button>
                        <div>
                            <h2 className="font-sans text-base sm:text-lg font-bold text-foreground capitalize leading-tight truncate max-w-[200px] sm:max-w-none">
                                {activeTab === 'dashboard' && 'Dashboard Overview'}
                                {activeTab === 'inventory' && 'Central Inventory & Batch Tracker'}
                                {activeTab === 'requisitions' && 'Stock Requisitions & Approvals'}
                                {activeTab === 'chat' && 'AI Inventory Assistant'}
                            </h2>
                            <span className="hidden sm:block text-xs text-muted-foreground">InvIQ Smart Wholesale &amp; Pharmacy Suite</span>
                        </div>
                    </div>

                    {/* Right: Sign In + Sign Up Buttons */}
                    <div className="flex items-center gap-3">
                        <div className="relative p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-full cursor-pointer transition-colors">
                            <Bell size={18} />
                            <span className="absolute top-1 right-1 w-2 h-2 bg-[#F26A4B] rounded-full" />
                        </div>

                        <div className="h-6 w-px bg-border" />

                        <button
                            onClick={() => navigate('/signin')}
                            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-foreground bg-background border border-border rounded-lg hover:bg-accent transition-colors cursor-pointer shadow-xs"
                        >
                            <LogIn size={16} />
                            <span>Sign In</span>
                        </button>

                        <button
                            onClick={() => navigate('/signup')}
                            className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-primary-foreground bg-primary hover:bg-black rounded-lg transition-colors cursor-pointer shadow-xs"
                        >
                            <UserPlus size={16} />
                            <span>Sign Up</span>
                        </button>
                    </div>
                </header>

                {/* ── 3. Tab Content ────────────────────────────────────────── */}
                <main className={`flex-1 overflow-y-auto ${activeTab === 'chat' ? 'p-0 h-[calc(100vh-4rem)] flex flex-col bg-card' : 'p-5 md:p-6 lg:p-8 bg-background'}`}>
                    {/* TAB 1: DASHBOARD OVERVIEW */}
                    {activeTab === 'dashboard' && (
                        <div className="space-y-6 max-w-7xl mx-auto">
                            {/* 4 KPI Matrix */}
                            <div className="bg-card border border-border rounded-lg grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border shadow-xs">
                                <div className="p-6 flex flex-col justify-between">
                                    <div>
                                        <p className="text-xs font-semibold text-muted-foreground tracking-wider font-mono">Active Pharmaceutical SKUs</p>
                                        <h3 className="font-sans text-3xl font-bold text-foreground mt-2 tracking-tight">1,300</h3>
                                    </div>
                                    <div className="mt-4 flex items-center text-xs font-medium text-foreground font-mono">
                                        <ArrowUpRight size={14} className="mr-0.5 text-[#F26A4B]" /> +4.2% <span className="text-muted-foreground ml-1">vs last month</span>
                                    </div>
                                </div>

                                <div className="p-6 flex flex-col justify-between">
                                    <div>
                                        <p className="text-xs font-semibold text-muted-foreground tracking-wider font-mono">Total Inventory Valuation</p>
                                        <h3 className="font-sans text-3xl font-bold text-foreground mt-2 tracking-tight">₹1,84,290</h3>
                                    </div>
                                    <div className="mt-4 flex items-center text-xs font-medium text-foreground font-mono">
                                        <ArrowUpRight size={14} className="mr-0.5 text-[#F26A4B]" /> +12.4% <span className="text-muted-foreground ml-1">asset value</span>
                                    </div>
                                </div>

                                <div className="p-6 flex flex-col justify-between">
                                    <div>
                                        <p className="text-xs font-semibold text-muted-foreground tracking-wider font-mono">Stock Fulfillment Rate</p>
                                        <h3 className="font-sans text-3xl font-bold text-foreground mt-2 tracking-tight">98.2%</h3>
                                    </div>
                                    <div className="mt-4 flex items-center text-foreground text-xs font-medium font-mono">
                                        <ArrowUpRight size={14} className="mr-0.5 text-[#F26A4B]" /> +0.4% <span className="text-muted-foreground ml-1">fulfillment</span>
                                    </div>
                                </div>

                                <div className="p-6 flex flex-col justify-between">
                                    <div>
                                        <p className="text-xs font-semibold text-muted-foreground tracking-wider font-mono">Critical Stock Alerts</p>
                                        <h3 className="font-sans text-3xl font-bold text-[#F26A4B] mt-2 tracking-tight">4 Critical</h3>
                                    </div>
                                    <div className="mt-4 flex items-center text-xs font-medium text-muted-foreground font-mono">
                                        <span>⚠️ 8 Near Minimum</span>
                                    </div>
                                </div>
                            </div>

                            {/* Connected Charts Grid Matrix */}
                            <div className="bg-card border border-border rounded-lg grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border shadow-xs">
                                {/* Stock Health Distribution - "Mono Rounded" Style */}
                                <div className="p-6 flex flex-col justify-between">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <h4 className="font-sans text-base font-bold text-foreground">Inventory Health Breakdown</h4>
                                            <span className="text-xs font-semibold text-foreground bg-accent px-2 py-0.5 border border-border rounded flex items-center gap-0.5 font-mono">
                                                <ArrowUpRight size={12} className="text-[#F26A4B]" /> 94.4% Healthy
                                            </span>
                                        </div>
                                        <p className="text-xs text-muted-foreground mb-4">Real-time batch stock status across warehouse locations.</p>
                                    </div>

                                    <MonoRoundedDonut
                                        data={MOCK_STATS.status_distribution}
                                        title="Stock Health"
                                        height={240}
                                        innerRadius={68}
                                        outerRadius={92}
                                        cornerRadius={8}
                                        paddingAngle={6}
                                    />
                                </div>

                                {/* Therapeutic Category Distribution */}
                                <div className="p-6">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h4 className="font-sans text-base font-bold text-foreground">Therapeutic Category Volume</h4>
                                        <span className="text-xs font-semibold text-foreground bg-accent px-2 py-0.5 border border-border rounded flex items-center gap-0.5 font-mono">
                                            <ArrowUpRight size={12} className="text-[#F26A4B]" /> 1,300 Units
                                        </span>
                                    </div>
                                    <p className="text-xs text-muted-foreground mb-6">Current units in stock by therapeutic medicine category.</p>
                                    <div className="h-64">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart
                                                data={MOCK_STATS.category_distribution}
                                                layout="vertical"
                                                margin={{ top: 8, right: 20, left: 10, bottom: 8 }}
                                                barCategoryGap="20%"
                                            >
                                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5DFD5" opacity={0.6} />
                                                <XAxis type="number" tick={{ fontSize: 11, fill: '#5E5A52' }} stroke="#D2CBBB" />
                                                <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11, fill: '#1E1E1E' }} stroke="#D2CBBB" />
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

                            {/* Critical Shortages Grid */}
                            <div className="bg-card border border-border rounded-lg shadow-xs overflow-hidden">
                                <div className="p-4 border-b border-border flex items-center justify-between bg-accent/40">
                                    <div>
                                        <h4 className="font-sans text-sm font-bold text-foreground">Immediate Action Required</h4>
                                        <p className="text-xs text-muted-foreground">Items below mandatory minimum threshold</p>
                                    </div>
                                    <span className="text-xs font-semibold text-white bg-[#F26A4B] px-2.5 py-1 rounded font-mono">
                                        {MOCK_STATS.low_stock_items.length} Critical
                                    </span>
                                </div>
                                <div className="divide-y divide-border">
                                    {MOCK_STATS.low_stock_items.map((item) => (
                                        <div key={item.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-accent/30 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-[#F26A4B]/10 text-[#F26A4B] border border-[#F26A4B]/30 flex items-center justify-center font-bold text-sm rounded">
                                                    !
                                                </div>
                                                <div>
                                                    <p className="font-bold text-foreground text-sm">{item.name}</p>
                                                    <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                                                        <MapPin size={12} className="text-muted-foreground" />
                                                        <span>{item.location}</span>
                                                        <span>•</span>
                                                        <span className="text-foreground font-medium">{item.category}</span>
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="text-right">
                                                    <span className="text-sm font-bold text-[#F26A4B] font-mono">{item.current_stock} in stock</span>
                                                    <p className="text-[11px] text-muted-foreground font-mono">Min: {item.min_stock}</p>
                                                </div>
                                                <button
                                                    onClick={() => navigate('/signin')}
                                                    className="px-3 py-1.5 text-xs font-semibold text-foreground bg-accent hover:bg-primary hover:text-primary-foreground border border-border rounded transition-colors cursor-pointer"
                                                >
                                                    Auto-Restock →
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 2: INVENTORY & BATCH TRACKER */}
                    {activeTab === 'inventory' && (
                        <div className="space-y-5 max-w-7xl mx-auto">
                            {/* Search & Location Filter Bar */}
                            <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card p-4 rounded-lg border border-border shadow-xs">
                                <div className="relative w-full sm:w-80">
                                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <input
                                        type="text"
                                        placeholder="Search by drug, category, or batch..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                </div>
                                <div className="flex items-center gap-3 w-full sm:w-auto">
                                    <select
                                        value={selectedLocation}
                                        onChange={(e) => setSelectedLocation(e.target.value)}
                                        className="w-full sm:w-auto px-3 py-2 bg-background border border-border rounded-md text-sm text-foreground focus:outline-none"
                                    >
                                        <option value="all">All Locations (4 Sites)</option>
                                        {MOCK_LOCATIONS.map(loc => (
                                            <option key={loc.id} value={loc.name}>{loc.name}</option>
                                        ))}
                                    </select>
                                    <button
                                        onClick={() => navigate('/signin')}
                                        className="px-4 py-2 bg-primary hover:bg-black text-primary-foreground rounded-md text-sm font-medium transition-colors shrink-0 shadow-xs cursor-pointer"
                                    >
                                        + Add Item
                                    </button>
                                </div>
                            </div>

                            {/* Inventory Table */}
                            <div className="bg-card rounded-lg border border-border shadow-xs overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-accent/50 border-b border-border text-muted-foreground text-xs font-semibold uppercase tracking-wider font-mono">
                                            <tr>
                                                <th className="py-3.5 px-5">Medicine / Item</th>
                                                <th className="py-3.5 px-5">Batch No.</th>
                                                <th className="py-3.5 px-5">Category</th>
                                                <th className="py-3.5 px-5">Storage Temp</th>
                                                <th className="py-3.5 px-5">Stock Level</th>
                                                <th className="py-3.5 px-5">Expiry Date</th>
                                                <th className="py-3.5 px-5">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border text-foreground">
                                            {filteredItems.map(item => (
                                                <tr key={item.id} className="hover:bg-accent/30 transition-colors">
                                                    <td className="py-3.5 px-5 font-bold text-foreground">{item.name}</td>
                                                    <td className="py-3.5 px-5 font-mono text-xs text-muted-foreground">{item.batch_number}</td>
                                                    <td className="py-3.5 px-5">{item.category}</td>
                                                    <td className="py-3.5 px-5">
                                                        {item.storage_temp === 'cold_chain' ? (
                                                            <span className="inline-flex items-center gap-1 text-xs font-bold text-primary bg-accent px-2 py-0.5 rounded border border-border">
                                                                ❄️ 2°–8°C Cold Chain
                                                            </span>
                                                        ) : (
                                                            <span className="text-xs text-muted-foreground">Ambient</span>
                                                        )}
                                                    </td>
                                                    <td className="py-3.5 px-5">
                                                        <span className="font-semibold font-mono">{item.current_stock}</span>
                                                        <span className="text-xs text-muted-foreground ml-1">{item.unit}</span>
                                                    </td>
                                                    <td className="py-3.5 px-5 text-muted-foreground font-mono">{item.expiry_date}</td>
                                                    <td className="py-3.5 px-5">
                                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold font-mono ${
                                                            item.status === 'HEALTHY'
                                                                ? 'bg-accent text-foreground border border-border'
                                                                : item.status === 'CRITICAL'
                                                                ? 'bg-[#F26A4B]/15 text-[#F26A4B] border border-[#F26A4B]/30'
                                                                : 'bg-muted text-foreground border border-border'
                                                        }`}>
                                                            {item.status}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 3: REQUISITIONS */}
                    {activeTab === 'requisitions' && (
                        <div className="space-y-5 max-w-7xl mx-auto">
                            <div className="flex justify-between items-center bg-card p-4 rounded-lg border border-border shadow-xs">
                                <div>
                                    <h3 className="font-sans font-bold text-foreground text-base">Requisition Approval Workflow</h3>
                                    <p className="text-xs text-muted-foreground">Staff requests awaiting management authorization</p>
                                </div>
                                <button
                                    onClick={() => navigate('/signin')}
                                    className="px-4 py-2 bg-primary hover:bg-black text-primary-foreground rounded-md text-sm font-semibold shadow-xs cursor-pointer"
                                >
                                    + New Requisition
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {requisitions.map(req => (
                                    <div key={req.id} className="bg-card p-5 rounded-lg border border-border shadow-xs flex flex-col justify-between space-y-4">
                                        <div>
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="font-mono text-xs font-bold text-foreground bg-accent px-2 py-0.5 rounded border border-border">
                                                    {req.id}
                                                </span>
                                                <span className={`text-xs font-bold px-2.5 py-0.5 rounded font-mono ${
                                                    req.status === 'APPROVED' ? 'bg-accent text-foreground border border-border' :
                                                    req.status === 'REJECTED' ? 'bg-[#F26A4B]/15 text-[#F26A4B] border border-[#F26A4B]/30' :
                                                    'bg-muted text-foreground border border-border'
                                                }`}>
                                                    {req.status}
                                                </span>
                                            </div>
                                            <h4 className="font-sans text-base font-bold text-foreground">{req.destination}</h4>
                                            <p className="text-xs text-muted-foreground mt-1">Requested by: <strong className="text-foreground">{req.requested_by}</strong> ({req.role})</p>
                                            <p className="text-xs text-muted-foreground font-mono mt-0.5">{req.created_at}</p>
                                        </div>

                                        <div className="flex items-center justify-between pt-3 border-t border-border">
                                            <span className="text-sm font-bold text-foreground font-mono">₹{req.total_cost.toLocaleString()} ({req.items_count} items)</span>
                                            {req.status === 'PENDING' ? (
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleRejectReq(req.id)}
                                                        className="px-3 py-1.5 text-xs font-semibold text-[#F26A4B] bg-[#F26A4B]/10 hover:bg-[#F26A4B]/20 rounded transition-colors cursor-pointer"
                                                    >
                                                        Reject
                                                    </button>
                                                    <button
                                                        onClick={() => handleApproveReq(req.id)}
                                                        className="px-3 py-1.5 text-xs font-semibold text-primary-foreground bg-primary hover:bg-black rounded transition-colors shadow-xs cursor-pointer"
                                                    >
                                                        Approve
                                                    </button>
                                                </div>
                                            ) : (
                                                <span className="text-xs text-muted-foreground">Processed</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TAB 4: SMART INVENTORY & SUPPLY CHAIN AI INTELLIGENCE */}
                    {activeTab === 'chat' && (
                        <div className="flex-1 w-full h-full bg-card overflow-hidden">
                            <AIAssistantInterface isPreview={true} />
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}
