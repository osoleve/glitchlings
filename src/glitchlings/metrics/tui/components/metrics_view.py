"""Responsive metrics view that swaps between table and vertical layout."""

from __future__ import annotations

from typing import Sequence

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ContentSwitcher, DataTable, TextArea


def _format_vertical_rows(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Format metrics as vertical key/value blocks for narrow terminals."""
    if not rows or not columns:
        return ["Run metrics (r) to view results."]

    formatted: list[str] = []
    label = columns[0]
    for row in rows:
        if not row:
            continue
        key_value = row[0]
        formatted.append(f"{label}: {key_value}")
        for index, column in enumerate(columns[1:], start=1):
            value = row[index] if index < len(row) else "-"
            formatted.append(f"  {column}: {value}")
        formatted.append("")
    return formatted


class MetricsView(Widget):  # type: ignore[misc]
    """Container that adapts the metrics display depending on width."""

    DEFAULT_CSS = """
    MetricsView {
        width: 1fr;
        height: 1fr;
    }

    MetricsView DataTable,
    MetricsView TextArea {
        height: 1fr;
    }
    """

    narrow = reactive(False, init=False)

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._columns: list[str] = []
        self._rows: list[list[str]] = []
        self._switcher: ContentSwitcher | None = None
        self._table: DataTable | None = None
        self._detail: TextArea | None = None

    def compose(self) -> ComposeResult:
        switcher = ContentSwitcher(initial="metrics-table")
        self._switcher = switcher
        with switcher:
            self._table = DataTable(zebra_stripes=True, id="metrics-table")
            yield self._table
            self._detail = TextArea(
                text="Run metrics (r) to view results.",
                read_only=True,
                show_cursor=False,
                soft_wrap=True,
                id="metrics-detail",
            )
            yield self._detail
        yield switcher

    def set_data(self, columns: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        """Update both views with the latest metrics."""
        self._columns = list(columns)
        self._rows = [list(row) for row in rows]
        self._render_table()
        self._render_detail()

    def clear(self) -> None:
        """Clear displayed results."""
        self._columns = []
        self._rows = []
        self._render_table()
        self._render_detail()

    def set_narrow_mode(self, narrow: bool) -> None:
        """Switch between table and stacked layout."""
        if self.narrow == narrow:
            return
        self.narrow = narrow

    def watch_narrow(self, narrow: bool) -> None:
        if self._switcher is None:
            return
        self._switcher.current = "metrics-detail" if narrow else "metrics-table"

    def _render_table(self) -> None:
        if self._table is None:
            return
        self._table.clear(columns=True)
        if not self._columns:
            return
        for column in self._columns:
            self._table.add_column(column)
        for row in self._rows:
            self._table.add_row(*row)

    def _render_detail(self) -> None:
        if self._detail is None:
            return
        lines = _format_vertical_rows(self._columns, self._rows)
        self._detail.load_text("\n".join(lines))


__all__ = ["MetricsView"]
