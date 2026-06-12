import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger(__name__)

_stock_list_cache = None
_stock_list_lock = threading.Lock()
_stock_list_loaded = False


def _get_exchange_prefix(symbol: str) -> str:
    """Determine exchange prefix for Tencent API: sh (上交所) or sz (深交所)."""
    if symbol.startswith(('0', '3')):  # 000xxx 002xxx 300xxx -> SZSE
        return 'sz'
    return 'sh'  # 600xxx 601xxx 603xxx 688xxx 510xxx -> SSE


def _load_stock_list():
    global _stock_list_cache, _stock_list_loaded
    with _stock_list_lock:
        if _stock_list_loaded:
            return
        try:
            logger.info("Loading A股 stock list...")
            stocks = ak.stock_info_a_code_name()
            stocks = stocks.rename(columns={"code": "symbol", "name": "name"})
            stocks["market"] = "A股"
            _stock_list_cache = stocks[["symbol", "name", "market"]].copy()
            _stock_list_loaded = True
            logger.info(f"Loaded {len(_stock_list_cache)} stocks")
        except Exception as e:
            logger.error(f"Failed to load stock list: {e}")
            _stock_list_loaded = True  # mark done to avoid infinite retry
            _stock_list_cache = pd.DataFrame(columns=["symbol", "name", "market"])


def get_stock_info(symbol: str) -> dict:
    """Get stock name and market type."""
    if not _stock_list_loaded:
        _load_stock_list()
    try:
        if _stock_list_cache is not None and len(_stock_list_cache) > 0:
            match = _stock_list_cache[_stock_list_cache["symbol"] == symbol]
            if not match.empty:
                row = match.iloc[0]
                return {"symbol": symbol, "name": row["name"], "market": row["market"]}
    except Exception as e:
        logger.warning(f"Could not get info for {symbol}: {e}")
    # Fallback: return symbol itself as name
    return {"symbol": symbol, "name": symbol, "market": "A股"}


def search_stocks(query: str) -> list:
    """Search stocks by code or name."""
    if not _stock_list_loaded:
        _load_stock_list()
    if _stock_list_cache is None or len(_stock_list_cache) == 0:
        return []
    try:
        q = query.strip()
        df = _stock_list_cache
        by_code = df[df["symbol"].str.startswith(q)]
        by_name = df[df["name"].str.contains(q, na=False)]
        result = pd.concat([by_code, by_name]).drop_duplicates("symbol")
        return result.head(10).to_dict("records")
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def get_stock_history(symbol: str, limit: int = 250) -> pd.DataFrame:
    """Fetch daily OHLCV via Tencent API (no proxy required)."""
    prefix = _get_exchange_prefix(symbol)
    full_symbol = prefix + symbol
    start_date = (datetime.now() - timedelta(days=max(limit * 2, 500))).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    df = None
    last_err = None
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_hist_tx(
                symbol=full_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                break
        except Exception as e:
            last_err = e
            logger.warning(f"TX attempt {attempt+1} failed for {symbol}: {type(e).__name__}")

    if df is None or df.empty:
        logger.error(f"All fetch attempts failed for {symbol}: {last_err}")
        return pd.DataFrame()

    # Tencent returns: date, open, close, high, low, amount
    # 'amount' here is trading volume in 手 (lots = 100 shares)
    df = df.rename(columns={"amount": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    df["change_pct"] = df["close"].pct_change() * 100
    df["amount"] = df["volume"] * df["close"] * 100  # approximate transaction value in yuan
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(limit).reset_index(drop=True)
