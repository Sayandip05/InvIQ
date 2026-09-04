import React from 'react';

export function Skeleton({ className = '', ...props }) {
    return (
        <div
            className={`animate-pulse bg-muted/70 rounded-md ${className}`}
            {...props}
        />
    );
}

export default Skeleton;
