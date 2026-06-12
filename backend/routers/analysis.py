from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date as date_type
from ..database import get_db
from ..models import AnalysisCache, Position
from ..services.data_fetcher import get_stock_history, get_stock_info
from ..services.ta_engine import calculate_all_indicators
from ..services.ai_analyst import generate_analysis

router = APIRouter()


@router.get("/{symbol}")
def get_cached_analysis(symbol: str, db: Session = Depends(get_db)):
    today = str(date_type.today())
    cache = (
        db.query(AnalysisCache)
        .filter(AnalysisCache.symbol == symbol, AnalysisCache.date == today)
        .first()
    )
    if cache and cache.ai_report:
        return {"symbol": symbol, "date": today, "report": cache.ai_report, "cached": True}
    return {"symbol": symbol, "date": today, "report": None, "cached": False}


@router.post("/{symbol}")
def create_analysis(symbol: str, db: Session = Depends(get_db)):
    info = get_stock_info(symbol)
    df = get_stock_history(symbol, limit=250)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    indicators = calculate_all_indicators(df)
    if not indicators:
        raise HTTPException(status_code=500, detail="Failed to calculate indicators")

    latest = indicators.get("latest", {})
    sr = indicators.get("support_resistance", {})

    positions = db.query(Position).filter(Position.symbol == symbol).all()
    pos_list = [{"cost_price": p.cost_price, "quantity": p.quantity, "notes": p.notes} for p in positions]

    report = generate_analysis(
        symbol=symbol,
        name=info["name"],
        latest=latest,
        sr=sr,
        positions=pos_list,
    )

    today = str(date_type.today())
    cache = (
        db.query(AnalysisCache)
        .filter(AnalysisCache.symbol == symbol, AnalysisCache.date == today)
        .first()
    )
    if cache:
        cache.ai_report = report
    else:
        cache = AnalysisCache(symbol=symbol, date=today, ai_report=report)
        db.add(cache)
    db.commit()

    return {"symbol": symbol, "date": today, "report": report, "cached": False}
