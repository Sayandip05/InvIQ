/**
 * AuthContext — Global authentication state for Smart Inventory Assistant.
 *
 * Provides:
 * - Login / logout functions
 * - Current user object decoded from JWT
 * - Token storage in localStorage
 * - Token refresh handling (automatic on 401)
 * - Role-based helpers (isAdmin, isManager, etc.)
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api, { auth, setAuthToken, getAuthToken } from '../services/api';

const AuthContext = createContext(null);
export const AuthContextConsumer = AuthContext;

/** Decode JWT payload safely without throwing exceptions on malformed tokens */
function decodeJwt(token) {
    if (!token || typeof token !== 'string') return null;
    try {
        const parts = token.split('.');
        if (parts.length < 2 || !parts[1]) return null;
        const base64Url = parts[1];
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
    const [loading, setLoading] = useState(true);
    const isRefreshing = useRef(false);
    const refreshSubscribers = useRef([]);

    // ── Restore session on first load ──────────────────────────────────────
    useEffect(() => {
        const initAuth = async () => {
            const token = getAuthToken();
            if (token) {
                const payload = decodeJwt(token);
                if (payload && payload.exp * 1000 > Date.now()) {
                    setUser({
                        id: payload.sub,
                        username: payload.username,
                        role: payload.role,
                        org_id: payload.org_id,
                        email: payload.email || '',
                        full_name: payload.full_name || '',
                        organization_name: payload.organization_name || '',
                    });
                }
            }

            // Always hydrate full fresh profile from backend /auth/me
            try {
                const meRes = await auth.me();
                if (meRes?.data?.data) {
                    const u = meRes.data.data;
                    setUser({
                        id: u.id,
                        username: u.username,
                        role: u.role,
                        org_id: u.org_id,
                        email: u.email || '',
                        full_name: u.full_name || '',
                        organization_name: u.organization_name || '',
                        location_ids: u.location_ids || [],
                    });
                }
            } catch {
                if (!token) {
                    setAuthToken(null);
                    setUser(null);
                }
            } finally {
                setLoading(false);
            }
        };

        initAuth();
    }, []);

    // ── Token Refresh Logic ────────────────────────────────────────────────
    const refreshAccessToken = useCallback(async () => {
        if (isRefreshing.current) {
            return new Promise((resolve) => {
                refreshSubscribers.current.push(resolve);
            });
        }

        isRefreshing.current = true;

        try {
            const response = await auth.refresh({});
            const { access_token } = response.data.data;

            setAuthToken(access_token);

            const payload = decodeJwt(access_token);
            setUser((prev) => ({
                ...prev,
                id: payload.sub,
                username: payload.username,
                role: payload.role,
                org_id: payload.org_id,
            }));

            notifySubscribers(access_token);
            return access_token;
        } catch {
            setAuthToken(null);
            setUser(null);
            notifySubscribers(null);
            return null;
        } finally {
            isRefreshing.current = false;
        }
    }, []);

    const notifySubscribers = (token) => {
        refreshSubscribers.current.forEach((callback) => callback(token));
        refreshSubscribers.current = [];
    };

    // ── Setup Axios Interceptor for Token Refresh ──────────────────────────
    useEffect(() => {
        const interceptor = api.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                // If 401 and not already retrying
                if (error?.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/login')) {
                    originalRequest._retry = true;

                    const newToken = await refreshAccessToken();
                    if (newToken) {
                        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                        return api(originalRequest);
                    }
                }

                return Promise.reject(error);
            }
        );

        return () => {
            api.interceptors.response.eject(interceptor);
        };
    }, [refreshAccessToken]);

    // ── Login (email + password) ──────────────────────────────────────────
    const login = useCallback(async (email, password) => {
        const cleanEmail = email?.trim()?.toLowerCase();
        const response = await api.post('/auth/login', { email: cleanEmail, password });
        const { access_token, user: apiUser } = response.data.data;

        setAuthToken(access_token);

        const payload = decodeJwt(access_token);
        const userData = {
            id: payload.sub,
            username: payload.username,
            role: payload.role,
            org_id: payload.org_id,
            organization_name: apiUser?.organization_name,
            email: apiUser?.email || cleanEmail,
            full_name: apiUser?.full_name,
            location_ids: apiUser?.location_ids || [],
        };
        setUser(userData);
        return userData;
    }, []);

    // ── Login (Google OAuth) ───────────────────────────────────────────────
    const loginWithGoogle = useCallback(async (idToken) => {
        const response = await api.post('/auth/google-auth', { id_token: idToken });
        const data = response?.data?.data || response?.data || {};
        const accessToken = data.access_token;
        const apiUser = data.user;

        if (accessToken) {
            setAuthToken(accessToken);
            const payload = decodeJwt(accessToken) || {};
            const userData = {
                id: payload.sub || apiUser?.id,
                username: payload.username || apiUser?.username,
                role: payload.role || apiUser?.role,
                org_id: payload.org_id || apiUser?.org_id,
                organization_name: apiUser?.organization_name,
                email: apiUser?.email,
                full_name: apiUser?.full_name,
                location_ids: apiUser?.location_ids || [],
            };
            setUser(userData);
            return userData;
        } else if (apiUser) {
            const userData = {
                id: apiUser.id,
                username: apiUser.username,
                role: apiUser.role,
                org_id: apiUser.org_id,
                organization_name: apiUser.organization_name,
                email: apiUser.email,
                full_name: apiUser.full_name,
                location_ids: apiUser.location_ids || [],
            };
            setUser(userData);
            return userData;
        }
        return data;
    }, []);

    // ── Logout ─────────────────────────────────────────────────────────────
    const logout = useCallback(async () => {
        try {
            await api.post('/auth/logout');
        } catch {
            // Ignore errors — still clear local state
        } finally {
            setAuthToken(null);
            setUser(null);
        }
    }, []);


    const updateUser = useCallback((updatedFields) => {
        setUser((prev) => {
            if (!prev) return null;
            return { ...prev, ...updatedFields };
        });
    }, []);

    // ── Role helpers ───────────────────────────────────────────────────────
    const isAdmin = user?.role === 'admin';
    const isManager = user?.role === 'manager' || isAdmin;
    const isStaff = user?.role === 'staff' || isManager;

    const value = {
        user,
        loading,
        login,
        loginWithGoogle,
        logout,
        updateUser,
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
