"""
Symbol directory: autocomplete search + lazy yfinance support marker.

Public (no auth): all symbol data is non-sensitive market reference data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from backend.core.supabase_client import get_service_postgrest
from backend.models.market_data_models import (
    MarkYFinanceRequest,
    SymbolProviders,
    SymbolSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/symbols", tags=["symbols"])

_MAX_LIMIT = 50
# ``exchange:exchanges(code)`` embeds the FK-joined row as {"code": "NASDAQ"}
# under the alias "exchange", so the API response shape matches pre-lookup.
_COLUMNS = "symbol,name,asset_type,twelvedata,yfinance,binance,exchange:exchanges(code)"


def _to_result(row: dict) -> SymbolSearchResult:
    exchange_embed = row.get("exchange")
    exchange_code = (
        exchange_embed.get("code") if isinstance(exchange_embed, dict) else None
    )
    return SymbolSearchResult(
        symbol=row["symbol"],
        name=row["name"],
        asset_type=row.get("asset_type"),
        exchange=exchange_code,
        providers=SymbolProviders(
            twelvedata=bool(row.get("twelvedata")),
            yfinance=bool(row.get("yfinance")),
            binance=bool(row.get("binance")),
        ),
    )


def _search_blocking(q: str, limit: int) -> list[SymbolSearchResult]:
    """Two-pass search so prefix matches rank first without needing an RPC.

    1. ``symbol ILIKE 'q%'`` — prefix hits first.
    2. Fill the remainder with ``name ILIKE '%q%'`` contains matches that
       weren't already returned in pass 1.
    """
    db = get_service_postgrest()
    qu = q.strip().upper()
    if not qu:
        return []

    # escape PostgREST ILIKE wildcards in user input so a literal '%' or '_'
    # in a query doesn't blow up the pattern (rare for tickers but safe).
    safe = qu.replace("%", r"\%").replace("_", r"\_")

    prefix_resp = (
        db.from_("symbols")
        .select(_COLUMNS)
        .ilike("symbol", f"{safe}%")
        .order("symbol")
        .limit(limit)
        .execute()
    )
    prefix_rows = list(prefix_resp.data or [])
    out = [_to_result(r) for r in prefix_rows]
    if len(out) >= limit:
        return out[:limit]

    seen = {r.symbol for r in out}
    remaining = limit - len(out)
    # Fallback: name contains; reuses the pg_trgm GIN index via ILIKE.
    name_resp = (
        db.from_("symbols")
        .select(_COLUMNS)
        .ilike("name", f"%{safe}%")
        .limit(remaining + len(seen))
        .execute()
    )
    for row in name_resp.data or []:
        sym = row.get("symbol")
        if not isinstance(sym, str) or sym in seen:
            continue
        out.append(_to_result(row))
        if len(out) >= limit:
            break
    return out


def _meta_by_symbol_blocking(symbol: str) -> SymbolSearchResult | None:
    """Exact primary-key lookup for one ticker."""
    db = get_service_postgrest()
    resp = db.from_("symbols").select(_COLUMNS).eq("symbol", symbol).limit(1).execute()
    rows = resp.data or []
    if not rows:
        return None
    return _to_result(rows[0])


@router.get("/meta", response_model=SymbolSearchResult)
async def symbol_meta(
    symbol: str = Query(..., min_length=1, description="Exact instrument symbol"),
) -> SymbolSearchResult:
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="symbol is required",
        )
    try:
        result = await run_in_threadpool(_meta_by_symbol_blocking, sym)
    except APIError as e:
        logger.warning("Symbol meta PostgREST error for %s: %s", sym, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symbol directory is not available.",
        ) from e
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown symbol.",
        )
    return result


@router.get("/search", response_model=list[SymbolSearchResult])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Query prefix or fragment"),
    limit: int = Query(20, ge=1, le=_MAX_LIMIT),
) -> list[SymbolSearchResult]:
    q_stripped = q.strip()
    if not q_stripped:
        return []
    try:
        return await run_in_threadpool(_search_blocking, q_stripped, limit)
    except APIError as e:
        logger.warning("Symbol search PostgREST error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symbol directory is not available.",
        ) from e


def _mark_yfinance_blocking(symbol: str) -> None:
    """Idempotent: update if present, insert with name=symbol if absent.

    We branch rather than upsert because PostgREST's merge-duplicates would
    clobber an existing provider-supplied ``name`` with the symbol string.
    """
    db = get_service_postgrest()
    existing = (
        db.from_("symbols").select("symbol").eq("symbol", symbol).limit(1).execute()
    )
    if existing.data:
        db.from_("symbols").update({"yfinance": True}).eq("symbol", symbol).execute()
    else:
        db.from_("symbols").insert(
            {"symbol": symbol, "name": symbol, "yfinance": True}
        ).execute()


@router.post("/mark-yfinance", status_code=status.HTTP_204_NO_CONTENT)
async def mark_yfinance(payload: MarkYFinanceRequest) -> None:
    sym = payload.symbol.strip().upper()
    if not sym:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="symbol is required"
        )
    try:
        await run_in_threadpool(_mark_yfinance_blocking, sym)
    except APIError as e:
        logger.warning("mark-yfinance PostgREST error for %s: %s", sym, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symbol directory is not available.",
        ) from e
