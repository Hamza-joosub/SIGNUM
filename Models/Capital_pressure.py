import yfinance as yf
import pandas as pd
import numpy as np
import requests
import zipfile
import io

# ── CONSTANTS ──────────────────────────────────────────────────────────────────

TICKERS = ['SPY', 'VGK', 'EEM', 'TLT', 'SHV', 'EMB', 'GLD', 'USO', 'DJP', 'GBTC', 'UUP', 'FXY', 'BIL', 'EZA', 'EMLC']

TICKER_LABELS = {
    'SPY':       'US Equities (SPY)',
    'VGK':       'European Equities (VGK)',
    'EEM':       'Emerging Markets (EEM)',
    'TLT':       'US Long Bonds (TLT)',
    'SHV':       'US Short Bonds (SHV)',
    'EMB':       'EM USD Bonds (EMB)',
    'GLD':       'Gold (GLD)',
    'USO':       'Crude Oil (USO)',
    'DJP':       'Broad Commodities (DJP)',
    'GBTC':      'Bitcoin (GBTC)',
    'UUP':       'US Dollar (UUP)',
    'FXY':       'Japanese Yen (FXY)',
    'BIL':       'T-Bills 1-3M (BIL)',
    'EZA':       'South African Equities (EZA)',
    'EMLC':      'EM Local Currency Bonds (EMLC)'
}

WINDOWS = {
    '1W': 5,    # ~1 trading week
    '1M': 21,   # ~1 trading month
    '3M': 63,   # ~1 trading quarter
    '6M': 126,  # ~2 trading quarters
    '1Y': 252,  # ~1 trading year
}

LAYER_WEIGHTS = {
    # Global defaults — sum to 0.85 by design.
    # Positioning (0.15) is applied as a modifier, not an addend.
    'momentum':    0.30,
    'volume':      0.25,
    'relative':    0.30,
    'positioning': 0.15,
}

INSTRUMENT_LAYER_WEIGHTS = {
    # Per-instrument overrides — used when ETF volume is structurally unreliable.
    # Volume is downweighted for OTC/thin instruments; weight shifts to momentum/relative.
    'GLD': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'TLT': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'BIL': {'momentum': 0.45, 'volume': 0.00, 'relative': 0.45, 'positioning': 0.10},
    'SHV': {'momentum': 0.45, 'volume': 0.00, 'relative': 0.45, 'positioning': 0.10},
    'UUP': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'FXY': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10},
    'EZA': {'momentum': 0.40, 'volume': 0.10, 'relative': 0.40, 'positioning': 0.10},
    'EMLC': {'momentum': 0.40, 'volume': 0.05, 'relative': 0.45, 'positioning': 0.10}
}

VOLUME_RELIABILITY = {
    # Discount factor applied to volume_norm per instrument.
    # 1.0 = full trust, 0.1 = heavily discounted.
    'SPY':  1.0,
    'TLT':  1.0,
    'GLD':  1.0,
    'EEM':  0.9,
    'GBTC': 0.85,
    'VGK':  0.8,
    'USO':  0.8,
    'EMB':  0.7,
    'UUP':  0.1,
    'DJP':  0.2,
    'FXY':  0.1,
    'BIL':  0.1,
    'SHV':  0.1,
    'EZA':0.65,
    'EMLC':0.7
}

COT_MAP = {
    # Maps ETF tickers to their CFTC futures contract names.
    # None = no clean futures equivalent.
    'SPY':  'E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE',
    'TLT':  'UST BOND - CHICAGO BOARD OF TRADE',
    'EEM':  'MSCI EM INDEX - ICE FUTURES U.S.',
    'VGK':  'MSCI EAFE  - ICE FUTURES U.S.',
    'DJP':  'BBG COMMODITY - CHICAGO BOARD OF TRADE',
    'GBTC': 'BITCOIN - CHICAGO MERCANTILE EXCHANGE',
    'UUP':  'USD INDEX - ICE FUTURES U.S.',
    'FXY':  'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE',
    'GLD':  'GOLD - COMMODITY EXCHANGE INC.',
    'USO':  'CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE',
    'SHV':  None,
    'BIL':  None,
    'EMB':  None,
    'EZA': [
        'SOUTH AFRICAN RAND - CHICAGO MERCANTILE EXCHANGE',  # 2020-01-07 → 2022-02-01
        'SO AFRICAN RAND - CHICAGO MERCANTILE EXCHANGE',],
    'EMLC':None
}

# ── DATE HELPERS ───────────────────────────────────────────────────────────────

def resolve_date(prices, as_of_date=None):
    """
    Resolves as_of_date to an actual trading day in the price index.

    - None       → returns the most recent trading day (latest snapshot)
    - Any date   → returns the nearest prior trading day (handles weekends/holidays)

    Args:
        prices     : MultiIndex OHLCV DataFrame from yfinance
        as_of_date : str, date, datetime, or None

    Returns:
        pd.Timestamp guaranteed to exist in prices.index
    """
    all_dates = prices.index

    if as_of_date is None:
        return all_dates[-1]

    target = pd.Timestamp(as_of_date)
    prior  = all_dates[all_dates <= target]

    if len(prior) == 0:
        raise ValueError(f"as_of_date {as_of_date} is before the start of price data ({all_dates[0].date()})")

    resolved = prior[-1]
    if resolved != target:
        print(f"[resolve_date] {target.date()} is not a trading day — using {resolved.date()}")

    return resolved


def resolve_cot_date(df_cot_all, as_of_date=None):
    """
    Filters COT data to only include reports publicly available by as_of_date.

    COT reports are released every Friday covering the prior Tuesday.
    We add 3 days to each report date to get its publication date,
    then filter to publication_date <= as_of_date.

    - None → returns all COT data unfiltered (most recent snapshot)

    Args:
        df_cot_all : combined COT DataFrame with 'date' column
        as_of_date : pd.Timestamp, str, or None

    Returns:
        pd.DataFrame — COT rows available as of the given date
    """
    if as_of_date is None:
        return df_cot_all

    df = df_cot_all.copy()
    df['publication_date'] = df['date'] + pd.Timedelta(days=3)
    df = df[df['publication_date'] <= pd.Timestamp(as_of_date)]
    df = df.drop(columns='publication_date')

    if df.empty:
        print(f"[resolve_cot_date] No COT data available as of {as_of_date}")

    return df


def build_date_index(prices, freq='W-FRI'):
    """
    Returns a sorted list of all Fridays in the price data,
    mapped to the nearest prior actual trading day.

    Weekly granularity matches the COT release cadence —
    each Friday is when the latest COT report is published.

    Args:
        prices : MultiIndex OHLCV DataFrame
        freq   : str — pandas frequency string

    Returns:
        list of pd.Timestamp
    """
    all_dates = prices.index
    fridays   = pd.date_range(start=all_dates.min(), end=all_dates.max(), freq=freq)

    valid = []
    for f in fridays:
        prior = all_dates[all_dates <= f]
        if len(prior) > 0:
            valid.append(prior[-1])

    return sorted(set(valid))


# ── DATA FETCHING ──────────────────────────────────────────────────────────────

def get_prices(tickers, start='2020-01-01'):
    """
    Downloads OHLCV price data for all tickers from yfinance.

    Pulls from start date to today. Forward-fills missing values
    (e.g. holidays where some markets are closed but others open).
    Drops any remaining rows with all NaN values.

    Args:
        tickers : list of str
        start   : str — start date for download

    Returns:
        pd.DataFrame — MultiIndex OHLCV DataFrame
    """
    df = yf.download(tickers=tickers, start=start, auto_adjust=True)
    df = df.ffill()
    df = df.dropna(how='all')
    return df


def get_financial_cot_data(years=[2023, 2024, 2025]):
    """
    Downloads CFTC financial futures COT data for the given years
    and returns a single concatenated DataFrame.

    Source: fut_fin_xls_{year}.zip from cftc.gov
    Contains: equities, bonds, FX, crypto futures positioning.

    Deduplicates on (market name, date) to handle year-boundary overlaps.

    Args:
        years : list of int

    Returns:
        pd.DataFrame — raw financial COT data
    """
    dfs = []
    for year in years:
        print(f"Fetching financial COT {year}...")
        url = f"https://www.cftc.gov/files/dea/history/fut_fin_xls_{year}.zip"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer':    'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        zf  = zipfile.ZipFile(io.BytesIO(response.content))
        xls = zf.open(zf.namelist()[0]).read()
        dfs.append(pd.read_excel(io.BytesIO(xls), engine='xlrd'))

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY'])
    combined = combined.sort_values('Report_Date_as_MM_DD_YYYY').reset_index(drop=True)
    return combined


def process_financial_cot(df):
    """
    Extracts leveraged money net position from raw financial COT data.

    Leveraged money = hedge funds + CTAs — the most directional
    and momentum-driven category of futures participants.

    Args:
        df : raw financial COT DataFrame

    Returns:
        pd.DataFrame with columns: Market_and_Exchange_Names, date, net_position
    """
    cols = ['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY',
            'Lev_Money_Positions_Long_All', 'Lev_Money_Positions_Short_All']
    df = df[cols].copy()
    df['date']         = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'], format='%m/%d/%Y')
    df['net_position'] = df['Lev_Money_Positions_Long_All'] - df['Lev_Money_Positions_Short_All']
    return df[['Market_and_Exchange_Names', 'date', 'net_position']].sort_values('date').reset_index(drop=True)


def get_commodities_cot_data(years=[2023, 2024, 2025]):
    """
    Downloads CFTC disaggregated (commodity) COT data for the given years.

    Source: fut_disagg_xls_{year}.zip from cftc.gov
    Contains: gold, crude oil, broad commodity futures positioning.

    Args:
        years : list of int

    Returns:
        pd.DataFrame — raw commodity COT data
    """
    dfs = []
    for year in years:
        print(f"Fetching commodity COT {year}...")
        url = f"https://www.cftc.gov/files/dea/history/fut_disagg_xls_{year}.zip"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer':    'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        zf  = zipfile.ZipFile(io.BytesIO(response.content))
        xls = zf.open(zf.namelist()[0]).read()
        dfs.append(pd.read_excel(io.BytesIO(xls), engine='xlrd'))

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY'])
    combined = combined.sort_values('Report_Date_as_MM_DD_YYYY').reset_index(drop=True)
    return combined


def process_commodities_cot(df):
    """
    Extracts managed money net position from raw commodity COT data.

    Note: commodity COT uses M_Money (managed money) rather than
    Lev_Money — different CFTC classification, same economic meaning.

    Args:
        df : raw commodity COT DataFrame

    Returns:
        pd.DataFrame with columns: Market_and_Exchange_Names, date, net_position
    """
    cols = ['Market_and_Exchange_Names', 'Report_Date_as_MM_DD_YYYY',
            'M_Money_Positions_Long_ALL', 'M_Money_Positions_Short_ALL']
    df = df[cols].copy()
    df['date']         = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'], format='%m/%d/%Y')
    df['net_position'] = df['M_Money_Positions_Long_ALL'] - df['M_Money_Positions_Short_ALL']
    return df[['Market_and_Exchange_Names', 'date', 'net_position']].sort_values('date').reset_index(drop=True)


# ── COT HELPERS ────────────────────────────────────────────────────────────────

def get_cot_series(df_cot_all, ticker, as_of_date=None):
    cot_name = COT_MAP.get(ticker)
    if cot_name is None:
        return None

    df = resolve_cot_date(df_cot_all, as_of_date)

    # Handle both single string and list of names (e.g. renamed contracts)
    if isinstance(cot_name, list):
        mask = df['Market_and_Exchange_Names'].isin(cot_name)
    else:
        mask = df['Market_and_Exchange_Names'] == cot_name

    series = (
        df[mask]
        [['date', 'net_position']]
        .sort_values('date')
        .drop_duplicates('date')
        .set_index('date')
        ['net_position']
    )

    return series if not series.empty else None


def positioning_stretch(series, lookback=52):
    """
    Computes the rolling z-score of net speculative positioning.

    shift(1) ensures the current week is excluded from its own rolling mean —
    preventing lookahead bias in historical replay.

    Returns None if the series has fewer rows than lookback — this happens
    when replaying early dates that don't yet have a full year of COT history.
    Scoring functions treat None as "no COT data" and apply no modifier.

    Args:
        series   : pd.Series — weekly net position
        lookback : int — number of weeks (default 52 = 1 year)

    Returns:
        pd.Series of z-scores, or None if insufficient history
    """
    if series is None or len(series.dropna()) < lookback:
        return None

    rolling_mean = series.shift(1).rolling(window=lookback).mean()
    rolling_std  = series.shift(1).rolling(window=lookback).std()
    z_score      = (series - rolling_mean) / rolling_std

    return z_score


# ── SCORING HELPERS ────────────────────────────────────────────────────────────

def normalise(value, min_val, max_val):
    """
    Linearly scales a value to [-1, +1] using provided min/max bounds.
    Returns 0.0 if min == max (flat series).
    """
    if max_val == min_val:
        return 0.0
    return 2 * (value - min_val) / (max_val - min_val) - 1


def get_layer_weights(ticker):
    """
    Returns layer weights for a ticker.
    Uses INSTRUMENT_LAYER_WEIGHTS override if one exists, otherwise LAYER_WEIGHTS.
    """
    return INSTRUMENT_LAYER_WEIGHTS.get(ticker, LAYER_WEIGHTS)


def positioning_modifier(z_score, direction):
    """
    Converts a COT z-score into a score discount multiplier.

    Direction-aware: only discounts when positioning is crowded in the SAME
    direction as the pressure signal (trade is exhausted).

    If positioning opposes the signal (contrarian setup), no discount is applied
    but contrarian_flag=True is returned so the UI can surface a warning.

    Args:
        z_score   : float or None
        direction : str — 'inflow' or 'outflow'

    Returns:
        tuple (modifier: float, contrarian_flag: bool)
            modifier 1.00 — neutral or insufficient data
            modifier 0.75 — moderately crowded (1.5 ≤ |z| < 2.0)
            modifier 0.50 — extremely crowded (|z| ≥ 2.0)
    """
    if z_score is None:
        return 1.0, False

    abs_z = abs(z_score)

    same_direction = (
        (z_score > 0 and direction == 'inflow') or
        (z_score < 0 and direction == 'outflow')
    )

    if not same_direction:
        return 1.0, True   # contrarian — no discount, flag it

    if abs_z < 1.5:   return 1.0,  False
    elif abs_z < 2.0: return 0.75, False
    else:             return 0.50, False


# ── MAIN SCORING FUNCTION ──────────────────────────────────────────────────────

def composite_pressure_score(
    ticker,
    prices,
    df_cot_all,
    window_label='3M',
    as_of_date=None,
    volume_reliability_override=None,
):
    """
    Computes the capital pressure score for a single asset as of a given date.

    Pass as_of_date=None (default) for the most recent available data.
    Pass a historical date for backtesting — all data is sliced to only
    use information that would have been available on that date.

    The four layers:
        L1 Momentum   : price return over window, normalised to instrument history
        L2 Volume     : current vs 30d avg volume, log-scaled + reliability discount
        L3 Relative   : performance vs equal-weighted universe average
        L4 Positioning: COT z-score modifier, direction-aware crowding discount

    Args:
        ticker                      : str
        prices                      : MultiIndex OHLCV DataFrame from yfinance
        df_cot_all                  : combined COT DataFrame
        window_label                : str — '1W','1M','3M','6M','1Y'
        as_of_date                  : str, datetime, or None
        volume_reliability_override : float or None

    Returns:
        dict with keys: ticker, window, as_of, pressure_score, direction,
                        confidence, momentum_norm, volume_norm, relative_norm,
                        positioning_z, positioning_mod, contrarian_position
    """
    as_of = resolve_date(prices, as_of_date)

    # Slice all price data to as_of — no future data leaks through
    prices_asof = prices.loc[:as_of]

    n       = WINDOWS[window_label]
    close   = prices_asof['Close'][ticker].ffill()
    volume  = prices_asof['Volume'][ticker].ffill()
    weights = get_layer_weights(ticker)

    if len(close.dropna()) < n + 30:
        raise ValueError(f"{ticker}: insufficient price history as of {as_of.date()}")

    # ── LAYER 1: Momentum ──────────────────────────────────────────────────────
    # Return over the window, normalised against this instrument's own full history.
    # A historically large return scores near ±1; a routine return scores near 0.
    momentum_series = close.pct_change(periods=n) * 100
    momentum_raw    = momentum_series.iloc[-1]
    momentum_norm   = normalise(momentum_raw, momentum_series.min(), momentum_series.max())

    # ── LAYER 2: Volume Conviction ─────────────────────────────────────────────
    # Today's volume vs 30d trailing average (shift(1) excludes today from its own avg).
    # Log-scaled: 3x avg = +1.0, 0.33x avg = -1.0.
    # Reliability discount applied for OTC/thin instruments.
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
    # This instrument's return minus the equal-weighted universe average.
    # Isolates rotation: an asset can fall in price but still show inflow
    # pressure if it falls less than everything else.
    
    all_returns = prices_asof['Close'].ffill().pct_change(periods=n, fill_method=None).iloc[-1] * 100
    universe_return = all_returns.mean()
    relative_raw    = all_returns[ticker] - universe_return
    relative_norm   = normalise(
        relative_raw,
        all_returns.min() - universe_return,
        all_returns.max() - universe_return,
    )

    # ── LAYER 4: Positioning Modifier ─────────────────────────────────────────
    # COT z-score filtered to data available as_of the target date.
    # Only discounts when positioning is crowded in the same direction as signal.
    cot_series = get_cot_series(df_cot_all, ticker, as_of_date=as_of)
    z_score    = None

    if cot_series is not None:
        z_series = positioning_stretch(cot_series, lookback=52)
        if z_series is not None and not z_series.dropna().empty:
            z_score = z_series.dropna().iloc[-1]

    raw_direction = 'inflow' if (
        weights['momentum'] * momentum_norm +
        weights['volume']   * volume_norm   +
        weights['relative'] * relative_norm
    ) > 0 else 'outflow'

    modifier, contrarian_flag = positioning_modifier(z_score, raw_direction)

    # ── COMPOSITE ──────────────────────────────────────────────────────────────
    raw_score       = (
        weights['momentum'] * momentum_norm +
        weights['volume']   * volume_norm   +
        weights['relative'] * relative_norm
    )
    adjusted_score  = raw_score * modifier
    final_score     = round(adjusted_score * 10, 2)
    final_direction = 'inflow' if final_score > 0 else 'outflow'

    score_magnitude = abs(final_score)
    if score_magnitude >= 6.0:   confidence = 'HIGH'
    elif score_magnitude >= 3.0: confidence = 'MEDIUM'
    else:                        confidence = 'LOW'

    return {
        'ticker':              ticker,
        'window':              window_label,
        'as_of':               as_of.date(),
        'pressure_score':      final_score,
        'direction':           final_direction,
        'confidence':          confidence,
        'momentum_norm':       round(momentum_norm, 3),
        'volume_norm':         round(volume_norm, 3),
        'relative_norm':       round(relative_norm, 3),
        'positioning_z':       round(float(z_score), 2) if z_score is not None else None,
        'positioning_mod':     modifier,
        'contrarian_position': contrarian_flag,
    }


# ── UNIVERSE RUNNER ────────────────────────────────────────────────────────────

def run_universe(prices, df_cot_all, window_label='3M', as_of_date=None):
    """
    Runs composite_pressure_score across all tickers as of a given date,
    then rescales so the strongest signal anchors at ±10.

    Pass as_of_date=None for the latest snapshot.
    Pass a historical date for backtesting / slider replay.

    Rescaling is essential — raw scores are mathematically compressed
    because most assets have mixed layer signals. Without rescaling
    everything clusters between ±2. Rescaling preserves relative magnitude
    while spreading scores across the readable ±10 range.

    Confidence is recomputed after rescaling — pre-rescale values
    from composite_pressure_score() should be ignored.

    Args:
        prices       : MultiIndex OHLCV DataFrame
        df_cot_all   : combined COT DataFrame
        window_label : str — '1W','1M','3M','6M','1Y'
        as_of_date   : str, datetime, or None

    Returns:
        pd.DataFrame sorted by pressure_score descending
    """
    as_of   = resolve_date(prices, as_of_date)
    results = []

    for ticker in TICKERS:
        try:
            score = composite_pressure_score(
                ticker, prices, df_cot_all,
                window_label=window_label,
                as_of_date=as_of,
            )
            results.append(score)
        except Exception as e:
            print(f"{ticker} failed as of {as_of.date()}: {e}")

    df = pd.DataFrame(results)

    max_abs = df['pressure_score'].abs().max()
    if max_abs > 0:
        df['pressure_score'] = (df['pressure_score'] / max_abs * 10).round(2)

    def rescaled_confidence(score):
        m = abs(score)
        if m >= 6.0:   return 'HIGH'
        elif m >= 3.0: return 'MEDIUM'
        else:          return 'LOW'

    df['confidence'] = df['pressure_score'].apply(rescaled_confidence)
    df = df.sort_values('pressure_score', ascending=False).reset_index(drop=True)

    df['positioning_z'] = pd.to_numeric(df['positioning_z'], errors='coerce')

    df['label'] = df['ticker'].map(TICKER_LABELS).fillna(df['ticker'])
    return df


# ── RUN ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # --- Load prices ---
    prices = get_prices(TICKERS, start='2009-01-01')
    print(f"Prices loaded: {prices.index[0].date()} → {prices.index[-1].date()}")

    # --- Build date index for slider ---
    date_index = build_date_index(prices)
    print(f"{len(date_index)} weekly snapshots available")
    print(f"Range: {date_index[0].date()} → {date_index[-1].date()}")

    # --- Load COT data ---
    df_cot_raw       = get_financial_cot_data(years=[2020, 2021, 2022, 2023, 2024, 2025])
    df_cot_fin       = process_financial_cot(df_cot_raw)

    df_cot_comm_raw  = get_commodities_cot_data(years=[2020, 2021, 2022, 2023, 2024, 2025])
    df_cot_comm      = process_commodities_cot(df_cot_comm_raw)

    df_cot_all       = pd.concat([df_cot_fin, df_cot_comm], ignore_index=True)
    print(f"COT data loaded: {df_cot_all['date'].min().date()} → {df_cot_all['date'].max().date()}")

    # --- Latest snapshot (default) ---
    df_scores = run_universe(prices, df_cot_all, window_label='3M')
    print("\n── LATEST SNAPSHOT ──")
    print(df_scores[['label', 'pressure_score', 'direction', 'confidence', 'positioning_z', 'contrarian_position']].to_string())

    # --- Historical replay examples ---
    df_covid      = run_universe(prices, df_cot_all, window_label='3M', as_of_date='2020-03-20')
    df_peak_hike  = run_universe(prices, df_cot_all, window_label='3M', as_of_date='2022-10-14')
    df_ai_rally   = run_universe(prices, df_cot_all, window_label='3M', as_of_date='2023-11-03')

    print("\n── COVID CRASH (2020-03-20) ──")
    print(df_covid[['label', 'pressure_score', 'direction', 'confidence', 'positioning_z', 'contrarian_position']].to_string())

    print("\n── PEAK RATE HIKE CYCLE (2022-10-14) ──")
    print(df_peak_hike[['label', 'pressure_score', 'direction', 'confidence', 'positioning_z', 'contrarian_position']].to_string())

    print("\n── AI RALLY (2023-11-03) ──")
    print(df_ai_rally[['label', 'pressure_score', 'direction', 'confidence', 'positioning_z', 'contrarian_position']].to_markdown())

