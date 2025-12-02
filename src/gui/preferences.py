from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, List

from .textual.definitions import DEFAULT_TOKENIZERS

PREFERENCES_PATH = Path.home() / ".glitchlings_gui_prefs.json"


@dataclass
class Preferences:
    """User-customizable application preferences."""

    font_family: str = "Consolas"
    font_size: int = 10
    default_tokenizers: List[str] = field(
        default_factory=lambda: list(DEFAULT_TOKENIZERS)
    )
    copy_metadata: bool = False
    sidebar_collapsed: bool = False
    last_tab: str = "input"

    def with_updates(self, **kwargs: Any) -> "Preferences":
        return replace(self, **kwargs)


def _coerce_tokenizers(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for name in values:
        trimmed = name.strip()
        if trimmed and trimmed not in seen:
            cleaned.append(trimmed)
            seen.add(trimmed)
    return cleaned or list(DEFAULT_TOKENIZERS)


def load_preferences() -> Preferences:
    """Load persisted preferences or fall back to defaults."""
    if not PREFERENCES_PATH.exists():
        return Preferences()

    try:
        data = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Preferences()

    font_family = data.get("font_family", Preferences.font_family)
    font_size = int(data.get("font_size", Preferences.font_size))
    copy_metadata = bool(data.get("copy_metadata", False))
    sidebar_collapsed = bool(data.get("sidebar_collapsed", False))
    last_tab = data.get("last_tab", "input")
    default_tokenizers = _coerce_tokenizers(data.get("default_tokenizers", []))

    if last_tab not in {"input", "diff"}:
        last_tab = "input"

    if font_size < 6:
        font_size = 6

    return Preferences(
        font_family=font_family,
        font_size=font_size,
        default_tokenizers=default_tokenizers,
        copy_metadata=copy_metadata,
        sidebar_collapsed=sidebar_collapsed,
        last_tab=last_tab,
    )


def save_preferences(preferences: Preferences) -> None:
    """Persist preferences to disk."""
    payload = {
        "font_family": preferences.font_family,
        "font_size": preferences.font_size,
        "default_tokenizers": preferences.default_tokenizers,
        "copy_metadata": preferences.copy_metadata,
        "sidebar_collapsed": preferences.sidebar_collapsed,
        "last_tab": preferences.last_tab,
    }
    PREFERENCES_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
