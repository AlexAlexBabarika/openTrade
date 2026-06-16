"""Datastore exceptions."""

from __future__ import annotations


class DataStoreError(Exception):
    """Base class for datastore errors."""


class DataNotFound(DataStoreError):
    """Requested symbol/index is absent from the store; run ingest first."""


class IngestError(DataStoreError):
    """An ingest run could not complete."""
