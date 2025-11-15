"""Simple modal dialogs used by the metrics TUI."""

from __future__ import annotations

from typing import Iterable

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class InfoDialog(ModalScreen[None]):  # type: ignore[misc]
    """Generic informational dialog with a title and bullet list."""

    DEFAULT_CSS = """
    InfoDialog {
        align: center middle;
    }

    InfoDialog > Vertical {
        width: 70%;
        max-width: 80;
        border: tall $primary;
        padding: 1 2;
        background: $surface;
    }

    .dialog-title {
        padding-bottom: 1;
        text-style: bold;
    }

    .dialog-body {
        padding-bottom: 1;
    }

    .dialog-actions {
        width: 100%;
        align-horizontal: right;
    }
    """

    def __init__(self, title: str, lines: Iterable[str]) -> None:
        super().__init__()
        self._title = title
        self._lines = list(lines)

    def compose(self) -> ComposeResult:
        with Vertical(id="info-dialog"):
            yield Static(self._title, classes="dialog-title")
            body_text = "\n".join(f"• {line}" if line else "" for line in self._lines)
            yield Static(body_text, classes="dialog-body")
            with Vertical(classes="dialog-actions"):
                yield Button("Close", id="info-dialog-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "info-dialog-close":
            event.stop()
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if event.key in {"escape", "q"}:
            event.stop()
            self.dismiss(None)


__all__ = ["InfoDialog"]
