import React, { useState } from 'react';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Misinformation Monitor Page
 * - Feed of flagged posts as cards
 * - Confidence filter slider
 * - Reviewed/Unreviewed toggle
 * - Mark as reviewed button (no delete)
 *
 * Implemented in Step 15.
 */
function MisinfoMonitorPage() {
    const [minConfidence, setMinConfidence] = useState(0.5);
    const [showReviewed, setShowReviewed] = useState(false);

    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-di-text">Misinformation Monitor</h1>
                        <p className="text-sm text-di-text-secondary mt-1">
                            AI-flagged posts requiring medical review
                        </p>
                    </div>
                    <div className="di-badge-red text-sm">
                        🛡️ 0 Flagged
                    </div>
                </div>

                {/* Filters */}
                <div className="di-card">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                        {/* Confidence Slider */}
                        <div className="flex-1">
                            <label className="block text-sm text-di-text-secondary mb-2">
                                Min Confidence: <span className="text-di-accent font-mono">{minConfidence.toFixed(2)}</span>
                            </label>
                            <input
                                type="range"
                                min="0.5"
                                max="1.0"
                                step="0.05"
                                value={minConfidence}
                                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                                className="w-full h-1.5 bg-di-border rounded-lg appearance-none cursor-pointer accent-di-accent"
                            />
                            <div className="flex justify-between text-xs text-di-text-secondary mt-1">
                                <span>0.50</span>
                                <span>1.00</span>
                            </div>
                        </div>

                        {/* Reviewed Toggle */}
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setShowReviewed(false)}
                                className={`di-btn text-sm ${!showReviewed ? 'bg-di-accent/10 text-di-accent border border-di-accent' : 'text-di-text-secondary border border-di-border'}`}
                            >
                                Unreviewed
                            </button>
                            <button
                                onClick={() => setShowReviewed(true)}
                                className={`di-btn text-sm ${showReviewed ? 'bg-di-accent/10 text-di-accent border border-di-accent' : 'text-di-text-secondary border border-di-border'}`}
                            >
                                Reviewed
                            </button>
                        </div>
                    </div>
                </div>

                {/* Feed */}
                <div className="space-y-4">
                    <div className="di-card text-center py-16">
                        <div className="text-5xl mb-4">🛡️</div>
                        <h2 className="text-xl font-semibold text-di-text mb-2">
                            No Flagged Posts Yet
                        </h2>
                        <p className="text-di-text-secondary max-w-md mx-auto">
                            The misinformation detection pipeline will flag posts
                            containing potentially dangerous medical claims.
                            Results will appear here after processing.
                        </p>
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default MisinfoMonitorPage;
