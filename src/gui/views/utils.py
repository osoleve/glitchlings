import tkinter as tk

from ..theme import COLORS, FONTS


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Create a tooltip for a widget."""
    tooltip: tk.Toplevel | None = None

    def show_tooltip(event: tk.Event) -> None:
        nonlocal tooltip
        if tooltip is not None:
            return
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 8
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        tooltip.configure(bg=COLORS["border"])

        # Border frame with subtle shadow effect
        border = tk.Frame(tooltip, bg=COLORS["surface"], padx=1, pady=1)
        border.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            border,
            text=text,
            font=FONTS["tiny"],
            fg=COLORS["green_bright"],
            bg=COLORS["surface"],
            padx=8,
            pady=4,
        )
        label.pack()

    def hide_tooltip(event: tk.Event) -> None:
        nonlocal tooltip
        if tooltip is not None:
            tooltip.destroy()
            tooltip = None

    widget.bind("<Enter>", show_tooltip, add="+")
    widget.bind("<Leave>", hide_tooltip, add="+")
