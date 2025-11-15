"""Persistent status/footer bar."""

from __future__ import annotations

from textual.widgets import Static


class StatusFooter(Static):  # type: ignore[misc]
    """Thin footer that surfaces run metadata."""

    DEFAULT_CSS = """
    StatusFooter {
        height: 1;
        dock: bottom;
        padding: 0 1;
        background: $surface 20%;
        color: $text;
    }
    """

    def __init__(self) -> None:
        super().__init__("", id="status-footer", markup=False)
        self.update_summary(0, 0)

    def update_summary(self, glitch_count: int, tokenizer_count: int) -> None:
        """Update footer text."""
        self.update(f"[r] Run | glitchlings={glitch_count} | tokenizers={tokenizer_count}")


__all__ = ["StatusFooter"]
