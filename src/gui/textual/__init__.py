"""Foundations for the Textual-based Glitchlings GUI."""

from .bus import MessageBus
from .charts_panel import ChartData, ChartsPanel
from .commands import GlitchlingCommands
from .dataset_panel import DatasetPanel
from .events import (
    AppEvent,
    StatusEvent,
    TransformCompleted,
    TransformFailed,
    TransformRequested,
)
from .export_dialog import ExportDialog, ExportResult, SweepExportDialog
from .glitchling_panel import GlitchlingConfig, GlitchlingPanel
from .navigation import NavigationPanel, NavTab
from .state import (
    AppState,
    DatasetState,
    SelectionState,
    StateStore,
    StatusLine,
    WorkspaceState,
)
from .sweep_panel import SweepConfig, SweepPanel, SweepPoint
from .tokenizer_panel import TokenizerPanel
from .workers import BackgroundJob, BackgroundWorker
from .workspace import DiffView, MetricsTable, WorkspacePanel

__all__ = [
    "AppEvent",
    "AppState",
    "BackgroundJob",
    "BackgroundWorker",
    "ChartData",
    "ChartsPanel",
    "DatasetPanel",
    "DatasetState",
    "DiffView",
    "ExportDialog",
    "ExportResult",
    "GlitchlingCommands",
    "GlitchlingConfig",
    "GlitchlingPanel",
    "main",
    "MessageBus",
    "MetricsTable",
    "NavigationPanel",
    "NavTab",
    "SelectionState",
    "StateStore",
    "StatusEvent",
    "StatusLine",
    "SweepConfig",
    "SweepExportDialog",
    "SweepPanel",
    "SweepPoint",
    "TokenizerPanel",
    "TransformCompleted",
    "TransformFailed",
    "TransformRequested",
    "WorkspacePanel",
    "WorkspaceState",
]


def main() -> None:
    """Entry point for the Textual-based Glitchlings TUI.

    Install the gui extra to enable this entrypoint:
        pip install glitchlings[gui]

    Then run:
        glitchlings-tui
    """
    from .app import GlitchlingsTextualApp

    GlitchlingsTextualApp().run()
