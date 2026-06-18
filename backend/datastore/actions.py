"""Corporate-actions persistence (Parquet) + model->frame conversion."""

from __future__ import annotations

import polars as pl

from backend.datastore.layout import StoreLayout
from backend.datastore.schema import ACTIONS_SCHEMA, empty_frame
from backend.market.models import CorporateAction


def actions_to_frame(actions: list[CorporateAction]) -> pl.DataFrame:
    if not actions:
        return empty_frame(ACTIONS_SCHEMA)
    return pl.DataFrame(
        {
            "symbol": [a.symbol for a in actions],
            "ex_date": [a.ex_date for a in actions],
            "kind": [a.kind for a in actions],
            "value": [float(a.value) for a in actions],
        },
        schema=ACTIONS_SCHEMA,
    )


def write_actions(
    layout: StoreLayout, provider: str, symbol: str, frame: pl.DataFrame
) -> None:
    path = layout.actions(provider, symbol)
    layout.ensure_parent(path)
    frame.write_parquet(path)


def read_actions(layout: StoreLayout, provider: str, symbol: str) -> pl.DataFrame:
    path = layout.actions(provider, symbol)
    if not path.exists():
        return empty_frame(ACTIONS_SCHEMA)
    return pl.read_parquet(path)
