"""Textual application for the metrics TUI."""

from __future__ import annotations

import difflib
import re
from typing import Iterable, Sequence

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.widgets import Button, Input, Static, Switch, TextArea

from ...core.session import SessionResult
from .components import (
    CollapsibleSection,
    MetricsView,
    PickerItem,
    PickerModal,
    SectionToggleRequested,
    StatusFooter,
)
from .controller import MetricsTUIController


def _format_list_summary(label: str, items: Iterable[str]) -> str:
    items_list = [item for item in items if item]
    if not items_list:
        return f"{label}: none"
    if len(items_list) <= 3:
        display = ", ".join(items_list)
    else:
        display = ", ".join(items_list[:3]) + f" (+{len(items_list) - 3} more)"
    return f"{label}: {display}"


def _text_summary(text: str) -> str:
    if not text:
        return "0 chars"
    lines = text.count("\n") + 1
    line_label = "line" if lines == 1 else "lines"
    return f"{len(text)} chars, {lines} {line_label}"


TOKEN_SPLIT_RE = re.compile(r"(\s+|[.,!?;:])")


def _tokenize_text(text: str) -> list[str]:
    """Split text into tokens preserving whitespace for more stable diffs."""
    if not text:
        return []
    tokens = [segment for segment in TOKEN_SPLIT_RE.split(text) if segment]
    return tokens if tokens else [text]


def _build_span_diff(before: str, after: str) -> Text:
    """Return a rich ``Text`` with inline span differences."""
    before_tokens = _tokenize_text(before)
    after_tokens = _tokenize_text(after)
    matcher = difflib.SequenceMatcher(None, before_tokens, after_tokens)
    result = Text()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        before_chunk = "".join(before_tokens[i1:i2])
        after_chunk = "".join(after_tokens[j1:j2])
        if tag == "equal":
            result.append(after_chunk)
        elif tag == "insert":
            result.append(after_chunk, style="bold green")
        elif tag == "delete":
            if before_chunk:
                result.append(before_chunk, style="bold red strike")
        elif tag == "replace":
            if before_chunk:
                result.append(before_chunk, style="bold red strike")
            if after_chunk:
                result.append(after_chunk, style="bold green")
    if not result:
        return Text("No differences detected.")
    return result


def _build_token_diff(tokens_before: Sequence[int], tokens_after: Sequence[int]) -> Text:
    """Generate a diff over token ids."""
    matcher = difflib.SequenceMatcher(None, tokens_before, tokens_after)
    text = Text()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        before_chunk = tokens_before[i1:i2]
        after_chunk = tokens_after[j1:j2]
        if tag == "equal":
            text.append(" ".join(str(token) for token in after_chunk) + " ")
        elif tag == "insert":
            text.append(" ".join(str(token) for token in after_chunk) + " ", style="bold green")
        elif tag == "delete":
            if before_chunk:
                text.append(
                    " ".join(str(token) for token in before_chunk) + " ", style="bold red strike"
                )
        elif tag == "replace":
            if before_chunk:
                text.append(
                    " ".join(str(token) for token in before_chunk) + " ", style="bold red strike"
                )
            if after_chunk:
                text.append(" ".join(str(token) for token in after_chunk) + " ", style="bold green")
    if not text.plain.strip():
        return Text("No token changes detected.")
    return text


class MetricsApp(App[None]):  # type: ignore[misc]
    """Responsive Textual application for exploring metrics."""

    CONTROL_COLUMN_WIDTH = 42

    CSS = """
    Screen {
        layout: vertical;
    }

    #title-bar {
        height: 1;
        padding: 0 1;
        content-align: left middle;
        background: $surface;
        color: $text;
    }

    #app-body {
        height: 1fr;
        layout: horizontal;
        padding: 0 1 1 1;
    }

    #app-body.narrow {
        layout: vertical;
    }

    #control-column {
        width: 42;
        min-width: 36;
        max-width: 48;
        height: 1fr;
        padding-right: 1;
        border-right: solid $surface 20%;
        margin-right: 1;
    }

    #app-body.narrow #control-column {
        width: 1fr;
        max-width: 1fr;
        border-right: none;
        padding-right: 0;
        margin-right: 0;
    }

    #control-scroll {
        height: 1fr;
        overflow-y: auto;
        padding-right: 1;
    }

    #section-stack {
        layout: vertical;
    }

    CollapsibleSection {
        border: none;
        background: $surface 5%;
        margin-bottom: 1;
    }

    .section-detail,
    .section-help {
        color: $text 70%;
        padding-bottom: 1;
    }

    #run-summary {
        min-height: 3;
        padding: 0 1;
        border: round $surface 20%;
        margin-top: 1;
    }

    TextArea {
        border: tall transparent;
        height: 1fr;
    }

    #input-text {
        height: 8;
    }

    #results-column {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    #results-column > * {
        margin-bottom: 1;
    }

    #results-primary {
        layout: horizontal;
        height: 1fr;
    }

    #results-primary.narrow {
        layout: vertical;
    }

    #results-primary > * {
        margin-right: 1;
    }

    #results-primary.narrow > * {
        margin-right: 0;
        margin-bottom: 1;
    }

    .results-panel {
        border: round $surface 15%;
        padding: 0 1 1 1;
        background: $surface 3%;
        height: 1fr;
        min-height: 12;
    }

    .panel-title {
        text-style: bold;
        padding: 0 0 1 0;
    }

    #diff-scroll,
    #token-diff-scroll,
    #debug-scroll {
        height: 1fr;
    }

    #diff-view,
    #token-diff-view {
        border: tall transparent;
        overflow-y: auto;
    }

    #aux-toolbar {
        border: round transparent;
        padding: 0 1;
        height: auto;
        content-align: left middle;
    }

    #aux-toolbar > * {
        margin-right: 2;
    }

    .toolbar-label {
        color: $text 80%;
        text-style: bold;
    }

    .toggle-row {
        align: center middle;
    }

    .toggle-row > * {
        margin-right: 1;
    }

    .toggle-label {
        color: $text 70%;
    }

    #aux-panels {
        layout: horizontal;
    }

    #aux-panels.narrow {
        layout: vertical;
    }

    #aux-panels > * {
        margin-right: 1;
    }

    #aux-panels.narrow > * {
        margin-right: 0;
        margin-bottom: 1;
    }

    .aux-panel {
        width: 1fr;
        min-height: 8;
        border: round $surface 15%;
        padding: 0 1 1 1;
        background: $surface 5%;
    }

    .aux-panel.hidden {
        display: none;
    }

    #output-panel,
    #diff-panel,
    #metrics-panel {
        min-width: 32;
    }
    """

    BINDINGS = [
        Binding("r", "run_metrics", "Run metrics"),
        Binding("q", "quit", "Quit"),
        Binding("c", "open_picker", "Edit section picker", show=False),
        Binding("g", "open_glitch_picker", "Glitchlings"),
        Binding("k", "open_tokenizer_picker", "Tokenizers"),
        Binding("t", "toggle_token_diff", "Token diff"),
        Binding("b", "toggle_debug", "Debug info"),
    ]

    def __init__(self, controller: MetricsTUIController) -> None:
        super().__init__()
        self.controller = controller
        self.input_section: CollapsibleSection | None = None
        self.glitch_section: CollapsibleSection | None = None
        self.tokenizer_section: CollapsibleSection | None = None
        self._sections: list[CollapsibleSection] = []
        self._active_section_id: str | None = None

        self.input_text: TextArea | None = None
        self.output_view: TextArea | None = None
        self.diff_view: Static | None = None
        self.token_diff_view: Static | None = None
        self.summary_display: Static | None = None
        self.metrics_view: MetricsView | None = None
        self.debug_view: TextArea | None = None
        self.footer: StatusFooter | None = None
        self.app_body: Horizontal | None = None
        self.results_primary: Horizontal | None = None
        self.aux_panels: Horizontal | None = None
        self.token_diff_container: Vertical | None = None
        self.debug_container: Vertical | None = None
        self.token_diff_switch: Switch | None = None
        self.debug_switch: Switch | None = None
        self._show_token_diff = False
        self._show_debug = False

        self.custom_glitch_input: Input | None = None
        self.custom_tokenizer_input: Input | None = None
        self.glitch_detail: Static | None = None
        self.tokenizer_detail: Static | None = None
        self._result: SessionResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("Attack on Token", id="title-bar")

        input_body = self._build_input_body()
        glitch_body = self._build_glitch_body()
        tokenizer_body = self._build_tokenizer_body()

        self.input_section = CollapsibleSection(
            "Input Text",
            input_body,
            collapsed=False,
            id="input-section",
        )
        self.glitch_section = CollapsibleSection(
            "Glitchling Selection",
            glitch_body,
            collapsed=True,
            id="glitch-section",
        )
        self.tokenizer_section = CollapsibleSection(
            "Tokenizer Selection",
            tokenizer_body,
            collapsed=True,
            id="tokenizer-section",
        )

        self.summary_display = Static("Run metrics (r) to view results.", id="run-summary")
        self.metrics_view = MetricsView(id="metrics-view")
        self.output_view = TextArea(
            text="",
            read_only=True,
            show_cursor=False,
            soft_wrap=True,
            id="output-view",
        )
        self.diff_view = Static("", id="diff-view", markup=False)
        self.token_diff_view = Static("", id="token-diff-view", markup=False)
        self.debug_view = TextArea(
            text="",
            read_only=True,
            show_cursor=False,
            soft_wrap=True,
            id="debug-view",
        )
        self.footer = StatusFooter()

        with Horizontal(id="app-body") as app_body:
            self.app_body = app_body
            with Vertical(id="control-column"):
                with VerticalScroll(id="control-scroll"):
                    with Vertical(id="section-stack"):
                        yield self.input_section
                        yield self.glitch_section
                        yield self.tokenizer_section
                yield self.summary_display
            with Vertical(id="results-column"):
                with Horizontal(id="results-primary") as results_primary:
                    self.results_primary = results_primary
                    with Vertical(id="output-panel", classes="results-panel"):
                        yield Static("Output", classes="panel-title")
                        yield self.output_view
                    with Vertical(id="diff-panel", classes="results-panel"):
                        yield Static("Diff", classes="panel-title")
                        with VerticalScroll(id="diff-scroll"):
                            yield self.diff_view
                    with Vertical(id="metrics-panel", classes="results-panel"):
                        yield Static("Metrics", classes="panel-title")
                        yield self.metrics_view
                with Horizontal(id="aux-toolbar"):
                    yield Static("Optional views", classes="toolbar-label")
                    with Horizontal(classes="toggle-row"):
                        self.token_diff_switch = Switch(id="token-diff-switch")
                        yield self.token_diff_switch
                        yield Static("Token diff", classes="toggle-label")
                    with Horizontal(classes="toggle-row"):
                        self.debug_switch = Switch(id="debug-switch")
                        yield self.debug_switch
                        yield Static("Debug info", classes="toggle-label")
                with Horizontal(id="aux-panels") as aux_panels:
                    self.aux_panels = aux_panels
                    with Vertical(id="token-diff-panel", classes="aux-panel hidden") as token_panel:
                        self.token_diff_container = token_panel
                        yield Static("Token diff", classes="panel-title")
                        with VerticalScroll(id="token-diff-scroll"):
                            yield self.token_diff_view
                    with Vertical(id="debug-panel", classes="aux-panel hidden") as debug_panel:
                        self.debug_container = debug_panel
                        yield Static("Debug info", classes="panel-title")
                        with VerticalScroll(id="debug-scroll"):
                            yield self.debug_view
        yield self.footer

    def _build_input_body(self) -> Vertical:
        self.input_text = TextArea(
            text=self.controller.text,
            placeholder="Type text and press r to compute metrics.",
            soft_wrap=True,
            id="input-text",
        )
        return Vertical(
            Static("Input text scrolls here. Press r to re-run metrics.", classes="section-help"),
            self.input_text,
            Button("Run metrics (r)", id="run-button"),
        )

    def _build_glitch_body(self) -> Vertical:
        self.glitch_detail = Static("", classes="section-detail")
        self.custom_glitch_input = Input(
            placeholder="Custom specs, comma separated",
            id="custom-glitch-input",
            value=self.controller.custom_glitchlings_text(),
        )
        return Vertical(
            self.glitch_detail,
            Button("Choose glitchlings", id="glitch-picker-button"),
            Static("Custom glitchlings:", classes="section-help"),
            self.custom_glitch_input,
        )

    def _build_tokenizer_body(self) -> Vertical:
        self.tokenizer_detail = Static("", classes="section-detail")
        self.custom_tokenizer_input = Input(
            placeholder="Custom tokenizers, comma separated",
            id="custom-tokenizer-input",
            value=self.controller.custom_tokenizers_text(),
        )
        return Vertical(
            self.tokenizer_detail,
            Button("Choose tokenizers", id="tokenizer-picker-button"),
            Static("Custom tokenizers:", classes="section-help"),
            self.custom_tokenizer_input,
        )

    async def on_mount(self) -> None:
        self._sections = [
            section
            for section in (self.input_section, self.glitch_section, self.tokenizer_section)
            if section is not None
        ]
        if self.input_section is not None:
            self._set_active_section(self.input_section)
        self._update_input_summary()
        self._update_glitch_summary()
        self._update_tokenizer_summary()
        self._apply_responsive_layout(self.size.width)
        await self.refresh_metrics()

    async def on_key(self, event: events.Key) -> None:  # pragma: no cover - UI behaviour
        if event.key == "escape":
            await self.action_quit()

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_layout(event.size.width)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "token-diff-switch":
            self._show_token_diff = event.value
            self._update_aux_panel_visibility()
        elif event.switch.id == "debug-switch":
            self._show_debug = event.value
            self._update_aux_panel_visibility()

    async def action_run_metrics(self) -> None:
        await self.refresh_metrics()

    async def action_open_picker(self) -> None:
        if self._active_section_id == "glitch-section":
            await self._open_glitch_modal()
        elif self._active_section_id == "tokenizer-section":
            await self._open_tokenizer_modal()

    async def action_open_glitch_picker(self) -> None:
        await self._open_glitch_modal()

    async def action_open_tokenizer_picker(self) -> None:
        await self._open_tokenizer_modal()

    def action_toggle_token_diff(self) -> None:
        self._show_token_diff = not self._show_token_diff
        self._update_aux_panel_visibility()

    def action_toggle_debug(self) -> None:
        self._show_debug = not self._show_debug
        self._update_aux_panel_visibility()

    async def refresh_metrics(self) -> None:
        try:
            result = self.controller.refresh()
        except ValueError as exc:
            if self.summary_display is not None:
                self.summary_display.update(f"[b]Error:[/b] {exc}")
            if self.metrics_view is not None:
                self.metrics_view.clear()
            return
        self._result = result
        if self.summary_display is not None:
            self.summary_display.update(self.controller.summary_text())
        if self.metrics_view is not None:
            self.metrics_view.set_data(
                self.controller.metric_columns(),
                self.controller.metric_rows(),
            )
        self._update_output_view(result)
        self._update_diff_view(result)
        self._update_token_diff_view(result)
        self._update_debug_view(result)
        self._update_footer_counts()

    def _update_output_view(self, result: SessionResult) -> None:
        if self.output_view is None:
            return
        self.output_view.load_text(result.text_after)

    def _update_diff_view(self, result: SessionResult) -> None:
        if self.diff_view is None:
            return
        diff_text = _build_span_diff(result.text_before, result.text_after)
        self.diff_view.update(diff_text)

    def _update_token_diff_view(self, result: SessionResult) -> None:
        if self.token_diff_view is None:
            return
        if not result.observations:
            self.token_diff_view.update("No tokenizers selected.")
            return
        combined = Text()
        for index, observation in enumerate(result.observations):
            diff_text = _build_token_diff(observation.tokens_before, observation.tokens_after)
            if index:
                combined.append("\n\n")
            combined.append(f"{observation.tokenizer_id}\n", style="bold")
            combined.append_text(diff_text)
        self.token_diff_view.update(combined)

    def _update_debug_view(self, result: SessionResult) -> None:
        if self.debug_view is None:
            return
        lines = [
            f"run_id: {result.run_id}",
            f"glitchling_id: {result.glitchling_id}",
            f"observations: {len(result.observations)}",
        ]
        for obs in result.observations:
            lines.append(
                f"- {obs.tokenizer_id}: tokens={len(obs.tokens_before)}->{len(obs.tokens_after)}"
            )
        self.debug_view.load_text("\n".join(lines))

    def _update_footer_counts(self) -> None:
        if self.footer is None:
            return
        glitch_count = len(self.controller.current_glitchling_specs())
        tokenizer_count = len(self.controller.selected_tokenizer_specs())
        self.footer.update_summary(glitch_count, tokenizer_count)

    def _apply_responsive_layout(self, width: int) -> None:
        is_narrow = width < 100
        if self.app_body is not None:
            self.app_body.set_class(is_narrow, "narrow")
        if self.results_primary is not None:
            self.results_primary.set_class(is_narrow, "narrow")
        if self.aux_panels is not None:
            self.aux_panels.set_class(is_narrow, "narrow")
        available_width = max(width - self.CONTROL_COLUMN_WIDTH, 40)
        if self.metrics_view is not None:
            self.metrics_view.set_narrow_mode(available_width < 80)
        self._update_aux_panel_visibility()

    def _update_aux_panel_visibility(self) -> None:
        if (
            self.token_diff_switch is not None
            and self.token_diff_switch.value != self._show_token_diff
        ):
            self.token_diff_switch.value = self._show_token_diff
        if (
            self.debug_switch is not None
            and self.debug_switch.value != self._show_debug
        ):
            self.debug_switch.value = self._show_debug
        if self.token_diff_container is not None:
            self.token_diff_container.set_class(not self._show_token_diff, "hidden")
        if self.debug_container is not None:
            self.debug_container.set_class(not self._show_debug, "hidden")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-button":
            await self.refresh_metrics()
        elif event.button.id == "glitch-picker-button":
            await self._open_glitch_modal()
        elif event.button.id == "tokenizer-picker-button":
            await self._open_tokenizer_modal()

    async def _open_glitch_modal(self) -> None:
        names = self.controller.available_glitchlings()
        items = [PickerItem(label=name, value=name) for name in names]
        selected = [name for name in names if self.controller.is_glitchling_selected(name)]
        picker = PickerModal("Glitchlings", items, selected=selected)
        await self.push_screen(picker, callback=self._handle_glitch_picker_result)

    async def _open_tokenizer_modal(self) -> None:
        available = self.controller.available_tokenizers()
        items = [PickerItem(label=label, value=spec, description=spec) for label, spec in available]
        selected = [spec for _, spec in available if self.controller.is_tokenizer_selected(spec)]
        picker = PickerModal("Tokenizers", items, selected=selected)
        await self.push_screen(picker, callback=self._handle_tokenizer_picker_result)

    async def _handle_glitch_picker_result(
        self, result: list[dict[str, str | None]] | None
    ) -> None:
        if result is None:
            return
        selected_set = {entry["value"] for entry in result if entry.get("value")}
        for name in self.controller.available_glitchlings():
            self.controller.set_builtin_glitchling(name, name in selected_set)
        self._update_glitch_summary()

    async def _handle_tokenizer_picker_result(
        self, result: list[dict[str, str | None]] | None
    ) -> None:
        if result is None:
            return
        selected_set = {entry["value"] for entry in result if entry.get("value")}
        for _, spec in self.controller.available_tokenizers():
            self.controller.set_builtin_tokenizer(spec, spec in selected_set)
        self._update_tokenizer_summary()

    def on_section_toggle_requested(self, message: SectionToggleRequested) -> None:
        if message.expand:
            self._set_active_section(message.section)
        else:
            message.section.collapse()
            if self._active_section_id == message.section.id:
                self._active_section_id = None

    def _set_active_section(self, target: CollapsibleSection) -> None:
        for section in self._sections:
            section.set_expanded(section is target)
        self._active_section_id = target.id

    def _update_input_summary(self) -> None:
        if self.input_section is not None:
            self.input_section.set_summary(_text_summary(self.controller.text))

    def _update_glitch_summary(self) -> None:
        specs = self.controller.current_glitchling_specs()
        summary = _format_list_summary("Glitchlings", specs) + " [press g]"
        if self.glitch_section is not None:
            self.glitch_section.set_summary(summary)
        if self.glitch_detail is not None:
            builtins = [
                name
                for name in self.controller.available_glitchlings()
                if self.controller.is_glitchling_selected(name)
            ]
            custom = self.controller.custom_glitchlings_text()
            parts = [f"Built-ins: {', '.join(builtins) or 'identity'}"]
            if custom:
                parts.append(f"Custom: {custom}")
            self.glitch_detail.update("\n".join(parts))
        self._update_footer_counts()

    def _update_tokenizer_summary(self) -> None:
        specs = self.controller.selected_tokenizer_specs()
        summary = _format_list_summary("Tokenizers", specs) + " [press k]"
        if self.tokenizer_section is not None:
            self.tokenizer_section.set_summary(summary)
        if self.tokenizer_detail is not None:
            builtins = [
                label
                for label, spec in self.controller.available_tokenizers()
                if self.controller.is_tokenizer_selected(spec)
            ]
            custom = self.controller.custom_tokenizers_text()
            parts = [f"Built-ins: {', '.join(builtins) or 'Simple'}"]
            if custom:
                parts.append(f"Custom: {custom}")
            self.tokenizer_detail.update("\n".join(parts))
        self._update_footer_counts()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "custom-glitch-input":
            self.controller.set_custom_glitchlings(event.value)
            self._update_glitch_summary()
        elif event.input.id == "custom-tokenizer-input":
            self.controller.set_custom_tokenizers(event.value)
            self._update_tokenizer_summary()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"custom-glitch-input", "custom-tokenizer-input"}:
            await self.refresh_metrics()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "input-text":
            self.controller.update_text(event.text_area.text)
            self._update_input_summary()


__all__ = ["MetricsApp"]
