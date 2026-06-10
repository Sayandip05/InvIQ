import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import AlertsDropdown from './AlertsDropdown';
import { useGuest } from '../../context/GuestContext';

const AdminLayout = () => {
    const { isGuest } = useGuest();

    return (
        // data-layout attribute used by CSS selector to apply banner offset
        <div
            className="flex bg-background min-h-screen font-sans text-slate-900"
            data-layout="admin"
            style={isGuest ? { paddingTop: '40px' } : undefined}
        >
            <Sidebar />
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

export default AdminLayout;
