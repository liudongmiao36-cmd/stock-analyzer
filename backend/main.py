from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import threading

from .database import engine, Base
from .models import Watchlist, Position, AnalysisCache
from .routers import watchlist, stocks, portfolio, analysis
from .services.data_fetcher import _load_stock_list

Base.metadata.create_all(bind=engine)

app = FastAPI(title="股票技术分析系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.on_event("startup")
async def startup_event():
    # Pre-load stock list in background to speed up first search
    t = threading.Thread(target=_load_stock_list, daemon=True)
    t.start()


@app.get("/")
async def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ping")
async def ping():
    # Keep-alive endpoint for Render free tier (use UptimeRobot to ping every 10 min)
    return "pong"
