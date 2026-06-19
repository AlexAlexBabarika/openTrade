"""Ingest CLI: ``python -m backend.datastore ingest --symbols AAPL,MSFT --index SP500``."""

from __future__ import annotations

import argparse

from backend.datastore.ingest import ingest_symbols
from backend.datastore.layout import StoreLayout
from backend.market.data_sources.yfinance_loader import YFinanceLoader


def main() -> None:
    parser = argparse.ArgumentParser(prog="backend.datastore")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="fetch + persist + stamp a data_version")
    ing.add_argument("--symbols", required=True, help="comma-separated tickers")
    ing.add_argument(
        "--index", action="append", default=[], help="index to seed (repeatable)"
    )
    ing.add_argument("--period", default="max")
    ing.add_argument("--interval", default="1d")
    args = parser.parse_args()

    layout = StoreLayout.default()
    provider = YFinanceLoader()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    report = ingest_symbols(
        layout,
        provider,
        symbols,
        period=args.period,
        interval=args.interval,
        indices=args.index,
    )
    print(f"data_version: {report.data_version}")
    print(f"rows_written: {report.rows_written}")
    print(f"quarantined:  {report.quarantined}")
    for w in report.gap_warnings:
        print(f"  gap-warning: {w}")


if __name__ == "__main__":
    main()
