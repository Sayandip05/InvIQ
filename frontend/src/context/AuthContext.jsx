/**
 * AuthContext — Global authentication state for Smart Inventory Assistant.
 *
 * Provides:
 * - Login / logout functions
 * - Current user object decoded from JWT
 * - Token storage in localStorage
 * - Role-based helpers (isAdmin, isManager, etc.)
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

/** Decode JWT payload without a library (tokens are base64 encoded, not encrypted). */
function decodeJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const json = decodeURIComponent(
            atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(json);
    } catch {
        return null;
    }
}

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true); // true while restoring session

    // ── Restore session on first load ──────────────────────────────────────
    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (token) {
            const payload = decodeJwt(token);
            // Check expiry
            if (payload && payload.exp * 1000 > Date.now()) {
                setUser({
                    id: payload.sub,
                    username: payload.username,
                    role: payload.role,
                });
            } else {
                // Token expired — clear storage
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
            }
        }
        setLoading(false);
    }, []);

    // ── Login ──────────────────────────────────────────────────────────────
    const login = useCallback(async (username, password) => {
        const response = await api.post('/auth/login', { username, password });
        const { access_token, refresh_token } = response.data.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        const payload = decodeJwt(access_token);
        const userData = {
            id: payload.sub,
            username: payload.username,
            role: payload.role,
        };
        setUser(userData);
        return userData;
    }, []);

    // ── Logout ─────────────────────────────────────────────────────────────
    const logout = useCallback(async () => {
        try {
            await api.post('/auth/logout');
        } catch {
            // Ignore errors — still clear local state
        } finally {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setUser(null);
        }
    }, []);

    // ── Role helpers ───────────────────────────────────────────────────────
    const isAdmin = user?.role === 'admin';
    const isManager = user?.role === 'manager' || isAdmin;
    const isStaff = user?.role === 'staff' || isManager;

    const value = {
        user,
        loading,
        login,
        logout,
        isAdmin,
        isManager,
        isStaff,
        isAuthenticated: !!user,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Hook to consume auth context anywhere in the app. */
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
