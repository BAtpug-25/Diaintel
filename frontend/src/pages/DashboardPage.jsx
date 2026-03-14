import React from 'react';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Dashboard Page
 * - Live stats bar (total posts, AEs, drugs, last updated)
 * - Trending AEs horizontal bar chart
 * - Recent signals feed
 * - Sentiment overview grouped bar chart
 * - Data ingestion status panel
 *
 * Implemented in Step 10.
 */
function DashboardPage() {
    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                {/* Page Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-di-text">Dashboard</h1>
                        <p className="text-sm text-di-text-secondary mt-1">
                            Real-time pharmacovigilance overview
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-di-accent animate-pulse" />
                        <span className="text-xs text-di-text-secondary">Updating live</span>
                    </div>
                </div>

                {/* Stats Bar */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: 'Total Posts', value: '—', icon: '📝' },
                        { label: 'AE Signals', value: '—', icon: '⚠️' },
                        { label: 'Drugs Tracked', value: '8', icon: '💊' },
                        { label: 'Last Updated', value: '—', icon: '🕐' },
                    ].map((stat) => (
                        <div key={stat.label} className="di-card flex items-center gap-3">
                            <span className="text-2xl">{stat.icon}</span>
                            <div>
                                <div className="di-stat-value">{stat.value}</div>
                                <div className="di-stat-label">{stat.label}</div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Trending AEs */}
                    <div className="di-card">
                        <h2 className="di-section-title">🔥 Trending AEs This Week</h2>
                        <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                            Chart will be implemented in Step 10
                        </div>
                    </div>

                    {/* Recent Signals */}
                    <div className="di-card">
                        <h2 className="di-section-title">📡 Recent Signals</h2>
                        <div className="space-y-3">
                            <div className="text-di-text-secondary text-sm text-center py-8">
                                No signals yet — run the NLP pipeline to detect adverse events
                            </div>
                        </div>
                    </div>

                    {/* Sentiment Overview */}
                    <div className="di-card">
                        <h2 className="di-section-title">😊 Sentiment Overview</h2>
                        <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                            Chart will be implemented in Step 10
                        </div>
                    </div>

                    {/* Ingestion Status */}
                    <div className="di-card">
                        <h2 className="di-section-title">📂 Data Ingestion Status</h2>
                        <div className="space-y-2">
                            {[
                                'diabetes_comments.zst',
                                'diabetes_t2_comments.zst',
                                'diabetes_submissions.zst',
                                'Ozempic_comments.zst',
                                'Ozempic_submissions.zst',
                                'Semaglutide_comments.zst',
                            ].map((file) => (
                                <div
                                    key={file}
                                    className="flex items-center justify-between py-2 px-3 bg-di-bg/50 rounded-lg"
                                >
                                    <span className="text-sm text-di-text-secondary">{file}</span>
                                    <span className="di-badge-yellow">Pending</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default DashboardPage;
