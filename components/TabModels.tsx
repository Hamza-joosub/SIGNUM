'use client';
import { useState } from 'react';
import Dashboard from './Dashboard';

export default function TabModels() {
    const [isModelLoading, setIsModelLoading] = useState(false);
    const [activeModel, setActiveModel] = useState<string | null>(null);

    const handleOpenModel = async (modelId: string) => {
        if (modelId === 'capital-pressure') {
            setIsModelLoading(true);
            try {
                const res = await fetch('/api/pressure?date=2024-05-10');
                if (!res.ok) throw new Error('Failed to fetch model');
                setActiveModel(modelId);
            } catch (err) {
                console.error(err);
                alert('Failed to load model data.');
            } finally {
                setIsModelLoading(false);
            }
        }
    };

    if (activeModel) {
        return <Dashboard onClose={() => setActiveModel(null)} />;
    }

    return (
        <div style={{ position: 'relative' }}>
            {/* Loading overlay */}
            {isModelLoading && (
                <div style={{
                    position: 'fixed', inset: 0, zIndex: 50,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    background: 'rgba(8,13,24,0.85)', backdropFilter: 'blur(12px)'
                }}>
                    <div style={{
                        width: 44, height: 44, borderRadius: '50%',
                        border: '2px solid rgba(200,169,110,0.2)',
                        borderTop: '2px solid #c8a96e',
                        animation: 'spin 0.8s linear infinite',
                        marginBottom: 20,
                        boxShadow: '0 0 30px rgba(200,169,110,0.3)'
                    }}></div>
                    <h2 style={{ fontFamily: 'Fraunces, serif', fontSize: 22, fontWeight: 300, color: '#c8a96e', marginBottom: 8 }}>
                        Spinning up model engine...
                    </h2>
                    <p style={{ fontSize: 13, color: 'rgba(234,230,222,0.35)' }}>
                        Fetching market snapshots and COT positioning data
                    </p>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
            )}

            {/* Header */}
            <div className="models-header">
                <h1 className="models-title">Models</h1>
                <p className="models-subtitle">Select a model to run an analysis. More models will be added over time.</p>
            </div>
            <p className="models-count"><span>1</span> model available · 2 in development</p>

            {/* Grid */}
            <div className="model-grid">

                {/* ── Card 1: Capital Pressure (LIVE) ── */}
                <div className="model-card live" onClick={() => handleOpenModel('capital-pressure')}>
                    <div className="card-accent-line"></div>
                    <div className="card-body">
                        <div className="card-header-row">
                            <span className="card-type-badge live-badge">CROSS-ASSET</span>
                            <div className="card-status">
                                <div className="card-status-dot live"></div>
                                <span className="card-status-text live">Live</span>
                            </div>
                        </div>
                        <div className="card-title">Capital Pressure Model</div>
                        <div className="card-desc">
                            Measures directional pressure across asset classes by analysing momentum, volume, and relative flow signals to identify risk-on / risk-off regimes.
                        </div>
                        <div className="card-preview">
                            <CapitalPressureSvg />
                        </div>
                        <div className="card-footer">
                            <div className="card-tags">
                                <span className="card-tag">Momentum</span>
                                <span className="card-tag">Pressure</span>
                                <span className="card-tag">Volume</span>
                            </div>
                            <button className="card-open-btn">Open →</button>
                        </div>
                    </div>
                </div>

                {/* ── Card 2: DCF Valuation Engine (LOCKED) ── */}
                <div className="model-card">
                    <div className="card-accent-line locked"></div>
                    <div className="card-body">
                        <div className="card-header-row">
                            <span className="card-type-badge locked-badge">VALUATION</span>
                            <div className="card-status">
                                <div className="card-status-dot locked"></div>
                                <span className="card-status-text locked">In development</span>
                            </div>
                        </div>
                        <div className="card-title locked">DCF Valuation Engine</div>
                        <div className="card-desc locked">
                            Discounted cash flow model with multi-scenario support. Outputs intrinsic value, WACC sensitivity, and terminal value breakdown.
                        </div>
                        <div className="card-preview locked">
                            <DcfSvg />
                        </div>
                        <div className="card-footer">
                            <div className="card-tags">
                                <span className="card-tag">DCF</span>
                                <span className="card-tag">Scenario</span>
                                <span className="card-tag">WACC</span>
                            </div>
                            <div className="card-coming-soon">Coming Soon</div>
                        </div>
                    </div>
                </div>

                {/* ── Card 3: Monte Carlo Simulator (LOCKED) ── */}
                <div className="model-card">
                    <div className="card-accent-line locked"></div>
                    <div className="card-body">
                        <div className="card-header-row">
                            <span className="card-type-badge locked-badge">SIMULATION</span>
                            <div className="card-status">
                                <div className="card-status-dot locked"></div>
                                <span className="card-status-text locked">In development</span>
                            </div>
                        </div>
                        <div className="card-title locked">Monte Carlo Simulator</div>
                        <div className="card-desc locked">
                            Runs thousands of randomised simulations to model outcome distributions, VaR estimates, and probability-weighted scenario analysis.
                        </div>
                        <div className="card-preview locked">
                            <MonteCarloSvg />
                        </div>
                        <div className="card-footer">
                            <div className="card-tags">
                                <span className="card-tag">Simulation</span>
                                <span className="card-tag">VaR</span>
                                <span className="card-tag">Risk</span>
                            </div>
                            <div className="card-coming-soon">Coming Soon</div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}

/* ── SVG Previews ─────────────────────────── */
function CapitalPressureSvg() {
    return (
        <svg width="100%" height="100%" viewBox="0 0 300 72" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <marker id="ag" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
                    <polygon points="0 0,5 2.5,0 5" fill="rgba(200,169,110,0.65)" />
                </marker>
                <marker id="ao" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
                    <polygon points="0 0,5 2.5,0 5" fill="rgba(138,184,112,0.65)" />
                </marker>
                <marker id="ar" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
                    <polygon points="0 0,5 2.5,0 5" fill="rgba(200,96,96,0.65)" />
                </marker>
            </defs>
            <rect x="110" y="4" width="80" height="16" rx="3" fill="rgba(200,169,110,0.08)" stroke="rgba(200,169,110,0.5)" strokeWidth="1" />
            <text x="150" y="15" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="6" fill="rgba(200,169,110,0.85)" fontWeight="600">MARKET INPUTS</text>
            <rect x="16" y="28" width="64" height="16" rx="3" fill="rgba(138,184,112,0.07)" stroke="rgba(138,184,112,0.45)" strokeWidth="1" />
            <text x="48" y="39" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="5.5" fill="rgba(138,184,112,0.8)" fontWeight="600">MOMENTUM</text>
            <rect x="110" y="28" width="80" height="16" rx="3" fill="rgba(200,169,110,0.07)" stroke="rgba(200,169,110,0.4)" strokeWidth="1" />
            <text x="150" y="39" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="5.5" fill="rgba(200,169,110,0.75)" fontWeight="600">PRESSURE INDEX</text>
            <rect x="220" y="28" width="64" height="16" rx="3" fill="rgba(200,96,96,0.07)" stroke="rgba(200,96,96,0.45)" strokeWidth="1" />
            <text x="252" y="39" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="5.5" fill="rgba(200,96,96,0.8)" fontWeight="600">VOLUME</text>
            <rect x="100" y="52" width="100" height="16" rx="3" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
            <text x="150" y="63" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="6" fill="rgba(234,230,222,0.7)" fontWeight="600">REGIME SIGNAL</text>
            <line x1="120" y1="20" x2="58" y2="28" stroke="rgba(200,169,110,0.5)" strokeWidth="1" markerEnd="url(#ag)" />
            <line x1="150" y1="20" x2="150" y2="28" stroke="rgba(200,169,110,0.5)" strokeWidth="1" markerEnd="url(#ag)" />
            <line x1="180" y1="20" x2="242" y2="28" stroke="rgba(200,169,110,0.5)" strokeWidth="1" markerEnd="url(#ag)" />
            <line x1="52" y1="44" x2="112" y2="52" stroke="rgba(138,184,112,0.55)" strokeWidth="1" markerEnd="url(#ao)" />
            <line x1="150" y1="44" x2="150" y2="52" stroke="rgba(200,169,110,0.55)" strokeWidth="1" markerEnd="url(#ag)" />
            <line x1="248" y1="44" x2="188" y2="52" stroke="rgba(200,96,96,0.55)" strokeWidth="1" markerEnd="url(#ar)" />
        </svg>
    );
}

function DcfSvg() {
    return (
        <svg width="100%" height="100%" viewBox="0 0 300 72" preserveAspectRatio="none">
            <path d="M0,60 L40,55 L80,48 L120,44 L160,36 L200,27 L240,18 L300,10"
                fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" strokeDasharray="4,3" />
        </svg>
    );
}

function MonteCarloSvg() {
    return (
        <svg width="100%" height="100%" viewBox="0 0 300 72" preserveAspectRatio="none">
            <path d="M0,36 L20,32 L40,38 L60,27 L80,42 L100,22 L120,31 L140,18 L160,27 L180,14 L200,21 L220,12 L240,18 L260,8 L280,14 L300,6"
                fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M0,36 L20,39 L40,44 L60,36 L80,46 L100,40 L120,45 L140,38 L160,43 L180,35 L200,41 L220,33 L240,38 L260,29 L280,35 L300,25"
                fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M0,36 L20,30 L40,34 L60,23 L80,35 L100,18 L120,26 L140,14 L160,20 L180,10 L200,16 L220,8 L240,13 L260,5 L280,10 L300,3"
                fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" strokeDasharray="3,3" />
        </svg>
    );
}
