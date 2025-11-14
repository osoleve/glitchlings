"""Textual application for the metrics TUI."""

from __future__ import annotations

from typing import Any

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        Button,
        Checkbox,
        DataTable,
        Footer,
        Header,
        Input,
        Static,
    )
except ImportError as exc:  # pragma: no cover - executed only when Textual missing
    raise RuntimeError(
        "Textual is required for the metrics TUI. Install with:\n"
        "    pip install glitchlings[metrics-tui]\n"
    ) from exc

from ...core.session import SessionResult
from .controller import MetricsTUIController


class MetricsApp(App[None]):  # type: ignore[misc]
    """Simple Textual UI that displays metrics per tokenizer."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        layout: horizontal;
        height: 1fr;
        padding: 1;
    }

    #controls-panel {
        width: 1fr;
        border: solid #666;
        padding: 1;
    }

    #content-panel {
        width: 2fr;
        border: solid #666;
        padding: 1;
    }

    #metrics-table {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("r", "recompute", "Re-run metrics"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, controller: MetricsTUIController) -> None:
        super().__init__()
        self.controller = controller
        self.table: DataTable | None = None
        self.summary: Static | None = None
        self.text_input: Input | None = None
        self.custom_glitch_input: Input | None = None
        self.custom_tokenizer_input: Input | None = None
        self.glitch_checkbox_lookup: dict[str, str] = {}
        self.tokenizer_checkbox_lookup: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="controls-panel"):
                yield Static("Input Text", classes="label")
                self.text_input = Input(
                    placeholder="Type text and press Enter to run",
                    id="text-input",
                    value=self.controller.text,
                )
                yield self.text_input

                yield Static("Glitchlings (select multiple)", classes="label")
                self.glitch_checkbox_lookup = {}
                for idx, name in enumerate(self.controller.available_glitchlings()):
                    checkbox = Checkbox(
                        name,
                        value=self.controller.is_glitchling_selected(name),
                        id=f"glitch-{idx}",
                    )
                    self.glitch_checkbox_lookup[checkbox.id] = name
                    yield checkbox
                self.custom_glitch_input = Input(
                    placeholder="Custom specs, comma-separated",
                    id="custom-glitch-input",
                    value=self.controller.custom_glitchlings_text(),
                )
                yield self.custom_glitch_input

                yield Static("Tokenizers", classes="label")
                self.tokenizer_checkbox_lookup = {}
                for idx, (label, spec) in enumerate(self.controller.available_tokenizers()):
                    checkbox = Checkbox(
                        label,
                        value=self.controller.is_tokenizer_selected(spec),
                        id=f"tokenizer-{idx}",
                    )
                    self.tokenizer_checkbox_lookup[checkbox.id] = spec
                    yield checkbox
                self.custom_tokenizer_input = Input(
                    placeholder="Custom tokenizers, comma-separated",
                    id="custom-tokenizer-input",
                    value=self.controller.custom_tokenizers_text(),
                )
                yield self.custom_tokenizer_input

                yield Button("Run (r)", id="run-button")

            with Vertical(id="content-panel"):
                self.summary = Static("Loading metrics...", id="summary")
                yield self.summary
                self.table = DataTable(zebra_stripes=True, id="metrics-table")
                yield self.table

        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_metrics()

    async def on_key(self, event: Any) -> None:  # pragma: no cover - UI behaviour
        if event.key == "escape":
            await self.action_quit()

    async def action_recompute(self) -> None:
        await self.refresh_metrics()

    async def refresh_metrics(self) -> None:
        try:
            result = self.controller.refresh()
        except ValueError as exc:
            if self.summary:
                self.summary.update(f"[b]Error:[/b] {exc}")
            return
        self._update_summary(result)
        self._update_table()

    def _update_summary(self, result: SessionResult) -> None:
        if not self.summary:
            return

        summary_text = self.controller.summary_text()
        detail = (
            f"{summary_text}\n\n"
            f"[b]Input[/b]\n{result.text_before}\n\n"
            f"[b]Output[/b]\n{result.text_after}"
        )
        self.summary.update(detail)

    def _update_table(self) -> None:
        if not self.table:
            return

        self.table.clear(columns=True)
        for column in self.controller.metric_columns():
            self.table.add_column(column)

        for row in self.controller.metric_rows():
            self.table.add_row(*row)

    # pragma: no cover - UI wiring
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-button":
            await self.refresh_metrics()

    # pragma: no cover
    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        widget_id = event.checkbox.id
        spec = self.glitch_checkbox_lookup.get(widget_id)
        if spec is not None:
            self.controller.set_builtin_glitchling(spec, event.value)
            return
        tok_spec = self.tokenizer_checkbox_lookup.get(widget_id)
        if tok_spec is not None:
            self.controller.set_builtin_tokenizer(tok_spec, event.value)

    # pragma: no cover
    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "text-input":
            self.controller.update_text(event.value)
        elif event.input.id == "custom-glitch-input":
            self.controller.set_custom_glitchlings(event.value)
        elif event.input.id == "custom-tokenizer-input":
            self.controller.set_custom_tokenizers(event.value)

    # pragma: no cover
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"text-input", "custom-glitch-input", "custom-tokenizer-input"}:
            await self.refresh_metrics()
