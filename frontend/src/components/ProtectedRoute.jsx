/**
 * ProtectedRoute — Redirects unauthenticated users to /login.
 *
 * Usage:
 *   <Route element={<ProtectedRoute />}>
 *     <Route path="dashboard" element={<Dashboard />} />
 *   </Route>
 *
 * Optional role restriction:
 *   <ProtectedRoute requiredRole="admin" />
 */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ROLE_HIERARCHY = { viewer: 1, vendor: 2, staff: 3, manager: 4, admin: 5, super_admin: 6 };

export default function ProtectedRoute({ requiredRole = null }) {
    const { isAuthenticated, user, loading } = useAuth();
    const location = useLocation();

    // While session is being restored from localStorage, show nothing
    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-950">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-blue-500" />
            </div>
        );
    }

    // Not logged in → redirect to login, preserve intended destination
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Role check — if a specific role is required
    if (requiredRole) {
        const userLevel = ROLE_HIERARCHY[user?.role] ?? 0;
        const requiredLevel = ROLE_HIERARCHY[requiredRole] ?? 999;
        if (userLevel < requiredLevel) {
            return <Navigate to="/admin/dashboard" replace />;
        }
    }

    return <Outlet />;
}
