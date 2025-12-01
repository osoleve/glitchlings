import random
from typing import TYPE_CHECKING, Dict, List

from .model import ScanResult, SessionState
from .service import GlitchlingService

if TYPE_CHECKING:
    from .views.main_window import MainFrame


class Controller:
    def __init__(self, model: SessionState, service: GlitchlingService):
        self.model = model
        self.service = service
        self.view: MainFrame | None = None  # Will be set after view creation

    def set_view(self, view: "MainFrame") -> None:
        self.view = view

    def update_input_text(self, text: str) -> None:
        self.model.input_text = text
        if self.model.auto_update:
            self.transform_text()

    def update_settings(
        self,
        seed: int,
        auto_update: bool,
        multi_seed_mode: bool = False,
        multi_seed_count: int = 10,
    ) -> None:
        self.model.seed = seed
        self.model.auto_update = auto_update
        self.model.multi_seed_mode = multi_seed_mode
        self.model.multi_seed_count = multi_seed_count

        if auto_update:
            self.transform_text()

    def randomize_seed(self) -> None:
        new_seed = random.randint(0, 999999)
        self.model.seed = new_seed
        if self.view:
            self.view.update_seed(new_seed)
        self.transform_text()

    def transform_text(self) -> None:
        """Main action: Transform text."""

        # Normal transform
        if not self.model.input_text:
            if self.view:
                self.view.set_status("No input text", "amber")
                self.view.set_output("")
            return

        # Get enabled glitchlings from View (or Model if we synced it)
        # For now, let's assume View passes it or we get it from View
        if self.view:
            self.model.enabled_glitchlings = self.view.get_enabled_glitchlings()
            self.model.enabled_tokenizers = self.view.get_enabled_tokenizers()

        if not self.model.enabled_glitchlings:
            self.model.output_text = self.model.input_text
            if self.view:
                self.view.set_output(self.model.output_text)
                self.view.update_metrics_display({})
                self.view.set_status("No glitchlings enabled - output unchanged", "amber")
            return

        try:
            # Check if multi-seed aggregation is enabled
            if self.model.multi_seed_mode:
                # Run multi-seed aggregation
                output, names, aggregated_metrics = self.service.transform_text_multi_seed(
                    self.model.input_text,
                    self.model.enabled_glitchlings,
                    self.model.seed,
                    self.model.multi_seed_count,
                    self.model.enabled_tokenizers,
                )
                self.model.output_text = output

                if self.view:
                    self.view.set_output(output)
                    self.view.update_metrics_display(aggregated_metrics)
                    gnames = ", ".join(names)
                    n_seeds = self.model.multi_seed_count
                    self.view.set_status(
                        f"Transformed with: {gnames} (avg over {n_seeds} seeds)",
                        "cyan",
                    )
            else:
                # Normal single-seed transform
                output, names = self.service.transform_text(
                    self.model.input_text, self.model.enabled_glitchlings, self.model.seed
                )
                self.model.output_text = output

                # Calculate metrics
                metrics = self.service.calculate_metrics(
                    self.model.input_text, self.model.output_text, self.model.enabled_tokenizers
                )

                if self.view:
                    self.view.set_output(output)
                    self.view.update_metrics_display(metrics)
                    gnames = ", ".join(names)
                    self.view.set_status(f"Transformed with: {gnames}", "green")

        except Exception as e:
            if self.view:
                self.view.set_output(f"Error: {e}")
                self.view.set_status(f"Error: {e}", "red")

    def process_dataset(self, samples: List[str]) -> None:
        """Run glitchlings across all loaded dataset samples."""
        if self.model.dataset_running:
            self.model.dataset_running = False
            if self.view:
                self.view.set_status("Canceling dataset run...", "amber")
            return

        if not samples:
            if self.view:
                self.view.set_status("No dataset loaded", "amber")
                self.view.set_dataset_running(False, total=0)
            return

        if self.view:
            self.model.enabled_glitchlings = self.view.get_enabled_glitchlings()
            self.model.enabled_tokenizers = self.view.get_enabled_tokenizers()

        if not self.model.enabled_glitchlings:
            if self.view:
                self.view.set_status("No glitchlings enabled", "amber")
                self.view.set_dataset_running(False, total=len(samples))
            return

        self.model.dataset_running = True
        self.model.dataset_total = len(samples)
        self.model.dataset_processed = 0
        self.model.dataset_results = {}

        if self.view:
            self.view.set_dataset_running(True, total=len(samples))
            gnames = ", ".join(cls.__name__ for cls, _ in self.model.enabled_glitchlings)
            self.view.set_status(f"Processing dataset with {gnames}...", "magenta")

        self.service.process_dataset(
            samples,
            self.model.enabled_glitchlings,
            self.model.seed,
            self.model.enabled_tokenizers,
            self._on_dataset_progress,
            self._on_dataset_complete,
            lambda: not self.model.dataset_running,
        )

    def _on_dataset_progress(self, current: int, total: int) -> None:
        """Handle dataset batch progress callbacks."""
        self.model.dataset_processed = current

        if self.view:
            view = self.view

            def update_status() -> None:
                view.update_dataset_progress(current, total)
                view.set_status(f"Processing dataset {current}/{total}", "magenta")

            view.after(0, update_status)

    def _on_dataset_complete(
        self,
        results: Dict[str, ScanResult],
        names: List[str],
        total_samples: int,
        processed_samples: int,
    ) -> None:
        """Handle dataset batch completion callbacks."""
        self.model.dataset_running = False
        self.model.dataset_results = results
        self.model.dataset_total = total_samples
        self.model.dataset_processed = processed_samples

        tokenizers = list(results.keys())
        formatted_metrics = self.service.format_scan_metrics(
            results,
            metrics=["token_delta", "jsd", "ned", "sr", "token_count_out", "char_count_out"],
        )

        def update_ui() -> None:
            if self.view:
                self.view.set_dataset_running(False, total=total_samples)
                self.view.display_dataset_results(tokenizers, formatted_metrics, processed_samples)
                status_prefix = (
                    "Dataset processed"
                    if processed_samples == total_samples
                    else "Dataset cancelled"
                )
                detail = f"{processed_samples}/{total_samples} samples"
                gnames = ", ".join(names) if names else "No glitchlings"
                self.view.set_status(f"{status_prefix}: {detail} with {gnames}", "cyan")
                self.view.refresh_charts()

        if self.view:
            self.view.after(0, update_ui)
