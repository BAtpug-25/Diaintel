import React, { useState } from 'react';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Drug Comparison Page
 * - Dropdown selectors for 2 drugs
 * - AE frequency heatmap
 * - Sentiment comparison bar chart
 * - Post volume comparison
 *
 * Implemented in Step 12.
 */

const DRUGS = ['Metformin', 'Ozempic', 'Jardiance', 'Januvia', 'Farxiga', 'Trulicity', 'Victoza', 'Glipizide'];

function DrugComparePage() {
    const [drug1, setDrug1] = useState('');
    const [drug2, setDrug2] = useState('');

    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h1 className="text-2xl font-bold text-di-text">Drug Comparison</h1>
                    <p className="text-sm text-di-text-secondary mt-1">
                        Compare adverse event profiles side-by-side
                    </p>
                </div>

                {/* Drug Selectors */}
                <div className="di-card">
                    <div className="flex flex-col sm:flex-row items-center gap-4">
                        <div className="flex-1 w-full">
                            <label className="block text-sm text-di-text-secondary mb-1">Drug 1</label>
                            <select
                                value={drug1}
                                onChange={(e) => setDrug1(e.target.value)}
                                className="di-input"
                            >
                                <option value="">Select a drug...</option>
                                {DRUGS.map((d) => (
                                    <option key={d} value={d.toLowerCase()} disabled={d.toLowerCase() === drug2}>
                                        {d}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="text-2xl text-di-text-secondary mt-4 sm:mt-6">⚖️</div>

                        <div className="flex-1 w-full">
                            <label className="block text-sm text-di-text-secondary mb-1">Drug 2</label>
                            <select
                                value={drug2}
                                onChange={(e) => setDrug2(e.target.value)}
                                className="di-input"
                            >
                                <option value="">Select a drug...</option>
                                {DRUGS.map((d) => (
                                    <option key={d} value={d.toLowerCase()} disabled={d.toLowerCase() === drug1}>
                                        {d}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button className="di-btn-primary mt-4 sm:mt-6 whitespace-nowrap">
                            Compare
                        </button>
                    </div>
                </div>

                {drug1 && drug2 ? (
                    <div className="grid grid-cols-1 gap-6">
                        {/* AE Frequency Heatmap */}
                        <div className="di-card">
                            <h2 className="di-section-title">AE Frequency Heatmap</h2>
                            <div className="h-96 flex items-center justify-center text-di-text-secondary text-sm">
                                Heatmap comparing {drug1} vs {drug2} — Step 12
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Sentiment Comparison */}
                            <div className="di-card">
                                <h2 className="di-section-title">Sentiment Comparison</h2>
                                <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                                    Bar chart — Step 12
                                </div>
                            </div>

                            {/* Post Volume */}
                            <div className="di-card">
                                <h2 className="di-section-title">Post Volume</h2>
                                <div className="h-64 flex items-center justify-center text-di-text-secondary text-sm">
                                    Volume comparison — Step 12
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="di-card text-center py-16">
                        <div className="text-5xl mb-4">⚖️</div>
                        <h2 className="text-xl font-semibold text-di-text mb-2">
                            Select Two Drugs to Compare
                        </h2>
                        <p className="text-di-text-secondary">
                            Choose two drugs from the dropdowns above to see a side-by-side
                            comparison of adverse events, sentiment, and post volume.
                        </p>
                    </div>
                )}
            </div>
        </ErrorBoundary>
    );
}

export default DrugComparePage;
