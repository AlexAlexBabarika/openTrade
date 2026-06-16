"""On-disk path conventions for the store.

Root resolves from ``OPENTRADE_DATA_ROOT`` or defaults to
``backend/datastore/_data``. All paths are derived from one ``root`` so the
whole store is relocatable and testable against ``tmp_path``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parent / "_data"


@dataclass(frozen=True)
class StoreLayout:
    root: Path

    @classmethod
    def default(cls) -> "StoreLayout":
        env = os.environ.get("OPENTRADE_DATA_ROOT")
        return cls(root=Path(env) if env else _DEFAULT_ROOT)

    def bars(self, provider: str, symbol: str) -> Path:
        return self.root / "bars" / provider / f"{symbol}.parquet"

    def actions(self, provider: str, symbol: str) -> Path:
        return self.root / "actions" / provider / f"{symbol}.parquet"

    def membership(self, index: str) -> Path:
        return self.root / "membership" / f"{index}.parquet"

    def quarantine(self, provider: str, symbol: str) -> Path:
        return self.root / "quarantine" / provider / f"{symbol}.parquet"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @staticmethod
    def ensure_parent(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
