/**
 * ProtectedRoute — Redirects unauthenticated users to /signin.
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
import { hasRolePermission, getRoleHome } from '@/shared/constants/roles';

export default function ProtectedRoute({ requiredRole = null }) {
    const { isAuthenticated, user, loading } = useAuth();
    const location = useLocation();

    // While session is being restored from localStorage, show nothing
    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-blue-500" />
            </div>
        );
    }

    // Not logged in → redirect to login, preserve intended destination
    if (!isAuthenticated) {
        return <Navigate to="/signin" state={{ from: location }} replace />;
    }

    // Role check — if a specific role is required
    if (requiredRole && !hasRolePermission(user?.role, requiredRole)) {
        const home = getRoleHome(user?.role);
        return <Navigate to={home} replace />;
    }

    return <Outlet />;
}
