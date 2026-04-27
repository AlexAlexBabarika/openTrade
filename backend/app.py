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

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from backend.market import cache
from backend.market.data_sources import load_csv, load_yfinance
from backend.market.data_sources.csv_loader import csv_preview
from backend.market.models import OHLCVCandleList
from backend.market.ohlcv_limits import cap_candles
from backend.market.shared_config import validate_interval, validate_period
from backend.websocket import stream_candles
from backend.streaming.hub import ClientSession, get_hub
from backend.streaming.protocol import (
    ClientMessage,
    ErrorMessage,
    PongMessage,
    ServerMessage,
    SubscribeMessage,
    UnsubscribeMessage,
)
from backend.core.supabase_client import get_supabase_client, is_supabase_configured
from backend.routes.auth_routes import router as auth_router
from backend.routes.user_routes import router as user_router
from backend.routes.ticker_workspace_routes import router as ticker_workspace_router
from backend.routes.api_key_routes import router as api_key_router
from backend.routes.market_routes import router as market_router
from backend.routes.indicator_routes import router as indicator_router
from backend.routes.symbol_routes import router as symbol_router
from backend.routes.volume_profile_routes import router as volume_profile_router
from backend.routes.position_metrics_routes import router as position_metrics_router
from backend.core.rate_limit import allow, client_key, retry_after_seconds

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

_WS_PROVIDERS = frozenset({"yfinance", "binance", "twelvedata", "csv"})


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

    hub = get_hub()
    await hub.start()
    try:
        yield
    finally:
        await hub.stop()


app = FastAPI(
    title="OpenTrade API",
    description="OHLCV data API with yfinance and CSV sources, WebSocket streaming",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(ticker_workspace_router)
app.include_router(api_key_router)
app.include_router(market_router)
app.include_router(indicator_router)
app.include_router(symbol_router)
app.include_router(volume_profile_router)
app.include_router(position_metrics_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data/yfinance/{symbol}", response_model=OHLCVCandleList, deprecated=True)
async def get_yfinance(
    request: Request,
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> OHLCVCandleList:
    """
    **Deprecated** — use ``GET /data/market`` with ``provider=yfinance``.

    Same validation and cache key as the unified market route (``yfinance:symbol``).

    Response includes ``Deprecation: true`` and a ``Link`` successor hint header;
    OpenAPI marks this operation deprecated; generated clients may not surface headers.
    """
    if not allow(client_key(request.client.host if request.client else None)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many market data requests. Try again shortly.",
            headers={"Retry-After": str(retry_after_seconds())},
        )
    validate_period(period)
    validate_interval(interval)
    sym = symbol.strip()
    candles = await run_in_threadpool(
        load_yfinance,
        sym,
        period,
        interval,
    )
    candles = cap_candles(candles)
    cache.set_cached("yfinance", sym, candles)
    body = OHLCVCandleList(symbol=sym, candles=candles)
    return JSONResponse(
        content=body.model_dump(mode="json"),
        headers={
            "Deprecation": "true",
            "Link": '</data/market?provider=yfinance>; rel="successor-version"',
        },
    )


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
        candles = await run_in_threadpool(load_csv, tmp_path, symbol)
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
    content = await file.read()
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        columns, rows = await run_in_threadpool(
            csv_preview, tmp_path, max_rows=max_rows
        )
        # Serialize rows for JSON (datetime -> str)
        out_rows = []
        for r in rows:
            out_rows.append(
                {k: str(v) if hasattr(v, "isoformat") else v for k, v in r.items()}
            )
        return {"columns": columns, "preview": out_rows}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _ws_stream_impl(websocket: WebSocket, provider: str, symbol: str) -> None:
    await websocket.accept()
    sym = symbol.strip()
    p = provider.strip().lower()
    if p not in _WS_PROVIDERS:
        await websocket.send_json(
            {"error": f"unknown provider '{provider}'", "symbol": sym}
        )
        return
    try:
        candles = cache.get_cached(p, sym)
        if not candles:
            if p == "yfinance":
                candles = await run_in_threadpool(load_yfinance, sym)
                candles = cap_candles(candles)
                cache.set_cached("yfinance", sym, candles)
            else:
                await websocket.send_json(
                    {
                        "error": (
                            "no cached data for this provider; "
                            "load the chart first (GET /data/market or POST /data/csv)"
                        ),
                        "symbol": sym,
                        "provider": p,
                    }
                )
                return
        if not candles:
            await websocket.send_json({"error": "no data", "symbol": sym})
            return
        await stream_candles(websocket, candles, delay_seconds=0.02)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


@app.websocket("/ws/stream/{provider}/{symbol}")
async def ws_stream(websocket: WebSocket, provider: str, symbol: str) -> None:
    """
    Replay cached OHLCV as a stream. Use the same **provider** as the data source
    (``yfinance``, ``binance``, ``twelvedata``, ``csv``). Load data via REST first
    except for **yfinance**, which can cold-fetch.
    """
    await _ws_stream_impl(websocket, provider, symbol)


@app.websocket("/ws/stream/{symbol}")
async def ws_stream_legacy(websocket: WebSocket, symbol: str) -> None:
    """Legacy URL: same as ``/ws/stream/yfinance/{symbol}``."""
    await _ws_stream_impl(websocket, "yfinance", symbol)


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    """
    Multiplexed live market-data stream.

    Protocol: see ``backend/streaming/protocol.py``. Clients send
    ``subscribe`` / ``unsubscribe`` / ``ping`` JSON messages; server replies
    with ``snapshot`` / ``candle`` / ``status`` / ``error`` / ``pong``.
    Auth (token query param + per-user gating) lands in a later step;
    happy-path is anonymous Binance public data.
    """
    from pydantic import TypeAdapter, ValidationError

    await websocket.accept()
    hub = get_hub()
    client_id = f"{id(websocket):x}"

    async def send(msg: ServerMessage) -> None:
        await websocket.send_json(msg.model_dump(mode="json"))

    session = ClientSession(client_id=client_id, send=send)
    client_msg_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                msg = client_msg_adapter.validate_python(raw)
            except ValidationError as exc:
                await send(ErrorMessage(code="bad_message", message=str(exc)))
                continue

            if isinstance(msg, SubscribeMessage):
                key = (msg.provider, msg.symbol, msg.interval)
                try:
                    await hub.subscribe(session, key, since=msg.since)
                except NotImplementedError as exc:
                    await send(ErrorMessage(code="unsupported", message=str(exc)))
                except Exception as exc:
                    # Don't tear down the socket on a single bad subscribe —
                    # the client would just reconnect and re-fire the same
                    # request, producing a tight failure loop.
                    logger.exception("subscribe failed for %s", key)
                    await hub.unsubscribe(session, key)
                    await send(ErrorMessage(code="subscribe_failed", message=str(exc)))
            elif isinstance(msg, UnsubscribeMessage):
                key = (msg.provider, msg.symbol, msg.interval)
                await hub.unsubscribe(session, key)
            else:
                # PingMessage (and quote subs, which land in step 7)
                if msg.type == "ping":
                    await send(PongMessage())
                else:
                    await send(
                        ErrorMessage(
                            code="not_implemented",
                            message=f"'{msg.type}' not yet supported",
                        )
                    )
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(session)


# Mount static files (must be at the end of the file to capture all remaining routes)
if FRONTEND_DIST.is_dir():
    app.mount(
        "/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend"
    )
