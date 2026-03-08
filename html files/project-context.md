# QuantLab — Project Context

## What This Is
QuantLab is a personal financial modelling dashboard. A single user (the owner) runs quantitative models against cross-asset market data and visualises the outputs. It is not a public-facing SaaS product — it is a private analytical tool deployed on Vercel.

---

## Objective
Provide a clean, authoritative interface for running and interpreting cross-asset capital flow models. The UI must communicate signal strength, direction, and institutional positioning at a glance — with zero ambiguity about what is positive vs negative, high confidence vs low.

---

## Tech Stack
- **Frontend:** Next.js 14 (App Router) + React + TypeScript + Tailwind CSS
- **Backend:** FastAPI (Python) deployed as Vercel serverless functions in `/api`
- **Hosting:** Vercel — single repo, both frontend and backend deploy together
- **Fonts:** Fraunces (serif, Google Fonts) for display/headings/values · DM Sans for all UI/body text
- **No component library** — all UI is custom, hand-coded to the design system below

---

## Design System — "Deep Navy · Gold & Olive · Glass"

**Background:** `#080d18` deep navy canvas. Three layered radial gradients as a `::before` pseudo-element: faint gold bloom top-right `rgba(200,169,110,0.07)`, faint olive bloom bottom-left `rgba(74,110,74,0.08)`, dark vignette centre.

**Colour palette:**
- Background: `#080d18`
- Gold accent: `#c8a96e` → `#a8883e` — CTAs, active states, topbar border, regime badges ONLY. Never used as a data colour.
- Olive/positive: `#8ab870` → `#6a9858` — all positive signals, inflows, upward deltas
- Red/negative: `#c86060` → `#d87070` — all negative signals, outflows, downward deltas
- Primary text: `#eae6de` (warm off-white)
- Secondary text: `rgba(255,255,255,0.5)`
- Muted text: `rgba(255,255,255,0.22)`
- Borders: always alpha `rgba(255,255,255,0.06–0.10)` — never opaque

**Glassmorphism:** every surface uses `backdrop-filter: blur()`. Hierarchy: sidebar `blur(24px)` · topbar `blur(28px)` · cards `blur(32px)`. Cards always have `inset 0 1px 0 rgba(255,255,255,0.07)` top highlight and `0 8px 40px rgba(0,0,0,0.45)` drop shadow.

**Layout:** 200px fixed left sidebar (view navigation) + fluid main content area + 260px right panel (signal summary). Right panel collapses to 0 on the Hydro Graph view.

**Topbar:** 58px height, `1px` gold border-bottom `rgba(200,169,110,0.18)`.

---

## Application Structure

**Landing page** has three tabs: Explore Overview · Models · Coming Soon. The Models tab shows a card grid — currently one live model (Capital Pressure Model) and two "coming soon" placeholders.

**Model dashboard** opens fullscreen (replaces landing page) when a model card is clicked. Back button returns to landing. The dashboard has:
- A topbar with model name, back button, and refresh CTA
- A regime strip (5 cells: Risk Mode, USD Trend, Rates, Vol Regime, Commodities) replacing a metrics bar
- A date slider (4 named snapshots: COVID Crash Mar 2020, Peak Hike Cycle Oct 2022, AI Rally Nov 2023, Today) — open-ended, snaps between snapshots
- A left sidenav with 6 views
- A right signal summary panel (hidden on Hydro view)

---

## Model: Capital Pressure Model
Cross-asset capital flow model. Analyses 15 assets across equities, bonds, FX, commodities, and crypto.

**Output fields per asset per snapshot:**
- `label` — asset name with ticker e.g. "Crude Oil (USO)"
- `pressure_score` — float [-10, +10], fixed scale. Positive = inflow, negative = outflow.
- `direction` — "inflow" | "outflow"
- `confidence` — "HIGH" | "MEDIUM" | "LOW"
- `positioning_z` — float or null. COT z-score vs 100-day mean. Null for assets not covered by COT reports.
- `contrarian_position` — boolean. True when institutional positioning opposes the pressure direction.

**Six views in the dashboard:**
1. **Momentum** — normalised cross-asset momentum score [-1, 1], diverging bar chart
2. **Volume** — relative volume z-score vs 30-day average, diverging bar chart
3. **Relative Returns** — 5-day return vs equal-weight benchmark, diverging bar chart
4. **COT Positioning** — `positioning_z` bar chart, ±3σ scale, COT-covered assets only, sorted descending
5. **Pressure** — `pressure_score` diverging bar chart, fixed [-10, +10] scale, confidence badges (HIGH=olive, MEDIUM=muted, LOW=red), ⚠ icon on contrarian positions
6. **Hydro Graph** — default view. Two sub-modes toggled by button:
   - *Grid mode:* 4-column grid of SVG "container" cards. Each tank's fill level = `positioning_z` (±3σ → 8–92% fill). Hatched fill for null COT. Animated pipe enters top for inflows, exits bottom for outflows. Pipe width scales with pressure magnitude.
   - *Rotation mode:* Single SVG diagram. Outflow assets (top row, alphabetical) drain via animated pipes into a central "Capital Rotation Pool" reservoir. Inflow assets (bottom row, alphabetical) receive pipes from the reservoir. Decorative pool fill. Assets centred when row is sparse.
   - Confidence filter toggle: All / ≥ Medium (default) / High only
   - Fullscreen button expands to 5-column grid

**Data semantics:** outflows from assets broadly fund inflows to others, but routing proportions are unknown — the pool is conceptual, not a precise accounting identity.

---

## Backend API Shape (FastAPI)
The frontend expects endpoints of the form:

```
GET /api/pressure?date=YYYY-MM-DD
→ { date, label, assets: [{ label, pressure_score, direction, confidence, positioning_z, contrarian_position }] }

GET /api/momentum?date=YYYY-MM-DD
→ { date, assets: [{ label, score }] }

GET /api/volume?date=YYYY-MM-DD
→ { date, assets: [{ label, z_score }] }

GET /api/returns?date=YYYY-MM-DD
→ { date, assets: [{ label, return_pct }] }
```

All responses are JSON. The frontend passes the selected slider date as a query parameter. The backend runs the appropriate Python model and returns sorted results.
