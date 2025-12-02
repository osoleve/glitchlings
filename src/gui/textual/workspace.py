"""Workspace panel for text input/output and diff viewing."""

from __future__ import annotations

import difflib
from typing import Any, Literal, Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Select, Static, TabbedContent, TabPane, TextArea

from glitchlings.attack.tokenization import resolve_tokenizer

from .theme import themed_css

DiffMode = Literal["label", "id", "raw"]

DEFAULT_TOKENIZERS = [
    "cl100k_base",
    "o200k_base",
    "gpt2",
    "r50k_base",
    "p50k_base",
]

CSS = """
WorkspacePanel {
    width: 100%;
    height: 100%;
}

WorkspacePanel .workspace-content {
    height: 1fr;
    padding: 0;
}

WorkspacePanel .text-panel {
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    padding: 0;
    margin-bottom: 1;
    height: 1fr;
    min-height: 6;
}

WorkspacePanel .panel-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

WorkspacePanel .panel-title {
    color: var(--glitch-accent);
    text-style: bold;
    width: auto;
}

WorkspacePanel .panel-actions {
    dock: right;
    width: auto;
    height: 100%;
    layout: horizontal;
    align: right middle;
}

WorkspacePanel .panel-actions Button {
    min-width: 6;
    height: 1;
    margin-left: 1;
    background: var(--glitch-surface);
    color: var(--glitch-muted);
    border: none;
}

WorkspacePanel .panel-actions Button:hover {
    background: var(--glitch-border);
    color: var(--glitch-bright);
}

WorkspacePanel TextArea {
    height: 1fr;
    min-height: 4;
    background: var(--glitch-bg);
    color: var(--glitch-ink);
    border: none;
}

WorkspacePanel TextArea:focus {
    border: none;
}

WorkspacePanel .diff-controls {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    layout: horizontal;
    align: left middle;
}

WorkspacePanel .diff-controls Label {
    width: auto;
    margin-right: 1;
    color: var(--glitch-muted);
}

WorkspacePanel .diff-controls Select {
    width: 12;
    margin-right: 1;
}

WorkspacePanel .diff-view {
    height: 1fr;
    min-height: 4;
    padding: 1;
    background: var(--glitch-bg);
    overflow-y: auto;
}

WorkspacePanel .metrics-panel {
    height: auto;
    min-height: 4;
    max-height: 8;
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
}

WorkspacePanel .metrics-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    color: var(--glitch-accent);
    text-style: bold;
}

WorkspacePanel .metrics-table {
    padding: 0 1;
    overflow-y: auto;
}

WorkspacePanel .metrics-row {
    height: 2;
    layout: horizontal;
}

WorkspacePanel .metrics-label {
    width: 20;
    color: var(--glitch-muted);
}

WorkspacePanel .metrics-value {
    width: 1fr;
    color: var(--glitch-ink);
}

WorkspacePanel TabbedContent {
    height: 1fr;
}

WorkspacePanel TabPane {
    height: 1fr;
    padding: 0;
}
"""


class DiffView(Static):  # type: ignore[misc]
    """Rich diff display with syntax highlighting for token changes."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._input_text = ""
        self._output_text = ""
        self._mode: DiffMode = "label"
        self._tokenizer = "cl100k_base"

    def set_texts(self, input_text: str, output_text: str) -> None:
        """Update the input/output texts and refresh the diff."""
        self._input_text = input_text
        self._output_text = output_text
        self._refresh_diff()

    def set_mode(self, mode: DiffMode) -> None:
        """Change the diff display mode."""
        self._mode = mode
        self._refresh_diff()

    def set_tokenizer(self, tokenizer: str) -> None:
        """Change the tokenizer used for diff."""
        self._tokenizer = tokenizer
        self._refresh_diff()

    def _refresh_diff(self) -> None:
        """Recompute and display the diff."""
        if not self._input_text or not self._output_text:
            self.update(Text("No text to compare", style="dim"))
            return

        if self._mode == "raw":
            self.update(Text(self._output_text, style="green"))
            return

        try:
            tok = resolve_tokenizer(self._tokenizer)
            if tok is None:
                self.update(Text(f"Tokenizer '{self._tokenizer}' unavailable", style="red"))
                return

            input_tokens, input_ids = tok.encode(self._input_text)
            output_tokens, output_ids = tok.encode(self._output_text)

            if self._mode == "id":
                input_items = [str(t) for t in input_ids]
                output_items = [str(t) for t in output_ids]
            else:
                input_items = list(input_tokens)
                output_items = list(output_tokens)

            # Build diff display
            delta = len(output_tokens) - len(input_tokens)
            delta_str = f"+{delta}" if delta > 0 else str(delta)

            result = Text()
            result.append(
                f"Token Diff: {len(input_tokens)} → {len(output_tokens)} ({delta_str})\n",
                style="cyan bold",
            )
            result.append("[+added] ", style="on green black")
            result.append("[-removed] ", style="on red black")
            result.append("\n\n")

            matcher = difflib.SequenceMatcher(None, input_items, output_items)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    for item in input_items[i1:i2]:
                        display = f"[{item}] " if self._mode == "label" else f"{item} "
                        result.append(display, style="dim")
                elif tag == "replace":
                    for item in input_items[i1:i2]:
                        display = f"[-{item}] " if self._mode == "label" else f"-{item} "
                        result.append(display, style="on red black")
                    for item in output_items[j1:j2]:
                        display = f"[+{item}] " if self._mode == "label" else f"+{item} "
                        result.append(display, style="on green black")
                elif tag == "delete":
                    for item in input_items[i1:i2]:
                        display = f"[-{item}] " if self._mode == "label" else f"-{item} "
                        result.append(display, style="on red black")
                elif tag == "insert":
                    for item in output_items[j1:j2]:
                        display = f"[+{item}] " if self._mode == "label" else f"+{item} "
                        result.append(display, style="on green black")

            self.update(result)

        except Exception as e:
            self.update(Text(f"Error: {e}", style="red"))


class MetricsTable(Static):  # type: ignore[misc]
    """Display metrics in a tabular format."""

    METRIC_LABELS = {
        "token_delta": "Token Delta",
        "jsd": "Jensen-Shannon Div.",
        "ned": "Norm. Edit Distance",
        "sr": "Subsequence Retention",
    }

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._metrics: dict[str, dict[str, str]] = {}
        self._tokenizers: list[str] = []

    def set_metrics(self, metrics: dict[str, dict[str, str]]) -> None:
        """Update the displayed metrics."""
        self._metrics = metrics
        self._tokenizers = list(metrics.keys()) if metrics else []
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Rebuild the metrics display."""
        if not self._metrics:
            self.update(Text("No metrics available", style="dim"))
            return

        result = Text()

        # Header row
        result.append("Metric".ljust(24), style="cyan bold")
        for tok in self._tokenizers:
            result.append(tok.ljust(16), style="cyan bold")
        result.append("\n")
        result.append("─" * (24 + 16 * len(self._tokenizers)) + "\n", style="dim")

        # Data rows
        for metric_key, metric_label in self.METRIC_LABELS.items():
            result.append(metric_label.ljust(24), style="")
            for tok in self._tokenizers:
                value = self._metrics.get(tok, {}).get(metric_key, "-")
                result.append(str(value).ljust(16), style="green")
            result.append("\n")

        self.update(result)


class WorkspacePanel(Static):  # type: ignore[misc]
    """Main workspace panel with input, output, diff, and metrics."""

    DEFAULT_CSS = themed_css(CSS)
    BINDINGS = [
        Binding("ctrl+l", "clear_input", "Clear", show=False),
    ]

    class InputChanged(Message):  # type: ignore[misc]
        """Posted when input text changes."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class TransformRequested(Message):  # type: ignore[misc]
        """Posted when transform is explicitly requested."""

        pass

    def __init__(
        self,
        *,
        initial_text: str = "",
        tokenizers: Sequence[str] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._initial_text = initial_text
        self._tokenizers = list(tokenizers) if tokenizers else list(DEFAULT_TOKENIZERS)
        self._input_area: TextArea | None = None
        self._output_area: TextArea | None = None
        self._diff_view: DiffView | None = None
        self._metrics_table: MetricsTable | None = None
        self._mode_select: Select[DiffMode] | None = None
        self._tok_select: Select[str] | None = None
        self._output_text = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="workspace-content"):
            with TabbedContent():
                with TabPane("Input", id="input-tab"):
                    with Container(classes="text-panel"):
                        with Horizontal(classes="panel-header"):
                            yield Label("INPUT", classes="panel-title")
                            with Container(classes="panel-actions"):
                                yield Button("Clear", id="clear-btn", variant="default")
                        self._input_area = TextArea(id="input-area")
                        self._input_area.text = self._initial_text
                        yield self._input_area

                with TabPane("Token Diff", id="diff-tab"):
                    with Container(classes="text-panel"):
                        with Horizontal(classes="diff-controls"):
                            yield Label("View:")
                            self._mode_select = Select(
                                [
                                    ("Label", "label"),
                                    ("ID", "id"),
                                    ("Raw", "raw"),
                                ],
                                value="label",
                                id="mode-select",
                            )
                            yield self._mode_select
                            yield Label("Tokenizer:")
                            self._tok_select = Select(
                                [(t, t) for t in self._tokenizers],
                                value=self._tokenizers[0] if self._tokenizers else "cl100k_base",
                                id="tok-select",
                            )
                            yield self._tok_select
                        self._diff_view = DiffView(id="diff-view")
                        yield Container(self._diff_view, classes="diff-view")

                    with Container(classes="text-panel"):
                        with Horizontal(classes="panel-header"):
                            yield Label("OUTPUT PREVIEW", classes="panel-title")
                            with Container(classes="panel-actions"):
                                yield Button("Copy", id="copy-btn", variant="default")
                        self._output_area = TextArea(id="output-area", read_only=True)
                        yield self._output_area

            with Container(classes="metrics-panel"):
                yield Static("METRICS", classes="metrics-header")
                self._metrics_table = MetricsTable(id="metrics-table")
                yield Container(self._metrics_table, classes="metrics-table")

    def on_mount(self) -> None:
        """Set up event handlers after mount."""
        if self._input_area:
            self._input_area.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        if event.text_area.id == "input-area":
            self.post_message(self.InputChanged(event.text_area.text))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "clear-btn":
            self.action_clear_input()
        elif event.button.id == "copy-btn":
            self._copy_output()

    def on_select_changed(self, event: Select.Changed[Any]) -> None:
        """Handle select changes."""
        if event.select.id == "mode-select" and self._diff_view:
            self._diff_view.set_mode(event.value)
        elif event.select.id == "tok-select" and self._diff_view:
            self._diff_view.set_tokenizer(str(event.value))

    def action_clear_input(self) -> None:
        """Clear the input text area."""
        if self._input_area:
            self._input_area.text = ""
            self.post_message(self.InputChanged(""))

    def _copy_output(self) -> None:
        """Copy output to clipboard."""
        if self._output_text:
            try:
                import pyperclip

                pyperclip.copy(self._output_text)
                self.app.notify("Output copied to clipboard", severity="information")
            except ImportError:
                self.app.notify("Clipboard not available (install pyperclip)", severity="warning")
        else:
            self.app.notify("No output to copy", severity="warning")

    @property
    def input_text(self) -> str:
        """Get the current input text."""
        return self._input_area.text if self._input_area else ""

    @input_text.setter
    def input_text(self, value: str) -> None:
        """Set the input text."""
        if self._input_area:
            self._input_area.text = value

    @property
    def output_text(self) -> str:
        """Get the current output text."""
        return self._output_text

    def set_output(self, text: str) -> None:
        """Set the output text and update diff."""
        self._output_text = text
        if self._output_area:
            self._output_area.text = text
        if self._diff_view and self._input_area:
            self._diff_view.set_texts(self._input_area.text, text)

    def set_metrics(self, metrics: dict[str, dict[str, str]]) -> None:
        """Update the metrics display."""
        if self._metrics_table:
            self._metrics_table.set_metrics(metrics)

    def set_tokenizers(self, tokenizers: Sequence[str]) -> None:
        """Update the available tokenizers."""
        self._tokenizers = list(tokenizers)
        if self._tok_select:
            self._tok_select.set_options([(t, t) for t in tokenizers])
            if tokenizers and self._tok_select.value not in tokenizers:
                self._tok_select.value = tokenizers[0]
