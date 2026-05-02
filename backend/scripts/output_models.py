"""Pydantic models for user-script outputs and run results.

Time fields are encoded as UNIX seconds (int) so the frontend can pass them
directly to Lightweight Charts as `UTCTimestamp`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, NonNegativeInt


MAX_ROWS_PER_SERIES = 50_000
MAX_OUTPUTS_PER_RUN = 50


class SeriesPoint(BaseModel):
    time: int = Field(..., description="UNIX seconds (UTC)")
    value: float


class HistogramPoint(BaseModel):
    time: int
    value: float
    color: str | None = None


class MarkerPoint(BaseModel):
    time: int


class OverlayOutput(BaseModel):
    type: Literal["overlay"] = "overlay"
    title: str
    data: list[SeriesPoint]
    color: str | None = None
    line_width: int | None = None
    line_style: str | None = None


class PaneOutput(BaseModel):
    type: Literal["pane"] = "pane"
    title: str
    data: list[SeriesPoint]
    color: str | None = None
    height: int | None = None
    pane_id: str | None = None


class HistogramOutput(BaseModel):
    type: Literal["histogram"] = "histogram"
    title: str
    data: list[HistogramPoint]
    pane_id: str | None = None


class MarkersOutput(BaseModel):
    type: Literal["markers"] = "markers"
    data: list[MarkerPoint]
    shape: str | None = None
    position: str | None = None
    color: str | None = None
    text: str | None = None


class TableOutput(BaseModel):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[Any]]


class TextOutput(BaseModel):
    type: Literal["text"] = "text"
    text: str
    level: Literal["info", "warn", "error"] = "info"


ScriptOutput = Annotated[
    Union[
        OverlayOutput,
        PaneOutput,
        HistogramOutput,
        MarkersOutput,
        TableOutput,
        TextOutput,
    ],
    Field(discriminator="type"),
]


class RunResult(BaseModel):
    status: Literal["ok", "error", "timeout", "killed"]
    outputs: list[ScriptOutput] = []
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: NonNegativeInt = 0
