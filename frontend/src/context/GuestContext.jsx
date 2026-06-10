/**
 * GuestContext — Demo Preview Mode infrastructure.
 *
 * Provides:
 * - isGuest: true when no authenticated user session exists
 * - showAuthModal(message): navigates directly to /signin
 *   Named "showAuthModal" to keep the call-sites in pages unchanged,
 *   but the behaviour is a clean redirect — no intermediate modal.
 *
 * Zero impact on authenticated users.
 */

import React, { createContext, useContext, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const GuestContext = createContext(null);

export function GuestProvider({ children }) {
    const { isAuthenticated } = useAuth();
    const navigate = useNavigate();

    const isGuest = !isAuthenticated;

    /**
     * Redirect the guest to the sign-in page.
     * The `message` param is accepted for call-site compatibility but unused —
     * the user is taken directly to /signin without an intermediate modal.
     */
    const showAuthModal = useCallback((_message) => {
        navigate('/signin');
    }, [navigate]);

    /**
     * No-op kept for call-site compatibility.
     * Previously dismissed a modal; now there is no modal to dismiss.
     */
    const hideAuthModal = useCallback(() => {}, []);

    return (
        <GuestContext.Provider value={{ isGuest, showAuthModal, hideAuthModal }}>
            {children}
        </GuestContext.Provider>
    );
}

/** Hook to consume guest context anywhere in the app. */
export function useGuest() {
    const ctx = useContext(GuestContext);
    if (!ctx) throw new Error('useGuest must be used inside <GuestProvider>');
    return ctx;
}
