import React from 'react';

/**
 * ErrorBoundary — Catches React rendering errors and displays a fallback UI.
 * Wrap every page component in this boundary.
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });
        console.error('ErrorBoundary caught:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex items-center justify-center min-h-[400px] p-8">
                    <div className="di-card max-w-lg w-full text-center">
                        <div className="text-4xl mb-4">⚠️</div>
                        <h2 className="text-xl font-semibold text-di-text mb-2">
                            Something went wrong
                        </h2>
                        <p className="text-di-text-secondary text-sm mb-4">
                            {this.state.error?.message || 'An unexpected error occurred'}
                        </p>
                        <button
                            className="di-btn-primary"
                            onClick={() => {
                                this.setState({ hasError: false, error: null, errorInfo: null });
                                window.location.reload();
                            }}
                        >
                            Reload Page
                        </button>
                        {this.props.showDetails && this.state.errorInfo && (
                            <details className="mt-4 text-left">
                                <summary className="text-di-text-secondary text-xs cursor-pointer">
                                    Error Details
                                </summary>
                                <pre className="mt-2 text-xs text-di-severity-high overflow-auto max-h-48 p-2 bg-di-bg rounded">
                                    {this.state.errorInfo.componentStack}
                                </pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
