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

    StatusFooter.-error {
        background: $error 40%;
        color: $text;
    }
    """

    def __init__(self) -> None:
        super().__init__("", id="status-footer", markup=False)
        self.update_summary(0, 0, "Idle")

    def update_summary(
        self,
        glitch_count: int,
        tokenizer_count: int,
        status: str,
        *,
        duration: float | None = None,
        is_error: bool = False,
    ) -> None:
        """Update footer text."""
        hint = "Keys: r=run • ?=help • /=filter • Ctrl+S=save"
        duration_text = f"{duration:.2f}s" if duration is not None else "—"
        summary = (
            f"glitchlings={glitch_count} • tokenizers={tokenizer_count} "
            f"• status={status} • last run={duration_text}"
        )
        self.update(f"{summary} • {hint}")
        self.set_class(is_error, "-error")


__all__ = ["StatusFooter"]
