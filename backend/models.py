from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from .database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    market = Column(String(10), default="A股")
    added_at = Column(DateTime, default=datetime.utcnow)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    cost_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    notes = Column(Text, default="")
    trade_date = Column(String(10), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    ai_report = Column(Text, default="")
    ta_summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
