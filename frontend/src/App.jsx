import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import ErrorBoundary from './ErrorBoundary';

// Pages
import DashboardPage from './pages/DashboardPage';
import DrugProfilePage from './pages/DrugProfilePage';
import DrugComparePage from './pages/DrugComparePage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import LiveAnalyzerPage from './pages/LiveAnalyzerPage';
import MisinfoMonitorPage from './pages/MisinfoMonitorPage';

const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/drug', label: 'Drug Profile', icon: '💊' },
    { path: '/compare', label: 'Compare', icon: '⚖️' },
    { path: '/graph', label: 'Knowledge Graph', icon: '🔗' },
    { path: '/analyze', label: 'Live Analyzer', icon: '🔬' },
    { path: '/misinfo', label: 'Misinfo Monitor', icon: '🛡️' },
];

function App() {
    return (
        <div className="min-h-screen bg-di-bg font-inter">
            {/* Navigation Header */}
            <nav className="sticky top-0 z-50 bg-di-card/95 backdrop-blur-sm border-b border-di-border">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-di-accent flex items-center justify-center">
                                <span className="text-di-bg font-bold text-sm">DI</span>
                            </div>
                            <div>
                                <h1 className="text-lg font-bold text-di-text leading-none">
                                    DiaIntel
                                </h1>
                                <p className="text-[10px] text-di-text-secondary leading-none mt-0.5">
                                    Pharmacovigilance Intelligence
                                </p>
                            </div>
                        </div>

                        {/* Navigation Links */}
                        <div className="hidden md:flex items-center gap-1">
                            {navItems.map((item) => (
                                <NavLink
                                    key={item.path}
                                    to={item.path}
                                    end={item.path === '/'}
                                    className={({ isActive }) =>
                                        `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                                            ? 'bg-di-accent/10 text-di-accent'
                                            : 'text-di-text-secondary hover:text-di-text hover:bg-di-bg/50'
                                        }`
                                    }
                                >
                                    <span className="text-base">{item.icon}</span>
                                    <span>{item.label}</span>
                                </NavLink>
                            ))}
                        </div>

                        {/* Status Indicator */}
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-di-accent animate-pulse-slow" />
                            <span className="text-xs text-di-text-secondary hidden sm:inline">
                                Live
                            </span>
                        </div>
                    </div>
                </div>

                {/* Mobile Navigation */}
                <div className="md:hidden border-t border-di-border px-4 pb-2 pt-1 flex gap-1 overflow-x-auto">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            className={({ isActive }) =>
                                `flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${isActive
                                    ? 'bg-di-accent/10 text-di-accent'
                                    : 'text-di-text-secondary'
                                }`
                            }
                        >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <ErrorBoundary showDetails={true}>
                    <Routes>
                        <Route path="/" element={<DashboardPage />} />
                        <Route path="/drug" element={<DrugProfilePage />} />
                        <Route path="/drug/:drugName" element={<DrugProfilePage />} />
                        <Route path="/compare" element={<DrugComparePage />} />
                        <Route path="/graph" element={<KnowledgeGraphPage />} />
                        <Route path="/analyze" element={<LiveAnalyzerPage />} />
                        <Route path="/misinfo" element={<MisinfoMonitorPage />} />
                    </Routes>
                </ErrorBoundary>
            </main>

            {/* Footer */}
            <footer className="mt-auto border-t border-di-border py-4 px-8">
                <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-di-text-secondary">
                    <span>DiaIntel v1.0 — Pharmacovigilance Intelligence Platform</span>
                    <span>HackCrux 2026 @ LNMIIT</span>
                </div>
            </footer>
        </div>
    );
}

export default App;
