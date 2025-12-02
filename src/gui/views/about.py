from __future__ import annotations

import tkinter as tk

from ..theme import APP_VERSION, COLORS, FONTS

ABOUT_WIDTH = 480
ABOUT_HEIGHT = 420


def _center_window(window: tk.Toplevel, width: int, height: int) -> None:
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"+{x}+{y}")


def show_about_dialog(parent: tk.Tk) -> None:
    """Render the themed about dialog."""
    about = tk.Toplevel(parent)
    about.title("ABOUT GLITCHLINGS")
    about.geometry(f"{ABOUT_WIDTH}x{ABOUT_HEIGHT}")
    about.configure(bg=COLORS["black"])
    about.resizable(False, False)

    about.transient(parent)
    about.grab_set()
    about.update_idletasks()
    _center_window(about, ABOUT_WIDTH, ABOUT_HEIGHT)

    outer_border = tk.Frame(about, bg=COLORS["green_dim"], padx=2, pady=2)
    outer_border.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    border = tk.Frame(outer_border, bg=COLORS["border"], padx=1, pady=1)
    border.pack(fill=tk.BOTH, expand=True)

    inner = tk.Frame(border, bg=COLORS["black"])
    inner.pack(fill=tk.BOTH, expand=True)

    header_text = """
╔══════════════════════════════════════════╦
║    ༼ つ ◕_◕ ༽つ  GLITCHLINGS            ║
║       ▓▒░ TERMINAL v{ver:<9} ░▒▓         ║
╚══════════════════════════════════════════╝
""".format(ver=APP_VERSION)
    header = tk.Label(
        inner,
        text=header_text,
        font=("Consolas", 11),
        fg=COLORS["green_bright"],
        bg=COLORS["black"],
        justify=tk.CENTER,
    )
    header.pack(pady=(12, 0))

    desc = tk.Label(
        inner,
        text="A vector terminal interface for\ncorrupting text with glitchlings.\n\n"
        "Summon creatures from the digital void\nto transform your tokens into chaos.",
        font=FONTS["body"],
        fg=COLORS["green"],
        bg=COLORS["black"],
        justify=tk.CENTER,
    )
    desc.pack(pady=12)

    features_frame = tk.Frame(inner, bg=COLORS["black"])
    features_frame.pack(pady=10)

    features = [
        "◆ 10 unique glitchling creatures",
        "◆ Deterministic transformations with seeds",
        "◆ Real-time token diff analysis",
        "◆ Multi-tokenizer metrics comparison",
    ]
    for feat in features:
        tk.Label(
            features_frame,
            text=feat,
            font=FONTS["small"],
            fg=COLORS["cyan"],
            bg=COLORS["black"],
            anchor="w",
        ).pack(anchor="w", padx=20)

    sep_frame = tk.Frame(inner, bg=COLORS["black"])
    sep_frame.pack(fill=tk.X, padx=40, pady=10)
    tk.Frame(sep_frame, bg=COLORS["green_dim"], height=1).pack(fill=tk.X)

    status = tk.Label(
        inner,
        text="◀▶ SYSTEM OPERATIONAL ◀▶",
        font=FONTS["status"],
        fg=COLORS["cyan_bright"],
        bg=COLORS["black"],
    )
    status.pack(pady=8)

    close_btn = tk.Button(
        inner,
        text="[ CLOSE ]",
        font=FONTS["button"],
        fg=COLORS["green"],
        bg=COLORS["surface"],
        activeforeground=COLORS["darker"],
        activebackground=COLORS["green"],
        bd=0,
        relief=tk.FLAT,
        padx=24,
        pady=8,
        cursor="hand2",
        command=about.destroy,
    )
    close_btn.pack(pady=18)

    about.bind("<Escape>", lambda e: about.destroy())
