from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models import Position

router = APIRouter()


class PositionCreate(BaseModel):
    symbol: str
    cost_price: float
    quantity: int
    notes: Optional[str] = ""
    trade_date: Optional[str] = ""


class PositionUpdate(BaseModel):
    cost_price: Optional[float] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    trade_date: Optional[str] = None


@router.get("")
def get_all_positions(db: Session = Depends(get_db)):
    positions = db.query(Position).order_by(Position.created_at.desc()).all()
    return [_to_dict(p) for p in positions]


@router.get("/{symbol}")
def get_positions_by_symbol(symbol: str, db: Session = Depends(get_db)):
    positions = db.query(Position).filter(Position.symbol == symbol).all()
    return [_to_dict(p) for p in positions]


@router.post("")
def add_position(req: PositionCreate, db: Session = Depends(get_db)):
    pos = Position(
        symbol=req.symbol,
        cost_price=req.cost_price,
        quantity=req.quantity,
        notes=req.notes or "",
        trade_date=req.trade_date or "",
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return _to_dict(pos)


@router.put("/{position_id}")
def update_position(position_id: int, req: PositionUpdate, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    if req.cost_price is not None:
        pos.cost_price = req.cost_price
    if req.quantity is not None:
        pos.quantity = req.quantity
    if req.notes is not None:
        pos.notes = req.notes
    if req.trade_date is not None:
        pos.trade_date = req.trade_date
    db.commit()
    db.refresh(pos)
    return _to_dict(pos)


@router.delete("/{position_id}")
def delete_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(pos)
    db.commit()
    return {"ok": True}


def _to_dict(p: Position) -> dict:
    return {
        "id": p.id,
        "symbol": p.symbol,
        "cost_price": p.cost_price,
        "quantity": p.quantity,
        "notes": p.notes,
        "trade_date": p.trade_date,
    }
