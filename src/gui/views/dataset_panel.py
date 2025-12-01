"""Dataset loading panel for the GUI.

Supports loading from HuggingFace, Project Gutenberg, and local files.
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, List

from ..theme import COLORS, FONTS
from .utils import create_tooltip


class DatasetPanel(ttk.Frame):
    """Panel for loading and previewing datasets."""

    def __init__(
        self,
        parent: ttk.Frame,
        on_dataset_loaded: Callable[[List[str]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_dataset_loaded = on_dataset_loaded

        # Dataset state
        self.samples: List[str] = []
        self.loading = False

        # Variables
        self.source_var = tk.StringVar(value="local")
        self.dataset_name_var = tk.StringVar()
        self.split_var = tk.StringVar(value="train")
        self.sample_size_var = tk.StringVar(value="100")
        self.text_field_var = tk.StringVar(value="text")

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        header_inner = tk.Frame(header_frame, bg=COLORS["dark"])
        header_inner.pack(fill=tk.X)

        header = tk.Label(
            header_inner,
            text="▓▒░ DATASET SOURCE ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=8,
            pady=5,
        )
        header.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header_inner,
            text="No dataset loaded",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=8,
        )
        self.status_label.pack(side=tk.RIGHT, padx=6, pady=5)

        # Main content with border
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        content = tk.Frame(content_container, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Source selection tabs
        source_frame = tk.Frame(content, bg=COLORS["black"])
        source_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        for value, label, tooltip in [
            ("local", "Local Files", "Load text from local .txt files"),
            ("huggingface", "HuggingFace", "Load from HuggingFace datasets"),
            ("gutenberg", "Gutenberg", "Load from Project Gutenberg"),
        ]:
            rb = tk.Radiobutton(
                source_frame,
                text=label,
                variable=self.source_var,
                value=value,
                font=FONTS["small"],
                fg=COLORS["green"],
                bg=COLORS["black"],
                activeforeground=COLORS["green_bright"],
                activebackground=COLORS["black"],
                selectcolor=COLORS["darker"],
                highlightthickness=0,
                cursor="hand2",
                command=self._on_source_change,
            )
            rb.pack(side=tk.LEFT, padx=(0, 15))
            create_tooltip(rb, tooltip)

        # Separator
        sep = tk.Frame(content, bg=COLORS["border"], height=1)
        sep.pack(fill=tk.X, padx=8, pady=6)

        # Source-specific options frame
        self.options_frame = tk.Frame(content, bg=COLORS["black"])
        self.options_frame.pack(fill=tk.X, padx=8, pady=4)

        # Create option panels (only one visible at a time)
        self.local_options = self._create_local_options()
        self.hf_options = self._create_huggingface_options()
        self.gutenberg_options = self._create_gutenberg_options()

        # Show initial option panel
        self._on_source_change()

        # Sample size and load button
        controls_frame = tk.Frame(content, bg=COLORS["black"])
        controls_frame.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(
            controls_frame,
            text="Sample Size:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        sample_spin = tk.Spinbox(
            controls_frame,
            from_=1,
            to=10000,
            textvariable=self.sample_size_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            buttonbackground=COLORS["dark"],
            relief=tk.SOLID,
            bd=1,
        )
        sample_spin.pack(side=tk.LEFT, padx=(4, 15))

        self.load_btn = tk.Button(
            controls_frame,
            text="▶ LOAD DATASET",
            font=FONTS["section"],
            fg=COLORS["black"],
            bg=COLORS["green"],
            activeforeground=COLORS["black"],
            activebackground=COLORS["green_bright"],
            bd=0,
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._load_dataset,
        )
        self.load_btn.pack(side=tk.RIGHT)

        # Preview section
        preview_header = tk.Frame(content, bg=COLORS["dark"])
        preview_header.pack(fill=tk.X, padx=8, pady=(8, 0))

        tk.Label(
            preview_header,
            text="░ PREVIEW",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=4,
        ).pack(side=tk.LEFT)

        self.preview_count = tk.Label(
            preview_header,
            text="",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=4,
        )
        self.preview_count.pack(side=tk.RIGHT)

        # Preview text area
        preview_container = tk.Frame(content, bg=COLORS["border"], padx=1, pady=1)
        preview_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.preview_text = scrolledtext.ScrolledText(
            preview_container,
            wrap=tk.WORD,
            height=8,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            selectbackground=COLORS["highlight"],
            selectforeground=COLORS["green_bright"],
            relief=tk.FLAT,
            padx=8,
            pady=6,
            state=tk.DISABLED,
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

    def _create_local_options(self) -> tk.Frame:
        """Create options for local file loading."""
        frame = tk.Frame(self.options_frame, bg=COLORS["black"])

        tk.Label(
            frame,
            text="Files:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        self.files_label = tk.Label(
            frame,
            text="No files selected",
            font=FONTS["small"],
            fg=COLORS["amber"],
            bg=COLORS["black"],
        )
        self.files_label.pack(side=tk.LEFT, padx=(8, 0))

        browse_btn = tk.Button(
            frame,
            text="Browse...",
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._browse_files,
        )
        browse_btn.pack(side=tk.LEFT, padx=(15, 0))

        self.selected_files: List[Path] = []
        return frame

    def _create_huggingface_options(self) -> tk.Frame:
        """Create options for HuggingFace dataset loading."""
        frame = tk.Frame(self.options_frame, bg=COLORS["black"])

        # Dataset name
        tk.Label(
            frame,
            text="Dataset:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).grid(row=0, column=0, sticky="w", pady=2)

        dataset_entry = tk.Entry(
            frame,
            textvariable=self.dataset_name_var,
            width=30,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        dataset_entry.grid(row=0, column=1, padx=(8, 0), pady=2, sticky="w")
        create_tooltip(dataset_entry, "e.g., imdb, squad, wikitext")

        # Split
        tk.Label(
            frame,
            text="Split:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).grid(row=0, column=2, padx=(20, 0), sticky="w", pady=2)

        split_combo = ttk.Combobox(
            frame,
            textvariable=self.split_var,
            values=["train", "test", "validation"],
            width=12,
            state="readonly",
        )
        split_combo.grid(row=0, column=3, padx=(8, 0), pady=2, sticky="w")

        # Text field
        tk.Label(
            frame,
            text="Text field:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).grid(row=1, column=0, sticky="w", pady=2)

        field_entry = tk.Entry(
            frame,
            textvariable=self.text_field_var,
            width=15,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        field_entry.grid(row=1, column=1, padx=(8, 0), pady=2, sticky="w")
        create_tooltip(field_entry, "Column containing text (e.g., text, sentence)")

        return frame

    def _create_gutenberg_options(self) -> tk.Frame:
        """Create options for Project Gutenberg loading."""
        frame = tk.Frame(self.options_frame, bg=COLORS["black"])

        tk.Label(
            frame,
            text="Book ID or URL:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        self.gutenberg_id_var = tk.StringVar()
        id_entry = tk.Entry(
            frame,
            textvariable=self.gutenberg_id_var,
            width=40,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        id_entry.pack(side=tk.LEFT, padx=(8, 0))
        create_tooltip(id_entry, "e.g., 1342 for Pride and Prejudice")

        return frame

    def _on_source_change(self) -> None:
        """Switch visible options based on selected source."""
        source = self.source_var.get()

        # Hide all
        self.local_options.pack_forget()
        self.hf_options.pack_forget()
        self.gutenberg_options.pack_forget()

        # Show selected
        if source == "local":
            self.local_options.pack(fill=tk.X)
        elif source == "huggingface":
            self.hf_options.pack(fill=tk.X)
        elif source == "gutenberg":
            self.gutenberg_options.pack(fill=tk.X)

    def _browse_files(self) -> None:
        """Browse for local text files."""
        files = filedialog.askopenfilenames(
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )
        if files:
            self.selected_files = [Path(f) for f in files]
            if len(self.selected_files) == 1:
                self.files_label.config(text=self.selected_files[0].name)
            else:
                self.files_label.config(text=f"{len(self.selected_files)} files selected")

    def _load_dataset(self) -> None:
        """Load dataset based on selected source."""
        if self.loading:
            return

        source = self.source_var.get()
        sample_size = int(self.sample_size_var.get())

        self.loading = True
        self.load_btn.config(text="Loading...", bg=COLORS["amber"])

        # Run in thread to avoid blocking UI
        thread = threading.Thread(
            target=self._load_dataset_worker,
            args=(source, sample_size),
            daemon=True,
        )
        thread.start()

    def _load_dataset_worker(self, source: str, sample_size: int) -> None:
        """Worker thread for loading dataset."""
        try:
            if source == "local":
                samples = self._load_local_files(sample_size)
            elif source == "huggingface":
                samples = self._load_huggingface(sample_size)
            elif source == "gutenberg":
                samples = self._load_gutenberg(sample_size)
            else:
                samples = []

            self.after(0, lambda: self._on_load_complete(samples, None))

        except Exception as exc:
            error_msg = str(exc)
            self.after(0, lambda: self._on_load_complete([], error_msg))

    def _load_local_files(self, sample_size: int) -> List[str]:
        """Load samples from local text files."""
        if not self.selected_files:
            raise ValueError("No files selected")

        samples: List[str] = []
        for path in self.selected_files:
            try:
                text = path.read_text(encoding="utf-8")
                # Split into paragraphs as samples
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                samples.extend(paragraphs)
            except OSError as e:
                raise ValueError(f"Could not read {path.name}: {e}") from e

        # Limit to sample size
        return samples[:sample_size]

    def _load_huggingface(self, sample_size: int) -> List[str]:
        """Load samples from HuggingFace datasets."""
        dataset_name = self.dataset_name_var.get().strip()
        if not dataset_name:
            raise ValueError("No dataset name provided")

        try:
            from glitchlings.dlc.huggingface import load_hf_dataset
        except ImportError as e:
            raise ValueError(
                "HuggingFace datasets not available. Install with: pip install datasets"
            ) from e

        split = self.split_var.get()
        text_field = self.text_field_var.get().strip() or "text"

        dataset = load_hf_dataset(dataset_name, split=split, streaming=True)

        samples: List[str] = []
        for i, item in enumerate(dataset):
            if i >= sample_size:
                break
            if text_field in item:
                samples.append(str(item[text_field]))

        if not samples:
            raise ValueError(f"No samples found with field '{text_field}'")

        return samples

    def _load_gutenberg(self, sample_size: int) -> List[str]:
        """Load samples from Project Gutenberg."""
        book_id = self.gutenberg_id_var.get().strip()
        if not book_id:
            raise ValueError("No book ID provided")

        try:
            from glitchlings.dlc.gutenberg import GutenbergBook
        except ImportError as e:
            raise ValueError("Gutenberg support not available") from e

        book = GutenbergBook.load(book_id)
        text = book.text

        # Split into paragraphs as samples
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs[:sample_size]

    def _on_load_complete(self, samples: List[str], error: str | None) -> None:
        """Handle load completion on main thread."""
        self.loading = False
        self.load_btn.config(text="▶ LOAD DATASET", bg=COLORS["green"])

        if error:
            messagebox.showerror("Load Failed", f"Could not load dataset:\n{error}")
            self.status_label.config(text="Load failed", fg=COLORS["red"])
            return

        self.samples = samples
        self.status_label.config(text=f"{len(samples)} samples loaded", fg=COLORS["green"])
        self.preview_count.config(text=f"Showing 1-{min(5, len(samples))} of {len(samples)}")

        # Update preview
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)

        for i, sample in enumerate(samples[:5]):
            if i > 0:
                self.preview_text.insert(tk.END, "\n\n---\n\n")
            preview = sample[:500] + "..." if len(sample) > 500 else sample
            self.preview_text.insert(tk.END, f"[{i + 1}] {preview}")

        self.preview_text.config(state=tk.DISABLED)

        # Notify callback
        if self.on_dataset_loaded:
            self.on_dataset_loaded(samples)

    def get_samples(self) -> List[str]:
        """Return currently loaded samples."""
        return self.samples
