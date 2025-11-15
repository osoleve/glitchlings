"""Compatibility shim for :mod:`glitchlings.metrics.cli.tui`.

The metrics TUI now lives in :mod:`glitchlings.metrics.tui`. This module keeps
imports and ``python -m glitchlings.metrics.cli.tui`` working while callers
migrate to the new location.
"""

from __future__ import annotations

from ..tui import launch_metrics_tui
from ..tui.__main__ import main

__all__ = ["launch_metrics_tui", "main"]


if __name__ == "__main__":  # pragma: no cover - compatibility shim
    main()
