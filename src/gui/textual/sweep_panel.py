"""Parameter sweep panel for the Textual GUI.

Supports sweeping glitchling parameters across a range of values.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    OptionList,
    ProgressBar,
    Select,
    Static,
)
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from glitchlings.zoo import Gaggle

from .definitions import AVAILABLE_GLITCHLINGS, GLITCHLING_PARAMS
from .theme import themed_css

CSS = """
SweepPanel {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

SweepPanel .sweep-content {
    height: 100%;
    padding: 0;
    overflow-y: auto;
}

SweepPanel .section-panel {
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    margin-bottom: 1;
    height: auto;
}

SweepPanel .section-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

SweepPanel .section-title {
    color: var(--glitch-accent);
    text-style: bold;
    width: auto;
}

SweepPanel .config-section {
    padding: 0 1;
    height: auto;
}

SweepPanel .config-row {
    height: 2;
    layout: horizontal;
    align: left middle;
    padding: 0;
}

SweepPanel .config-label {
    width: 10;
    color: var(--glitch-muted);
}

SweepPanel .config-input {
    width: 10;
    margin-right: 1;
}

SweepPanel Select {
    width: 16;
}

SweepPanel .glitchling-list {
    height: 8;
    max-height: 10;
    padding: 0 1;
    background: var(--glitch-bg);
    border: solid var(--glitch-border);
    overflow-y: auto;
}

SweepPanel .glitchling-check {
    margin-bottom: 0;
}

SweepPanel .select-buttons {
    height: 2;
    layout: horizontal;
    padding: 0 1;
}

SweepPanel .select-btn {
    width: auto;
    min-width: 6;
    margin-right: 1;
    background: var(--glitch-surface);
    color: var(--glitch-muted);
    border: none;
}

SweepPanel .select-btn:hover {
    color: var(--glitch-bright);
}

SweepPanel .run-controls {
    height: 3;
    padding: 0 1;
    layout: horizontal;
    align: left middle;
    border-top: solid var(--glitch-border);
}

SweepPanel .run-btn {
    width: auto;
    min-width: 10;
    background: var(--glitch-bright);
    color: var(--glitch-bg);
}

SweepPanel .run-btn:hover {
    background: var(--glitch-accent);
}

SweepPanel .run-btn.-running {
    background: var(--glitch-danger);
}

SweepPanel .export-btn {
    width: auto;
    min-width: 8;
    margin-left: 1;
    background: var(--glitch-surface);
    color: var(--glitch-muted);
}

SweepPanel .export-btn:hover {
    color: var(--glitch-bright);
}

SweepPanel .progress-section {
    padding: 0 1;
    height: auto;
}

SweepPanel ProgressBar {
    width: 1fr;
    height: 1;
}

SweepPanel .progress-label {
    height: 1;
    color: var(--glitch-muted);
}

SweepPanel .results-panel {
    height: 1fr;
    min-height: 12;
}

SweepPanel .results-table {
    height: 1fr;
    padding: 0 1;
}

SweepPanel OptionList {
    height: 1fr;
    background: var(--glitch-bg);
}
"""


@dataclass
class SweepPoint:
    """Results for a single sweep point."""

    param_value: float
    metrics: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    glitchling_names: list[str] = field(default_factory=list)
    parameter_name: str = ""


@dataclass
class SweepConfig:
    """Configuration for a parameter sweep."""

    glitchling_names: list[str]
    parameter_name: str
    start: float
    end: float
    step: float
    seeds_per_point: int = 10


class SweepPanel(Static):  # type: ignore[misc]
    """Panel for running parameter sweeps."""

    DEFAULT_CSS = themed_css(CSS)
    BINDINGS = [
        Binding("f5", "run_sweep", "Run Sweep", show=False),
    ]

    class SweepRequested(Message):  # type: ignore[misc]
        """Posted when a sweep is requested."""

        def __init__(self, config: SweepConfig) -> None:
            super().__init__()
            self.config = config

    class SweepCancelled(Message):  # type: ignore[misc]
        """Posted when sweep is cancelled."""

        pass

    class SweepCompleted(Message):  # type: ignore[misc]
        """Posted when sweep completes."""

        def __init__(self, results: list[SweepPoint]) -> None:
            super().__init__()
            self.results = results

    def __init__(
        self,
        *,
        get_input_text: Callable[[], str] | None = None,
        get_tokenizers: Callable[[], list[str]] | None = None,
        service: Any = None,
        on_results_changed: Callable[[], None] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._get_input_text = get_input_text
        self._get_tokenizers = get_tokenizers
        self._service = service
        self._on_results_changed = on_results_changed

        # State
        self._running: bool = False
        self._results: list[SweepPoint] = []
        self._glitchling_vars: dict[str, bool] = {
            cls.__name__: False for cls in AVAILABLE_GLITCHLINGS
        }
        if AVAILABLE_GLITCHLINGS:
            self._glitchling_vars[AVAILABLE_GLITCHLINGS[0].__name__] = True

        # Widget refs
        self._glitchling_container: Container | None = None
        self._param_select: Select[str] | None = None
        self._start_input: Input | None = None
        self._end_input: Input | None = None
        self._step_input: Input | None = None
        self._seeds_input: Input | None = None
        self._run_btn: Button | None = None
        self._export_btn: Button | None = None
        self._progress_bar: ProgressBar | None = None
        self._progress_label: Static | None = None
        self._results_list: OptionList | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="sweep-content"):
            # Configuration panel
            with Container(classes="section-panel"):
                with Horizontal(classes="section-header"):
                    yield Label("▓▒░ PARAMETER SWEEP ░▒▓", classes="section-title")

                with Container(classes="config-section"):
                    # Glitchling selection
                    with Horizontal(classes="config-row"):
                        yield Label("Glitchlings:", classes="config-label")

                    self._glitchling_container = Container(classes="glitchling-list")
                    with self._glitchling_container:
                        for cls in AVAILABLE_GLITCHLINGS:
                            name = cls.__name__
                            yield Checkbox(
                                name,
                                value=self._glitchling_vars.get(name, False),
                                id=f"glitch-{name}",
                                classes="glitchling-check",
                            )

                    with Horizontal(classes="select-buttons"):
                        yield Button("All", id="select-all", classes="select-btn")
                        yield Button("None", id="select-none", classes="select-btn")

                    # Parameter selection
                    with Horizontal(classes="config-row"):
                        yield Label("Parameter:", classes="config-label")
                        self._param_select = Select(
                            [],
                            id="param-select",
                            allow_blank=True,
                        )
                        yield self._param_select

                    # Range configuration
                    with Horizontal(classes="config-row"):
                        yield Label("Range:", classes="config-label")
                        self._start_input = Input(
                            value="0.0", id="start-input", classes="config-input"
                        )
                        yield self._start_input
                        yield Label("to", classes="config-label")
                        self._end_input = Input(value="1.0", id="end-input", classes="config-input")
                        yield self._end_input
                        yield Label("step", classes="config-label")
                        self._step_input = Input(
                            value="0.1", id="step-input", classes="config-input"
                        )
                        yield self._step_input

                    # Seeds per point
                    with Horizontal(classes="config-row"):
                        yield Label("Seeds/point:", classes="config-label")
                        self._seeds_input = Input(
                            value="10", id="seeds-input", classes="config-input"
                        )
                        yield self._seeds_input

                # Run controls
                with Horizontal(classes="run-controls"):
                    self._run_btn = Button("▶ RUN SWEEP", id="run-btn", classes="run-btn")
                    yield self._run_btn
                    self._export_btn = Button(
                        "⬇ Export", id="export-btn", classes="export-btn", disabled=True
                    )
                    yield self._export_btn

                # Progress
                with Container(classes="progress-section"):
                    self._progress_bar = ProgressBar(total=100, show_eta=False, id="sweep-progress")
                    yield self._progress_bar
                    self._progress_label = Static("", classes="progress-label")
                    yield self._progress_label

            # Results panel
            with Container(classes="section-panel results-panel"):
                with Horizontal(classes="section-header"):
                    yield Label("SWEEP RESULTS", classes="section-title")

                self._results_list = OptionList(id="results-list", classes="results-table")
                yield self._results_list

    def on_mount(self) -> None:
        """Initialize UI state on mount."""
        self._update_param_options()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle glitchling checkbox changes."""
        if event.checkbox.id and event.checkbox.id.startswith("glitch-"):
            name = event.checkbox.id.replace("glitch-", "")
            self._glitchling_vars[name] = event.value
            self._update_param_options()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id
        if btn_id == "select-all":
            self._select_all_glitchlings(True)
        elif btn_id == "select-none":
            self._select_all_glitchlings(False)
        elif btn_id == "run-btn":
            self._toggle_sweep()
        elif btn_id == "export-btn":
            self._export_results()

    def _select_all_glitchlings(self, selected: bool) -> None:
        """Select or deselect all glitchlings."""
        for name in self._glitchling_vars:
            self._glitchling_vars[name] = selected

        if self._glitchling_container:
            for checkbox in self._glitchling_container.query(Checkbox):
                checkbox.value = selected

        self._update_param_options()

    def _get_selected_glitchlings(self) -> list[str]:
        """Get list of selected glitchling names."""
        return [name for name, selected in self._glitchling_vars.items() if selected]

    def _update_param_options(self) -> None:
        """Update parameter dropdown based on selected glitchlings."""
        selected = self._get_selected_glitchlings()

        if not selected:
            if self._param_select:
                self._param_select.set_options([])
            return

        # Find parameters common to all selected glitchlings
        common_params: set[str] | None = None
        for name in selected:
            params = GLITCHLING_PARAMS.get(name, {})
            numeric_params = {
                pname for pname, info in params.items() if info.get("type") in ("float", "int")
            }
            if common_params is None:
                common_params = numeric_params
            else:
                common_params &= numeric_params

        param_list = sorted(common_params) if common_params else []

        if self._param_select:
            current = self._param_select.value
            self._param_select.set_options([(p, p) for p in param_list])

            if param_list:
                if current not in param_list:
                    self._param_select.value = param_list[0]
                    # Update range based on first glitchling's param info
                    self._update_range_defaults(selected[0], param_list[0])
            else:
                self._param_select.value = Select.BLANK

    def _update_range_defaults(self, glitchling_name: str, param_name: str) -> None:
        """Update range inputs with default values for the parameter."""
        param_info = GLITCHLING_PARAMS.get(glitchling_name, {}).get(param_name, {})
        if self._start_input:
            self._start_input.value = str(param_info.get("min", 0.0))
        if self._end_input:
            self._end_input.value = str(param_info.get("max", 1.0))

    def on_select_changed(self, event: Select.Changed[str]) -> None:
        """Handle parameter selection change."""
        if event.select.id == "param-select" and event.value != Select.BLANK:
            selected = self._get_selected_glitchlings()
            if selected:
                self._update_range_defaults(selected[0], str(event.value))

    def _toggle_sweep(self) -> None:
        """Toggle sweep running state."""
        if self._running:
            self._running = False
            self.post_message(self.SweepCancelled())
            return

        # Validate inputs
        input_text = self._get_input_text() if self._get_input_text else ""
        if not input_text:
            self.app.notify("Provide input text to sweep", severity="warning")
            return

        selected = self._get_selected_glitchlings()
        if not selected:
            self.app.notify("Select at least one glitchling", severity="warning")
            return

        param_name = str(self._param_select.value) if self._param_select else ""
        if not param_name or param_name == str(Select.BLANK):
            self.app.notify("Select a parameter to sweep", severity="warning")
            return

        try:
            start = float(self._start_input.value if self._start_input else "0")
            end = float(self._end_input.value if self._end_input else "1")
            step = float(self._step_input.value if self._step_input else "0.1")
            seeds = int(self._seeds_input.value if self._seeds_input else "10")
        except ValueError:
            self.app.notify("Invalid range values", severity="error")
            return

        if step <= 0 or start >= end:
            self.app.notify("Invalid range: step must be > 0 and start < end", severity="error")
            return

        config = SweepConfig(
            glitchling_names=selected,
            parameter_name=param_name,
            start=start,
            end=end,
            step=step,
            seeds_per_point=seeds,
        )

        self._running = True
        self._results = []
        if self._run_btn:
            self._run_btn.label = "■ CANCEL"
            self._run_btn.add_class("-running")
        if self._results_list:
            self._results_list.clear_options()
        if self._progress_label:
            self._progress_label.update("Starting sweep...")

        self.post_message(self.SweepRequested(config))

        # Run sweep in worker
        tokenizers = self._get_tokenizers() if self._get_tokenizers else ["cl100k_base"]
        self.run_worker(
            self._sweep_worker(input_text, config, tokenizers),
            name="sweep",
            exclusive=True,
        )

    async def _sweep_worker(
        self,
        input_text: str,
        config: SweepConfig,
        tokenizers: list[str],
    ) -> list[SweepPoint]:
        """Worker that runs the parameter sweep."""
        # Calculate sweep points
        points: list[float] = []
        current = config.start
        while current <= config.end + 0.0001:
            points.append(round(current, 4))
            current += config.step

        total = len(points) * config.seeds_per_point
        results: list[SweepPoint] = []

        # Find glitchling classes
        glitchling_classes: list[type] = []
        for cls in AVAILABLE_GLITCHLINGS:
            if cls.__name__ in config.glitchling_names:
                glitchling_classes.append(cls)

        for i, param_value in enumerate(points):
            if not self._running:
                break

            point_metrics: dict[str, dict[str, list[float]]] = {}

            for seed_offset in range(config.seeds_per_point):
                if not self._running:
                    break

                seed = 42 + seed_offset

                # Create glitchlings with this parameter value
                glitchlings = []
                for cls in glitchling_classes:
                    cls_params = GLITCHLING_PARAMS.get(cls.__name__, {})
                    if config.parameter_name in cls_params:
                        glitchling = cls(seed=seed, **{config.parameter_name: param_value})
                    else:
                        glitchling = cls(seed=seed)
                    glitchlings.append(glitchling)

                gaggle = Gaggle(glitchlings, seed=seed)
                output = str(gaggle.corrupt(input_text))

                # Calculate metrics
                if self._service:
                    metrics = self._service.calculate_metrics(input_text, output, tokenizers)

                    for tok_name, tok_metrics in metrics.items():
                        if tok_name not in point_metrics:
                            point_metrics[tok_name] = {"jsd": [], "ned": [], "sr": []}

                        for metric in ["jsd", "ned", "sr"]:
                            val = tok_metrics.get(metric, "-")
                            if val != "-":
                                try:
                                    point_metrics[tok_name][metric].append(float(val))
                                except (ValueError, TypeError):
                                    pass

                # Update progress
                progress = ((i * config.seeds_per_point + seed_offset + 1) / total) * 100
                self.call_from_thread(
                    self._update_progress,
                    progress,
                    i + 1,
                    len(points),
                    seed_offset + 1,
                    config.seeds_per_point,
                )

            # Store results
            sweep_point = SweepPoint(
                param_value=param_value,
                metrics=point_metrics,
                glitchling_names=config.glitchling_names,
                parameter_name=config.parameter_name,
            )
            results.append(sweep_point)

            # Add row to results table
            self.call_from_thread(self._add_result_row, sweep_point)

        return results

    def _update_progress(
        self,
        percent: float,
        point: int,
        total_points: int,
        seed: int,
        total_seeds: int,
    ) -> None:
        """Update progress display."""
        if self._progress_bar:
            self._progress_bar.progress = percent
        if self._progress_label:
            self._progress_label.update(f"Point {point}/{total_points} · Seed {seed}/{total_seeds}")

    def _add_result_row(self, point: SweepPoint) -> None:
        """Add a row to the results table."""
        if not point.metrics or not self._results_list:
            return

        # Aggregate across tokenizers (use first tokenizer)
        first_tok = next(iter(point.metrics.values()), {})

        def fmt(values: list[float]) -> str:
            if not values:
                return "-"
            mean = statistics.mean(values)
            if len(values) > 1:
                std = statistics.stdev(values)
                return f"{mean:.4f} ± {std:.4f}"
            return f"{mean:.4f}"

        jsd = fmt(first_tok.get("jsd", []))
        ned = fmt(first_tok.get("ned", []))
        sr = fmt(first_tok.get("sr", []))

        row = f"{point.param_value:.3f}".ljust(10) + jsd.ljust(18) + ned.ljust(18) + sr.ljust(18)
        self._results_list.add_option(Option(row))
        self._results.append(point)

        if self._on_results_changed:
            self._on_results_changed()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker.name == "sweep":
            done_states = (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED)
            if event.state in done_states:
                result = event.worker.result if event.state == WorkerState.SUCCESS else []
                self._on_sweep_complete(result)

    def _on_sweep_complete(self, results: list[SweepPoint]) -> None:
        """Handle sweep completion."""
        self._running = False
        self._results = results

        if self._run_btn:
            self._run_btn.label = "▶ RUN SWEEP"
            self._run_btn.remove_class("-running")

        if self._progress_label:
            self._progress_label.update(f"Complete · {len(results)} points")

        if self._export_btn:
            self._export_btn.disabled = not results

        self.post_message(self.SweepCompleted(results))

        if self._on_results_changed:
            self._on_results_changed()

    def action_run_sweep(self) -> None:
        """Action to start sweep."""
        self._toggle_sweep()

    def _export_results(self) -> None:
        """Export sweep results."""
        if not self._results:
            return

        # For now, just notify - full export dialog can be added later
        self.app.notify(f"Export {len(self._results)} sweep points", severity="information")

    def get_results(self) -> list[SweepPoint]:
        """Return current sweep results."""
        return self._results

    @property
    def results(self) -> list[SweepPoint]:
        """Current sweep results."""
        return self._results

    @property
    def is_running(self) -> bool:
        """Whether a sweep is currently running."""
        return self._running

    def set_results_header(self) -> None:
        """Set up the results table header."""
        if self._results_list:
            self._results_list.clear_options()
            header = "Param".ljust(10) + "JSD".ljust(18) + "NED".ljust(18) + "SR".ljust(18)
            self._results_list.add_option(Option(header))
            self._results_list.add_option(Option("─" * 64))
