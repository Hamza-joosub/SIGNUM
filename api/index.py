import os
import sys

# Add root project folder to sys.path so we can import from Models
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from typing import Optional

from Models.Capital_pressure import (
    get_prices, build_date_index,
    get_financial_cot_data, process_financial_cot,
    get_commodities_cot_data, process_commodities_cot,
    run_universe, TICKERS,
)
import pandas as pd

app = FastAPI()

# ── CORS ─────────────────────────────────────────────────────────────────
# In production set FRONTEND_URL env var in the Vercel dashboard.
# Falls back to "*" for local dev convenience.
_frontend_url = os.environ.get("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url] if _frontend_url != "*" else ["*"],
    allow_credentials=_frontend_url != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data loading (module-level, lazy) ────────────────────────────────────
# On Vercel, each warm function instance reuses these globals across requests.
# Cold starts (~20-30s) re-fetch from yfinance/CFTC. This is acceptable.
_global_prices = None
_global_cot = None
_dataset_ready = False

def _ensure_data_loaded():
    """
    Lazy-loads price and COT data on first call within a function instance.
    Synchronous — safe for Vercel's single-threaded serverless environment.
    """
    global _global_prices, _global_cot, _dataset_ready
    if _dataset_ready:
        return

    print("[coldstart] Fetching yfinance prices…")
    _global_prices = get_prices(TICKERS, start="2009-01-01")

    print("[coldstart] Fetching COT data…")
    df_fin_raw  = get_financial_cot_data(years=[2020, 2021, 2022, 2023, 2024, 2025])
    df_fin      = process_financial_cot(df_fin_raw)
    df_comm_raw = get_commodities_cot_data(years=[2020, 2021, 2022, 2023, 2024, 2025])
    df_comm     = process_commodities_cot(df_comm_raw)
    _global_cot = pd.concat([df_fin, df_comm], ignore_index=True)

    _dataset_ready = True
    print("[coldstart] Done.")

@lru_cache(maxsize=32)
def _cached_run(date_str: Optional[str]):
    """Cache model runs — instant on repeated date requests within the same warm instance."""
    return run_universe(_global_prices, _global_cot, window_label="3M", as_of_date=date_str)

# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "data_ready": _dataset_ready}

@app.get("/api/pressure")
def get_pressure(date: str = None):
    _ensure_data_loaded()
    df = _cached_run(date)
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
            # null = no COT data — frontend greys container out
            "positioning_z":       float(row["positioning_z"])        if pd.notna(row.get("positioning_z"))        else None,
            "contrarian_position": bool(row.get("contrarian_position", False)),
        })
    return {"date": date or str(df["as_of"].iloc[0]), "assets": records}

@app.get("/api/momentum")
def get_momentum(date: str = None):
    _ensure_data_loaded()
    df = _cached_run(date)
    assets = (
        df[["label", "momentum_norm"]]
        .rename(columns={"momentum_norm": "score"})
        .fillna(0)
        .to_dict(orient="records")
    )
    return {"date": date or str(df["as_of"].iloc[0]), "assets": assets}

@app.get("/api/volume")
def get_volume(date: str = None):
    _ensure_data_loaded()
    df = _cached_run(date)
    assets = (
        df[["label", "volume_norm"]]
        .rename(columns={"volume_norm": "z_score"})
        .fillna(0)
        .to_dict(orient="records")
    )
    return {"date": date or str(df["as_of"].iloc[0]), "assets": assets}

@app.get("/api/returns")
def get_returns(date: str = None):
    _ensure_data_loaded()
    df = _cached_run(date)
    assets = (
        df[["label", "relative_norm"]]
        .rename(columns={"relative_norm": "return_pct"})
        .fillna(0)
        .to_dict(orient="records")
    )
    return {"date": date or str(df["as_of"].iloc[0]), "assets": assets}
