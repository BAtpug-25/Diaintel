import React, { useState } from 'react';
import ErrorBoundary from '../ErrorBoundary';

/**
 * Live Analyzer Page
 * - Textarea for pasting patient text
 * - Analyze button with animated processing indicator
 * - Results: highlighted text, sentiment, misinfo warning
 * - Must use DistilBERT and complete in < 3 seconds
 *
 * Implemented in Step 14.
 */
function LiveAnalyzerPage() {
    const [text, setText] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState(null);

    const handleAnalyze = async () => {
        if (!text.trim()) return;
        setIsAnalyzing(true);

        // TODO: Implement API call in Step 14
        // POST /api/v1/analyze { text }
        setTimeout(() => {
            setIsAnalyzing(false);
            // Placeholder result
            setResult({
                message: 'Analysis endpoint not yet implemented (Step 14)',
            });
        }, 1000);
    };

    return (
        <ErrorBoundary>
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h1 className="text-2xl font-bold text-di-text">Live Analyzer</h1>
                    <p className="text-sm text-di-text-secondary mt-1">
                        Paste patient text for real-time drug safety analysis
                    </p>
                </div>

                {/* Input Area */}
                <div className="di-card">
                    <textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Paste a patient report, forum post, or clinical note here...

Example: I've been on Metformin 500mg for 3 months now. The nausea was terrible the first two weeks but it's gotten better. Still dealing with some stomach cramps after meals."
                        className="di-input min-h-[200px] resize-y font-mono text-sm"
                        rows={8}
                    />
                    <div className="flex items-center justify-between mt-4">
                        <span className="text-xs text-di-text-secondary">
                            {text.length > 0 ? `${text.split(/\s+/).filter(Boolean).length} words` : 'Enter text to analyze'}
                        </span>
                        <button
                            onClick={handleAnalyze}
                            disabled={!text.trim() || isAnalyzing}
                            className={`di-btn-primary flex items-center gap-2 ${(!text.trim() || isAnalyzing) ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                        >
                            {isAnalyzing ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-di-bg border-t-transparent rounded-full animate-spin" />
                                    Analyzing...
                                </>
                            ) : (
                                <>🔬 Analyze</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Results */}
                {result && (
                    <div className="space-y-4 animate-slide-up">
                        <div className="di-card">
                            <h2 className="di-section-title">Analysis Results</h2>
                            <p className="text-di-text-secondary text-sm">
                                {result.message}
                            </p>
                            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-di-bg/50 rounded-lg p-4 text-center">
                                    <div className="text-sm text-di-text-secondary mb-1">Drugs Found</div>
                                    <div className="text-xl font-bold text-di-accent">—</div>
                                </div>
                                <div className="bg-di-bg/50 rounded-lg p-4 text-center">
                                    <div className="text-sm text-di-text-secondary mb-1">AEs Detected</div>
                                    <div className="text-xl font-bold text-di-severity-high">—</div>
                                </div>
                                <div className="bg-di-bg/50 rounded-lg p-4 text-center">
                                    <div className="text-sm text-di-text-secondary mb-1">Sentiment</div>
                                    <div className="text-xl font-bold text-di-text">—</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Info */}
                <div className="di-card bg-di-accent/5 border-di-accent/20">
                    <div className="flex items-start gap-3">
                        <span className="text-lg">ℹ️</span>
                        <div className="text-sm text-di-text-secondary">
                            <p className="font-medium text-di-text mb-1">How it works</p>
                            <ul className="space-y-1 list-disc list-inside">
                                <li>Drug names highlighted in <span className="highlight-drug">green</span></li>
                                <li>Adverse events highlighted in <span className="highlight-ae">red</span></li>
                                <li>Dosages highlighted in <span className="highlight-dosage">blue</span></li>
                                <li>Uses DistilBERT for fast inference (&lt; 3 seconds)</li>
                                <li>All predictions include confidence scores</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}

export default LiveAnalyzerPage;
