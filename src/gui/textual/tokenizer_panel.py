"""Tokenizer selection panel for the Textual GUI."""

from __future__ import annotations

from typing import Callable, Sequence

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Checkbox, Input, Label, Static

from .theme import themed_css


def _sanitize_id(name: str) -> str:
    """Sanitize a tokenizer name for use as a widget ID."""
    return name.replace("/", "--").replace(".", "-")


DEFAULT_TOKENIZERS = [
    "cl100k_base",
    "o200k_base",
    "gpt2",
    "r50k_base",
    "p50k_base",
]

CSS = """
TokenizerPanel {
    width: 100%;
    height: auto;
    min-height: 6;
    max-height: 14;
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
}

TokenizerPanel .panel-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    color: var(--glitch-accent);
    text-style: bold;
    content-align: left middle;
}

TokenizerPanel .tokenizer-list {
    height: 1fr;
    min-height: 4;
    padding: 0;
    background: transparent;
    overflow-y: auto;
}

TokenizerPanel .tokenizer-item {
    height: 2;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}

TokenizerPanel .tokenizer-checkbox {
    width: auto;
    padding-right: 1;
}

TokenizerPanel .tokenizer-name {
    width: 1fr;
    color: var(--glitch-ink);
}

TokenizerPanel .tokenizer-name.-enabled {
    color: var(--glitch-bright);
}

TokenizerPanel .add-tokenizer {
    height: 2;
    padding: 0 1;
    border-top: solid var(--glitch-border);
    layout: horizontal;
    align: left middle;
}

TokenizerPanel .add-tokenizer Input {
    width: 1fr;
    height: 1;
    min-height: 1;
    margin-right: 1;
    background: var(--glitch-bg);
    color: var(--glitch-ink);
    border: solid var(--glitch-border);
}

TokenizerPanel .add-tokenizer Label {
    width: auto;
    color: var(--glitch-muted);
}
"""


class TokenizerItem(Static):  # type: ignore[misc]
    """A single tokenizer checkbox item."""

    class ToggleChanged(Message):  # type: ignore[misc]
        """Posted when tokenizer toggle changes."""

        def __init__(self, name: str, enabled: bool) -> None:
            super().__init__()
            self.name = name
            self.enabled = enabled

    def __init__(self, name: str, enabled: bool = True, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._name = name
        self._enabled = enabled
        self._checkbox: Checkbox | None = None
        self._label: Label | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="tokenizer-item"):
            self._checkbox = Checkbox(
                "", value=self._enabled, id=f"tok-check-{_sanitize_id(self._name)}"
            )
            yield self._checkbox
            self._label = Label(self._name, classes="tokenizer-name")
            if self._enabled:
                self._label.add_class("-enabled")
            yield self._label

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox toggle."""
        self._enabled = event.value
        if self._label:
            if self._enabled:
                self._label.add_class("-enabled")
            else:
                self._label.remove_class("-enabled")
        self.post_message(self.ToggleChanged(self._name, self._enabled))

    @property
    def name(self) -> str:
        """The tokenizer name."""
        return self._name

    @property
    def enabled(self) -> bool:
        """Whether this tokenizer is enabled."""
        return self._enabled


class TokenizerPanel(Static):  # type: ignore[misc]
    """Panel for selecting tokenizers to use for metrics."""

    DEFAULT_CSS = themed_css(CSS)

    class SelectionChanged(Message):  # type: ignore[misc]
        """Posted when tokenizer selection changes."""

        def __init__(self, tokenizers: list[str]) -> None:
            super().__init__()
            self.tokenizers = tokenizers

    def __init__(
        self,
        *,
        tokenizers: Sequence[str] | None = None,
        on_change: Callable[[list[str]], None] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._tokenizers = list(tokenizers) if tokenizers else list(DEFAULT_TOKENIZERS)
        self._on_change = on_change
        self._items: dict[str, TokenizerItem] = {}
        self._list_container: VerticalScroll | None = None
        self._add_input: Input | None = None

    def compose(self) -> ComposeResult:
        yield Static("TOKENIZERS", classes="panel-header")
        self._list_container = VerticalScroll(classes="tokenizer-list")
        with self._list_container:
            for name in self._tokenizers:
                item = TokenizerItem(name, enabled=True, id=f"tokenizer-{_sanitize_id(name)}")
                self._items[name] = item
                yield item
        yield self._list_container

        with Container(classes="add-tokenizer"):
            self._add_input = Input(placeholder="Add tokenizer...", id="add-tokenizer-input")
            yield self._add_input
            yield Label("Enter to add", classes="add-hint")

    def on_tokenizer_item_toggle_changed(self, event: TokenizerItem.ToggleChanged) -> None:
        """Handle tokenizer toggle changes."""
        self._notify_change()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle adding a new tokenizer."""
        if event.input.id != "add-tokenizer-input":
            return
        name = event.value.strip()
        if not name or name in self._items:
            return

        # Add new tokenizer
        item = TokenizerItem(name, enabled=True, id=f"tokenizer-{_sanitize_id(name)}")
        self._items[name] = item
        if self._list_container:
            self._list_container.mount(item)

        # Clear input
        event.input.value = ""
        self._notify_change()

    def _notify_change(self) -> None:
        """Notify listeners of selection changes."""
        enabled = self.get_enabled_tokenizers()
        if self._on_change:
            self._on_change(enabled)
        self.post_message(self.SelectionChanged(enabled))

    def get_enabled_tokenizers(self) -> list[str]:
        """Get list of enabled tokenizer names."""
        return [item.name for item in self._items.values() if item.enabled]

    def get_all_tokenizers(self) -> list[str]:
        """Get list of all tokenizer names."""
        return list(self._items.keys())

    def set_tokenizers(self, tokenizers: Sequence[str]) -> None:
        """Replace the tokenizer list."""
        # Clear existing items
        if self._list_container:
            for item in list(self._items.values()):
                item.remove()
        self._items.clear()

        # Add new items
        self._tokenizers = list(tokenizers)
        for name in self._tokenizers:
            item = TokenizerItem(name, enabled=True, id=f"tokenizer-{_sanitize_id(name)}")
            self._items[name] = item
            if self._list_container:
                self._list_container.mount(item)

        self._notify_change()
