import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard, Package, MessageSquare, LogOut, ClipboardList,
    Users
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import AlertsDropdown from './AlertsDropdown';

const ROLE_LABELS = {
    super_admin: { label: 'Super Admin', color: 'bg-purple-900 text-purple-300' },
    admin: { label: 'Admin', color: 'bg-red-900 text-red-300' },
    manager: { label: 'Manager', color: 'bg-yellow-900 text-yellow-300' },
    staff: { label: 'Staff', color: 'bg-blue-900 text-blue-300' },
    vendor: { label: 'Vendor', color: 'bg-green-900 text-green-300' },
};

const MANAGER_NAV_ITEMS = [
    { path: '/manager/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/manager/inventory', label: 'Inventory', icon: Package },
    { path: '/manager/requisitions', label: 'Requisitions', icon: ClipboardList },
    { path: '/manager/chat', label: 'AI Assistant', icon: MessageSquare },
];

const ManagerLayout = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const role = user?.role || 'manager';
    const roleInfo = ROLE_LABELS[role] || ROLE_LABELS.manager;

    const handleLogout = async () => {
        await logout();
        navigate('/signin', { replace: true });
    };

    return (
        <div className="flex bg-background min-h-screen font-sans text-slate-900">
            <div className="h-screen w-64 bg-white border-r border-slate-100 flex flex-col p-4 shrink-0">
                <div className="mb-8 px-4 py-2 flex flex-col">
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">InvIQ</h1>
                    </div>
                    <p className="text-xs text-slate-500 font-medium mt-1 uppercase tracking-wider">Manager Portal</p>
                </div>

                <nav className="flex-1 space-y-1">
                    {MANAGER_NAV_ITEMS.map((item) => (
                        <NavLink
                            key={item.path}
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
                    ))}
                </nav>

                <div className="mt-auto pt-4 border-t border-slate-100 space-y-2">
                    {user && (
                        <div className="px-3 py-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-yellow-600 text-white flex items-center justify-center text-xs font-bold uppercase shadow-sm">
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
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors text-left text-sm font-medium"
                    >
                        <LogOut size={20} />
                        <span>Sign Out</span>
                    </button>
                </div>
            </div>
            <main className="flex-1 p-8 overflow-y-auto h-screen">
                <div className="max-w-7xl mx-auto">
                    <div className="flex justify-end mb-4">
                        <AlertsDropdown />
                    </div>
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default ManagerLayout;