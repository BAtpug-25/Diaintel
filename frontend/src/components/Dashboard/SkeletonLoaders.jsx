/**
 * DiaIntel — Skeleton Loader Component
 * Reusable skeleton loaders for all data fetching states.
 */

import React from 'react';

export function SkeletonCard({ lines = 3, className = '' }) {
    return (
        <div className={`di-card ${className}`}>
            <div className="di-skeleton h-5 w-1/3 mb-4 rounded" />
            {Array.from({ length: lines }).map((_, i) => (
                <div
                    key={i}
                    className="di-skeleton h-3 rounded mb-2"
                    style={{ width: `${85 - i * 15}%` }}
                />
            ))}
        </div>
    );
}

export function SkeletonStat() {
    return (
        <div className="di-card">
            <div className="di-skeleton h-8 w-16 mb-2 rounded" />
            <div className="di-skeleton h-3 w-24 rounded" />
        </div>
    );
}

export function SkeletonChart({ height = 'h-64' }) {
    return (
        <div className="di-card">
            <div className="di-skeleton h-5 w-1/4 mb-4 rounded" />
            <div className={`di-skeleton ${height} rounded`} />
        </div>
    );
}

export function SkeletonList({ items = 5 }) {
    return (
        <div className="di-card">
            <div className="di-skeleton h-5 w-1/3 mb-4 rounded" />
            {Array.from({ length: items }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 py-2">
                    <div className="di-skeleton h-8 w-8 rounded-full" />
                    <div className="flex-1">
                        <div className="di-skeleton h-3 w-3/4 rounded mb-1" />
                        <div className="di-skeleton h-2 w-1/2 rounded" />
                    </div>
                </div>
            ))}
        </div>
    );
}

export default SkeletonCard;
