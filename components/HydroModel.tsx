'use client';
import { useState, useMemo } from 'react';

/* ─── Types ──────────────────────────────────────────── */
export interface PressureAsset {
    label: string;
    ticker: string;
    pressure_score: number;
    direction: string;
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    momentum_norm: number;
    volume_norm: number;
    relative_norm: number;
    positioning_z: number | null;   // null = no COT data
    contrarian_position: boolean;
}

type Confidence = 'HIGH' | 'HIGH_MED' | 'ALL';

const CONF_OPTIONS: { key: Confidence; label: string }[] = [
    { key: 'HIGH', label: '🔴 High Only' },
    { key: 'HIGH_MED', label: '🟡 High + Medium' },
    { key: 'ALL', label: '⬜ All Flows' },
];

/* ─── Helpers ────────────────────────────────────────── */
function shortName(label: string): string {
    return label.replace(/\s*\([^)]+\)/, '').trim();
}

function tickerOf(label: string): string {
    const m = label.match(/\(([^)]+)\)/);
    return m ? m[1] : label;
}

function zToFillPct(z: number | null): number {
    if (z === null) return 0;
    const clamped = Math.max(-3, Math.min(3, z));
    return ((clamped + 3) / 6) * 70 + 10;
}

function passesFilter(conf: PressureAsset['confidence'], filter: Confidence): boolean {
    if (filter === 'HIGH') return conf === 'HIGH';
    if (filter === 'HIGH_MED') return conf === 'HIGH' || conf === 'MEDIUM';
    return true;
}

/* ─── Asset Container ────────────────────────────────── */
function AssetContainer({ asset, position }: { asset: PressureAsset; position: 'outflow' | 'inflow' }) {
    const hasCot = asset.positioning_z !== null;
    const z = asset.positioning_z;
    const zLong = z !== null && z > 0;
    const fillPct = zToFillPct(z);
    const isHigh = asset.confidence === 'HIGH';
    const tk = tickerOf(asset.label);
    const name = shortName(asset.label);
    const absPct = Math.abs(asset.pressure_score) / 10; // 0→1

    // Pipe dimensions scale with |pressure_score|
    const pipeH = 28 + absPct * 24;          // 28–52px height
    const pipeW = Math.max(4, Math.round(absPct * 14)); // 4–14px width
    // Animation speed: 2s (low pressure) → 0.25s (max pressure)
    const pipeSpeed = `${Math.max(0.25, 2 - absPct * 1.75).toFixed(2)}s`;

    // The pipe segment with animated dashes
    const pipeSegment = (
        <div
            className={`asset-pipe ${position} ${isHigh ? 'high-conf' : ''}`}
            style={{ height: pipeH, width: pipeW, '--pipe-speed': pipeSpeed } as React.CSSProperties}
        />
    );

    // Arrow triangle pointing in direction of flow:
    // Outflow: capital drains DOWN out of asset → arrow points down (toward pool) — at BOTTOM of pipe
    // Inflow: capital flows DOWN from pool into asset → arrow points down (toward container) — at BOTTOM of pipe
    const arrowEl = <div className={`asset-pipe-arrow ${position}`} />;

    const pipeWithArrow = (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {pipeSegment}
            {arrowEl}
        </div>
    );

    return (
        <div className="hydro-asset">
            {/* Score + ticker label — ABOVE for outflow */}
            {position === 'outflow' && (
                <div className="asset-score-label outflow">
                    <span className="asset-ticker">{tk}</span>
                    <span className="asset-score-num">{asset.pressure_score.toFixed(2)}</span>
                </div>
            )}

            {/* Inflow: pipe+arrow runs above the box (from pool → box) */}
            {position === 'inflow' && pipeWithArrow}

            {/* Container box */}
            <div className={`asset-box ${position === 'outflow' ? 'outflow-box' : 'inflow-box'} ${!hasCot ? 'no-cot' : ''}`}>
                {hasCot && (
                    <div
                        className={`asset-fluid-bg ${zLong ? 'long' : 'short'} ${asset.contrarian_position ? 'contrarian' : ''}`}
                        style={{ height: `${fillPct}%` }}
                    />
                )}
                <div className="asset-box-inner">
                    <div className="asset-box-top">
                        <span className={`asset-conf-badge ${asset.confidence}`}>
                            {asset.confidence === 'HIGH' ? 'High Confidence'
                                : asset.confidence === 'MEDIUM' ? 'Med Confidence'
                                    : 'Low Confidence'}
                        </span>
                        {asset.contrarian_position && (
                            <span className="asset-contrarian-flag" title="Contrarian signal">⚠️</span>
                        )}
                    </div>
                    <div className="asset-name">{name}</div>
                    <div className="asset-z-label">
                        z&thinsp;
                        {hasCot ? (
                            <span className={`asset-z-val ${zLong ? 'long' : 'short'}`}>
                                {z! > 0 ? '+' : ''}{z!.toFixed(2)}
                            </span>
                        ) : (
                            <span className="asset-z-val" style={{ color: 'rgba(255,255,255,0.25)' }}>— no COT</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Outflow: pipe+arrow below the box (from box → pool) */}
            {position === 'outflow' && pipeWithArrow}

            {/* Score label BELOW for inflow */}
            {position === 'inflow' && (
                <div className="asset-score-below">
                    <span className="asset-ticker">{tk}</span>
                    <span className="asset-score-num inflow">+{asset.pressure_score.toFixed(2)}</span>
                </div>
            )}
        </div>
    );
}

/* ─── Main HydroModel Component ──────────────────────── */
export default function HydroModel({ assets }: { assets: PressureAsset[] }) {
    const [filter, setFilter] = useState<Confidence>('HIGH');

    const { outflows, inflows } = useMemo(() => {
        const filtered = assets.filter(a => passesFilter(a.confidence, filter));
        return {
            outflows: filtered.filter(a => a.pressure_score < 0)
                .sort((a, b) => a.pressure_score - b.pressure_score),
            inflows: filtered.filter(a => a.pressure_score >= 0)
                .sort((a, b) => b.pressure_score - a.pressure_score),
        };
    }, [assets, filter]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            <div style={{ marginBottom: 20 }}>
                <div className="db-view-title">Hydro Model</div>
                <div className="db-view-subtitle" style={{ marginBottom: 14 }}>
                    Capital rotation diagram — fluid level = COT z-score, pipe width &amp; speed = pressure magnitude.
                </div>

                {/* Legend */}
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 14, flexWrap: 'wrap' }}>
                    <span>🔴 Outflow → pool</span>
                    <span>🟢 Inflow ← pool</span>
                    <span style={{ color: 'rgba(255,255,255,0.2)' }}>░ No COT data</span>
                    <span>⚠️ Contrarian signal</span>
                    <span>Pipe width &amp; speed ∝ |pressure|</span>
                </div>

                {/* Confidence filter */}
                <div className="hydro-switcher">
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginRight: 6 }}>Show:</span>
                    {CONF_OPTIONS.map(opt => (
                        <button
                            key={opt.key}
                            className={`hydro-switch-btn ${filter === opt.key ? 'active' : ''}`}
                            onClick={() => setFilter(opt.key)}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="hydro-scene">
                {/* OUTFLOWS — above pool */}
                <div className="hydro-row outflow">
                    {outflows.length === 0 ? (
                        <div className="hydro-empty-hint">No outflow assets at this confidence level</div>
                    ) : (
                        outflows.map(a => <AssetContainer key={a.label} asset={a} position="outflow" />)
                    )}
                </div>

                {/* Capital Rotation Pool */}
                <div className="crp-wrap">
                    <div className="crp-bar">
                        <span className="crp-label">Capital Rotation Pool</span>
                    </div>
                </div>

                {/* INFLOWS — below pool */}
                <div className="hydro-row inflow">
                    {inflows.length === 0 ? (
                        <div className="hydro-empty-hint">No inflow assets at this confidence level</div>
                    ) : (
                        inflows.map(a => <AssetContainer key={a.label} asset={a} position="inflow" />)
                    )}
                </div>
            </div>
        </div>
    );
}
