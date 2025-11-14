"""Textual application for the metrics TUI."""

from __future__ import annotations

import difflib
from typing import Iterable

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Resize
from textual.widgets import Button, Input, Static, TabbedContent, TabPane, TextArea

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


def _build_diff(before: str, after: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="input",
            tofile="output",
            lineterm="",
        )
    )
    return "\n".join(diff_lines) if diff_lines else "No differences detected."


class MetricsApp(App[None]):  # type: ignore[misc]
    """Responsive Textual application for exploring metrics."""

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
        layout: vertical;
        padding: 0 1;
    }

    #section-stack {
        layout: vertical;
    }

    CollapsibleSection {
        border: none;
        background: $surface 5%;
    }

    .section-detail {
        color: $text 70%;
        padding-bottom: 1;
    }

    .section-help {
        color: $text 70%;
        padding-bottom: 1;
    }

    #run-summary {
        min-height: 2;
        padding: 0 1;
        border: none;
    }

    #main-tabs {
        height: 1fr;
    }

    TextArea {
        border: tall transparent;
        height: 1fr;
    }

    #input-text {
        height: 8;
    }

    TabPane {
        padding: 0 1;
    }

    #debug-view {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("r", "run_metrics", "Run metrics"),
        Binding("q", "quit", "Quit"),
        Binding("c", "open_picker", "Edit section picker", show=False),
        Binding("g", "open_glitch_picker", "Glitchlings"),
        Binding("k", "open_tokenizer_picker", "Tokenizers"),
        Binding("ctrl+right", "tab_next", "Next tab", show=False),
        Binding("ctrl+left", "tab_previous", "Prev tab", show=False),
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
        self.diff_view: TextArea | None = None
        self.summary_display: Static | None = None
        self.metrics_view: MetricsView | None = None
        self.debug_view: TextArea | None = None
        self.footer: StatusFooter | None = None
        self.tabs: TabbedContent | None = None

        self.custom_glitch_input: Input | None = None
        self.custom_tokenizer_input: Input | None = None
        self.glitch_detail: Static | None = None
        self.tokenizer_detail: Static | None = None
        self._result: SessionResult | None = None

    def compose(self) -> ComposeResult:
        yield Static("Glitchlings Metrics", id="title-bar")

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
        self.diff_view = TextArea(
            text="",
            read_only=True,
            show_cursor=False,
            soft_wrap=False,
            id="diff-view",
        )
        self.debug_view = TextArea(
            text="",
            read_only=True,
            show_cursor=False,
            soft_wrap=True,
            id="debug-view",
        )
        self.footer = StatusFooter()

        with Vertical(id="app-body"):
            with Vertical(id="section-stack"):
                yield self.input_section
                yield self.glitch_section
                yield self.tokenizer_section
            yield self.summary_display
            with TabbedContent(id="main-tabs", initial="output") as tabs:
                self.tabs = tabs
                with TabPane("Output", id="output"):
                    yield self.output_view
                with TabPane("Metrics", id="metrics"):
                    yield self.metrics_view
                with TabPane("Diff", id="diff"):
                    yield self.diff_view
                with TabPane("Debug", id="debug"):
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
        if self.metrics_view is not None:
            self.metrics_view.set_narrow_mode(self.size.width < 120)
        await self.refresh_metrics()

    async def on_key(self, event: events.Key) -> None:  # pragma: no cover - UI behaviour
        if event.key == "escape":
            await self.action_quit()

    def on_resize(self, event: Resize) -> None:
        if self.metrics_view is not None:
            self.metrics_view.set_narrow_mode(event.size.width < 120)

    async def action_run_metrics(self) -> None:
        await self.refresh_metrics()

    def action_tab_next(self) -> None:
        if self.tabs is not None:
            self.tabs.action_next_tab()

    def action_tab_previous(self) -> None:
        if self.tabs is not None:
            self.tabs.action_previous_tab()

    async def action_open_picker(self) -> None:
        if self._active_section_id == "glitch-section":
            await self._open_glitch_modal()
        elif self._active_section_id == "tokenizer-section":
            await self._open_tokenizer_modal()

    async def action_open_glitch_picker(self) -> None:
        await self._open_glitch_modal()

    async def action_open_tokenizer_picker(self) -> None:
        await self._open_tokenizer_modal()

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
        self._update_debug_view(result)
        self._update_footer_counts()

    def _update_output_view(self, result: SessionResult) -> None:
        if self.output_view is None:
            return
        self.output_view.load_text(result.text_after)

    def _update_diff_view(self, result: SessionResult) -> None:
        if self.diff_view is None:
            return
        diff_text = _build_diff(result.text_before, result.text_after)
        self.diff_view.load_text(diff_text)

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
        tokens_before = 0
        tokens_after = 0
        if self._result and self._result.observations:
            obs = self._result.observations[0]
            tokens_before = len(obs.tokens_before)
            tokens_after = len(obs.tokens_after)
        self.footer.update_summary(glitch_count, tokenizer_count, tokens_before, tokens_after)

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

    async def _handle_glitch_picker_result(self, result: list[str] | None) -> None:
        if result is None:
            return
        selected_set = set(result)
        for name in self.controller.available_glitchlings():
            self.controller.set_builtin_glitchling(name, name in selected_set)
        self._update_glitch_summary()

    async def _handle_tokenizer_picker_result(self, result: list[str] | None) -> None:
        if result is None:
            return
        selected_set = set(result)
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
