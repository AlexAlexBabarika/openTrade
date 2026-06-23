# backend/routes/datastore_routes.py
"""Datastore ingest endpoint.

Populates the on-disk store for a set of symbols: fetch from the market-data
provider, quality-check, write Parquet, stamp a new ``data_version``. This is
the explicit population step the backtest routes never perform — they read
only. Network-bound, so the fetch runs in the threadpool.
"""

from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.datastore.ingest import ingest_symbols
from backend.datastore.layout import StoreLayout
from backend.market.data_sources.yfinance_loader import YFinanceLoader

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datastore", tags=["datastore"])

_MAX_SYMBOLS = 50

# Module-level handles (overridable in tests).
_STORE_LAYOUT = StoreLayout.default()


def _provider() -> YFinanceLoader:
    return YFinanceLoader()


class IngestRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=_MAX_SYMBOLS)
    interval: str = "1d"


@router.post("/ingest")
async def ingest(body: IngestRequest) -> dict:
    symbols = sorted({s.strip() for s in body.symbols if s.strip()})
    if not symbols:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no symbols given")
    # period="max": the store isn't keyed by date range and backtests clip by
    # window, so full history is strictly better than any single run's span.
    report = await run_in_threadpool(
        ingest_symbols,
        _STORE_LAYOUT,
        _provider(),
        symbols,
        period="max",
        interval=body.interval,
    )
    return dataclasses.asdict(report)
