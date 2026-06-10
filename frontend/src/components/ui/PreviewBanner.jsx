/**
 * PreviewBanner — Sticky demo-mode indicator for guests.
 *
 * Only renders when isGuest === true. Authenticated users never see it.
 * Fixed at the top of the viewport with a warm amber gradient.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useGuest } from '../../context/GuestContext';

export default function PreviewBanner() {
    const { isGuest } = useGuest();
    const navigate = useNavigate();

    if (!isGuest) return null;

    return (
        <div className="preview-banner" id="preview-mode-banner" role="status">
            <div className="preview-banner-content">
                {/* Eye icon */}
                <svg
                    className="preview-banner-icon"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                >
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                </svg>
                <span className="preview-banner-label">Preview Mode</span>
                <span className="preview-banner-text">
                    You're viewing live demo data.
                </span>
            </div>

            <button
                id="preview-banner-signin-btn"
                className="preview-banner-cta"
                onClick={() => navigate('/signin')}
            >
                Sign in for full access →
            </button>
        </div>
    );
}
