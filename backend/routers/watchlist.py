from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import Watchlist
from ..services.data_fetcher import get_stock_info

router = APIRouter()


class AddWatchlistRequest(BaseModel):
    symbol: str


@router.get("")
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(Watchlist).order_by(Watchlist.added_at).all()
    return [
        {"id": w.id, "symbol": w.symbol, "name": w.name, "market": w.market}
        for w in items
    ]


@router.post("")
def add_to_watchlist(req: AddWatchlistRequest, db: Session = Depends(get_db)):
    symbol = req.symbol.strip().zfill(6)
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        return {"symbol": existing.symbol, "name": existing.name, "market": existing.market}

    info = get_stock_info(symbol)
    item = Watchlist(symbol=symbol, name=info["name"], market=info["market"])
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "symbol": item.symbol, "name": item.name, "market": item.market}


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
