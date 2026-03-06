import yfinance as yf
import charset_normalizer
import pandas as pd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
import zipfile
import io

WINDOWS = {
    '1W': 5,    # ~1 trading week
    '1M': 21,   # ~1 trading month  
    '3M': 63,   # ~1 trading quarter
    '6M': 126,  # ~2 trading quarters
    '1Y': 252,  # ~1 trading year
}

LAYER_WEIGHTS = {
    # Controls how much each layer contributes to the final score.
    # Must sum to 1.0. Tune these after backtesting against known rotation events.
    # Momentum and relative are weighted equally as the primary signals.
    # Volume is slightly lower — thinner instruments make it less reliable universally.
    # Positioning is lowest — weekly, lagged data with incomplete coverage.
    'momentum':    0.30,
    'volume':      0.25,
    'relative':    0.30,
    'positioning': 0.15,
}

VOLUME_RELIABILITY = {
    # Per-instrument layer weight overrides.
    # Only specify the layers you want to change — missing keys fall back to LAYER_WEIGHTS.
    # Use this when an instrument's volume is structurally unreliable (e.g. GLD, TLT)
    # and momentum/relative pressure should carry more weight instead.
    #
    # Example: GLD often accumulates quietly on below-average volume during
    # institutional buying phases. Penalising it for low volume produces a
    # misleadingly weak score. Shift weight from volume to momentum and relative.
    # Discount factor applied to volume_norm for each instrument.
    # 1.0 = full trust, 0.1 = heavily discounted.
    # Lower values for instruments that trade OTC, have thin markets,
    # or where volume does not meaningfully reflect capital intent.
    'SPY':  1.0,   # most liquid equity ETF — volume is highly meaningful
    'TLT':  1.0,   # highly liquid bond ETF
    'GLD':  1.0,   # liquid gold ETF — but often accumulates on low volume
    'EEM':  0.9,   # liquid but EM flows can be noisy
    'IBIT': 0.85,  # reasonably liquid but crypto volume can be erratic
    'VGK':  0.8,   # decent EU equity liquidity
    'USO':  0.8,   # oil ETF — reasonable but subject to roll distortions
    'EMB':  0.7,   # EM bond ETF — OTC bond market limits volume signal
    'UUP':  0.1,   # USD ETF — FX is largely OTC, ETF volume is proxy only
    'DJP':  0.2,   # broad commodity — complex basket, volume less meaningful
    'FXY':  0.1,   # JPY ETF — same OTC FX limitation as UUP
    'BIL':  0.1,   # T-bill ETF — institutional parking, barely trades
    'SHV':  0.1,   # same as BIL — volume essentially meaningless
}

INSTRUMENT_LAYER_WEIGHTS = {
    'GLD': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'TLT': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'BIL': {'momentum': 0.45, 'volume': 0.00, 'relative': 0.45, 'positioning': 0.10},
    'SHV': {'momentum': 0.45, 'volume': 0.00, 'relative': 0.45, 'positioning': 0.10},
    'UUP': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'FXY': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
}

COT_MAP = {

    # Maps each ETF ticker to its corresponding CFTC futures contract name.
    # None = no clean futures equivalent exists in the COT data.
    'SPY':  'E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE',
    'TLT':  'UST BOND - CHICAGO BOARD OF TRADE',
    'EEM':  'MSCI EM INDEX - ICE FUTURES U.S.',
    'VGK':  'MSCI EAFE  - ICE FUTURES U.S.',
    'DJP':  'BBG COMMODITY - CHICAGO BOARD OF TRADE',
    'IBIT': 'BITCOIN - CHICAGO MERCANTILE EXCHANGE',
    'UUP':  'USD INDEX - ICE FUTURES U.S.',
    'FXY':  'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE',
    'GLD':  'GOLD - COMMODITY EXCHANGE INC.',
    'USO':  'CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE',
    'SHV':  None,
    'BIL':  None,
    'EMB':  None,
}

def build_date_index(prices, freq='W-FRI'):
    """
    Returns list of all Fridays in the price data.
    Weekly granularity matches COT release cadence.
    """
    all_dates = prices.index
    start = all_dates.min()
    end   = all_dates.max()
    
    fridays = pd.date_range(start=start, end=end, freq='W-FRI')
    
    # Filter to dates where market was actually open
    # (some Fridays are holidays — use nearest prior trading day)
    valid = []
    for f in fridays:
        prior = all_dates[all_dates <= f]
        if len(prior) > 0:
            valid.append(prior[-1])
    
    return sorted(set(valid))



def get_financial_cot_data(years=[2024, 2025]):
    dfs = []
    
    for year in years:
        print(f"Fetching {year}...")
        url = f"https://www.cftc.gov/files/dea/history/fut_fin_xls_{year}.zip"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        xls_name = zip_file.namelist()[0]
        
        xls_bytes = zip_file.open(xls_name).read()
        df = pd.read_excel(io.BytesIO(xls_bytes), engine='xlrd')
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY'])
    combined = combined.sort_values('Report_Date_as_MM_DD_YYYY').reset_index(drop=True)
    
    return combined

def process_financial_cot(df):
    cols = [
        'Market_and_Exchange_Names',
        'Report_Date_as_MM_DD_YYYY',
        'Lev_Money_Positions_Long_All',
        'Lev_Money_Positions_Short_All',
    ]
    
    df = df[cols].copy()
    df['date'] = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'], format='%m/%d/%Y')
    df['net_position'] = df['Lev_Money_Positions_Long_All'] - df['Lev_Money_Positions_Short_All']
    df = df[['Market_and_Exchange_Names', 'date', 'net_position']]
    df = df.sort_values('date').reset_index(drop=True)
    
    return df

def get_commodities_cot_data(years=[2023, 2024, 2025]):
    dfs = []
    
    for year in years:
        print(f"Fetching commodities {year}...")
        url = f"https://www.cftc.gov/files/dea/history/fut_disagg_xls_{year}.zip"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        xls_name = zip_file.namelist()[0]
        
        xls_bytes = zip_file.open(xls_name).read()
        df = pd.read_excel(io.BytesIO(xls_bytes), engine='xlrd')
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY'])
    combined = combined.sort_values('Report_Date_as_MM_DD_YYYY').reset_index(drop=True)
    
    return combined

def process_commodities_cot(df):
    cols = [
        'Market_and_Exchange_Names',
        'Report_Date_as_MM_DD_YYYY',
        'M_Money_Positions_Long_ALL',
        'M_Money_Positions_Short_ALL',
    ]
    
    df = df[cols].copy()
    df['date'] = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'], format='%m/%d/%Y')
    df['net_position'] = df['M_Money_Positions_Long_ALL'] - df['M_Money_Positions_Short_ALL']
    df = df[['Market_and_Exchange_Names', 'date', 'net_position']]
    df = df.sort_values('date').reset_index(drop=True)
    
    return df

def get_cot_series(df_cot_all, etf_ticker):
    cot_name = COT_MAP.get(etf_ticker)
    
    if cot_name is None:
        return None
    
    series = (
        df_cot_all[df_cot_all['Market_and_Exchange_Names'] == cot_name]
        [['date', 'net_position']]
        .sort_values('date')
        .set_index('date')
        ['net_position']
    )
    
    return series

def get_cot_as_of(df_cot_all, as_of_date):
    """
    Returns the COT dataframe filtered to only include reports
    that would have been publicly available on as_of_date.
    
    COT reports are released every Friday covering the previous Tuesday.
    So a report dated Tuesday 2024-01-02 is published Friday 2024-01-05.
    We add 3 days to each report date to get its publication date,
    then filter to publication_date <= as_of_date.
    """
    df = df_cot_all.copy()
    
    # When was each report actually available to the public?
    df['publication_date'] = df['date'] + pd.Timedelta(days=3)
    
    # Only keep reports available on or before as_of_date
    df = df[df['publication_date'] <= pd.Timestamp(as_of_date)]
    
    return df

def positioning_stretch(series, lookback=100):
    """
    series   : weekly net position pd.Series with datetime index
    lookback : int — weeks (52 = 1 year)
    
    Returns z-score series — current reading vs trailing lookback window
    """
    if series is None:
        return None
    
    rolling_mean = series.shift(1).rolling(window=lookback).mean()
    rolling_std  = series.shift(1).rolling(window=lookback).std()
    
    z_score = (series - rolling_mean) / rolling_std
    
    return z_score

def normalise(value, min_val, max_val):
    """
    Linearly scales a single value to the range [-1, +1]
    based on the provided min and max bounds.

    Used to put all layers on a common scale before combining them.
    A value at min_val returns -1, at max_val returns +1, at midpoint returns 0.

    Args:
        value   : float — the value to normalise
        min_val : float — lower bound (maps to -1)
        max_val : float — upper bound (maps to +1)

    Returns:
        float in [-1, +1]
    """
    if max_val == min_val:
        return 0.0
    return 2 * (value - min_val) / (max_val - min_val) - 1

def get_layer_weights(ticker):
    """
    Returns the layer weights for a given ticker.

    Checks INSTRUMENT_LAYER_WEIGHTS first — if an override exists for
    this ticker, use it. Otherwise fall back to the global LAYER_WEIGHTS.

    This allows per-instrument tuning without changing the global defaults.
    For example, GLD and TLT have volume downweighted because these assets
    often move on low ETF volume during institutional accumulation phases.

    Args:
        ticker : str — ETF ticker

    Returns:
        dict with keys: momentum, volume, relative, positioning
    """
    return INSTRUMENT_LAYER_WEIGHTS.get(ticker, LAYER_WEIGHTS)

def positioning_modifier(z_score, direction):
    """
    Converts a COT positioning z-score into a discount multiplier,
    taking the pressure signal direction into account.

    A crowded position in the SAME direction as the pressure signal
    means most capital has already moved — the trade is exhausted and
    vulnerable to reversal. We discount the score.

    A crowded position in the OPPOSITE direction to the pressure signal
    is a contrarian setup — shorts/longs are stretched against the move.
    This does NOT warrant a discount (the signal may actually be stronger),
    but we flag it via the 'contrarian' return value for transparency.

    Args:
        z_score   : float or None
                    - None      → no COT data, no modification
                    - positive  → funds are more net long than average
                    - negative  → funds are more net short than average
        direction : str — 'inflow' or 'outflow' (the pressure signal direction)

    Returns:
        tuple (modifier, contrarian_flag)
            modifier        : float 0.5–1.0  — score multiplier
            contrarian_flag : bool  — True if positioning opposes the signal
                                      (useful to surface in the UI as a warning)

    Modifier thresholds (only applied when positioning confirms signal direction):
        |z| < 1.0  → neutral, no discount       → 1.00
        |z| < 2.0  → moderately crowded         → 0.75
        |z| >= 2.0 → extremely crowded          → 0.50
    """
    if z_score is None:
        return 1.0, False

    abs_z = abs(z_score)

    # Check if positioning is in the same direction as the pressure signal
    # inflow signal + positive z  = crowded long  = same direction = discount
    # outflow signal + negative z = crowded short = same direction = discount
    same_direction = (
        (z_score > 0 and direction == 'inflow') or
        (z_score < 0 and direction == 'outflow')
    )

    if not same_direction:
        # Positioning is against the signal — contrarian setup
        # Don't discount, but flag it so the UI can show a warning
        return 1.0, True

    # Positioning confirms the signal — apply crowding discount
    if abs_z < 1.5:   return 1.0,  False
    elif abs_z < 2.0: return 0.75, False
    else:             return 0.50, False

def composite_pressure_score(
    ticker,
    prices,
    df_cot_all,
    window_label='3M',
    volume_reliability_override=None,
):
    """
    Computes a capital pressure score for a single asset.

    Capital pressure is a composite signal estimating whether capital
    is flowing INTO (positive) or OUT OF (negative) an asset class,
    and with what conviction. It is NOT a direct measurement of dollar
    flows — it is a weight-of-evidence inference from four observable
    footprints left by capital movement.

    The four layers:
        Layer 1 — Momentum    : price return over the chosen window,
                                normalised against this instrument's own history
        Layer 2 — Volume      : current volume vs 30-day average,
                                log-scaled and reliability-discounted
        Layer 3 — Relative    : performance vs the universe average,
                                isolates rotation from broad market moves
        Layer 4 — Positioning : COT z-score modifier, discounts crowded
                                positions in the same direction as the signal

    Layers 1-3 are normalised to [-1, +1] and combined using per-instrument
    layer weights (INSTRUMENT_LAYER_WEIGHTS or global LAYER_WEIGHTS fallback).
    Layer 4 is applied as a multiplier — only discounts when positioning
    is crowded in the same direction as the pressure signal.

    Important: scores are compressed before rescaling. Always call
    run_universe() to get properly scaled, comparable scores.

    Args:
        ticker                      : str   — ETF ticker e.g. 'GLD'
        prices                      : df    — MultiIndex OHLCV DataFrame from yfinance
        df_cot_all                  : df    — combined financial + commodity COT DataFrame
        window_label                : str   — '1W','1M','3M','6M','1Y'
        volume_reliability_override : float or None
                                      — overrides VOLUME_RELIABILITY for this ticker

    Returns:
        dict with keys:
            ticker              : str
            window              : str
            pressure_score      : float  raw score before rescaling
            direction           : str    'inflow' or 'outflow'
            confidence          : str    'HIGH', 'MEDIUM', 'LOW' (post-rescale only)
            momentum_norm       : float  normalised momentum [-1, +1]
            volume_norm         : float  normalised volume conviction [-1, +1]
            relative_norm       : float  normalised relative pressure [-1, +1]
            positioning_z       : float or None
            positioning_mod     : float  crowding discount multiplier
            contrarian_position : bool   True if COT positioning opposes the signal
    """

    n      = WINDOWS[window_label]
    close  = prices['Close'][ticker].ffill()
    volume = prices['Volume'][ticker].ffill()

    # Fetch per-instrument layer weights — falls back to global if no override
    weights = get_layer_weights(ticker)

    # ── LAYER 1: Momentum ──────────────────────────────────────────────────────
    # Price return over the chosen window as a percentage.
    # Normalised against this instrument's own rolling history — a 5% return
    # that is historically large for this asset scores higher than a 5% return
    # that is routine. This makes scores comparable across volatile and
    # stable instruments.
    momentum_series = close.pct_change(periods=n) * 100
    momentum_raw    = momentum_series.iloc[-1]
    momentum_norm   = normalise(momentum_raw, momentum_series.min(), momentum_series.max())

    # ── LAYER 2: Volume Conviction ─────────────────────────────────────────────
    # Today's volume vs the 30-day trailing average (shift(1) excludes today).
    # Log-scaled: ratio of 3x average = score of 1.0, ratio of 0.33x = -1.0.
    # Reliability discount applied for OTC/thin instruments where ETF volume
    # is a poor proxy for true capital intent.
    avg_volume    = volume.shift(1).rolling(window=30).mean()
    volume_ratio  = volume / avg_volume
    current_ratio = volume_ratio.dropna().iloc[-1]
    volume_raw    = np.log(max(current_ratio, 0.01))
    volume_norm   = np.clip(volume_raw / np.log(3), -1, 1)

    reliability = (
        volume_reliability_override
        if volume_reliability_override is not None
        else VOLUME_RELIABILITY.get(ticker, 0.7)
    )
    volume_norm = volume_norm * reliability

    # ── LAYER 3: Relative Pressure ─────────────────────────────────────────────
    # This instrument's return minus the equal-weighted universe average return.
    # Positive = outperforming the field = capital preferring this asset.
    # Negative = underperforming the field = capital leaving relative to alternatives.
    # Critical for distinguishing rotation from broad liquidity expansion —
    # if everything rises equally, relative pressure is zero for all assets.
    all_returns     = prices['Close'].ffill().pct_change(periods=n).iloc[-1] * 100
    universe_return = all_returns.mean()
    relative_raw    = all_returns[ticker] - universe_return
    relative_norm   = normalise(
        relative_raw,
        all_returns.min() - universe_return,
        all_returns.max() - universe_return,
    )

    # ── LAYER 4: Positioning Modifier ─────────────────────────────────────────
    # COT z-score: how stretched are speculative futures positions vs past 52 weeks.
    # Direction-aware: only discounts when positioning is crowded in the SAME
    # direction as the pressure signal (confirming crowding = exhausted trade).
    # If positioning opposes the signal, sets contrarian_flag = True instead —
    # this is surfaced in the output for the UI to display as a warning/note.
    cot_series = get_cot_series(df_cot_all, ticker)
    z_score    = None

    if cot_series is not None:
        z_series = positioning_stretch(cot_series, lookback=52)
        if not z_series.dropna().empty:
            z_score = z_series.dropna().iloc[-1]

    # Determine direction before calling modifier
    raw_direction  = 'inflow' if (
        weights['momentum'] * momentum_norm +
        weights['volume']   * volume_norm   +
        weights['relative'] * relative_norm
    ) > 0 else 'outflow'

    modifier, contrarian_flag = positioning_modifier(z_score, raw_direction)

    # ── COMPOSITE ──────────────────────────────────────────────────────────────
    # Weighted sum of three normalised layers using per-instrument weights,
    # then multiplied by the positioning modifier.
    raw_score = (
        weights['momentum'] * momentum_norm +
        weights['volume']   * volume_norm   +
        weights['relative'] * relative_norm
    )
    adjusted_score = raw_score * modifier
    final_score    = round(adjusted_score * 10, 2)
    final_direction = 'inflow' if final_score > 0 else 'outflow'

    # ── CONFIDENCE ─────────────────────────────────────────────────────────────
    # Computed on the raw score here — recomputed properly in run_universe()
    # after rescaling. Do not interpret individual confidence values before
    # run_universe() has been called.
    score_magnitude = abs(final_score)
    if score_magnitude >= 6.0:   confidence = 'HIGH'
    elif score_magnitude >= 3.0: confidence = 'MEDIUM'
    else:                        confidence = 'LOW'

    return {
        'ticker':               ticker,
        'window':               window_label,
        'pressure_score':       final_score,
        'direction':            final_direction,
        'confidence':           confidence,
        'momentum_norm':        round(momentum_norm, 3),
        'volume_norm':          round(volume_norm, 3),
        'relative_norm':        round(relative_norm, 3),
        'positioning_z':        round(z_score, 2) if z_score is not None else None,
        'positioning_mod':      modifier,
        'contrarian_position':  contrarian_flag,
    }

def run_universe(prices, df_cot_all, window_label='3M'):
    """
    Runs composite_pressure_score across the full ticker universe,
    then rescales all scores so the strongest signal anchors at ±10.

    Rescaling is essential — raw scores are mathematically compressed
    because most assets have mixed signals across layers. Without rescaling,
    everything clusters between ±2 and the relative differences are hard
    to read. Rescaling preserves ranking and relative magnitude while
    spreading scores across the readable ±10 range.

    Confidence is recomputed after rescaling — pre-rescale confidence
    values from composite_pressure_score() should be ignored.

    Args:
        prices       : df  — MultiIndex OHLCV DataFrame from yfinance
        df_cot_all   : df  — combined financial + commodity COT DataFrame
        window_label : str — '1W','1M','3M','6M','1Y'

    Returns:
        pd.DataFrame sorted by pressure_score descending, columns:
            ticker, pressure_score, direction, confidence,
            momentum_norm, volume_norm, relative_norm,
            positioning_z, positioning_mod, contrarian_position
    """
    TICKERS = list(VOLUME_RELIABILITY.keys())
    results = []

    for ticker in TICKERS:
        try:
            score = composite_pressure_score(ticker, prices, df_cot_all, window_label)
            results.append(score)
        except Exception as e:
            print(f"{ticker} failed: {e}")

    df = pd.DataFrame(results)

    # Rescale: strongest absolute signal becomes ±10, all others scale relative to it
    max_abs = df['pressure_score'].abs().max()
    if max_abs > 0:
        df['pressure_score'] = (df['pressure_score'] / max_abs * 10).round(2)

    # Recompute confidence on rescaled scores
    def rescaled_confidence(score):
        magnitude = abs(score)
        if magnitude >= 6.0:   return 'HIGH'
        elif magnitude >= 3.0: return 'MEDIUM'
        else:                  return 'LOW'

    df['confidence'] = df['pressure_score'].apply(rescaled_confidence)
    df = df.sort_values('pressure_score', ascending=False).reset_index(drop=True)

    return df

def run_universe_as_of(prices, df_cot_all, as_of_date, window_label='3M'):
    """
    Computes the full universe pressure scores as they would have
    appeared on as_of_date — using only data available at that time.
    
    Args:
        prices       : full price DataFrame (all history)
        df_cot_all   : full COT DataFrame (all history)  
        as_of_date   : str or datetime — the historical date to compute for
        window_label : str
    
    Returns:
        pd.DataFrame — same format as run_universe()
    """
    as_of = pd.Timestamp(as_of_date)
    
    # Slice prices to only include data up to as_of_date
    prices_asof = prices.loc[:as_of]
    
    # Slice COT to only include reports published by as_of_date
    cot_asof = get_cot_as_of(df_cot_all, as_of)
    
    # Run the normal scoring engine on the sliced data
    return run_universe(prices_asof, cot_asof, window_label)


# ── RUN ────────────────────────────────────────────────────────────────────────
prices = yf.download(tickers=['SPY', 'VGK','EEM','TLT', 'SHV', 'EMB','GLD', 'USO', 'DJP', 'IBIT', 'UUP', 'FXY', 'BIL'], start='2025-01-01')
prices = df.ffill()
prices = df.dropna()
prices

date_index = build_date_index(prices)
print(f"{len(date_index)} snapshots available")
print(f"Range: {date_index[0].date()} → {date_index[-1].date()}")

df_cot = get_financial_cot_data(years=[2023, 2024, 2025])

df_cot_fin = process_financial_cot(df_cot)

df_cot_commodity = get_commodities_cot_data(years=[2023, 2024, 2025])

df_cot_comm = process_commodities_cot(df_cot_commodity)

df_cot_all = pd.concat([df_cot_fin, df_cot_comm], ignore_index=True)

df_cot_all = get_cot_as_of(df_cot_all, '2024-01-02')

df_scores = run_universe(prices, df_cot_all, window_label='3M')

run_universe_as_of(prices, df_cot_all,'2024-01-02', window_label='3M')

print(df_scores[[
    'ticker', 'pressure_score', 'direction', 'confidence',
    'positioning_z', 'positioning_mod', 'contrarian_position'
]].to_string())