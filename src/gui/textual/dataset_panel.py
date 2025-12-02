"""Dataset panel for the Textual GUI.

Supports loading from local files, HuggingFace datasets, and Project Gutenberg.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    ProgressBar,
    RadioButton,
    RadioSet,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from .theme import themed_css

CSS = """
DatasetPanel {
    width: 100%;
    height: 100%;
    overflow-y: auto;
}

DatasetPanel .dataset-content {
    height: 1fr;
    padding: 0;
}

DatasetPanel .section-panel {
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    margin-bottom: 1;
    height: auto;
}

DatasetPanel .section-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

DatasetPanel .section-title {
    color: var(--glitch-accent);
    text-style: bold;
    width: auto;
}

DatasetPanel .section-status {
    dock: right;
    color: var(--glitch-muted);
}

DatasetPanel .source-options {
    padding: 0 1;
    height: auto;
}

DatasetPanel RadioSet {
    layout: horizontal;
    height: auto;
    background: transparent;
    border: none;
}

DatasetPanel RadioButton {
    margin-right: 1;
    background: transparent;
}

DatasetPanel .source-config {
    padding: 0 1;
    border-top: solid var(--glitch-border);
    height: auto;
}

DatasetPanel .config-row {
    height: 2;
    layout: horizontal;
    align: left middle;
    padding: 0;
}

DatasetPanel .config-label {
    width: 10;
    color: var(--glitch-muted);
}

DatasetPanel .config-input {
    width: 1fr;
    max-width: 30;
}

DatasetPanel .config-input-small {
    width: 10;
}

DatasetPanel .load-controls {
    height: 3;
    padding: 0 1;
    layout: horizontal;
    align: left middle;
    border-top: solid var(--glitch-border);
}

DatasetPanel .load-btn {
    width: auto;
    min-width: 12;
    background: var(--glitch-bright);
    color: var(--glitch-bg);
}

DatasetPanel .load-btn:hover {
    background: var(--glitch-accent);
}

DatasetPanel .preview-panel {
    height: 1fr;
    min-height: 8;
}

DatasetPanel .nav-row {
    height: 3;
    padding: 0 1;
    layout: horizontal;
    align: left middle;
    border-bottom: solid var(--glitch-border);
}

DatasetPanel .nav-btn {
    width: 6;
    background: var(--glitch-surface);
    color: var(--glitch-muted);
    border: none;
}

DatasetPanel .nav-btn:hover {
    background: var(--glitch-border);
    color: var(--glitch-bright);
}

DatasetPanel .nav-index {
    width: 8;
    margin: 0 1;
}

DatasetPanel .nav-total {
    width: auto;
    margin-right: 1;
    color: var(--glitch-muted);
}

DatasetPanel .use-btn {
    dock: right;
    width: auto;
    min-width: 10;
    background: var(--glitch-bright);
    color: var(--glitch-bg);
}

DatasetPanel .preview-text {
    height: 1fr;
    min-height: 4;
    background: var(--glitch-bg);
    border: none;
}

DatasetPanel .batch-panel {
    height: auto;
    min-height: 10;
}

DatasetPanel .progress-row {
    height: 2;
    padding: 0 1;
    layout: horizontal;
    align: left middle;
}

DatasetPanel .batch-btn {
    width: auto;
    min-width: 14;
    margin-right: 1;
    background: var(--glitch-bright);
    color: var(--glitch-bg);
}

DatasetPanel .batch-btn.-running {
    background: var(--glitch-danger);
}

DatasetPanel ProgressBar {
    width: 1fr;
    height: 1;
}

DatasetPanel .results-table {
    height: 1fr;
    min-height: 4;
    padding: 0 1;
}

DatasetPanel OptionList {
    height: 1fr;
    background: var(--glitch-bg);
}
"""


class DatasetPanel(Static):  # type: ignore[misc]
    """Panel for loading datasets and running batch processing."""

    DEFAULT_CSS = themed_css(CSS)
    BINDINGS = [
        Binding("left", "prev_sample", "Previous", show=False),
        Binding("right", "next_sample", "Next", show=False),
        Binding("enter", "use_sample", "Use Sample", show=False),
    ]

    class SampleSelected(Message):  # type: ignore[misc]
        """Posted when a sample is selected for use."""

        def __init__(self, text: str, index: int, total: int) -> None:
            super().__init__()
            self.text = text
            self.index = index
            self.total = total

    class DatasetLoaded(Message):  # type: ignore[misc]
        """Posted when dataset loading completes."""

        def __init__(self, samples: list[str]) -> None:
            super().__init__()
            self.samples = samples

    class BatchRequested(Message):  # type: ignore[misc]
        """Posted when batch processing is requested."""

        def __init__(self, samples: list[str]) -> None:
            super().__init__()
            self.samples = samples

    class BatchCancelled(Message):  # type: ignore[misc]
        """Posted when batch processing is cancelled."""

        pass

    def __init__(
        self,
        *,
        on_sample_selected: Callable[[str, int, int], None] | None = None,
        on_batch_requested: Callable[[list[str]], None] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._on_sample_selected = on_sample_selected
        self._on_batch_requested = on_batch_requested

        # State
        self._samples: list[str] = []
        self._current_index: int = 0
        self._loading: bool = False
        self._batch_running: bool = False

        # Widget refs
        self._source_set: RadioSet | None = None
        self._local_path_input: Input | None = None
        self._hf_dataset_input: Input | None = None
        self._hf_split_input: Input | None = None
        self._hf_field_input: Input | None = None
        self._gutenberg_id_input: Input | None = None
        self._sample_size_input: Input | None = None
        self._status_label: Static | None = None
        self._load_btn: Button | None = None
        self._prev_btn: Button | None = None
        self._next_btn: Button | None = None
        self._index_input: Input | None = None
        self._total_label: Static | None = None
        self._use_btn: Button | None = None
        self._preview_area: TextArea | None = None
        self._batch_btn: Button | None = None
        self._progress_bar: ProgressBar | None = None
        self._batch_status: Static | None = None
        self._results_list: OptionList | None = None

        # Source config containers
        self._local_config: Container | None = None
        self._hf_config: Container | None = None
        self._gutenberg_config: Container | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="dataset-content"):
            # Source selection panel
            with Container(classes="section-panel"):
                with Horizontal(classes="section-header"):
                    yield Label("▓▒░ DATASET SOURCE ░▒▓", classes="section-title")
                    self._status_label = Static("No dataset loaded", classes="section-status")
                    yield self._status_label

                with Container(classes="source-options"):
                    self._source_set = RadioSet(
                        RadioButton("Local Files", id="source-local", value=True),
                        RadioButton("HuggingFace", id="source-hf"),
                        RadioButton("Gutenberg", id="source-gutenberg"),
                        id="source-set",
                    )
                    yield self._source_set

                # Local file config
                self._local_config = Container(classes="source-config", id="local-config")
                with self._local_config:
                    with Horizontal(classes="config-row"):
                        yield Label("Path:", classes="config-label")
                        self._local_path_input = Input(
                            placeholder="Enter file path...",
                            id="local-path",
                            classes="config-input",
                        )
                        yield self._local_path_input

                # HuggingFace config
                self._hf_config = Container(classes="source-config", id="hf-config")
                with self._hf_config:
                    with Horizontal(classes="config-row"):
                        yield Label("Dataset:", classes="config-label")
                        self._hf_dataset_input = Input(
                            placeholder="e.g., imdb, squad",
                            id="hf-dataset",
                            classes="config-input",
                        )
                        yield self._hf_dataset_input
                    with Horizontal(classes="config-row"):
                        yield Label("Split:", classes="config-label")
                        self._hf_split_input = Input(
                            value="train",
                            id="hf-split",
                            classes="config-input-small",
                        )
                        yield self._hf_split_input
                        yield Label("  Field:", classes="config-label")
                        self._hf_field_input = Input(
                            value="text",
                            id="hf-field",
                            classes="config-input-small",
                        )
                        yield self._hf_field_input

                # Gutenberg config
                self._gutenberg_config = Container(classes="source-config", id="gutenberg-config")
                with self._gutenberg_config:
                    with Horizontal(classes="config-row"):
                        yield Label("Book ID:", classes="config-label")
                        self._gutenberg_id_input = Input(
                            placeholder="e.g., 1342",
                            id="gutenberg-id",
                            classes="config-input",
                        )
                        yield self._gutenberg_id_input

                # Load controls
                with Horizontal(classes="load-controls"):
                    yield Label("Sample Size:", classes="config-label")
                    self._sample_size_input = Input(
                        value="100",
                        id="sample-size",
                        classes="config-input-small",
                    )
                    yield self._sample_size_input
                    self._load_btn = Button("▶ LOAD DATASET", id="load-btn", classes="load-btn")
                    yield self._load_btn

            # Preview panel
            with Container(classes="section-panel preview-panel"):
                with Horizontal(classes="section-header"):
                    yield Label("PREVIEW", classes="section-title")

                with Horizontal(classes="nav-row"):
                    self._prev_btn = Button("◀ Prev", id="prev-btn", classes="nav-btn")
                    yield self._prev_btn
                    self._index_input = Input(value="1", id="index-input", classes="nav-index")
                    yield self._index_input
                    self._total_label = Static("/ 0", classes="nav-total")
                    yield self._total_label
                    self._next_btn = Button("Next ▶", id="next-btn", classes="nav-btn")
                    yield self._next_btn
                    self._use_btn = Button("▶ Use Sample", id="use-btn", classes="use-btn")
                    yield self._use_btn

                self._preview_area = TextArea(
                    read_only=True, id="preview-area", classes="preview-text"
                )
                yield self._preview_area

            # Batch processing panel
            with Container(classes="section-panel batch-panel"):
                with Horizontal(classes="section-header"):
                    yield Label("BATCH METRICS", classes="section-title")
                    self._batch_status = Static("Idle", classes="section-status")
                    yield self._batch_status

                with Horizontal(classes="progress-row"):
                    self._batch_btn = Button(
                        "▶ PROCESS DATASET", id="batch-btn", classes="batch-btn"
                    )
                    yield self._batch_btn
                    self._progress_bar = ProgressBar(total=100, show_eta=False, id="batch-progress")
                    yield self._progress_bar

                self._results_list = OptionList(id="results-list", classes="results-table")
                yield self._results_list

    def on_mount(self) -> None:
        """Initialize UI state on mount."""
        self._show_source_config("local")
        self._update_nav_state()
        self._show_empty_preview()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle source selection changes."""
        if event.radio_set.id == "source-set":
            btn_id = event.pressed.id if event.pressed else None
            if btn_id == "source-local":
                self._show_source_config("local")
            elif btn_id == "source-hf":
                self._show_source_config("hf")
            elif btn_id == "source-gutenberg":
                self._show_source_config("gutenberg")

    def _show_source_config(self, source: str) -> None:
        """Show/hide source configuration panels."""
        if self._local_config:
            self._local_config.display = source == "local"
        if self._hf_config:
            self._hf_config.display = source == "hf"
        if self._gutenberg_config:
            self._gutenberg_config.display = source == "gutenberg"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id
        if btn_id == "load-btn":
            self._start_load()
        elif btn_id == "prev-btn":
            self.action_prev_sample()
        elif btn_id == "next-btn":
            self.action_next_sample()
        elif btn_id == "use-btn":
            self.action_use_sample()
        elif btn_id == "batch-btn":
            self._toggle_batch()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)."""
        if event.input.id == "index-input":
            self._jump_to_sample()

    def _start_load(self) -> None:
        """Start loading the dataset."""
        if self._loading:
            return

        # Get sample size
        try:
            sample_size = int(self._sample_size_input.value if self._sample_size_input else "100")
        except ValueError:
            self._set_status("Invalid sample size", "error")
            return

        # Determine source
        source = self._get_selected_source()

        self._loading = True
        self._set_status("Loading...", "progress")
        if self._load_btn:
            self._load_btn.label = "Loading..."
            self._load_btn.disabled = True

        # Run in worker
        self.run_worker(
            self._load_dataset_worker(source, sample_size),
            name="load_dataset",
            exclusive=True,
        )

    def _get_selected_source(self) -> str:
        """Get the currently selected source type."""
        if self._source_set and self._source_set.pressed_button:
            btn_id = self._source_set.pressed_button.id
            if btn_id == "source-hf":
                return "hf"
            elif btn_id == "source-gutenberg":
                return "gutenberg"
        return "local"

    async def _load_dataset_worker(self, source: str, sample_size: int) -> list[str]:
        """Worker that loads the dataset."""
        if source == "local":
            return await self._load_local(sample_size)
        elif source == "hf":
            return await self._load_huggingface(sample_size)
        elif source == "gutenberg":
            return await self._load_gutenberg(sample_size)
        return []

    async def _load_local(self, sample_size: int) -> list[str]:
        """Load from local file."""
        path_str = self._local_path_input.value if self._local_path_input else ""
        if not path_str:
            raise ValueError("No file path provided")

        path = Path(path_str)
        if not path.exists():
            raise ValueError(f"File not found: {path}")

        text = path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs[:sample_size]

    async def _load_huggingface(self, sample_size: int) -> list[str]:
        """Load from HuggingFace datasets."""
        dataset_name = self._hf_dataset_input.value if self._hf_dataset_input else ""
        if not dataset_name:
            raise ValueError("No dataset name provided")

        try:
            from datasets import load_dataset
        except ImportError as e:
            raise ValueError(
                "HuggingFace datasets not available. Install with: pip install datasets"
            ) from e

        split = self._hf_split_input.value if self._hf_split_input else "train"
        text_field = self._hf_field_input.value if self._hf_field_input else "text"

        dataset = load_dataset(dataset_name, split=split, streaming=True)

        samples: list[str] = []
        for i, item in enumerate(dataset):
            if i >= sample_size:
                break
            if text_field in item:
                samples.append(str(item[text_field]))

        if not samples:
            raise ValueError(f"No samples found with field '{text_field}'")

        return samples

    async def _load_gutenberg(self, sample_size: int) -> list[str]:
        """Load from Project Gutenberg."""
        book_id = self._gutenberg_id_input.value if self._gutenberg_id_input else ""
        if not book_id:
            raise ValueError("No book ID provided")

        try:
            from glitchlings.dlc.gutenberg import GlitchenbergAPI
        except ImportError as e:
            raise ValueError("Gutenberg support not available") from e

        try:
            book_id_int = int(book_id)
        except ValueError as e:
            raise ValueError(f"Invalid book ID: {book_id}") from e

        # Use identity (no corruption) to just fetch raw text
        api = GlitchenbergAPI([], seed=42)  # Empty gaggle = no corruption
        book = api.get_book(book_id_int)
        text = book.get_text()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs[:sample_size]

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker.name == "load_dataset":
            if event.state == WorkerState.SUCCESS:
                samples = event.worker.result
                self._on_load_complete(samples, None)
            elif event.state == WorkerState.ERROR:
                self._on_load_complete([], str(event.worker.error))
            elif event.state == WorkerState.CANCELLED:
                self._on_load_complete([], "Cancelled")

    def _on_load_complete(self, samples: list[str], error: str | None) -> None:
        """Handle load completion."""
        self._loading = False
        if self._load_btn:
            self._load_btn.label = "▶ LOAD DATASET"
            self._load_btn.disabled = False

        if error:
            self._set_status(f"Error: {error}", "error")
            self.app.notify(f"Load failed: {error}", severity="error")
            return

        self._samples = samples
        self._current_index = 0
        self._set_status(f"{len(samples)} samples loaded", "success")

        self._update_nav_state()
        if samples:
            self._show_sample(0)

        self.post_message(self.DatasetLoaded(samples))
        self.app.notify(f"Loaded {len(samples)} samples", severity="information")

    def _show_sample(self, index: int) -> None:
        """Display a specific sample."""
        if not self._samples:
            self._show_empty_preview()
            return

        clamped = max(0, min(index, len(self._samples) - 1))
        self._current_index = clamped
        sample = self._samples[clamped]

        if self._preview_area:
            self._preview_area.text = f"[{clamped + 1}] {sample}"

        self._update_nav_state()

    def _show_empty_preview(self) -> None:
        """Show empty state in preview."""
        if self._preview_area:
            self._preview_area.text = (
                "No samples loaded.\n\n"
                "Load a dataset to browse individual samples.\n"
                "Use the navigation controls to move between them."
            )

    def _update_nav_state(self) -> None:
        """Update navigation controls state."""
        total = len(self._samples)
        has_samples = total > 0

        if self._prev_btn:
            self._prev_btn.disabled = not has_samples or self._current_index <= 0
        if self._next_btn:
            self._next_btn.disabled = not has_samples or self._current_index >= total - 1
        if self._use_btn:
            self._use_btn.disabled = not has_samples
        if self._index_input:
            self._index_input.value = str(self._current_index + 1 if has_samples else 1)
            self._index_input.disabled = not has_samples
        if self._total_label:
            self._total_label.update(f"/ {total}")

    def action_prev_sample(self) -> None:
        """Navigate to previous sample."""
        if self._samples and self._current_index > 0:
            self._show_sample(self._current_index - 1)

    def action_next_sample(self) -> None:
        """Navigate to next sample."""
        if self._samples and self._current_index < len(self._samples) - 1:
            self._show_sample(self._current_index + 1)

    def _jump_to_sample(self) -> None:
        """Jump to sample by index."""
        if not self._samples:
            return

        try:
            target = int(self._index_input.value if self._index_input else "1") - 1
        except ValueError:
            self._update_nav_state()
            return

        self._show_sample(target)

    def action_use_sample(self) -> None:
        """Use the current sample."""
        if not self._samples:
            return

        sample = self._samples[self._current_index]
        if self._on_sample_selected:
            self._on_sample_selected(sample, self._current_index + 1, len(self._samples))

        self.post_message(self.SampleSelected(sample, self._current_index + 1, len(self._samples)))

    def _toggle_batch(self) -> None:
        """Toggle batch processing."""
        if not self._samples:
            self._set_batch_status("Load a dataset first")
            return

        if self._batch_running:
            self._batch_running = False
            self.post_message(self.BatchCancelled())
        else:
            self._batch_running = True
            if self._batch_btn:
                self._batch_btn.label = "■ CANCEL"
                self._batch_btn.add_class("-running")
            if self._on_batch_requested:
                self._on_batch_requested(list(self._samples))
            self.post_message(self.BatchRequested(list(self._samples)))

    def set_batch_running(self, running: bool, total: int = 0) -> None:
        """Update batch processing state."""
        self._batch_running = running
        if self._progress_bar:
            self._progress_bar.total = max(1, total)
            self._progress_bar.progress = 0

        if running:
            if self._batch_btn:
                self._batch_btn.label = "■ CANCEL"
                self._batch_btn.add_class("-running")
            self._set_batch_status("Processing...")
        else:
            if self._batch_btn:
                self._batch_btn.label = "▶ PROCESS DATASET"
                self._batch_btn.remove_class("-running")

    def update_batch_progress(self, current: int, total: int) -> None:
        """Update batch progress."""
        if self._progress_bar:
            self._progress_bar.total = max(1, total)
            self._progress_bar.progress = current
        self._set_batch_status(f"{current}/{total} processed")

    def display_batch_results(
        self,
        tokenizers: list[str],
        rows: list[tuple[str, list[str]]],
        processed: int,
    ) -> None:
        """Display aggregated batch results."""
        if self._results_list:
            self._results_list.clear_options()

            if not rows:
                self._results_list.add_option(Option("No metrics produced"))
                return

            # Header row
            header = "Metric".ljust(24) + "".join(t.ljust(16) for t in tokenizers)
            self._results_list.add_option(Option(header))
            self._results_list.add_option(Option("─" * len(header)))

            for metric_name, values in rows:
                row = metric_name.ljust(24) + "".join(v.ljust(16) for v in values)
                self._results_list.add_option(Option(row))

        self._set_batch_status(f"Aggregated {processed} samples")

    def reset_batch_results(self) -> None:
        """Clear batch results."""
        self._batch_running = False
        if self._progress_bar:
            self._progress_bar.progress = 0
        if self._batch_btn:
            self._batch_btn.label = "▶ PROCESS DATASET"
            self._batch_btn.remove_class("-running")
        if self._results_list:
            self._results_list.clear_options()
        self._set_batch_status("Idle")

    def _set_status(self, message: str, tone: str = "info") -> None:
        """Update the status label."""
        if self._status_label:
            style = {
                "info": "var(--glitch-muted)",
                "success": "var(--glitch-bright)",
                "error": "var(--glitch-danger)",
                "progress": "var(--glitch-warn)",
            }.get(tone, "var(--glitch-muted)")
            self._status_label.update(Text(message, style=style))

    def _set_batch_status(self, message: str) -> None:
        """Update the batch status label."""
        if self._batch_status:
            self._batch_status.update(message)

    def get_samples(self) -> list[str]:
        """Return currently loaded samples."""
        return self._samples

    @property
    def is_batch_running(self) -> bool:
        """Whether batch processing is running."""
        return self._batch_running
