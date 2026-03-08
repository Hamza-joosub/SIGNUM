'use client';
import { useRef, useState, useCallback, useEffect } from 'react';

/* ─── Config ─────────────────────────────────────────── */
// Start: first Friday in Jan 2020
const RANGE_START = new Date('2020-01-03T00:00:00');
// End: today snapped to the most recent Friday
const today = new Date();
const dayOfWeek = today.getDay(); // 0=Sun, 5=Fri
const daysToLastFriday = dayOfWeek >= 5 ? dayOfWeek - 5 : dayOfWeek + 2;
const RANGE_END = new Date(today);
RANGE_END.setDate(RANGE_END.getDate() - daysToLastFriday);
RANGE_END.setHours(0, 0, 0, 0);

const RANGE_MS = RANGE_END.getTime() - RANGE_START.getTime();
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;



/* ─── Helpers ────────────────────────────────────────── */
function dateToFraction(dateStr: string): number {
    const d = new Date(dateStr + 'T00:00:00').getTime();
    return Math.max(0, Math.min(1, (d - RANGE_START.getTime()) / RANGE_MS));
}

function fractionToNearestFriday(frac: number): string {
    const ms = RANGE_START.getTime() + frac * RANGE_MS;
    const d = new Date(ms);
    // snap to nearest Friday
    const dow = d.getDay(); // 0=Sun … 6=Sat
    const diff = dow < 3 ? -(dow === 0 ? 2 : dow + 2) : (5 - dow);
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    // clamp
    if (d < RANGE_START) return formatDate(RANGE_START);
    if (d > RANGE_END) return formatDate(RANGE_END);
    return formatDate(d);
}

function formatDate(d: Date): string {
    return d.toISOString().slice(0, 10);
}

function formatDateDisplay(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

/* ─── Year ticks to show along the track ────────────── */
const YEAR_TICKS = [2020, 2021, 2022, 2023, 2024, 2025, 2026].filter(y => {
    const d = new Date(`${y}-01-02T00:00:00`).getTime();
    return d >= RANGE_START.getTime() && d <= RANGE_END.getTime();
});

/* ─── Component ──────────────────────────────────────── */
interface TimelineSliderProps {
    /** Currently committed date string (YYYY-MM-DD) */
    value: string;
    /** Called only on mouseup/touchend with the final snapped date */
    onChange: (date: string) => void;
    /** Whether data is currently being fetched for the committed date */
    loading?: boolean;
}

export default function TimelineSlider({ value, onChange, loading = false }: TimelineSliderProps) {
    const trackRef = useRef<HTMLDivElement>(null);
    const isDragging = useRef(false);

    // "live" fraction while dragging; null = not dragging
    const [dragFrac, setDragFrac] = useState<number | null>(null);
    const [showTooltip, setShowTooltip] = useState(false);

    const committedFrac = dateToFraction(value);
    const displayFrac = dragFrac ?? committedFrac;
    const displayDate = dragFrac !== null
        ? fractionToNearestFriday(dragFrac)
        : value;

    /* Compute fraction from pointer position */
    const fracFromEvent = useCallback((clientX: number): number => {
        const rect = trackRef.current!.getBoundingClientRect();
        return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    }, []);

    /* ── Mouse events ── */
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isDragging.current = true;
        setShowTooltip(true);
        setDragFrac(fracFromEvent(e.clientX));

        const onMove = (ev: MouseEvent) => {
            if (!isDragging.current) return;
            setDragFrac(fracFromEvent(ev.clientX));
        };
        const onUp = (ev: MouseEvent) => {
            isDragging.current = false;
            setShowTooltip(false);
            const final = fractionToNearestFriday(fracFromEvent(ev.clientX));
            setDragFrac(null);
            onChange(final);
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    }, [fracFromEvent, onChange]);

    /* ── Touch events ── */
    const onTouchStart = useCallback((e: React.TouchEvent) => {
        isDragging.current = true;
        setShowTooltip(true);
        setDragFrac(fracFromEvent(e.touches[0].clientX));

        const onMove = (ev: TouchEvent) => {
            setDragFrac(fracFromEvent(ev.touches[0].clientX));
        };
        const onEnd = (ev: TouchEvent) => {
            isDragging.current = false;
            setShowTooltip(false);
            const touch = ev.changedTouches[0];
            const final = fractionToNearestFriday(fracFromEvent(touch.clientX));
            setDragFrac(null);
            onChange(final);
            window.removeEventListener('touchmove', onMove);
            window.removeEventListener('touchend', onEnd);
        };
        window.addEventListener('touchmove', onMove, { passive: true });
        window.addEventListener('touchend', onEnd);
    }, [fracFromEvent, onChange]);

    /* Click anywhere on track = jump + commit */
    const onTrackClick = useCallback((e: React.MouseEvent) => {
        if (isDragging.current) return;
        const final = fractionToNearestFriday(fracFromEvent(e.clientX));
        onChange(final);
    }, [fracFromEvent, onChange]);

    return (
        <div className="timeline-wrapper">
            {/* Header row */}
            <div className="timeline-label-row">
                <span className="timeline-section-title">Snapshot Date</span>
                <span className="timeline-current-date">{formatDateDisplay(displayDate)}</span>
            </div>

            {/* Fetching badge */}
            {loading && (
                <div className="timeline-fetching-badge">
                    <div className="timeline-fetching-dot"></div>
                    Fetching data…
                </div>
            )}

            {/* Track */}
            <div
                ref={trackRef}
                className="timeline-track-container"
                onMouseDown={onMouseDown}
                onTouchStart={onTouchStart}
                onClick={onTrackClick}
            >
                {/* Background rail */}
                <div className="timeline-track-bg"></div>

                {/* Filled portion */}
                <div
                    className="timeline-track-fill"
                    style={{ width: `${displayFrac * 100}%` }}
                ></div>




                {/* Thumb */}
                <div
                    className={`timeline-thumb ${loading ? 'loading' : ''}`}
                    style={{ left: `${displayFrac * 100}%` }}
                >
                    {/* Tooltip while dragging */}
                    {showTooltip && (
                        <div className="slider-tooltip">
                            {formatDateDisplay(displayDate)}
                        </div>
                    )}
                </div>
            </div>

            {/* Year ticks */}
            <div style={{ position: 'relative', height: 14 }}>
                {YEAR_TICKS.map(yr => {
                    const frac = (new Date(`${yr}-01-02T00:00:00`).getTime() - RANGE_START.getTime()) / RANGE_MS;
                    return (
                        <span
                            key={yr}
                            className="timeline-year-tick"
                            style={{
                                position: 'absolute',
                                left: `${frac * 100}%`,
                                transform: 'translateX(-50%)',
                                fontSize: 9,
                                color: 'rgba(255,255,255,0.2)',
                                fontWeight: 600,
                            }}
                        >
                            {yr}
                        </span>
                    );
                })}
            </div>
        </div>
    );
}
