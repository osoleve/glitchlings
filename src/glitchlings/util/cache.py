"""Deterministic caching helpers for multi-glitch runs."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, is_dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any, Generic, Iterator, Mapping, MutableMapping, TypeVar, cast, overload

CacheValue = TypeVar("CacheValue")
_Default = TypeVar("_Default")

__all__ = ["CacheManager"]

log = logging.getLogger("glitchlings.cache")

_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "glitchlings"
_CACHE_ENV_VAR = "GLITCHLINGS_CACHE_DIR"


class CacheManager(MutableMapping[str, CacheValue], Generic[CacheValue]):
    """Manage reproducible caches stored on disk and/or in memory."""

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        *,
        persist: bool = True,
    ) -> None:
        self._memory: dict[str, CacheValue] = {}
        self._persist = persist

        resolved_dir: Path | None
        if not persist:
            resolved_dir = None
        else:
            if cache_dir is None:
                override = os.environ.get(_CACHE_ENV_VAR)
                resolved_dir = Path(override) if override else _DEFAULT_CACHE_DIR
            else:
                resolved_dir = Path(cache_dir)

            try:
                resolved_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:  # pragma: no cover - defensive fallback
                log.warning(
                    "Unable to create cache directory %s; falling back to in-memory cache only",
                    resolved_dir,
                    exc_info=exc,
                )
                resolved_dir = None
                self._persist = False
        self._cache_dir = resolved_dir

    # -- MutableMapping protocol -------------------------------------------------
    def __getitem__(self, key: str) -> CacheValue:
        cached = self.get(key)
        if cached is None:
            raise KeyError(key)
        return cached

    def __setitem__(self, key: str, value: CacheValue) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __iter__(self) -> Iterator[str]:
        yielded: set[str] = set()
        for key in self._memory:
            yielded.add(key)
            yield key

        if self._cache_dir is not None and self._cache_dir.exists():
            for entry in self._cache_dir.iterdir():
                if entry.is_file():
                    name = entry.name
                    if name in yielded:
                        continue
                    yielded.add(name)
                    yield name

    def __len__(self) -> int:
        keys = set(self._memory)
        if self._cache_dir is not None and self._cache_dir.exists():
            for entry in self._cache_dir.iterdir():
                if entry.is_file():
                    keys.add(entry.name)
        return len(keys)

    # ---------------------------------------------------------------------------
    @property
    def cache_dir(self) -> Path | None:
        """Return the directory used for disk persistence, if any."""

        return self._cache_dir

    def make_key(self, *, text: str, configuration: Mapping[str, Any]) -> str:
        """Create a deterministic cache key from text and configuration."""

        payload = {
            "text": text,
            "configuration": self._normalise(configuration),
        }
        normalised = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return blake2b(normalised.encode("utf-8"), digest_size=32).hexdigest()

    @overload
    def get(self, key: str, default: None = None) -> CacheValue | None:
        ...

    @overload
    def get(self, key: str, default: _Default) -> CacheValue | _Default:
        ...

    def get(
        self,
        key: str,
        default: _Default | CacheValue | None = None,
    ) -> CacheValue | _Default | None:
        """Return the cached value for ``key`` or ``default`` when missing."""

        if key in self._memory:
            log.info("Cache hit (memory) for key %s", key)
            return self._memory[key]

        if not self._persist or self._cache_dir is None:
            log.info("Cache miss (memory-only) for key %s", key)
            return default

        path = self._cache_dir / key
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            log.info("Cache miss for key %s", key)
            return default
        except json.JSONDecodeError:  # pragma: no cover - cache corruption fallback
            log.warning("Cache entry %s is corrupt; ignoring", path)
            return default

        if "value" not in payload:
            log.info("Cache miss for key %s", key)
            return default

        value = cast(CacheValue, payload["value"])
        log.info("Cache hit (disk) for key %s", key)
        self._memory[key] = value
        return value

    def set(self, key: str, value: CacheValue) -> None:
        """Persist ``value`` under ``key`` in memory and on disk."""

        self._memory[key] = value
        if not self._persist or self._cache_dir is None:
            log.info("Cached value for key %s in memory only", key)
            return

        path = self._cache_dir / key
        tmp_path = path.with_suffix(".tmp")
        data = {"value": value}
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
        tmp_path.replace(path)
        log.info("Cached value for key %s on disk", key)

    def delete(self, key: str) -> None:
        """Remove ``key`` from the cache if it exists."""

        self._memory.pop(key, None)
        if self._cache_dir is None:
            return
        path = self._cache_dir / key
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def clear(self) -> None:
        """Clear both the in-memory and on-disk caches."""

        self._memory.clear()
        if self._cache_dir is None or not self._cache_dir.exists():
            return

        for entry in self._cache_dir.iterdir():
            if entry.is_file():
                try:
                    entry.unlink()
                except OSError:  # pragma: no cover - best-effort cleanup
                    log.warning("Unable to delete cache file %s", entry, exc_info=True)
        log.info("Cleared cache directory %s", self._cache_dir)

    @staticmethod
    def _normalise(value: Any) -> Any:
        """Convert ``value`` into a JSON-serialisable structure."""

        if isinstance(value, Mapping):
            return {str(key): CacheManager._normalise(val) for key, val in sorted(value.items())}

        if isinstance(value, (list, tuple, set, frozenset)):
            return [CacheManager._normalise(item) for item in value]

        if isinstance(value, Path):
            return str(value)

        if is_dataclass(value) and not isinstance(value, type):
            return CacheManager._normalise(asdict(value))

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return repr(value)
