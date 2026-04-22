"""
Ticker workspace (groups + sidebar filters) stored in public.ticker_workspaces.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

FLAGGED_PRIORITIES = frozenset({"ignore", "low", "normal", "high", "critical"})
FLAGGED_STANCES = frozenset({"watch", "hold", "buy", "sell"})
PRIORITY_OPTIONS = frozenset({"none", "ignore", "low", "normal", "high", "critical"})
STANCE_OPTIONS = frozenset({"none", "watch", "hold", "buy", "sell"})


class SymbolProvidersModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    twelvedata: bool = False
    yfinance: bool = False
    binance: bool = False


class TrackedTickerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    priority: str
    stance: str
    providers: SymbolProvidersModel | None = None

    @model_validator(mode="after")
    def _validate_enums(self) -> Self:
        if self.priority not in PRIORITY_OPTIONS:
            raise ValueError(f"invalid priority: {self.priority!r}")
        if self.stance not in STANCE_OPTIONS:
            raise ValueError(f"invalid stance: {self.stance!r}")
        return self


class TickerGroupModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    tickers: list[TrackedTickerModel]


class TickerWorkspaceBody(BaseModel):
    """Wire format (camelCase) matching the frontend."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    groups: list[TickerGroupModel]
    selected_group: str = Field(alias="selectedGroup")
    selected_priority: str | None = Field(alias="selectedPriority")
    selected_stance: str | None = Field(alias="selectedStance")

    @model_validator(mode="after")
    def _validate_filters(self) -> Self:
        if (
            self.selected_priority is not None
            and self.selected_priority not in FLAGGED_PRIORITIES
        ):
            raise ValueError(
                f"selectedPriority must be a flagged value or null, got {self.selected_priority!r}"
            )
        if (
            self.selected_stance is not None
            and self.selected_stance not in FLAGGED_STANCES
        ):
            raise ValueError(
                f"selectedStance must be a flagged value or null, got {self.selected_stance!r}"
            )
        names = {g.name for g in self.groups}
        if self.selected_group not in names:
            raise ValueError("selectedGroup must match a group name")
        return self


def default_ticker_workspace() -> TickerWorkspaceBody:
    return TickerWorkspaceBody(
        groups=[TickerGroupModel(name="All", tickers=[])],
        selected_group="All",
        selected_priority=None,
        selected_stance=None,
    )


class TickerWorkspaceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace: TickerWorkspaceBody
    from_database: bool = Field(
        description="True if loaded from a stored row, False if no row (defaults).",
    )
    updated_at: str | None = None
