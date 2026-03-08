'use client';
import { useState, useEffect } from 'react';
import TimelineSlider from './TimelineSlider';
import HydroModel, { type PressureAsset } from './HydroModel';

/* ─── Types ──────────────────────────────────────────── */
type Asset = { label: string;[key: string]: any };

interface DateBundle {
    pressure: { date?: string; assets: Asset[] };
    momentum: { date?: string; assets: Asset[] };
    volume: { date?: string; assets: Asset[] };
    returns: { date?: string; assets: Asset[] };
}

type DataCache = { [dateKey: string]: DateBundle };

/* ─── Helpers ────────────────────────────────────────── */
function addWeeks(dateStr: string, weeks: number): string {
    const d = new Date(dateStr + 'T00:00:00');
    d.setDate(d.getDate() + weeks * 7);
    return d.toISOString().slice(0, 10);
}

function clamp(dateStr: string, min: string, max: string): string {
    if (dateStr < min) return min;
    if (dateStr > max) return max;
    return dateStr;
}

const RANGE_START = '2018-01-05';
const today = new Date();
const dow = today.getDay();
const offset = dow >= 5 ? dow - 5 : dow + 2;
const rangeEnd = new Date(today);
rangeEnd.setDate(rangeEnd.getDate() - offset);
const RANGE_END = rangeEnd.toISOString().slice(0, 10);

/* ─── Tab config ─────────────────────────────────────── */
const TABS = [
    { id: 'hydro', label: 'Hydro Model' },
    { id: 'momentum', label: 'Momentum' },
    { id: 'volume', label: 'Volume' },
    { id: 'cot', label: 'COT Positioning' },
    { id: 'pressure', label: 'Pressure' },
];

/* ─── Main Dashboard ─────────────────────────────────── */
export default function Dashboard({ onClose }: { onClose: () => void }) {
    const [activeDate, setActiveDate] = useState(RANGE_END);
    const [activeTab, setActiveTab] = useState('hydro');
    const [cache, setCache] = useState<DataCache>({});
    const [loading, setLoading] = useState(false);
    const [preloaded, setPreloaded] = useState(false); // true once precomputed JSON loaded

    /** Derive all four tab bundles from a single pressure asset list */
    function bundleFromAssets(dateStr: string, assets: Asset[]): DateBundle {
        return {
            pressure: { date: dateStr, assets },
            momentum: { date: dateStr, assets: assets.map(a => ({ label: a.label, score: a.momentum_norm ?? 0 })) },
            volume: { date: dateStr, assets: assets.map(a => ({ label: a.label, z_score: a.volume_norm ?? 0 })) },
            returns: { date: dateStr, assets: assets.map(a => ({ label: a.label, return_pct: a.relative_norm ?? 0 })) },
        };
    }

    /**
     * Fetch a single date from the live API.
     * ONE request only (/api/pressure) — it already contains all fields
     * (momentum_norm, volume_norm, relative_norm) so we derive the other
     * tab bundles client-side. This avoids 3 extra parallel cold starts.
     */
    async function fetchFromApi(dateStr: string) {
        if (cache[dateStr]) return; // already have it
        setLoading(true);
        try {
            const res = await fetch(`/api/pressure?date=${dateStr}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const pressure = await res.json();
            const assets: Asset[] = pressure.assets ?? [];
            setCache(prev => ({ ...prev, [dateStr]: bundleFromAssets(dateStr, assets) }));
        } catch (e) {
            console.error('[Dashboard] API fetch failed:', e);
        } finally {
            setLoading(false);
        }
    }

    /** Try to load pre-built JSON. Falls back to live API silently. */
    useEffect(() => {
        fetch('/precomputed_results.json')
            .then(r => r.ok ? r.json() : Promise.reject('not found'))
            .then((json: { data: Record<string, Asset[]> }) => {
                const fullCache: DataCache = {};
                for (const [d, assets] of Object.entries(json.data)) {
                    fullCache[d] = bundleFromAssets(d, assets as Asset[]);
                }
                setCache(fullCache);
                setPreloaded(true);
                setLoading(false);
            })
            .catch(() => {
                // Precomputed JSON not available — initial load via API
                setPreloaded(true); // mark as done so date-change effect unblocks
                fetchFromApi(activeDate);
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /** On date change: if cache has it → instant, else fetch via API */
    useEffect(() => {
        if (!preloaded) return; // wait for initial precomputed check to finish
        if (!cache[activeDate]) {
            fetchFromApi(activeDate);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeDate, preloaded]);

    const bundle = cache[activeDate];

    return (
        <div className="dashboard-overlay">
            {/* ── Topbar ── */}
            <header className="db-topbar">
                <div className="db-topbar-left">
                    <button className="db-back-btn" onClick={onClose}>←</button>
                    <span className="db-model-name">Capital Pressure Model</span>
                    <span className="db-model-badge">Cross-Asset</span>
                </div>
                <div className="db-topbar-right">
                    <span className="db-last-run">
                        Snapshot: <span>{activeDate}</span>
                    </span>
                    <button className="db-refresh-btn" onClick={() => { setCache({}); }}>↻ Refresh</button>
                </div>
            </header>


            {/* ── Horizontal tab bar ── */}
            <div className="db-tab-bar">
                {TABS.map((tab, i) => (
                    <div
                        key={tab.id}
                        className={`db-tab ${activeTab === tab.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <span className="db-tab-num">{i + 1}</span>
                        {tab.label}
                    </div>
                ))}
            </div>

            {/* ── Body: sidebar + main ── */}
            <div className="db-body">
                {/* Left sidebar */}
                <aside className="db-sidebar">
                    {/* Timeline slider at the top */}
                    <TimelineSlider
                        value={activeDate}
                        onChange={setActiveDate}
                        loading={loading}
                    />

                    {/* Summary below */}
                    <div className="db-summary-area">
                        {!bundle ? (
                            <div style={{ paddingTop: 16, color: 'rgba(255,255,255,0.2)', fontSize: 11 }}>
                                Loading summary…
                            </div>
                        ) : (
                            <SummarySidebar bundle={bundle} />
                        )}
                    </div>
                </aside>

                {/* Main content */}
                <main className="db-main">
                    {!bundle ? (
                        <div className="db-spinner"><div className="spinner-ring"></div></div>
                    ) : (
                        <TabContent activeTab={activeTab} bundle={bundle} />
                    )}
                </main>
            </div>
        </div>
    );
}

/* ─── Summary Sidebar ────────────────────────────────── */
function SummarySidebar({ bundle }: { bundle: DateBundle }) {
    const pressureAssets = bundle.pressure?.assets ?? [];
    const momentumAssets = bundle.momentum?.assets ?? [];

    const topPressure = [...pressureAssets]
        .sort((a, b) => Math.abs(b.pressure_score ?? 0) - Math.abs(a.pressure_score ?? 0))
        .slice(0, 7);

    const topMomentum = [...momentumAssets]
        .sort((a, b) => Math.abs(b.score ?? 0) - Math.abs(a.score ?? 0))
        .slice(0, 4);

    return (
        <>
            <div className="db-summary-section-label">Pressure Rankings</div>
            {topPressure.map(a => {
                const val = Number(a.pressure_score ?? 0);
                const isPos = val >= 0;
                const pct = Math.min(Math.abs(val) / 10 * 100, 100);
                return (
                    <div key={a.label} className="summary-row">
                        <span className="summary-row-name" title={a.label}>{a.label?.slice(0, 15)}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div className="summary-bar-bg">
                                <div className={`summary-bar-fill ${isPos ? 'pos' : 'neg'}`} style={{ width: `${pct}%` }}></div>
                            </div>
                            <span className={`summary-score ${isPos ? 'pos' : 'neg'}`}>
                                {val > 0 ? '+' : ''}{val.toFixed(1)}
                            </span>
                        </div>
                    </div>
                );
            })}

            <div className="db-summary-section-label">Top Momentum</div>
            {topMomentum.map(a => {
                const val = Number(a.score ?? 0);
                const isPos = val >= 0;
                return (
                    <div key={a.label} className="summary-row">
                        <span className="summary-row-name" title={a.label}>{a.label?.slice(0, 15)}</span>
                        <span className={`summary-score ${isPos ? 'pos' : 'neg'}`}>
                            {val > 0 ? '+' : ''}{val.toFixed(2)}
                        </span>
                    </div>
                );
            })}
        </>
    );
}

/* ─── Tab Router ─────────────────────────────────────── */
function TabContent({ activeTab, bundle }: { activeTab: string; bundle: DateBundle }) {
    switch (activeTab) {
        case 'hydro':
            return <HydroModel assets={(bundle.pressure?.assets ?? []) as PressureAsset[]} />;
        case 'momentum':
            return <BarView
                title="Momentum Signals"
                subtitle="Trend direction based on price momentum across assets."
                assets={bundle.momentum?.assets ?? []}
                valueKey="score" maxScale={1}
            />;
        case 'volume':
            return <BarView
                title="Volume Conviction"
                subtitle="Relative volume z-scores indicating participant conviction."
                assets={bundle.volume?.assets ?? []}
                valueKey="z_score" maxScale={3}
            />;
        case 'cot':
            return <BarView
                title="COT Positioning"
                subtitle="Commitment of Traders net positioning percentile."
                assets={bundle.pressure?.assets ?? []}
                valueKey="positioning_z" maxScale={3}
            />;
        case 'pressure':
            return <BarView
                title="Pressure Index"
                subtitle="Composite directional pressure combining all signal layers."
                assets={bundle.pressure?.assets ?? []}
                valueKey="pressure_score" maxScale={10}
            />;
        default:
            return null;
    }
}

/* ─── Reusable Bar Chart ─────────────────────────────── */
function BarView({ title, subtitle, assets, valueKey, maxScale }: {
    title: string; subtitle: string;
    assets: Asset[]; valueKey: string; maxScale: number;
}) {
    if (!assets.length) {
        return (
            <>
                <div>
                    <div className="db-view-title">{title}</div>
                    <div className="db-view-subtitle">{subtitle}</div>
                </div>
                <div style={{ color: 'rgba(255,255,255,0.2)', fontSize: 12, paddingTop: 20 }}>
                    No data available for this view or date.
                </div>
            </>
        );
    }
    return (
        <>
            <div>
                <div className="db-view-title">{title}</div>
                <div className="db-view-subtitle">{subtitle}</div>
            </div>
            <div className="chart-container">
                <div className="chart-header">{assets.length} Assets</div>
                <div className="chart-rows">
                    {assets.map(asset => {
                        const val = Number(asset[valueKey] ?? 0);
                        const isPos = val >= 0;
                        const pct = Math.min(Math.abs(val) / maxScale * 100, 100);
                        return (
                            <div key={asset.label} className="chart-row">
                                <div className="chart-row-label" title={asset.label}>{asset.label}</div>
                                <div className="chart-axis-area">
                                    <div className="chart-axis-line"></div>
                                    <div className="chart-bar-neg-side">
                                        {!isPos && <div className="chart-bar neg" style={{ width: `${pct}%` }}></div>}
                                    </div>
                                    <div className="chart-bar-pos-side">
                                        {isPos && <div className="chart-bar pos" style={{ width: `${pct}%` }}></div>}
                                    </div>
                                </div>
                                <div className={`chart-val ${isPos ? 'pos' : 'neg'}`}>
                                    {val > 0 ? '+' : ''}{val.toFixed(2)}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </>
    );
}
