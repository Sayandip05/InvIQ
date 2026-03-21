import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Package, MessageSquare, LogOut, ClipboardList, Users } from 'lucide-react';

const Sidebar = () => {
    const navItems = [
        { path: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/admin/inventory', label: 'Inventory', icon: Package },
        { path: '/admin/requisitions', label: 'Requisitions', icon: ClipboardList },
        { path: '/admin/chat', label: 'AI Assistant', icon: MessageSquare },
    ];

    return (
        <div className="h-screen w-64 bg-slate-900 text-white flex flex-col p-4 shadow-xl">
            <div className="mb-8 px-4 py-2">
                <h1 className="text-xl font-bold text-blue-400">SmartInventory</h1>
                <p className="text-xs text-slate-400 mt-1">Admin Portal</p>
            </div>

            <nav className="flex-1 space-y-1">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${isActive
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                            }`
                        }
                    >
                        <item.icon size={20} />
                        <span className="font-medium">{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="mt-auto pt-4 border-t border-slate-800 space-y-1">
                <NavLink
                    to="/staff"
                    className="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                >
                    <Users size={20} />
                    <span className="font-medium">Staff Portal</span>
                </NavLink>
                <NavLink
                    to="/vendor"
                    className="flex items-center space-x-3 px-4 py-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                >
                    <LogOut size={20} />
                    <span className="font-medium">Vendor Portal</span>
                </NavLink>
            </div>
        </div>
    );
};

export default Sidebar;
