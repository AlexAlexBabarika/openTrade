"""
FastAPI backend: REST + WebSocket for OHLCV data.
Standalone runnable (uvicorn backend.app:app).

In production the built frontend (frontend/dist/) can be served as static
files by mounting it on "/" — see the startup event below.
"""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend import cache
from backend.data_sources import load_csv, load_yfinance
from backend.indicators import sma
from backend.models import OHLCVCandle, OHLCVCandleList
from backend.websocket import stream_candles
from backend.supabase_client import get_supabase_client, is_supabase_configured
from backend.auth_routes import router as auth_router

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_supabase_configured():
        client = get_supabase_client()
        if client:
            logger.info("Supabase client initialized successfully.")
        else:
            logger.warning("Supabase credentials set but client creation failed.")
    else:
        if os.environ.get("SUPABASE_REQUIRED") == "1":
            raise RuntimeError(
                "SUPABASE_REQUIRED=1 but Supabase is not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )
        logger.warning(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "for auth and user data. Auth features will be unavailable."
        )

    yield


app = FastAPI(
    title="OpenTrade API",
    description="OHLCV data API with yfinance and CSV sources, WebSocket streaming",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data/yfinance/{symbol}", response_model=OHLCVCandleList)
async def get_yfinance(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> OHLCVCandleList:
    """
    Load OHLCV for symbol from yfinance and return unified candles.
    Cached in memory for subsequent WebSocket streaming.
    """
    candles = load_yfinance(symbol=symbol, period=period, interval=interval)
    cache.set_cached(symbol, candles)
    return OHLCVCandleList(symbol=symbol, candles=candles)


@app.post("/data/csv", response_model=dict)
async def post_csv(
    file: UploadFile = File(...),
    symbol: str = "CSV",
) -> dict:
    """
    Upload CSV; auto-detect columns, normalize to OHLCV, cache by symbol.
    """
    content = await file.read()
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        candles = load_csv(tmp_path, symbol=symbol)
        cache.set_cached_csv(symbol, candles)
        return {
            "symbol": symbol,
            "count": len(candles),
            "preview_columns": ["timestamp", "open", "high", "low", "close", "volume"],
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/data/csv/preview")
async def csv_preview_endpoint(
    file: UploadFile = File(...),
    max_rows: int = 5,
) -> dict:
    """
    Preview CSV: returns column names and first max_rows.
    Request body: multipart form with 'file' and optional 'max_rows'.
    """
    from backend.data_sources.csv_loader import csv_preview

    content = await file.read()
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        columns, rows = csv_preview(tmp_path, max_rows=max_rows)
        # Serialize rows for JSON (datetime -> str)
        out_rows = []
        for r in rows:
            out_rows.append(
                {k: str(v) if hasattr(v, "isoformat") else v for k, v in r.items()}
            )
        return {"columns": columns, "preview": out_rows}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/data/indicators/sma")
async def get_sma(symbol: str, period: int = 20) -> dict:
    """
    Return cached candles for symbol plus SMA(period) of close.
    """
    candles = cache.get_cached(symbol)
    if not candles:
        candles = load_yfinance(symbol=symbol)
        cache.set_cached(symbol, candles)
    if not candles:
        return {"symbol": symbol, "candles": [], "sma": []}
    sma_values = sma(candles, period)
    candle_list = [
        {
            "symbol": c.symbol,
            "timestamp": c.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    return {"symbol": symbol, "candles": candle_list, "sma": sma_values}


@app.websocket("/ws/stream/{symbol}")
async def ws_stream(websocket: WebSocket, symbol: str) -> None:
    """
    Stream OHLCV candles for symbol. Uses cached data if available,
    otherwise fetches from yfinance and caches.
    """
    await websocket.accept()
    try:
        candles = cache.get_cached(symbol)
        if not candles:
            candles = load_yfinance(symbol=symbol)
            cache.set_cached(symbol, candles)
        if not candles:
            await websocket.send_json({"error": "no data", "symbol": symbol})
            return
        await stream_candles(websocket, candles, delay_seconds=0.02)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


# Mount static files (must be at the end of the file to capture all remaining routes)
if FRONTEND_DIST.is_dir():
    app.mount(
        "/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend"
    )
