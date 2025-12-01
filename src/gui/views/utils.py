import tkinter as tk
from ..theme import COLORS, FONTS


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Create a tooltip for a widget."""
    tooltip: tk.Toplevel | None = None

    def show_tooltip(event: tk.Event) -> None:  # type: ignore[type-arg]
        nonlocal tooltip
        if tooltip is not None:
            return
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        tooltip.configure(bg=COLORS["dark"])

        # Border frame
        border = tk.Frame(tooltip, bg=COLORS["border"], padx=1, pady=1)
        border.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            border,
            text=text,
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            padx=6,
            pady=3,
        )
        label.pack()

    def hide_tooltip(event: tk.Event) -> None:  # type: ignore[type-arg]
        nonlocal tooltip
        if tooltip is not None:
            tooltip.destroy()
            tooltip = None

    widget.bind("<Enter>", show_tooltip, add="+")
    widget.bind("<Leave>", hide_tooltip, add="+")
