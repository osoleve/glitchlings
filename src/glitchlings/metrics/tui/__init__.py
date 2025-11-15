"""Metrics TUI helpers."""

from __future__ import annotations

from typing import Mapping, Sequence

from ..core.session import MetricsSession
from .controller import ControllerOptions, MetricsTUIController


def launch_metrics_tui(
    *,
    text: str,
    glitchlings: Sequence[str],
    tokenizers: Sequence[str],
    metrics: Sequence[str] | None = None,
    context: Mapping[str, object] | None = None,
    input_type: str = "adhoc",
) -> None:
    """Instantiate the Textual app and run it."""
    session = MetricsSession(context=context)
    options = ControllerOptions(
        text=text,
        glitchling_specs=glitchlings,
        tokenizer_specs=tokenizers,
        metric_keys=metrics,
        input_type=input_type,
    )
    controller = MetricsTUIController(session, options)

    from .app import MetricsApp

    app = MetricsApp(controller)
    app.run()


__all__ = ["launch_metrics_tui"]
