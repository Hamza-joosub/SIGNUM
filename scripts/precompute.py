"""
Vercel build-time pre-computation script.

Runs the Capital Pressure Model for every weekly Friday from 2018 to today
and serialises the results to public/precomputed_results.json.

The Next.js frontend fetches this file once on load and uses it for all
historical date queries — zero API calls, instant date switching.
"""
import sys, os, json
from datetime import datetime, timedelta

# Make Models/ importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from Models.Capital_pressure import (
    get_prices, get_financial_cot_data, process_financial_cot,
    get_commodities_cot_data, process_commodities_cot,
    build_date_index, run_universe, TICKERS,
)
import pandas as pd

# ── 1. Download base data ────────────────────────────────────────────────
print("[precompute] Fetching yfinance prices (2018→today)…")
prices = get_prices(TICKERS, start="2018-01-01")

current_year = datetime.now().year
cot_years = list(range(2018, current_year + 1))
print(f"[precompute] Fetching COT data ({cot_years[0]}–{cot_years[-1]})…")

df_fin_raw  = get_financial_cot_data(years=cot_years)
df_fin      = process_financial_cot(df_fin_raw)
df_comm_raw = get_commodities_cot_data(years=cot_years)
df_comm     = process_commodities_cot(df_comm_raw)
df_cot      = pd.concat([df_fin, df_comm], ignore_index=True)

# ── 2. Build list of weekly Friday dates ─────────────────────────────────
all_dates = build_date_index(prices, freq="W-FRI")
date_strs = [d.strftime("%Y-%m-%d") for d in all_dates]
print(f"[precompute] {len(date_strs)} weekly dates to compute.")

# ── 3. Run model for every date ──────────────────────────────────────────
results: dict = {}
failed = 0

for i, date_str in enumerate(date_strs):
    try:
        df = run_universe(prices, df_cot, window_label="3M", as_of_date=date_str)
        records = []
        for _, row in df.iterrows():
            records.append({
                "label":               row.get("label"),
                "ticker":              row.get("ticker"),
                "pressure_score":      float(row["pressure_score"])      if pd.notna(row.get("pressure_score"))      else 0.0,
                "direction":           row.get("direction", ""),
                "confidence":          row.get("confidence", "LOW"),
                "momentum_norm":       float(row["momentum_norm"])        if pd.notna(row.get("momentum_norm"))        else 0.0,
                "volume_norm":         float(row["volume_norm"])          if pd.notna(row.get("volume_norm"))          else 0.0,
                "relative_norm":       float(row["relative_norm"])        if pd.notna(row.get("relative_norm"))        else 0.0,
                "positioning_z":       float(row["positioning_z"])        if pd.notna(row.get("positioning_z"))        else None,
                "contrarian_position": bool(row.get("contrarian_position", False)),
            })
        results[date_str] = records
    except Exception as e:
        failed += 1

    if (i + 1) % 25 == 0 or (i + 1) == len(date_strs):
        print(f"  [{i+1}/{len(date_strs)}] computed ({failed} skipped)")

# ── 4. Write output ───────────────────────────────────────────────────────
output = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "dates":        sorted(results.keys()),
    "data":         results,
}

out_path = os.path.join(ROOT, "public", "precomputed_results.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(output, f, separators=(",", ":"))  # compact — smaller file

size_kb = os.path.getsize(out_path) / 1024
print(f"[precompute] Done — {len(results)} dates, {size_kb:.1f} KB → {out_path}")
