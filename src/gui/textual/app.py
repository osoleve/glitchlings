from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Sequence

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Checkbox, Footer, Input, Static

from glitchlings.util import SAMPLE_TEXT
from glitchlings.zoo import Glitchling

from ..export import ExportData
from ..preferences import load_preferences, save_preferences
from ..service import GlitchlingService
from ..session import SessionConfig
from . import (
    AppState,
    BackgroundWorker,
    MessageBus,
    SelectionState,
    StateStore,
    StatusEvent,
    StatusLine,
    TransformCompleted,
    TransformFailed,
    TransformRequested,
    WorkspaceState,
)
from .charts_panel import ChartsPanel
from .commands import GlitchlingCommands
from .dataset_panel import DatasetPanel
from .export_dialog import ExportDialog, SweepExportDialog
from .glitchling_panel import GlitchlingPanel
from .navigation import NavigationPanel, NavTab
from .state import DatasetState
from .sweep_panel import SweepPanel
from .theme import themed_css
from .tokenizer_panel import TokenizerPanel
from .workspace import WorkspacePanel


class StatusBar(Static):  # type: ignore[misc]
    """Displays status messages pulled from the state store."""

    STATUS_STYLES = {
        "info": "var(--glitch-ink)",
        "success": "var(--glitch-bright)",
        "warning": "var(--glitch-warn)",
        "error": "var(--glitch-danger)",
        "progress": "var(--glitch-accent)",
    }

    def set_status(self, status: StatusLine, *, busy: bool = False) -> None:
        glyph = "⟳ " if busy and status.tone == "progress" else "● "
        style = self.STATUS_STYLES.get(status.tone, "var(--glitch-ink)")
        self.update(Text(f"{glyph}{status.message}", style=style))


class PlaceholderPanel(Static):  # type: ignore[misc]
    """Lightweight shell panel to reserve space for future views."""

    def __init__(self, title: str, body: str, *, panel_id: str):
        super().__init__(id=panel_id)
        self._title = title
        self._body = body
        self.can_focus = False

    def on_mount(self) -> None:
        title = Text(self._title, style="bold var(--glitch-accent)")
        copy = Text(self._body, style="dim var(--glitch-muted)")
        self.update(Text.assemble(title, "\n", copy))
        self.add_class("panel")


class SeedControl(Static):  # type: ignore[misc]
    """Seed input with randomize button and multi-seed toggle."""

    class MultiSeedChanged(Message):  # type: ignore[misc]
        """Posted when multi-seed settings change."""

        def __init__(self, enabled: bool, count: int) -> None:
            super().__init__()
            self.enabled = enabled
            self.count = count

    def __init__(
        self,
        initial_seed: int = 151,
        *,
        multi_seed: bool = False,
        multi_seed_count: int = 10,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._seed = initial_seed
        self._multi_seed = multi_seed
        self._multi_seed_count = multi_seed_count
        self._input: Input | None = None
        self._multi_checkbox: Checkbox | None = None
        self._count_input: Input | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="seed-control"):
            yield Static("SEED", classes="seed-label")
            self._input = Input(str(self._seed), id="seed-input", classes="seed-input")
            yield self._input
            yield Button("🎲", id="randomize-btn", classes="seed-btn")
            self._multi_checkbox = Checkbox(
                "Multi",
                value=self._multi_seed,
                id="multi-seed-check",
                classes="multi-seed-check",
            )
            yield self._multi_checkbox
            self._count_input = Input(
                str(self._multi_seed_count),
                id="multi-seed-count",
                classes="multi-seed-count",
            )
            yield self._count_input

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "randomize-btn":
            self._seed = random.randint(0, 999999)
            if self._input:
                self._input.value = str(self._seed)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "seed-input":
            try:
                self._seed = int(event.value)
            except ValueError:
                # Ignore invalid input, keep previous value
                return
        elif event.input.id == "multi-seed-count":
            try:
                self._multi_seed_count = max(1, int(event.value))
                self._notify_multi_seed_change()
            except ValueError:
                # Ignore invalid input, keep previous value
                return

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "multi-seed-check":
            self._multi_seed = event.value
            self._notify_multi_seed_change()

    def _notify_multi_seed_change(self) -> None:
        """Notify about multi-seed changes."""
        self.post_message(self.MultiSeedChanged(self._multi_seed, self._multi_seed_count))

    @property
    def seed(self) -> int:
        return self._seed

    @seed.setter
    def seed(self, value: int) -> None:
        self._seed = value
        if self._input:
            self._input.value = str(value)

    @property
    def multi_seed_enabled(self) -> bool:
        return self._multi_seed

    @property
    def multi_seed_count(self) -> int:
        return self._multi_seed_count


EXTRA_CSS = """
#chrome {
    height: 3;
    padding: 0 1;
    layout: horizontal;
    align: left middle;
    background: var(--glitch-panel);
    border-bottom: solid var(--glitch-border);
}

#chrome .app-title {
    width: auto;
    color: var(--glitch-bright);
    text-style: bold;
}

#chrome .controls-group {
    dock: right;
    width: auto;
    height: 100%;
    layout: horizontal;
    align: right middle;
}

#chrome .auto-update-checkbox {
    width: auto;
    margin-right: 1;
    padding: 0 1;
    color: var(--glitch-muted);
}

#chrome .auto-update-checkbox:focus {
    text-style: bold;
}

#chrome .seed-control {
    width: auto;
    height: 100%;
    layout: horizontal;
    align: right middle;
    padding-right: 1;
}

#chrome .seed-label {
    width: auto;
    padding-right: 1;
    color: var(--glitch-muted);
}

#chrome .seed-input {
    width: 8;
    height: 1;
    min-height: 1;
    background: var(--glitch-bg);
    color: var(--glitch-accent);
    border: solid var(--glitch-border);
}

#chrome .seed-btn {
    width: 3;
    height: 1;
    min-width: 3;
    margin-left: 1;
    background: var(--glitch-surface);
    color: var(--glitch-accent);
}

#chrome .seed-btn:hover {
    background: var(--glitch-border);
}

#chrome .multi-seed-check {
    width: auto;
    margin-left: 1;
    color: var(--glitch-muted);
}

#chrome .multi-seed-count {
    width: 5;
    height: 1;
    min-height: 1;
    margin-left: 1;
    background: var(--glitch-bg);
    color: var(--glitch-accent);
    border: solid var(--glitch-border);
}

#chrome .transform-btn {
    dock: right;
    width: auto;
    height: 1;
    margin-left: 1;
    margin-right: 1;
    padding: 0 1;
    background: var(--glitch-bright);
    color: var(--glitch-bg);
    text-style: bold;
}

#chrome .transform-btn:hover {
    background: var(--glitch-accent);
}

#body {
    layout: horizontal;
    height: 1fr;
    padding: 0 1;
}

#sidebar {
    width: 42;
    min-width: 36;
    max-width: 56;
    height: 100%;
    padding-right: 1;
}

#nav-panel {
    height: auto;
    max-height: 14;
    margin-bottom: 1;
}

#sidebar-panels {
    height: 1fr;
    min-height: 16;
    overflow-y: auto;
}

#main-content {
    width: 1fr;
    height: 100%;
}

#workspace-panel {
    width: 100%;
    height: 100%;
}

#dataset-panel,
#sweep-panel,
#charts-panel {
    display: none;
    width: 100%;
    height: 100%;
}

.panel {
    padding: 1 1;
    border: solid var(--glitch-border);
    min-height: 5;
}

#status {
    height: 2;
    padding: 0 1;
    content-align: left middle;
    background: var(--glitch-bg);
    border-top: solid var(--glitch-border);
}
"""


class GlitchlingsTextualApp(App[AppState]):  # type: ignore[misc]
    """Textual shell for the Glitchlings GUI rewrite."""

    CSS = themed_css(dedent(EXTRA_CSS))
    TITLE = "Glitchlings (Textual)"
    COMMANDS = {GlitchlingCommands}
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "run_transform", "Transform"),
        Binding("ctrl+enter", "run_transform", "Transform", show=False),
        Binding("ctrl+r", "randomize_seed", "Random Seed", show=False),
        Binding("ctrl+c", "copy_output", "Copy Output", show=False),
        Binding("ctrl+v", "paste_input", "Paste", show=False),
        Binding("ctrl+l", "clear_input", "Clear", show=False),
        Binding("ctrl+n", "new_session", "New Session", show=False),
        Binding("ctrl+e", "export", "Export", show=True),
        Binding("ctrl+shift+e", "export_sweep", "Export Sweep", show=False),
        Binding("escape", "focus_input", "Focus Input", show=False),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
    ]

    def __init__(self) -> None:
        self.bus = MessageBus()
        self.worker = BackgroundWorker(self.bus)
        self.service = GlitchlingService()
        prefs = load_preferences()
        initial_state = AppState(
            selections=SelectionState(
                tokenizers=list(prefs.default_tokenizers),
                seed=151,
            ),
            workspace=WorkspaceState(input_text=SAMPLE_TEXT),
            dataset=DatasetState(),
            preferences=prefs,
        )
        self.store = StateStore(initial_state)
        self.status_bar: StatusBar | None = None
        self._unsubscribers: list[Callable[[], None]] = []

        # Panel references
        self._nav_panel: NavigationPanel | None = None
        self._glitchling_panel: GlitchlingPanel | None = None
        self._tokenizer_panel: TokenizerPanel | None = None
        self._workspace_panel: WorkspacePanel | None = None
        self._dataset_panel: DatasetPanel | None = None
        self._sweep_panel: SweepPanel | None = None
        self._charts_panel: ChartsPanel | None = None
        self._seed_control: SeedControl | None = None
        self._auto_update_checkbox: Checkbox | None = None
        self._current_view: NavTab = "workspace"

        # Content container for view switching
        self._main_content: Container | None = None

        super().__init__()

    def compose(self) -> ComposeResult:
        # Header bar with title, seed control, and transform button
        with Container(id="chrome"):
            yield Static("༼ つ ◕_◕ ༽つ GLITCHLINGS", classes="app-title")
            yield Button("▶ TRANSFORM", id="transform-btn", classes="transform-btn")
            with Container(classes="controls-group"):
                self._auto_update_checkbox = Checkbox(
                    "Auto",
                    value=self.store.snapshot.selections.auto_update,
                    id="auto-update",
                    classes="auto-update-checkbox",
                )
                yield self._auto_update_checkbox
                self._seed_control = SeedControl(
                    initial_seed=self.store.snapshot.selections.seed,
                    multi_seed=self.store.snapshot.selections.multi_seed_mode,
                    multi_seed_count=self.store.snapshot.selections.multi_seed_count,
                    id="seed-control",
                )
                yield self._seed_control

        # Main body with sidebar and content
        with Container(id="body"):
            with Vertical(id="sidebar"):
                # Navigation panel
                self._nav_panel = NavigationPanel(
                    initial_tab="workspace",
                    on_tab_change=self._on_tab_change,
                )
                yield self._nav_panel

                with Vertical(id="sidebar-panels"):
                    self._glitchling_panel = GlitchlingPanel(
                        on_change=self._on_glitchlings_change,
                        id="glitchling-panel",
                    )
                    yield self._glitchling_panel
                    self._tokenizer_panel = TokenizerPanel(
                        tokenizers=self.store.snapshot.selections.tokenizers,
                        on_change=self._on_tokenizers_change,
                        id="tokenizer-panel",
                    )
                    yield self._tokenizer_panel

            self._main_content = Container(id="main-content")
            with self._main_content:
                # Workspace panel (default view)
                self._workspace_panel = WorkspacePanel(
                    initial_text=SAMPLE_TEXT,
                    tokenizers=self.store.snapshot.selections.tokenizers,
                    id="workspace-panel",
                )
                yield self._workspace_panel

                # Dataset panel (hidden initially)
                self._dataset_panel = DatasetPanel(
                    on_sample_selected=self._on_sample_selected,
                    on_batch_requested=self._on_batch_requested,
                    id="dataset-panel",
                )
                yield self._dataset_panel

                # Sweep panel (hidden initially)
                self._sweep_panel = SweepPanel(
                    get_input_text=self._get_input_text,
                    get_tokenizers=self._get_tokenizers,
                    service=self.service,
                    on_results_changed=self._on_sweep_results_changed,
                    id="sweep-panel",
                )
                yield self._sweep_panel

                # Charts panel (hidden initially)
                self._charts_panel = ChartsPanel(
                    get_scan_results=self._get_scan_results,
                    get_sweep_results=self._get_sweep_results,
                    get_dataset_results=self._get_dataset_results,
                    id="charts-panel",
                )
                yield self._charts_panel

        # Status bar
        self.status_bar = StatusBar(id="status")
        yield self.status_bar
        yield Footer()

    def on_mount(self) -> None:
        self._unsubscribers.extend(
            [
                self.bus.subscribe(TransformRequested, self._handle_transform_request),
                self.bus.subscribe(TransformCompleted, self._handle_transform_complete),
                self.bus.subscribe(TransformFailed, self._handle_transform_failed),
                self.bus.subscribe(StatusEvent, self._handle_status_event),
                self.store.subscribe(self._on_state_change),
            ]
        )
        if self.status_bar:
            self.status_bar.set_status(self.store.snapshot.status, busy=self.store.snapshot.busy)

        # Initialize view visibility
        self._switch_view("workspace")

    def _switch_view(self, view: NavTab) -> None:
        """Switch the visible main content panel."""
        self._current_view = view

        # Hide all panels
        if self._workspace_panel:
            self._workspace_panel.display = view == "workspace"
        if self._dataset_panel:
            self._dataset_panel.display = view == "datasets"
        if self._sweep_panel:
            self._sweep_panel.display = view == "sweeps"
        if self._charts_panel:
            self._charts_panel.display = view == "charts"
            # Refresh charts when switching to the charts tab
            if view == "charts":
                self._charts_panel.refresh_charts()

    def _on_tab_change(self, tab: NavTab) -> None:
        """Handle navigation tab changes."""
        self._switch_view(tab)

    def _get_input_text(self) -> str:
        """Get the current input text for sweep/batch operations."""
        if self._workspace_panel:
            return str(self._workspace_panel.input_text)
        return str(self.store.snapshot.workspace.input_text)

    def _get_tokenizers(self) -> list[str]:
        """Get the current tokenizers for sweep/batch operations."""
        return list(self.store.snapshot.selections.tokenizers) or ["cl100k_base"]

    def _get_scan_results(self) -> dict[str, Any]:
        """Get scan results for charts."""
        state = self.store.snapshot
        return dict(state.metrics)

    def _get_sweep_results(self) -> list[Any]:
        """Get sweep results for charts."""
        if self._sweep_panel:
            return list(self._sweep_panel.results)
        return []

    def _get_dataset_results(self) -> dict[str, Any]:
        """Get dataset batch results for charts."""
        state = self.store.snapshot
        return dict(state.dataset.results)

    def _on_sample_selected(self, text: str, index: int, total: int) -> None:
        """Handle dataset sample selection."""
        if self._workspace_panel:
            self._workspace_panel.input_text = text
            self.store.update_from_thread(
                lambda state: replace(
                    state,
                    workspace=replace(state.workspace, input_text=text),
                )
            )
            # Switch to workspace view to show the sample
            if self._nav_panel:
                self._nav_panel._select_tab("workspace")
            self._switch_view("workspace")
            self.notify(f"Sample {index}/{total} loaded", severity="information")

    def _on_batch_requested(self, samples: list[str]) -> None:
        """Handle dataset batch processing request."""
        if not samples:
            return

        state = self.store.snapshot
        glitchlings = list(state.selections.glitchlings)
        tokenizers = list(state.selections.tokenizers) or ["cl100k_base"]
        seed = self._seed_control.seed if self._seed_control else state.selections.seed

        if self._dataset_panel:
            self._dataset_panel.set_batch_running(True, len(samples))

        # Run batch processing in background
        self.service.process_dataset(
            samples=samples,
            glitchlings_config=glitchlings,
            base_seed=seed,
            tokenizers=tokenizers,
            progress_callback=self._on_batch_progress,
            completion_callback=self._on_batch_complete,
            check_cancel=lambda: not (self._dataset_panel and self._dataset_panel.is_batch_running),
        )

    def _on_batch_progress(self, current: int, total: int) -> None:
        """Handle batch processing progress updates."""
        if self._dataset_panel:
            self.call_from_thread(self._dataset_panel.update_batch_progress, current, total)

    def _on_batch_complete(
        self,
        results: dict[str, Any],
        names: list[str],
        total: int,
        processed: int,
    ) -> None:
        """Handle batch processing completion."""
        if self._dataset_panel:
            tokenizers = list(results.keys())
            rows = self.service.format_scan_metrics(results)
            self.call_from_thread(
                self._dataset_panel.display_batch_results,
                tokenizers,
                rows,
                processed,
            )
            self.call_from_thread(self._dataset_panel.set_batch_running, False, 0)

        # Update state with results
        self.store.update_from_thread(
            lambda state: replace(
                state,
                dataset=replace(
                    state.dataset,
                    running=False,
                    processed=processed,
                    total=total,
                    results=results,
                ),
            )
        )

        self.call_from_thread(
            self.notify,
            f"Processed {processed}/{total} samples",
            severity="information",
        )

    def _on_sweep_results_changed(self) -> None:
        """Handle sweep results updates."""
        # Charts panel automatically fetches results via callback
        # No additional action needed here

    def on_unmount(self) -> None:
        # Save preferences before exit
        state = self.store.snapshot
        updated_prefs = state.preferences.with_updates(
            default_tokenizers=list(state.selections.tokenizers),
        )
        save_preferences(updated_prefs)

        for unsubscribe in reversed(self._unsubscribers):
            unsubscribe()
        self.worker.shutdown()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "transform-btn":
            self.action_run_transform()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        if event.checkbox.id == "auto-update":
            self.store.update_from_thread(
                lambda state: replace(
                    state,
                    selections=replace(state.selections, auto_update=event.value),
                )
            )

    def on_seed_control_multi_seed_changed(self, event: SeedControl.MultiSeedChanged) -> None:
        """Handle multi-seed settings changes."""
        self.store.update_from_thread(
            lambda state: replace(
                state,
                selections=replace(
                    state.selections,
                    multi_seed_mode=event.enabled,
                    multi_seed_count=event.count,
                ),
            )
        )

    def on_workspace_panel_input_changed(self, event: WorkspacePanel.InputChanged) -> None:
        """Handle input text changes from the workspace."""
        # Update store with new input text
        self.store.update_from_thread(
            lambda state: replace(
                state,
                workspace=replace(state.workspace, input_text=event.text),
            )
        )
        # Auto-update if enabled
        if self.store.snapshot.selections.auto_update:
            self.request_transform()

    def _on_glitchlings_change(
        self, configs: list[tuple[type[Glitchling], dict[str, Any]]]
    ) -> None:
        """Handle glitchling selection changes."""
        self.store.update_from_thread(
            lambda state: replace(
                state,
                selections=replace(state.selections, glitchlings=configs),
            )
        )
        # Auto-update if enabled
        if self.store.snapshot.selections.auto_update:
            self.request_transform()

    def _on_tokenizers_change(self, tokenizers: list[str]) -> None:
        """Handle tokenizer selection changes."""
        self.store.update_from_thread(
            lambda state: replace(
                state,
                selections=replace(state.selections, tokenizers=tokenizers),
            )
        )
        if self._workspace_panel:
            self._workspace_panel.set_tokenizers(tokenizers)

    def action_run_transform(self) -> None:
        self.request_transform()

    def action_randomize_seed(self) -> None:
        """Randomize the seed and trigger a transform."""
        new_seed = random.randint(0, 999999)
        if self._seed_control:
            self._seed_control.seed = new_seed
        self.store.update_from_thread(
            lambda state: replace(
                state,
                selections=replace(state.selections, seed=new_seed),
            )
        )
        self.request_transform()

    def action_copy_output(self) -> None:
        """Copy the output text to clipboard."""
        if self._workspace_panel and self._workspace_panel.output_text:
            try:
                import pyperclip

                pyperclip.copy(self._workspace_panel.output_text)
                self.notify("Output copied to clipboard", severity="information")
            except ImportError:
                self.notify("Clipboard not available (install pyperclip)", severity="warning")
        else:
            self.notify("No output to copy", severity="warning")

    def action_paste_input(self) -> None:
        """Paste clipboard content into the input area."""
        try:
            import pyperclip

            text = pyperclip.paste()
            if text and self._workspace_panel:
                self._workspace_panel.input_text = text
                self.store.update_from_thread(
                    lambda state: replace(
                        state,
                        workspace=replace(state.workspace, input_text=text),
                    )
                )
                self.notify("Text pasted from clipboard", severity="information")
        except ImportError:
            self.notify("Clipboard not available (install pyperclip)", severity="warning")
        except Exception as e:
            self.notify(f"Paste failed: {e}", severity="error")

    def action_clear_input(self) -> None:
        """Clear the input text area."""
        if self._workspace_panel:
            self._workspace_panel.action_clear_input()
            self.notify("Input cleared", severity="information")

    def action_new_session(self) -> None:
        """Start a new session (clear everything)."""
        if self._workspace_panel:
            self._workspace_panel.action_clear_input()
            self._workspace_panel.set_output("")
            self._workspace_panel.set_metrics({})
        self.notify("New session started", severity="information")

    def action_focus_input(self) -> None:
        """Focus the input text area."""
        if self._workspace_panel and self._workspace_panel._input_area:
            self._workspace_panel._input_area.focus()

    def action_export(self) -> None:
        """Open the export dialog for the current session."""
        state = self.store.snapshot
        input_text = self._workspace_panel.input_text if self._workspace_panel else ""
        output_text = self._workspace_panel.output_text if self._workspace_panel else ""

        if not output_text:
            self.notify("No output to export. Run a transform first.", severity="warning")
            return

        # Build glitchling config list for SessionConfig
        glitchling_config: list[tuple[str, dict[str, Any]]] = []
        for cls, params in state.selections.glitchlings:
            glitchling_config.append((cls.__name__, dict(params)))

        seed = self._seed_control.seed if self._seed_control else state.selections.seed

        # Create SessionConfig for export
        session_config = SessionConfig(
            glitchlings=glitchling_config,
            tokenizers=list(state.selections.tokenizers),
            seed=seed,
            auto_update=state.selections.auto_update,
            input_text=input_text,
        )

        # Create ExportData bundle
        export_data = ExportData(
            config=session_config,
            input_text=input_text,
            output_text=output_text,
            metrics=dict(state.metrics),
        )

        dialog = ExportDialog(
            export_data=export_data,
            on_file_save=self._save_file_callback,
        )
        self.push_screen(dialog)

    def action_export_sweep(self) -> None:
        """Open the sweep export dialog."""
        if not self._sweep_panel or not self._sweep_panel.results:
            self.notify("No sweep results to export. Run a sweep first.", severity="warning")
            return

        dialog = SweepExportDialog(
            sweep_results=list(self._sweep_panel.results),
            on_file_save=self._save_file_callback,
        )
        self.push_screen(dialog)

    def _save_file_callback(self, content: str, extension: str) -> Path | None:
        """Handle file save from export dialogs.

        This is a simple implementation that writes to a default location.
        A more complete implementation would use a file dialog.
        """
        # Generate a default filename
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"glitchlings_export_{timestamp}{extension}"

        # Try to find a reasonable save location
        try:
            # Use current working directory
            path = Path.cwd() / filename
            path.write_text(content, encoding="utf-8")
            return path
        except OSError:
            return None

    def request_transform(self, *, input_text: str | None = None) -> None:
        state = self.store.snapshot

        # Get current input from workspace panel
        text = input_text
        if text is None and self._workspace_panel:
            text = self._workspace_panel.input_text
        if text is None:
            text = state.workspace.input_text

        if not text.strip():
            self.notify("Provide input text to transform.", severity="warning")
            return

        # Get current seed from control
        seed = self._seed_control.seed if self._seed_control else state.selections.seed

        glitchlings = list(state.selections.glitchlings)
        tokenizers: Sequence[str] = (
            state.selections.tokenizers or state.preferences.default_tokenizers
        )

        self.bus.post(
            TransformRequested(
                input_text=text,
                glitchlings=glitchlings,
                tokenizers=tokenizers,
                seed=seed,
                diff_mode=state.workspace.diff_mode,
                diff_tokenizer=state.workspace.diff_tokenizer,
                multi_seed_mode=state.selections.multi_seed_mode,
                multi_seed_count=state.selections.multi_seed_count,
            )
        )

    async def _handle_transform_request(self, event: TransformRequested) -> None:
        await self.store.update(
            lambda state: replace(
                state,
                busy=True,
                status=StatusLine("Transforming...", "progress"),
                last_error=None,
            )
        )

        def _run() -> tuple[str, list[str], dict[str, dict[str, str]]]:
            glitchlings = list(event.glitchlings)
            tokenizers = list(event.tokenizers)

            if event.multi_seed_mode:
                output, names, metrics = self.service.transform_text_multi_seed(
                    event.input_text,
                    glitchlings,
                    event.seed,
                    event.multi_seed_count,
                    tokenizers,
                )
            else:
                output, names = self.service.transform_text(
                    event.input_text, glitchlings, event.seed
                )
                metrics = self.service.calculate_metrics(event.input_text, output, tokenizers)
            return output, names, metrics

        self.worker.run(
            "transform",
            _run,
            on_success=lambda result: TransformCompleted(
                output_text=result[0],
                glitchling_names=result[1],
                metrics=result[2],
                diff_tokenizer=event.diff_tokenizer,
                diff_mode=event.diff_mode,
            ),
            on_error=lambda exc: TransformFailed("Transform failed", exc),
        )

    async def _handle_transform_complete(self, event: TransformCompleted) -> None:
        message = (
            f"Transformed with: {', '.join(event.glitchling_names)}"
            if event.glitchling_names
            else "Output unchanged (no glitchlings selected)"
        )

        await self.store.update(
            lambda state: replace(
                state,
                busy=False,
                workspace=replace(state.workspace, output_text=event.output_text),
                metrics=dict(event.metrics),
                status=StatusLine(message, "success"),
                last_error=None,
            )
        )

        # Update the workspace panel with results
        if self._workspace_panel:
            self._workspace_panel.set_output(event.output_text)
            self._workspace_panel.set_metrics(event.metrics)

        # Show success toast
        if event.glitchling_names:
            self.notify(f"✓ {', '.join(event.glitchling_names)}", severity="information")

    async def _handle_transform_failed(self, event: TransformFailed) -> None:
        await self.store.update(
            lambda state: replace(
                state,
                busy=False,
                status=StatusLine(event.message, "error"),
                last_error=str(event.error or event.message),
            )
        )
        # Show error toast
        self.notify(f"Transform failed: {event.error}", severity="error")

    async def _handle_status_event(self, event: StatusEvent) -> None:
        await self.store.update(
            lambda state: replace(state, status=StatusLine(event.message, event.tone))
        )

    async def _on_state_change(self, state: AppState) -> None:
        if self.status_bar:
            self.status_bar.set_status(state.status, busy=state.busy)


if __name__ == "__main__":
    GlitchlingsTextualApp().run()
