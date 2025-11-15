"""Walkthrough hint widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Static


class WalkthroughAdvance(Message):  # type: ignore[misc]
    """Message emitted when the walkthrough advances or is dismissed."""

    def __init__(self, step_id: str, dismissed: bool) -> None:
        super().__init__()
        self.step_id = step_id
        self.dismissed = dismissed


class WalkthroughHint(Vertical):  # type: ignore[misc]
    """Pill-shaped widget that explains the current onboarding step."""

    DEFAULT_CSS = """
    WalkthroughHint {
        border: round $secondary-darken-1;
        background: $surface 10%;
        padding: 1 1 0 1;
        width: 1fr;
    }

    WalkthroughHint > .walkthrough-actions {
        width: 100%;
        align-horizontal: right;
        padding-bottom: 1;
    }
    """

    def __init__(
        self,
        *,
        step_id: str,
        title: str,
        body: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        super().__init__(classes="walkthrough-hint")
        self._step_id = step_id
        self._title = title
        self._body = body
        self._step_index = step_index
        self._total_steps = total_steps

    def compose(self) -> ComposeResult:
        step_label = f"{self._step_index + 1}/{self._total_steps}"
        yield Static(f"{self._title} ({step_label})", classes="hint-title")
        yield Static(self._body, classes="hint-body")
        next_label = "Next tip" if self._step_index + 1 < self._total_steps else "Finish"
        with Horizontal(classes="walkthrough-actions"):
            yield Button(next_label, id="walkthrough-next", variant="success")
            yield Button("Skip tour", id="walkthrough-dismiss", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "walkthrough-next":
            event.stop()
            self.post_message(WalkthroughAdvance(self._step_id, dismissed=False))
        elif event.button.id == "walkthrough-dismiss":
            event.stop()
            self.post_message(WalkthroughAdvance(self._step_id, dismissed=True))


__all__ = ["WalkthroughAdvance", "WalkthroughHint"]
