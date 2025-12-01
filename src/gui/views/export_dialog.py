"""Export dialog for the GUI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from ..export import ExportData, ExportOptions, export_session
from ..theme import COLORS, FONTS


class ExportDialog(tk.Toplevel):
    """Dialog for exporting session data in various formats."""

    def __init__(
        self,
        parent: tk.Tk,
        export_data: ExportData,
    ) -> None:
        super().__init__(parent)
        self.title("Export Session")
        self.configure(bg=COLORS["black"])
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.export_data = export_data

        # Format selection
        self.format_var = tk.StringVar(value="json")

        # Export options
        self.include_config_var = tk.BooleanVar(value=True)
        self.include_input_var = tk.BooleanVar(value=True)
        self.include_output_var = tk.BooleanVar(value=True)
        self.include_metrics_var = tk.BooleanVar(value=True)
        self.include_scan_var = tk.BooleanVar(value=True)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg=COLORS["black"], padx=15, pady=15)
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            container,
            text="▓▒░ EXPORT SESSION ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["black"],
        ).pack(anchor="w", pady=(0, 15))

        # Format selection
        format_frame = tk.Frame(container, bg=COLORS["black"])
        format_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            format_frame,
            text="Export Format:",
            font=FONTS["body"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        for value, label in [("json", "JSON"), ("csv", "CSV"), ("markdown", "Markdown")]:
            rb = tk.Radiobutton(
                format_frame,
                text=label,
                variable=self.format_var,
                value=value,
                font=FONTS["body"],
                fg=COLORS["green"],
                bg=COLORS["black"],
                activeforeground=COLORS["green_bright"],
                activebackground=COLORS["black"],
                selectcolor=COLORS["darker"],
                highlightthickness=0,
                cursor="hand2",
            )
            rb.pack(side=tk.LEFT, padx=(15, 0))

        # Options section
        options_frame = tk.Frame(container, bg=COLORS["dark"], padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            options_frame,
            text="Include:",
            font=FONTS["small"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
        ).pack(anchor="w", pady=(0, 8))

        for var, label in [
            (self.include_config_var, "Configuration (glitchlings, tokenizers, parameters)"),
            (self.include_input_var, "Input text"),
            (self.include_output_var, "Output text"),
            (self.include_metrics_var, "Metrics"),
            (self.include_scan_var, "Scan results (if available)"),
        ]:
            cb = tk.Checkbutton(
                options_frame,
                text=label,
                variable=var,
                font=FONTS["small"],
                fg=COLORS["green"],
                bg=COLORS["dark"],
                activeforeground=COLORS["green_bright"],
                activebackground=COLORS["dark"],
                selectcolor=COLORS["darker"],
                highlightthickness=0,
                cursor="hand2",
            )
            cb.pack(anchor="w", pady=2)

        # Preview / info
        info_frame = tk.Frame(container, bg=COLORS["black"])
        info_frame.pack(fill=tk.X, pady=(0, 15))

        has_scan = bool(self.export_data.scan_results)
        has_metrics = bool(self.export_data.metrics)

        status_parts = []
        if has_metrics:
            status_parts.append(f"{len(self.export_data.metrics)} tokenizers with metrics")
        if has_scan:
            status_parts.append("scan results available")

        status_text = " · ".join(status_parts) if status_parts else "Basic export (no metrics yet)"

        tk.Label(
            info_frame,
            text=f"● {status_text}",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(anchor="w")

        # Buttons
        button_row = tk.Frame(container, bg=COLORS["black"])
        button_row.pack(fill=tk.X)

        tk.Button(
            button_row,
            text="Cancel",
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            button_row,
            text="Copy to Clipboard",
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._copy_to_clipboard,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            button_row,
            text="Export to File...",
            font=FONTS["body"],
            fg=COLORS["black"],
            bg=COLORS["green"],
            activeforeground=COLORS["black"],
            activebackground=COLORS["green_bright"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._export_to_file,
        ).pack(side=tk.RIGHT)

    def _get_options(self) -> ExportOptions:
        return ExportOptions(
            include_config=self.include_config_var.get(),
            include_input=self.include_input_var.get(),
            include_output=self.include_output_var.get(),
            include_metrics=self.include_metrics_var.get(),
            include_scan_results=self.include_scan_var.get(),
        )

    def _get_export_content(self) -> str:
        options = self._get_options()
        format_type = self.format_var.get()
        return export_session(self.export_data, format_type, options)

    def _copy_to_clipboard(self) -> None:
        try:
            content = self._get_export_content()
            self.clipboard_clear()
            self.clipboard_append(content)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export:\n{e}", parent=self)

    def _export_to_file(self) -> None:
        format_type = self.format_var.get()

        extensions = {
            "json": (".json", [("JSON files", "*.json")]),
            "csv": (".csv", [("CSV files", "*.csv")]),
            "markdown": (".md", [("Markdown files", "*.md")]),
        }

        default_ext, filetypes = extensions.get(format_type, (".txt", [("Text files", "*.txt")]))
        filetypes.append(("All files", "*.*"))

        file_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=default_ext,
            filetypes=filetypes,
            initialfile=f"glitchlings_export{default_ext}",
        )

        if not file_path:
            return

        try:
            content = self._get_export_content()
            Path(file_path).write_text(content, encoding="utf-8")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file:\n{e}", parent=self)
