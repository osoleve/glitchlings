"""Export dialog for sweep results."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, List

from ..export import SweepExportOptions, export_sweep
from ..theme import COLORS, FONTS


class SweepExportDialog(tk.Toplevel):
    """Dialog for exporting sweep results in various formats."""

    def __init__(
        self,
        parent: tk.Tk,
        sweep_results: List[Any],
    ) -> None:
        super().__init__(parent)
        self.title("Export Sweep Results")
        self.configure(bg=COLORS["black"])
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.sweep_results = sweep_results

        # Format selection
        self.format_var = tk.StringVar(value="csv")

        # Export options
        self.include_metadata_var = tk.BooleanVar(value=True)
        self.include_raw_var = tk.BooleanVar(value=False)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["surface"], height=40)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="▓▒░ EXPORT SWEEP ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["surface"],
            padx=12,
        ).pack(side=tk.LEFT, pady=10)

        # Content
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        container = tk.Frame(content_container, bg=COLORS["black"], padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        # Format selection
        format_frame = tk.Frame(container, bg=COLORS["black"])
        format_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            format_frame,
            text="Export Format:",
            font=FONTS["small"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        for value, label in [("json", "JSON"), ("csv", "CSV"), ("markdown", "Markdown")]:
            rb = tk.Radiobutton(
                format_frame,
                text=label,
                variable=self.format_var,
                value=value,
                font=FONTS["small"],
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
            text="Options:",
            font=FONTS["small"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
        ).pack(anchor="w", pady=(0, 8))

        for var, label in [
            (self.include_metadata_var, "Include metadata (glitchling, parameter, etc.)"),
            (self.include_raw_var, "Include raw per-seed values (JSON only)"),
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

        point_count = len(self.sweep_results)
        if point_count > 0:
            first = self.sweep_results[0]
            glitch = getattr(first, "glitchling_name", "Unknown")
            param = getattr(first, "parameter_name", "Unknown")
            status_text = f"{point_count} sweep points · {glitch}.{param}"
        else:
            status_text = "No sweep results to export"

        tk.Label(
            info_frame,
            text=f"● {status_text}",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(anchor="w")

        # Buttons
        button_row = tk.Frame(container, bg=COLORS["black"])
        button_row.pack(fill=tk.X, pady=(12, 0))

        tk.Button(
            button_row,
            text="Cancel",
            font=FONTS["button"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            button_row,
            text="Copy to Clipboard",
            font=FONTS["button"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._copy_to_clipboard,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            button_row,
            text="Export to File...",
            font=FONTS["button"],
            fg=COLORS["darker"],
            bg=COLORS["green"],
            activeforeground=COLORS["darker"],
            activebackground=COLORS["green_bright"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._export_to_file,
        ).pack(side=tk.RIGHT)

    def _get_options(self) -> SweepExportOptions:
        return SweepExportOptions(
            include_metadata=self.include_metadata_var.get(),
            include_raw_values=self.include_raw_var.get(),
        )

    def _get_export_content(self) -> str:
        options = self._get_options()
        format_type = self.format_var.get()
        return export_sweep(self.sweep_results, format_type, options)

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

        # Build a default filename from sweep metadata
        default_name = "sweep_results"
        if self.sweep_results:
            first = self.sweep_results[0]
            glitch = getattr(first, "glitchling_name", "")
            param = getattr(first, "parameter_name", "")
            if glitch and param:
                default_name = f"sweep_{glitch}_{param}"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=default_ext,
            filetypes=filetypes,
            initialfile=f"{default_name}{default_ext}",
        )

        if not file_path:
            return

        try:
            content = self._get_export_content()
            Path(file_path).write_text(content, encoding="utf-8")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file:\n{e}", parent=self)
