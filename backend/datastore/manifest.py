"""data_version registry.

The manifest is a JSON file mapping each ``data_version`` to the file set it
covers (per-file checksums), the adjustment-logic version, ranges and an
ingest timestamp, plus a ``head`` pointer to the latest version. ``data_version``
is a content hash over the checksums + adjust-logic version, so identical inputs
always yield the same version and any byte change yields a new one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from backend.datastore.layout import StoreLayout

_VERSION_LEN = 16


@dataclass(frozen=True)
class ManifestEntry:
    data_version: str
    symbols: list[str]
    ranges: dict[str, tuple[str, str]]
    checksums: dict[str, str]
    adjust_logic_version: str
    ingested_at: str


def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def compute_version(checksums: dict[str, str], *, adjust_logic_version: str) -> str:
    h = hashlib.sha256()
    for key in sorted(checksums):
        h.update(key.encode())
        h.update(b"\0")
        h.update(checksums[key].encode())
        h.update(b"\0")
    h.update(b"adjust=")
    h.update(adjust_logic_version.encode())
    return h.hexdigest()[:_VERSION_LEN]


def load_manifest(layout: StoreLayout) -> dict:
    if not layout.manifest.exists():
        return {"head": None, "versions": {}}
    return json.loads(layout.manifest.read_text())


def write_entry(layout: StoreLayout, entry: ManifestEntry) -> None:
    manifest = load_manifest(layout)
    manifest["versions"][entry.data_version] = asdict(entry)
    manifest["head"] = entry.data_version
    layout.manifest.parent.mkdir(parents=True, exist_ok=True)
    layout.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True))
