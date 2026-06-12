import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from scipy.signal import argrelextrema
import logging

logger = logging.getLogger(__name__)


def _s(series: pd.Series) -> list:
    """Convert Series to JSON-safe list, replacing NaN with None."""
    return [None if pd.isna(v) else round(float(v), 3) for v in series]


def _calculate_kdj(df: pd.DataFrame, n: int = 9, m: int = 3) -> tuple:
    """Chinese KDJ indicator using EWM smoothing."""
    low_n = df["low"].rolling(window=n, min_periods=1).min()
    high_n = df["high"].rolling(window=n, min_periods=1).max()
    denom = high_n - low_n
    denom = denom.replace(0, np.nan)
    rsv = (df["close"] - low_n) / denom * 100
    rsv = rsv.fillna(50)
    k = rsv.ewm(com=m - 1, adjust=False).mean()
    d = k.ewm(com=m - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def find_support_resistance(df: pd.DataFrame, order: int = 5) -> dict:
    """Detect support and resistance levels from local extrema."""
    if len(df) < order * 2 + 1:
        return {"resistance": [], "support": []}
    try:
        highs = df["high"].values
        lows = df["low"].values
        current = float(df["close"].iloc[-1])

        peak_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
        trough_idx = argrelextrema(lows, np.less_equal, order=order)[0]

        def cluster(levels, above: bool):
            if len(levels) == 0:
                return []
            levels = np.array(levels)
            levels = levels[levels > current * 1.002] if above else levels[levels < current * 0.998]
            if len(levels) == 0:
                return []
            levels = np.sort(levels)
            groups = [[levels[0]]]
            for v in levels[1:]:
                if abs(v / groups[-1][-1] - 1) < 0.025:
                    groups[-1].append(v)
                else:
                    groups.append([v])
            result = [round(float(np.mean(g)), 2) for g in groups]
            return (result[:3] if above else list(reversed(result))[:3])

        return {
            "resistance": cluster(highs[peak_idx].tolist(), above=True),
            "support": cluster(lows[trough_idx].tolist(), above=False),
        }
    except Exception as e:
        logger.warning(f"S/R detection error: {e}")
        return {"resistance": [], "support": []}


def calculate_all_indicators(df: pd.DataFrame) -> dict:
    """Calculate all technical indicators and return as JSON-ready dict."""
    if df.empty or len(df) < 10:
        return {}
    try:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        dates = [d.strftime("%Y-%m-%d") for d in df["date"]]
        # ECharts candlestick: [open, close, low, high]
        ohlcv = [
            [
                round(float(r["open"]), 2),
                round(float(r["close"]), 2),
                round(float(r["low"]), 2),
                round(float(r["high"]), 2),
                round(float(r["volume"]), 0),
            ]
            for _, r in df.iterrows()
        ]

        ema5 = _s(EMAIndicator(close, window=5).ema_indicator())
        ema10 = _s(EMAIndicator(close, window=10).ema_indicator())
        ema20 = _s(EMAIndicator(close, window=20).ema_indicator())
        ema60 = _s(EMAIndicator(close, window=60).ema_indicator())
        ema120 = _s(EMAIndicator(close, window=120).ema_indicator())

        macd_obj = MACD(close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = _s(macd_obj.macd())
        signal_line = _s(macd_obj.macd_signal())
        hist = _s(macd_obj.macd_diff())

        rsi14 = _s(RSIIndicator(close, window=14).rsi())
        rsi6 = _s(RSIIndicator(close, window=6).rsi())

        k, d, j = _calculate_kdj(df)
        kdj_k = _s(k)
        kdj_d = _s(d)
        kdj_j = _s(j)

        bb = BollingerBands(close, window=20, window_dev=2)
        bb_upper = _s(bb.bollinger_hband())
        bb_middle = _s(bb.bollinger_mavg())
        bb_lower = _s(bb.bollinger_lband())

        sr = find_support_resistance(df)

        latest_idx = -1
        latest = {
            "price": round(float(close.iloc[latest_idx]), 2),
            "change_pct": round(float(df["change_pct"].iloc[latest_idx]), 2) if "change_pct" in df.columns else 0,
            "volume": round(float(volume.iloc[latest_idx]), 0),
            "amount": round(float(df["amount"].iloc[latest_idx]), 0) if "amount" in df.columns else 0,
            "ema5": ema5[latest_idx],
            "ema10": ema10[latest_idx],
            "ema20": ema20[latest_idx],
            "ema60": ema60[latest_idx],
            "macd": macd_line[latest_idx],
            "macd_signal": signal_line[latest_idx],
            "macd_hist": hist[latest_idx],
            "rsi14": rsi14[latest_idx],
            "rsi6": rsi6[latest_idx],
            "kdj_k": kdj_k[latest_idx],
            "kdj_d": kdj_d[latest_idx],
            "kdj_j": kdj_j[latest_idx],
            "bb_upper": bb_upper[latest_idx],
            "bb_middle": bb_middle[latest_idx],
            "bb_lower": bb_lower[latest_idx],
        }

        return {
            "dates": dates,
            "ohlcv": ohlcv,
            "ema5": ema5,
            "ema10": ema10,
            "ema20": ema20,
            "ema60": ema60,
            "ema120": ema120,
            "macd": {"macd": macd_line, "signal": signal_line, "hist": hist},
            "rsi": {"rsi14": rsi14, "rsi6": rsi6},
            "kdj": {"k": kdj_k, "d": kdj_d, "j": kdj_j},
            "boll": {"upper": bb_upper, "middle": bb_middle, "lower": bb_lower},
            "support_resistance": sr,
            "latest": latest,
        }
    except Exception as e:
        logger.error(f"TA calculation error: {e}")
        return {}
