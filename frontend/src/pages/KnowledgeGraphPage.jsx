import React from 'react';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Knowledge Graph Explorer
 * - D3.js force-directed graph
 * - Drug nodes: accent green (#00C896), larger
 * - AE nodes: amber (#F59E0B), smaller
 * - Edge thickness proportional to frequency
 * - Click interactions, zoom, drag
 *
 * Implemented in Step 13.
 */
function KnowledgeGraphPage() {
    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-di-text">Knowledge Graph</h1>
                        <p className="text-sm text-di-text-secondary mt-1">
                            Drug–Adverse Event relationship network
                        </p>
                    </div>
                    {/* Legend */}
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-di-accent" />
                            <span className="text-xs text-di-text-secondary">Drug</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-di-warning" />
                            <span className="text-xs text-di-text-secondary">Adverse Event</span>
                        </div>
                    </div>
                </div>

                <div className="di-card">
                    <div
                        className="h-[600px] flex items-center justify-center text-di-text-secondary"
                        id="knowledge-graph-container"
                    >
                        <div className="text-center">
                            <div className="text-5xl mb-4">🔗</div>
                            <h2 className="text-lg font-semibold text-di-text mb-2">
                                D3.js Force-Directed Graph
                            </h2>
                            <p className="text-sm text-di-text-secondary max-w-md">
                                Interactive knowledge graph will be rendered here in Step 13.
                                Drug nodes connect to their associated adverse events with
                                edge thickness proportional to report frequency.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Graph Info */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: 'Drug Nodes', value: '8', color: 'text-di-accent' },
                        { label: 'AE Nodes', value: '—', color: 'text-di-warning' },
                        { label: 'Total Edges', value: '—', color: 'text-di-text' },
                        { label: 'Avg Connections', value: '—', color: 'text-di-text' },
                    ].map((stat) => (
                        <div key={stat.label} className="di-card text-center">
                            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                            <div className="text-xs text-di-text-secondary mt-1">{stat.label}</div>
                        </div>
                    ))}
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default KnowledgeGraphPage;
