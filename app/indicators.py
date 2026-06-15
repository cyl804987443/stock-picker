"""Technical indicator calculations (pandas-based)."""

import pandas as pd
import numpy as np


def calc_ma(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    if periods is None:
        periods = [5, 10, 20, 60]
    for p in periods:
        df[f"ma{p}"] = df["close"].rolling(window=p).mean()
    return df


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd_dif"] = ema_fast - ema_slow
    df["macd_dea"] = df["macd_dif"].ewm(span=signal, adjust=False).mean()
    df["macd_bar"] = 2 * (df["macd_dif"] - df["macd_dea"])
    return df


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df



def calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """Calculate KDJ indicator.
    RSV = (close - low_n) / (high_n - low_n) * 100
    K = smoothing(RSV, m1), D = smoothing(K, m2), J = 3*K - 2*D
    """
    import numpy as np
    low_n = df["low"].rolling(window=n).min()
    high_n = df["high"].rolling(window=n).max()
    rsv = ((df["close"] - low_n) / (high_n - low_n + 1e-10)) * 100

    k_vals, d_vals = [], []
    k_prev, d_prev = 50.0, 50.0
    for r in rsv:
        if pd.isna(r):
            k_vals.append(np.nan); d_vals.append(np.nan)
        else:
            k = (m1 - 1) / m1 * k_prev + 1 / m1 * r
            d = (m2 - 1) / m2 * d_prev + 1 / m2 * k
            k_vals.append(k); d_vals.append(d)
            k_prev, d_prev = k, d
    df["kdj_k"] = k_vals
    df["kdj_d"] = d_vals
    df["kdj_j"] = [3 * k - 2 * d if not pd.isna(k) else np.nan for k, d in zip(k_vals, d_vals)]
    return df


def calc_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df["vol_ma20"] = df["volume"].rolling(window=20).mean()
    df["vol_ma5"] = df["volume"].rolling(window=5).mean()
    df["vol_ratio"] = (df["volume"] / df["vol_ma20"].replace(0, np.nan)).fillna(0)
    df["amount_ma20"] = df["amount"].rolling(window=20).mean()
    df["price_range"] = ((df["high"] - df["low"]) / df["close"].replace(0, np.nan) * 100).fillna(0)
    return df


def calc_price_position(df: pd.DataFrame, period: int = 60) -> pd.DataFrame:
    """Calculate price position percentile within recent period."""
    if len(df) < period:
        period = len(df)
    recent = df["close"].tail(period)
    df["price_position"] = ((df["close"] - recent.min()) / (recent.max() - recent.min() + 1e-10) * 100).fillna(50)
    return df


def calc_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 5:
        return df
    df = df.copy()
    df = calc_ma(df)
    df = calc_macd(df)
    df = calc_rsi(df)
    df = calc_kdj(df)
    df = calc_volume_metrics(df)
    df = calc_price_position(df)
    return df


def is_macd_golden_cross(df: pd.DataFrame) -> bool:
    """Check if MACD golden cross happened on latest day."""
    if len(df) < 2:
        return False
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return (prev["macd_dif"] <= prev["macd_dea"] and
            last["macd_dif"] > last["macd_dea"] and
            not pd.isna(last["macd_dif"]))


def is_ma_bullish(df: pd.DataFrame, periods: list[int] | None = None) -> bool:
    """Check if MA alignment is bullish: MA5 > MA10 > MA20 > MA60."""
    if periods is None:
        periods = [5, 10, 20, 60]
    last = df.iloc[-1]
    mas = [safe_get(last, f"ma{p}") for p in periods]
    if any(pd.isna(m) or m == 0 for m in mas):
        return False
    return all(mas[i] > mas[i + 1] for i in range(len(mas) - 1))


def safe_get(row, key: str, default: float = 0.0) -> float:
    val = row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)
    return float(val) if val and not pd.isna(val) else default
