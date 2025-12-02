from __future__ import annotations

from textwrap import dedent

from ..theme import COLORS

DEFAULT_FONT_STACK = "Cascadia Code, JetBrains Mono, Consolas, Monaco, monospace"
PALETTE = dict(COLORS)

GREEN_NOISE = PALETTE["green_dim"].lstrip("#")
CYAN_NOISE = PALETTE["cyan_dim"].lstrip("#")

BACKGROUND_GRADIENT = (
    f"radial-gradient(circle at 20% 20%, #{GREEN_NOISE}11, transparent 60%),\n"
    f"            radial-gradient(circle at 80% 10%, #{CYAN_NOISE}12, transparent 55%),\n"
    "            var(--glitch-bg);"
)

PANEL_GRADIENT = (
    f"linear-gradient(180deg, #{PALETTE['panel'].lstrip('#')}e6, "
    f"#{PALETTE['black'].lstrip('#')}e6 65%)"
)

# Mapping from var(--glitch-*) to actual color values
# Textual TCSS doesn't support CSS custom properties, so we substitute them
VAR_SUBSTITUTIONS = {
    "var(--glitch-bg)": PALETTE["black"],
    "var(--glitch-surface)": PALETTE["surface"],
    "var(--glitch-panel)": PALETTE["dark"],
    "var(--glitch-accent)": PALETTE["cyan"],
    "var(--glitch-ink)": PALETTE["green"],
    "var(--glitch-bright)": PALETTE["green_bright"],
    "var(--glitch-muted)": PALETTE["text_muted"],
    "var(--glitch-border)": PALETTE["border"],
    "var(--glitch-danger)": PALETTE["red"],
    "var(--glitch-warn)": PALETTE["amber"],
}

BASE_CSS = dedent(
    f"""
    Screen {{
        background: {PALETTE["black"]};
        color: {PALETTE["green"]};
    }}

    .panel {{
        background: {PALETTE["dark"]};
        border: solid {PALETTE["border"]};
        color: {PALETTE["green"]};
    }}

    .muted {{
        color: {PALETTE["text_muted"]};
    }}

    .accent {{
        color: {PALETTE["cyan"]};
    }}

    .warning {{
        color: {PALETTE["amber"]};
    }}

    .danger {{
        color: {PALETTE["red"]};
    }}
    """
)


def substitute_vars(css: str) -> str:
    """Replace var(--glitch-*) references with actual color values.

    Textual TCSS doesn't support CSS custom properties, so this function
    substitutes them with the actual color hex values at load time.
    """
    result = css
    for var_ref, color_value in VAR_SUBSTITUTIONS.items():
        result = result.replace(var_ref, color_value)
    return result


def themed_css(extra: str | None = None) -> str:
    """Return base CSS plus optional additions, with var() substitutions applied."""
    if not extra:
        return BASE_CSS
    combined = BASE_CSS + "\n" + extra.strip() + "\n"
    return substitute_vars(combined)
