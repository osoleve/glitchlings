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
        if self.model.auto_update and not self.model.scan_mode:
            self.transform_text()

    def update_settings(
        self, seed: int, auto_update: bool, scan_mode: bool, scan_count: int
    ) -> None:
        self.model.seed = seed
        self.model.auto_update = auto_update
        self.model.scan_mode = scan_mode
        self.model.scan_count = scan_count

        if auto_update and not scan_mode:
            self.transform_text()

    def randomize_seed(self) -> None:
        new_seed = random.randint(0, 999999)
        self.model.seed = new_seed
        if self.view:
            self.view.update_seed(new_seed)
        self.transform_text()

    def toggle_scan_mode(self, enabled: bool) -> None:
        self.model.scan_mode = enabled
        if enabled:
            self.model.auto_update = False
            if self.view:
                self.view.set_auto_update(False)
                self.view.update_transform_button(is_scan=True)
        else:
            self.model.scan_results = {}
            if self.view:
                self.view.update_transform_button(is_scan=False)
            self.transform_text()

    def transform_text(self) -> None:
        """Main action: Transform or Scan."""
        if self.model.scan_mode:
            self.run_scan()
            return

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

    def run_scan(self) -> None:
        if self.model.scan_running:
            # Cancel
            self.model.scan_running = False
            return

        if not self.model.input_text:
            if self.view:
                self.view.set_status("No input text", "amber")
            return

        if self.view:
            self.model.enabled_glitchlings = self.view.get_enabled_glitchlings()
            self.model.enabled_tokenizers = self.view.get_enabled_tokenizers()

        if not self.model.enabled_glitchlings:
            if self.view:
                self.view.set_status("No glitchlings enabled", "amber")
            return

        self.model.scan_running = True
        if self.view:
            self.view.set_scan_running(True)
            self.view.set_status(f"Scanning 0/{self.model.scan_count} seeds...", "magenta")

        self.service.run_scan(
            self.model.input_text,
            self.model.enabled_glitchlings,
            self.model.seed,
            self.model.scan_count,
            self.model.enabled_tokenizers,
            self._on_scan_progress,
            self._on_scan_complete,
            lambda: not self.model.scan_running,
        )

    def _on_scan_progress(self, current: int, total: int) -> None:
        if self.view:
            # Schedule UI update on main thread
            view = self.view

            def update_status() -> None:
                view.set_status(f"Scanning {current}/{total} seeds...", "magenta")

            view.after(0, update_status)

    def _on_scan_complete(self, results: Dict[str, ScanResult], names: List[str]) -> None:
        self.model.scan_running = False
        self.model.scan_results = results

        # Format results for display
        formatted_metrics = self.service.format_scan_metrics(results)
        tokenizers = list(results.keys())

        def update_ui() -> None:
            if self.view:
                self.view.set_scan_running(False)
                self.view.display_scan_results(tokenizers, formatted_metrics)

                # Show example output (last seed)
                last_seed = self.model.seed + self.model.scan_count - 1
                try:
                    output, _ = self.service.transform_text(
                        self.model.input_text, self.model.enabled_glitchlings, last_seed
                    )
                    self.view.set_output(output)
                except Exception:
                    pass

                gnames = ", ".join(names)
                status = (
                    f"Scan complete: {self.model.scan_count} seeds with {gnames} "
                    f"| Example shown: seed {last_seed}"
                )
                self.view.set_status(status, "cyan")

        if self.view:
            self.view.after(0, update_ui)
