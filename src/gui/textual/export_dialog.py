"""Export dialog for the Textual GUI.

Provides dialogs for exporting session and sweep data in various formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from ..export import (
    ExportData,
    ExportOptions,
    SweepExportOptions,
    export_session,
    export_sweep,
)

if TYPE_CHECKING:
    from typing import Any

CSS = """
ExportDialog, SweepExportDialog, BaseExportDialog {
    align: center middle;
}

ExportDialog > Container,
SweepExportDialog > Container,
BaseExportDialog > Container {
    width: 60;
    height: auto;
    max-height: 40;
    background: $surface;
    border: solid $primary;
    padding: 1 2;
}

ExportDialog .dialog-header,
SweepExportDialog .dialog-header,
BaseExportDialog .dialog-header {
    text-align: center;
    color: $secondary;
    text-style: bold;
    padding-bottom: 1;
}

ExportDialog .section-label,
SweepExportDialog .section-label,
BaseExportDialog .section-label {
    color: $primary;
    text-style: bold;
    padding-bottom: 1;
}

ExportDialog .format-row,
SweepExportDialog .format-row,
BaseExportDialog .format-row {
    height: auto;
    padding-bottom: 1;
}

ExportDialog .options-container,
SweepExportDialog .options-container,
BaseExportDialog .options-container {
    height: auto;
    padding: 1;
    background: $panel;
    margin-bottom: 1;
}

ExportDialog .status-label,
SweepExportDialog .status-label,
BaseExportDialog .status-label {
    color: $text-muted;
    text-style: italic;
    padding-bottom: 1;
}

ExportDialog .button-row,
SweepExportDialog .button-row,
BaseExportDialog .button-row {
    height: 3;
    align: right middle;
}

ExportDialog .button-row Button,
SweepExportDialog .button-row Button,
BaseExportDialog .button-row Button {
    margin-left: 1;
}
"""

FORMAT_EXTENSIONS = {
    "json": ".json",
    "csv": ".csv",
    "markdown": ".md",
}


@dataclass
class ExportResult:
    """Result from export dialog."""

    cancelled: bool = True
    content: str = ""
    format: str = "json"
    file_path: str | None = None


class BaseExportDialog(ModalScreen[ExportResult]):
    """Base class for export dialogs with common functionality.

    Subclasses should implement:
    - _get_dialog_title() -> str
    - _get_status_text() -> str
    - _compose_options() -> ComposeResult
    - _get_export_content() -> str
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = CSS

    def __init__(
        self,
        on_file_save: Callable[[str, str], Path | None] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize base export dialog.

        Args:
            on_file_save: Callback to save file (content, extension) -> Path or None
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.on_file_save = on_file_save
        self._format = "json"

    def _get_dialog_title(self) -> str:
        """Get the dialog title text. Subclasses should override."""
        raise NotImplementedError("Subclasses must implement _get_dialog_title")

    def _get_status_text(self) -> str:
        """Build status text describing available data. Subclasses should override."""
        raise NotImplementedError("Subclasses must implement _get_status_text")

    def _compose_options(self) -> ComposeResult:
        """Compose dialog-specific options widgets. Subclasses should override."""
        raise NotImplementedError("Subclasses must implement _compose_options")
        yield  # Make this a generator

    def _get_export_content(self) -> str:
        """Generate export content in selected format. Subclasses should override."""
        raise NotImplementedError("Subclasses must implement _get_export_content")

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Container():
            yield Static(self._get_dialog_title(), classes="dialog-header")

            # Format selection
            yield Label("Export Format:", classes="section-label")
            with Horizontal(classes="format-row"):
                with RadioSet(id="format-set"):
                    yield RadioButton("JSON", id="format-json", value=True)
                    yield RadioButton("CSV", id="format-csv")
                    yield RadioButton("Markdown", id="format-markdown")

            # Dialog-specific options
            yield from self._compose_options()

            # Status
            status_text = self._get_status_text()
            yield Static(f"● {status_text}", classes="status-label")

            # Buttons
            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Copy", variant="primary", id="btn-copy")
                yield Button("Save...", variant="success", id="btn-save")

    def _get_extension(self) -> str:
        """Get file extension for current format."""
        return FORMAT_EXTENSIONS.get(self._format, ".txt")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle format selection change."""
        if event.radio_set.id == "format-set":
            button_id = str(event.pressed.id) if event.pressed else ""
            if button_id == "format-json":
                self._format = "json"
            elif button_id == "format-csv":
                self._format = "csv"
            elif button_id == "format-markdown":
                self._format = "markdown"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = str(event.button.id)

        if button_id == "btn-cancel":
            self.dismiss(ExportResult(cancelled=True))

        elif button_id == "btn-copy":
            try:
                content = self._get_export_content()
                self.app.copy_to_clipboard(content)
                self.app.notify("Copied to clipboard", severity="information")
                self.dismiss(ExportResult(cancelled=False, content=content, format=self._format))
            except Exception as e:
                self.app.notify(f"Export failed: {e}", severity="error")

        elif button_id == "btn-save":
            try:
                content = self._get_export_content()
                ext = self._get_extension()
                if self.on_file_save:
                    path = self.on_file_save(content, ext)
                    if path:
                        self.app.notify(f"Saved to {path}", severity="information")
                        self.dismiss(
                            ExportResult(
                                cancelled=False,
                                content=content,
                                format=self._format,
                                file_path=str(path),
                            )
                        )
                else:
                    self.app.notify("File save not available", severity="warning")
            except Exception as e:
                self.app.notify(f"Save failed: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(ExportResult(cancelled=True))


class ExportDialog(BaseExportDialog):
    """Dialog for exporting session data in various formats."""

    def __init__(
        self,
        export_data: ExportData,
        on_file_save: Callable[[str, str], Path | None] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize export dialog.

        Args:
            export_data: The data to export
            on_file_save: Callback to save file (content, extension) -> Path or None
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(on_file_save=on_file_save, name=name, id=id, classes=classes)
        self.export_data = export_data

        # Current selections
        self._include_config = True
        self._include_input = True
        self._include_output = True
        self._include_metrics = True
        self._include_scan = True

    def _get_dialog_title(self) -> str:
        """Get the dialog title text."""
        return "▓▒░ EXPORT SESSION ░▒▓"

    def _get_status_text(self) -> str:
        """Build status text describing available data."""
        has_scan = bool(self.export_data.scan_results)
        has_metrics = bool(self.export_data.metrics)

        status_parts = []
        if has_metrics:
            status_parts.append(f"{len(self.export_data.metrics)} tokenizers with metrics")
        if has_scan:
            status_parts.append("scan results available")

        return " · ".join(status_parts) if status_parts else "Basic export (no metrics yet)"

    def _compose_options(self) -> ComposeResult:
        """Compose dialog-specific options widgets."""
        yield Label("Include:", classes="section-label")
        with Vertical(classes="options-container"):
            yield Checkbox(
                "Configuration (glitchlings, tokenizers, parameters)",
                value=True,
                id="opt-config",
            )
            yield Checkbox("Input text", value=True, id="opt-input")
            yield Checkbox("Output text", value=True, id="opt-output")
            yield Checkbox("Metrics", value=True, id="opt-metrics")
            yield Checkbox("Scan results (if available)", value=True, id="opt-scan")

    def _get_export_content(self) -> str:
        """Generate export content in selected format."""
        options = ExportOptions(
            include_config=self._include_config,
            include_input=self._include_input,
            include_output=self._include_output,
            include_metrics=self._include_metrics,
            include_scan_results=self._include_scan,
        )
        return export_session(self.export_data, self._format, options)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle option checkbox changes."""
        checkbox_id = str(event.checkbox.id)
        if checkbox_id == "opt-config":
            self._include_config = event.value
        elif checkbox_id == "opt-input":
            self._include_input = event.value
        elif checkbox_id == "opt-output":
            self._include_output = event.value
        elif checkbox_id == "opt-metrics":
            self._include_metrics = event.value
        elif checkbox_id == "opt-scan":
            self._include_scan = event.value


class SweepExportDialog(BaseExportDialog):
    """Dialog for exporting sweep results in various formats."""

    def __init__(
        self,
        sweep_results: list[Any],
        on_file_save: Callable[[str, str], Path | None] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize sweep export dialog.

        Args:
            sweep_results: List of SweepPoint results
            on_file_save: Callback to save file (content, extension) -> Path or None
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(on_file_save=on_file_save, name=name, id=id, classes=classes)
        self.sweep_results = sweep_results

        # Current selections
        self._include_metadata = True
        self._include_raw_values = False

    def _get_dialog_title(self) -> str:
        """Get the dialog title text."""
        return "▓▒░ EXPORT SWEEP ░▒▓"

    def _get_status_text(self) -> str:
        """Build status text describing sweep data."""
        if not self.sweep_results:
            return "No sweep results to export"

        count = len(self.sweep_results)
        first = self.sweep_results[0]
        param_name = getattr(first, "parameter_name", "Unknown")
        return f"{count} sweep points for parameter '{param_name}'"

    def _compose_options(self) -> ComposeResult:
        """Compose dialog-specific options widgets."""
        yield Label("Options:", classes="section-label")
        with Vertical(classes="options-container"):
            yield Checkbox("Include metadata", value=True, id="opt-metadata")
            yield Checkbox("Include raw values (all seeds)", value=False, id="opt-raw")

    def _get_export_content(self) -> str:
        """Generate export content in selected format."""
        options = SweepExportOptions(
            include_metadata=self._include_metadata,
            include_raw_values=self._include_raw_values,
        )
        return export_sweep(self.sweep_results, self._format, options)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle option checkbox changes."""
        checkbox_id = str(event.checkbox.id)
        if checkbox_id == "opt-metadata":
            self._include_metadata = event.value
        elif checkbox_id == "opt-raw":
            self._include_raw_values = event.value
