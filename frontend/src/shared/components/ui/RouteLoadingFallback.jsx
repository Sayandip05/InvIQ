import React from 'react';

/**
 * RouteLoadingFallback — sleek branded loading skeleton shown while
 * code-split lazy routes are fetched.
 */
export default function RouteLoadingFallback() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] w-full p-8 transition-opacity duration-300">
            <div className="relative flex items-center justify-center w-14 h-14 mb-4">
                {/* Outer spinning accent ring */}
                <div className="absolute inset-0 rounded-full border-2 border-[#1E1E1E]/10 border-t-[#F26A4B] animate-spin" />
                {/* Center pulse dot */}
                <div className="w-4 h-4 rounded-full bg-[#F26A4B] animate-pulse" />
            </div>

            <p className="text-xs font-mono font-medium uppercase tracking-widest text-[#7A7268] animate-pulse">
                Loading module...
            </p>
        </div>
    );
}
