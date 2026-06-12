from fastapi import APIRouter, HTTPException, Query
from ..services.data_fetcher import get_stock_history, get_stock_info, search_stocks
from ..services.ta_engine import calculate_all_indicators

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    results = search_stocks(q)
    return results


@router.get("/{symbol}")
def get_stock_kline(symbol: str, limit: int = Query(default=250, ge=60, le=500)):
    info = get_stock_info(symbol)
    df = get_stock_history(symbol, limit=limit)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    indicators = calculate_all_indicators(df)
    if not indicators:
        raise HTTPException(status_code=500, detail="Failed to calculate indicators")

    return {
        "symbol": symbol,
        "name": info["name"],
        "market": info["market"],
        "kline": indicators,
    }
