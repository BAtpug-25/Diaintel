import React from 'react';
import { useParams } from 'react-router-dom';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Drug Profile Page
 * - Search bar
 * - Drug identity card
 * - Top AEs horizontal bar chart
 * - Sentiment timeline line chart
 * - Severity breakdown donut chart
 * - Real patient posts with highlights
 *
 * Implemented in Step 11.
 */
function DrugProfilePage() {
    const { drugName } = useParams();

    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                {/* Search Bar */}
                <div className="di-card">
                    <div className="flex items-center gap-3">
                        <span className="text-xl">🔍</span>
                        <input
                            type="text"
                            placeholder="Search for a drug (e.g., Metformin, Ozempic, Jardiance...)"
                            className="di-input"
                            defaultValue={drugName || ''}
                        />
                        <button className="di-btn-primary whitespace-nowrap">
                            Search
                        </button>
                    </div>
                </div>

                {drugName ? (
                    <>
                        {/* Drug Identity Card */}
                        <div className="di-card">
                            <div className="flex items-start justify-between">
                                <div>
                                    <h1 className="text-3xl font-bold text-di-text capitalize">
                                        {drugName}
                                    </h1>
                                    <p className="text-di-text-secondary mt-1">
                                        Drug profile will be populated in Step 11
                                    </p>
                                </div>
                                <a href="/compare" className="di-btn-secondary">
                                    ⚖️ Compare
                                </a>
                            </div>
                        </div>

                        {/* Charts Grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="di-card">
                                <h2 className="di-section-title">Top Adverse Events</h2>
                                <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                                    Bar chart — Step 11
                                </div>
                            </div>

                            <div className="di-card">
                                <h2 className="di-section-title">Sentiment Timeline</h2>
                                <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                                    Line chart — Step 11
                                </div>
                            </div>

                            <div className="di-card">
                                <h2 className="di-section-title">Severity Breakdown</h2>
                                <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                                    Donut chart — Step 11
                                </div>
                            </div>

                            <div className="di-card">
                                <h2 className="di-section-title">Patient Posts</h2>
                                <div className="text-di-text-secondary text-sm text-center py-8">
                                    Highlighted posts — Step 11
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    /* Empty State */
                    <div className="di-card text-center py-16">
                        <div className="text-5xl mb-4">💊</div>
                        <h2 className="text-xl font-semibold text-di-text mb-2">
                            Search for a Drug
                        </h2>
                        <p className="text-di-text-secondary max-w-md mx-auto">
                            Enter a drug name above to view its safety profile, adverse events,
                            sentiment trends, and real patient posts.
                        </p>
                        <div className="flex flex-wrap justify-center gap-2 mt-6">
                            {['Metformin', 'Ozempic', 'Jardiance', 'Januvia', 'Farxiga', 'Trulicity', 'Victoza', 'Glipizide'].map(
                                (drug) => (
                                    <a
                                        key={drug}
                                        href={`/drug/${drug.toLowerCase()}`}
                                        className="di-btn-secondary text-sm"
                                    >
                                        {drug}
                                    </a>
                                )
                            )}
                        </div>
                    </div>
                )}
            </div>
        </ErrorBoundary>
    );
}

export default DrugProfilePage;
