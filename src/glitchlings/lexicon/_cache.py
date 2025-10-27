"""Shared cache helpers for lexicon backends."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import Mapping, Sequence, cast

CacheEntries = dict[str, list[str]]


@dataclass(frozen=True)
class CacheSnapshot:
    """Materialised cache data and its integrity checksum."""

    entries: CacheEntries
    checksum: str | None = None


def _normalize_entries(payload: Mapping[str, object]) -> CacheEntries:
    """Convert raw cache payloads into canonical mapping form."""
    entries: CacheEntries = {}
    for key, values in payload.items():
        if not isinstance(key, str):
            raise RuntimeError("Synonym cache keys must be strings.")
        if not isinstance(values, Sequence):
            raise RuntimeError("Synonym cache values must be sequences of strings.")
        entries[key] = [str(value) for value in values]
    return entries


def _canonical_json(entries: Mapping[str, Sequence[str]]) -> str:
    """Return a deterministic JSON serialisation for ``entries``."""
    serialisable = {key: list(values) for key, values in sorted(entries.items())}
    return json.dumps(serialisable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_checksum(entries: Mapping[str, Sequence[str]]) -> str:
    """Return a BLAKE2s checksum for ``entries``."""
    digest = blake2s(_canonical_json(entries).encode("utf8"), digest_size=16)
    return digest.hexdigest()


def load_cache(path: Path) -> CacheSnapshot:
    """Load a cache from ``path`` and verify its checksum if present."""
    if not path.exists():
        return CacheSnapshot(entries={}, checksum=None)

    with path.open("r", encoding="utf8") as handle:
        payload_obj = json.load(handle)

    checksum: str | None = None
    entries_payload: Mapping[str, object]

    if not isinstance(payload_obj, Mapping):
        raise RuntimeError("Synonym cache payload must be a mapping of strings to lists.")

    payload = cast(Mapping[str, object], payload_obj)

    if "__meta__" in payload and "entries" in payload:
        meta_obj = payload["__meta__"]
        entries_obj = payload["entries"]
        if not isinstance(entries_obj, Mapping):
            raise RuntimeError("Synonym cache entries must be stored as a mapping.")
        entries_payload = cast(Mapping[str, object], entries_obj)
        if isinstance(meta_obj, Mapping):
            raw_checksum = meta_obj.get("checksum")
            if raw_checksum is not None and not isinstance(raw_checksum, str):
                raise RuntimeError("Synonym cache checksum must be a string when provided.")
            checksum = raw_checksum if isinstance(raw_checksum, str) else None
        else:
            raise RuntimeError("Synonym cache metadata must be a mapping.")
    else:
        entries_payload = payload  # legacy format without metadata

    entries = _normalize_entries(entries_payload)
    if checksum is not None:
        expected = compute_checksum(entries)
        if checksum != expected:
            raise RuntimeError(
                "Synonym cache checksum mismatch; the cache file appears to be corrupted."
            )

    return CacheSnapshot(entries=entries, checksum=checksum)


def write_cache(path: Path, entries: Mapping[str, Sequence[str]]) -> CacheSnapshot:
    """Persist ``entries`` to ``path`` with checksum metadata."""
    serialisable: CacheEntries = {key: list(values) for key, values in sorted(entries.items())}
    checksum = compute_checksum(serialisable)
    payload = {
        "__meta__": {
            "checksum": checksum,
            "entries": len(serialisable),
        },
        "entries": serialisable,
    }
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    return CacheSnapshot(entries=serialisable, checksum=checksum)


__all__ = ["CacheEntries", "CacheSnapshot", "compute_checksum", "load_cache", "write_cache"]
