import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard, Package, MessageSquare, LogOut, ClipboardList,
    Users, ShieldCheck, Upload, Building2, Eye, FileText
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const ROLE_LABELS = {
    super_admin: { label: 'Super Admin', color: 'bg-purple-900 text-purple-300' },
    admin: { label: 'Admin', color: 'bg-red-900 text-red-300' },
    manager: { label: 'Manager', color: 'bg-yellow-900 text-yellow-300' },
    staff: { label: 'Staff', color: 'bg-blue-900 text-blue-300' },
    vendor: { label: 'Vendor', color: 'bg-green-900 text-green-300' },
    viewer: { label: 'Viewer', color: 'bg-slate-700 text-slate-300' },
};

/**
 * Role-based navigation items.
 * Each item specifies which roles can see it.
 */
const ALL_NAV_ITEMS = [
    // ── Super Admin ───────────────────────────────
    { path: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['super_admin', 'admin', 'manager', 'viewer'] },
    { path: '/admin/inventory', label: 'Inventory', icon: Package, roles: ['super_admin', 'admin', 'manager', 'viewer'] },
    { path: '/admin/requisitions', label: 'Requisitions', icon: ClipboardList, roles: ['super_admin', 'admin', 'manager'] },
    { path: '/admin/chat', label: 'AI Assistant', icon: MessageSquare, roles: ['super_admin', 'admin', 'manager', 'staff'] },

    // ── Staff shortcuts (shown when staff visits admin layout) ──
    { path: '/staff', label: 'Staff Portal', icon: Users, roles: ['super_admin', 'admin', 'manager', 'staff'], divider: true },
    { path: '/vendor', label: 'Vendor Portal', icon: Upload, roles: ['super_admin', 'admin', 'vendor'] },
];

const Sidebar = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const role = user?.role || 'viewer';

    // Filter nav items by current user role
    const navItems = ALL_NAV_ITEMS.filter(item => item.roles.includes(role));

    const handleLogout = async () => {
        await logout();
        navigate('/signin', { replace: true });
    };

    const roleInfo = ROLE_LABELS[role] || ROLE_LABELS.viewer;

    // Portal label based on role
    const portalLabel = {
        super_admin: 'Super Admin Portal',
        admin: 'Admin Portal',
        manager: 'Manager Portal',
        staff: 'Staff Portal',
        vendor: 'Vendor Portal',
        viewer: 'Viewer Portal',
    }[role] || 'Portal';

    return (
        <div className="h-screen w-64 bg-white border-r border-slate-100 flex flex-col p-4 shrink-0">
            {/* Brand */}
            <div className="mb-8 px-4 py-2 flex flex-col">
                <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">InvIQ</h1>
                </div>
                <p className="text-xs text-slate-500 font-medium mt-1 uppercase tracking-wider">{portalLabel}</p>
            </div>

            {/* Nav links */}
            <nav className="flex-1 space-y-1">
                {navItems.map((item, idx) => (
                    <React.Fragment key={item.path}>
                        {item.divider && idx > 0 && (
                            <div className="border-t border-slate-100 my-2" />
                        )}
                        <NavLink
                            to={item.path}
                            className={({ isActive }) =>
                                `flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm font-medium ${isActive
                                    ? 'bg-primaryLight text-primary shadow-sm'
                                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                                }`
                            }
                        >
                            <item.icon size={20} />
                            <span className="font-medium">{item.label}</span>
                        </NavLink>
                    </React.Fragment>
                ))}
            </nav>

            {/* Bottom section */}
            <div className="mt-auto pt-4 border-t border-slate-100 space-y-2">
                {/* Logged-in user info */}
                {user && (
                    <div className="px-3 py-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center text-xs font-bold uppercase shadow-sm">
                            {user.username?.[0] || '?'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-900 truncate">{user.username}</p>
                            <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold ${roleInfo.color}`}>
                                {roleInfo.label}
                            </span>
                        </div>
                    </div>
                )}

                {/* Logout button */}
                <button
                    id="sidebar-logout"
                    onClick={handleLogout}
                    className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors text-left text-sm font-medium"
                >
                    <LogOut size={20} />
                    <span>Sign Out</span>
                </button>
            </div>
        </div>
    );
};

export default Sidebar;
