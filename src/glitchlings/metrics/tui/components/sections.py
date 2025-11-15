"""Collapsible section widget used in the Metrics TUI."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class SectionToggleRequested(Message):  # type: ignore[misc]
    """Message emitted when a section header is toggled."""

    def __init__(self, section: "CollapsibleSection", expand: bool) -> None:
        super().__init__()
        self.section = section
        self.expand = expand


class CollapsibleSection(Widget):  # type: ignore[misc]
    """Simple accordion-style container."""

    DEFAULT_CSS = """
    CollapsibleSection {
        width: 1fr;
        border: none;
        padding: 0;
    }

    CollapsibleSection > .section-header {
        padding: 0 1;
        height: auto;
        color: $text;
    }

    CollapsibleSection > .section-header:focus {
        background: $accent-darken-1 30%;
    }

    CollapsibleSection > .section-body {
        padding: 0 1 1 1;
    }

    CollapsibleSection.-collapsed > .section-body {
        display: none;
    }
    """

    can_focus = True
    collapsed = reactive(True, init=False)

    def __init__(
        self,
        title: str,
        body: Widget,
        *,
        summary: str = "",
        collapsed: bool = True,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._title = title
        self._summary = summary
        self._body = body
        self._header: Static | None = None
        self._body_container: Container | None = None
        self._initial_collapsed = collapsed

    def compose(self) -> ComposeResult:
        self._header = Static(
            "",
            classes="section-header",
            markup=False,
        )
        yield self._header

        self._body_container = Container(self._body, classes="section-body")
        yield self._body_container

    def on_mount(self) -> None:
        self.collapsed = self._initial_collapsed
        self._refresh_header()

    def watch_collapsed(self, collapsed: bool) -> None:
        self.set_class(collapsed, "-collapsed")
        self.set_class(not collapsed, "-expanded")
        if self._body_container is not None:
            self._body_container.display = "none" if collapsed else "block"
        self._refresh_header()

    def set_summary(self, summary: str) -> None:
        """Update the summary text shown in the header."""
        self._summary = summary
        self._refresh_header()

    def set_expanded(self, expanded: bool) -> None:
        """Programmatically expand/collapse without emitting messages."""
        self.collapsed = not expanded

    def expand(self) -> None:
        self.set_expanded(True)

    def collapse(self) -> None:
        self.set_expanded(False)

    def on_key(self, event: events.Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            self._request_toggle()

    def on_click(self, event: events.Click) -> None:
        if self._header is None:
            return
        if event.control is self._header:
            event.stop()
            self._request_toggle()

    def _request_toggle(self) -> None:
        self.post_message(SectionToggleRequested(self, expand=self.collapsed))

    def _refresh_header(self) -> None:
        if self._header is None:
            return
        icon = "[+]" if self.collapsed else "[-]"
        summary = f" - {self._summary}" if self._summary else ""
        self._header.update(f"{icon} {self._title}{summary}")


__all__ = ["CollapsibleSection", "SectionToggleRequested"]
