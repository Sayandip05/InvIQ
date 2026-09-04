import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard, Package, MessageSquare, LogOut, ClipboardList,
    Users, ShieldCheck, Upload, Building2, FileText, Eye, HelpCircle, X,
    PanelLeftClose, Truck, ScanBarcode
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useGuest } from '../../context/GuestContext';

import AdminProfileModal from '../ui/AdminProfileModal';

const ROLE_LABELS = {
    admin:       { label: 'Admin',       color: 'bg-red-900 text-red-300' },
    staff:       { label: 'Staff',       color: 'bg-blue-900 text-blue-300' },
    vendor:      { label: 'Vendor',      color: 'bg-green-900 text-green-300' },
};

/**
 * Role-based navigation items.
 * "guest" role is a virtual role — maps to the public-accessible /admin/* routes.
 */
const ALL_NAV_ITEMS = [
    // ── Admin Portal ──────────────────────────────────────────────────────
    { path: '/admin/dashboard',         label: 'Dashboard',           icon: LayoutDashboard, roles: ['admin', 'guest'] },
    { path: '/admin/billing',           label: 'Billing Counter',     icon: ScanBarcode,     roles: ['admin', 'staff', 'guest'] },
    { path: '/admin/inventory',         label: 'Inventory',           icon: Package,          roles: ['admin', 'guest'] },
    { path: '/admin/stock-acquisition', label: 'Stock Acquisition',   icon: Upload,           roles: ['admin', 'vendor', 'guest'] },
    { path: '/admin/requisitions',      label: 'Requisitions',        icon: ClipboardList,    roles: ['admin', 'guest'] },
    { path: '/admin/chat',              label: 'AI Assistant',        icon: MessageSquare,    roles: ['admin'] },
    { path: '/admin/suppliers',         label: 'Suppliers & Vendors', icon: Truck,            roles: ['admin'] },
    { path: '/admin/users',             label: 'Users & Staff',       icon: Users,            roles: ['admin'] },
    { path: '/admin/organization',      label: 'Store & Branches',    icon: Building2,        roles: ['admin'] },
    { path: '/admin/reports',           label: 'Reports',             icon: FileText,         roles: ['admin'] },

    // ── Staff Portal shortcut ──────────────────────────────────────────────
    { path: '/staff',                   label: 'Staff Portal',        icon: Users,            roles: ['admin', 'staff'], divider: true },
];

const Sidebar = () => {
    const { user, logout } = useAuth();
    const { isGuest, showAuthModal } = useGuest();
    const [collapsed, setCollapsed] = useState(false);
    const [showHelp, setShowHelp] = useState(false);
    const [showProfileModal, setShowProfileModal] = useState(false);
    const navigate = useNavigate();

    const roleInfo = user?.role ? ROLE_LABELS[user.role] : null;

    const handleLogout = async () => {
        await logout();
        navigate('/signin');
    };

    const displayName = user?.full_name || user?.username || 'Admin';

    return (
        <aside
            className={`h-screen sticky top-0 flex flex-col bg-sidebar border-r border-sidebar-border text-sidebar-foreground transition-all duration-300 z-40 ${
                collapsed ? 'w-18 p-3' : 'w-64 p-4'
            }`}
        >
            {/* ── Brand / Header ────────────────────────────────────────── */}
            <div className={`flex items-center pb-4 border-b border-sidebar-border ${collapsed ? 'justify-center' : 'justify-between'}`}>
                {!collapsed ? (
                    <>
                        <div className="flex items-center space-x-2.5 min-w-0">
                            <img
                                src="/logo.png"
                                alt="InvIQ Logo"
                                className="w-8 h-8 object-contain shrink-0"
                            />
                            <div className="min-w-0">
                                <span className="font-sans font-bold text-sidebar-foreground tracking-tight text-lg block leading-none">
                                    InvIQ
                                </span>
                                <span className="text-[10px] text-muted-foreground block mt-1 tracking-wider font-mono font-medium uppercase">
                                    Smart Inventory
                                </span>
                            </div>
                        </div>

                        {/* Collapse button (shown only in expanded view) */}
                        <button
                            onClick={() => setCollapsed(true)}
                            className="text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent p-1.5 transition-colors cursor-pointer rounded-md"
                            title="Collapse sidebar"
                            aria-label="Collapse sidebar"
                        >
                            <PanelLeftClose size={16} />
                        </button>
                    </>
                ) : (
                    /* Collapsed view: The logo itself acts as the toggle button */
                    <button
                        onClick={() => setCollapsed(false)}
                        className="w-9 h-9 flex items-center justify-center mx-auto hover:bg-sidebar-accent transition-all cursor-pointer rounded-md group p-1"
                        title="Expand sidebar"
                        aria-label="Expand sidebar"
                    >
                        <img
                            src="/logo.png"
                            alt="InvIQ Logo"
                            className="w-7 h-7 object-contain group-hover:scale-110 transition-transform"
                        />
                    </button>
                )}
            </div>

            {/* ── Navigation Items ──────────────────────────────────────── */}
            <nav className="mt-4 flex-1 space-y-1 overflow-y-auto">
                {ALL_NAV_ITEMS.map((item, idx) => (
                    <React.Fragment key={item.path}>
                        {item.divider && !collapsed && (
                            <div className="pt-3 pb-1">
                                <p className="px-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                                    Operations
                                </p>
                            </div>
                        )}
                        <NavLink
                            to={item.path}
                            title={collapsed ? item.label : undefined}
                            className={({ isActive }) =>
                                `flex items-center ${collapsed ? 'justify-center px-2' : 'space-x-3 px-3'} py-2.5 transition-colors text-sm font-medium rounded-md ${
                                    isActive
                                        ? 'bg-sidebar-accent text-sidebar-primary border-l-2 border-primary font-semibold'
                                        : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                                }`
                            }
                        >
                            <item.icon size={19} className="shrink-0" />
                            {!collapsed && <span className="font-medium truncate">{item.label}</span>}
                        </NavLink>
                    </React.Fragment>
                ))}
            </nav>

            {/* Help & Support Button */}
            <div className="pt-2 border-t border-sidebar-border">
                <button
                    onClick={() => setShowHelp(true)}
                    title={collapsed ? "Help & Support" : undefined}
                    className={`w-full flex items-center ${collapsed ? 'justify-center px-2' : 'gap-3 px-3'} py-2 text-sm font-medium text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors rounded-md cursor-pointer`}
                >
                    <HelpCircle size={18} className="shrink-0" />
                    {!collapsed && <span>Help & Support</span>}
                </button>
            </div>

            {/* Bottom section */}
            <div className="mt-auto pt-3 border-t border-sidebar-border space-y-2">
                {/* Authenticated user info — Clickable to edit profile */}
                {user && (
                    <div 
                        onClick={() => setShowProfileModal(true)}
                        title={collapsed ? `${displayName} (Click to edit profile)` : "Click to edit your profile"}
                        className={`p-2.5 bg-sidebar-accent/50 border border-sidebar-border rounded-md flex items-center cursor-pointer hover:bg-sidebar-accent transition-all group ${collapsed ? 'justify-center' : 'gap-3'}`}
                    >
                        <div className="w-8 h-8 bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold uppercase shrink-0 rounded-md" title={collapsed ? displayName : undefined}>
                            {displayName[0] || 'A'}
                        </div>
                        {!collapsed && (
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between">
                                    <p className="text-xs font-bold text-sidebar-foreground truncate">
                                        {displayName}
                                    </p>
                                    <span className="text-[10px] text-muted-foreground group-hover:text-sidebar-foreground font-medium ml-1">Edit</span>
                                </div>
                                {roleInfo && (
                                    <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 font-bold rounded ${roleInfo.color}`}>
                                        {roleInfo.label}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Guest sign-in CTA */}
                {isGuest && (
                    <button
                        id="sidebar-signin-cta"
                        onClick={() => navigate('/signin')}
                        title={collapsed ? "Sign In" : undefined}
                        className={`w-full flex items-center justify-center gap-2 py-2.5 bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-semibold rounded-md ${collapsed ? 'px-2' : 'px-3'} cursor-pointer`}
                    >
                        <Eye size={16} className="shrink-0" />
                        {!collapsed && <span>Sign In</span>}
                    </button>
                )}

                {/* Logout button — only for authenticated users */}
                {!isGuest && (
                    <button
                        id="sidebar-logout"
                        onClick={handleLogout}
                        title={collapsed ? "Sign Out" : undefined}
                        className={`w-full flex items-center ${collapsed ? 'justify-center px-2' : 'space-x-3 px-3'} py-2 text-destructive hover:bg-destructive/10 transition-colors text-left text-sm font-medium rounded-md cursor-pointer`}
                    >
                        <LogOut size={18} className="shrink-0" />
                        {!collapsed && <span>Sign Out</span>}
                    </button>
                )}
            </div>

            {/* Help & Support Modal */}
            {showHelp && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border text-card-foreground w-full max-w-md p-6 shadow-2xl rounded-lg space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-primary text-primary-foreground flex items-center justify-center rounded-md">
                                    <HelpCircle size={18} />
                                </div>
                                <div>
                                    <h3 className="text-base font-bold text-foreground">Help & Support</h3>
                                    <p className="text-xs text-muted-foreground">InvIQ Pharmacy & Supply Chain Desk</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowHelp(false)}
                                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded-md cursor-pointer"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs sm:text-sm">
                            <div className="p-3 bg-background border border-border rounded-md space-y-1">
                                <p className="font-semibold text-foreground">Enterprise Hotline</p>
                                <p className="text-muted-foreground">Call 24/7 Supply Chain Support: <span className="font-mono text-foreground">+1 (800) 555-INVIQ</span></p>
                            </div>

                            <div className="p-3 bg-background border border-border rounded-md space-y-1">
                                <p className="font-semibold text-foreground">Direct Email Desk</p>
                                <p className="text-muted-foreground">Technical & Batch Queries: <span className="font-mono text-foreground">support@inviq.ai</span></p>
                            </div>

                            <div className="p-3 bg-background border border-border rounded-md space-y-1">
                                <p className="font-semibold text-foreground">Documentation & Guides</p>
                                <p className="text-muted-foreground">Access cold-chain SOPs, FEFO guides, and automated requisition walkthroughs.</p>
                            </div>
                        </div>

                        <div className="pt-2">
                            <button
                                onClick={() => setShowHelp(false)}
                                className="w-full py-2.5 bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity rounded-md cursor-pointer"
                            >
                                OK, Got It
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Admin Profile Modal */}
            <AdminProfileModal
                isOpen={showProfileModal}
                onClose={() => setShowProfileModal(false)}
            />
        </aside>
    );
};

export default Sidebar;
