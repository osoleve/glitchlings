"""Configuration loading for Glitchlings."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    try:
        import tomli as tomllib  # type: ignore[assignment]
    except ModuleNotFoundError:  # pragma: no cover - missing optional dependency
        tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LexiconSettings:
    """Configuration for lexicon backend resolution."""

    priority: tuple[str, ...]
    vector_cache: Path | None
    graph_cache: Path | None


@dataclass(frozen=True)
class Config:
    """Runtime configuration derived from ``config.toml`` or defaults."""

    lexicon: LexiconSettings
    path: Path | None = None


_DEFAULT_VECTOR_CACHE = (
    Path(__file__).resolve().parent
    / "lexicon"
    / "data"
    / "default_vector_cache.json"
)

_DEFAULT_CONFIG = Config(
    lexicon=LexiconSettings(
        priority=("vector", "graph"),
        vector_cache=_DEFAULT_VECTOR_CACHE if _DEFAULT_VECTOR_CACHE.exists() else None,
        graph_cache=None,
    )
)

_CONFIG_CACHE: Config | None = None

_ENVIRONMENT_VARIABLE = "GLITCHLINGS_CONFIG"


def _candidate_paths(path: str | Path | None = None) -> Iterable[Path]:
    if path is not None:
        yield Path(path)
        return

    env_override = os.getenv(_ENVIRONMENT_VARIABLE)
    if env_override:
        yield Path(env_override)

    cwd_candidate = Path.cwd() / "config.toml"
    yield cwd_candidate

    package_candidate = Path(__file__).resolve().parent / "config.toml"
    yield package_candidate


def _load_file(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError(
            "Reading configuration requires Python 3.11+ or the tomli package."
        )
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise
    except OSError as exc:  # pragma: no cover - filesystem failures are rare
        raise RuntimeError(f"Failed to read config file at {path!s}: {exc}") from exc


def _resolve_path(value: str | None, *, base: Path) -> Path | None:
    if value is None:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from disk, falling back to defaults when absent."""

    for candidate in _candidate_paths(path):
        if candidate.exists():
            try:
                payload = _load_file(candidate)
            except FileNotFoundError:
                continue
            lexicon_table = payload.get("lexicon", {})
            if not isinstance(lexicon_table, dict):
                raise RuntimeError("[lexicon] section in config.toml must be a table.")

            priority_raw = lexicon_table.get("priority", _DEFAULT_CONFIG.lexicon.priority)
            if isinstance(priority_raw, (list, tuple)):
                priority = tuple(str(entry).lower() for entry in priority_raw if entry)
            elif isinstance(priority_raw, str):
                priority = (priority_raw.lower(),)
            else:
                raise RuntimeError(
                    "lexicon.priority must be a string or array of strings."
                )

            base = candidate.parent
            vector_raw = lexicon_table.get("vector_cache", "__DEFAULT__")
            if vector_raw == "__DEFAULT__":
                vector_cache = _DEFAULT_CONFIG.lexicon.vector_cache
            elif vector_raw is None:
                vector_cache = None
            elif isinstance(vector_raw, str):
                vector_cache = _resolve_path(vector_raw, base=base)
            else:
                raise RuntimeError("lexicon.vector_cache must be a string path or null.")

            graph_raw = lexicon_table.get("graph_cache", "__DEFAULT__")
            if graph_raw == "__DEFAULT__":
                graph_cache = _DEFAULT_CONFIG.lexicon.graph_cache
            elif graph_raw is None:
                graph_cache = None
            elif isinstance(graph_raw, str):
                graph_cache = _resolve_path(graph_raw, base=base)
            else:
                raise RuntimeError("lexicon.graph_cache must be a string path or null.")

            return Config(
                lexicon=LexiconSettings(
                    priority=priority,
                    vector_cache=vector_cache,
                    graph_cache=graph_cache,
                ),
                path=candidate,
            )

    return _DEFAULT_CONFIG


def get_config() -> Config:
    """Return the cached configuration, loading it on first use."""

    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE


def reload_config(path: str | Path | None = None) -> Config:
    """Force a configuration reload from ``path`` or the default candidates."""

    global _CONFIG_CACHE
    _CONFIG_CACHE = load_config(path)
    return _CONFIG_CACHE


def reset_config() -> None:
    """Clear the cached configuration so the next access reloads it."""

    global _CONFIG_CACHE
    _CONFIG_CACHE = None


__all__ = [
    "Config",
    "LexiconSettings",
    "get_config",
    "load_config",
    "reload_config",
    "reset_config",
]
