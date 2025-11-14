"""Modal picker used for glitchling/tokenizer selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import SelectionList, Static


@dataclass(slots=True)
class PickerItem:
    """Represents a selectable entry inside the picker."""

    label: str
    value: str
    description: str | None = None


class PickerModal(ModalScreen[list[str] | None]):  # type: ignore[misc]
    """Full-screen picker that supports toggling entries."""

    DEFAULT_CSS = """
    PickerModal {
        align: center middle;
    }

    PickerModal > Vertical {
        width: 90%;
        height: 90%;
        border: tall $primary;
        padding: 1 2;
        background: $surface;
    }

    .picker-title {
        padding-bottom: 1;
    }

    .picker-help {
        padding-top: 1;
        color: $text 70%;
    }

    #picker-options {
        height: 1fr;
        border: tall $background 70%;
    }
    """

    def __init__(
        self,
        title: str,
        items: Sequence[PickerItem],
        *,
        selected: Iterable[str] = (),
    ) -> None:
        super().__init__()
        self._title = title
        self._items = list(items)
        self._selected = set(selected)
        self._option_list: SelectionList[str] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-modal"):
            yield Static(self._title, classes="picker-title")
            option_list: SelectionList[str] = SelectionList(id="picker-options")
            self._option_list = option_list
            for item in self._items:
                label = f"{item.label} [{item.description}]" if item.description else item.label
                option_list.add_option((label, item.value, item.value in self._selected))
            yield option_list
            yield Static("Space = toggle • Enter = apply • Esc = cancel", classes="picker-help")

    def on_mount(self) -> None:
        if self._option_list is not None:
            self._option_list.focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
            return
        if event.key in {"enter", "return"}:
            event.stop()
            self.dismiss(self._selection())

    def _selection(self) -> list[str]:
        option_list = self._option_list
        if option_list is None:
            return []
        return list(option_list.selected)


__all__ = ["PickerItem", "PickerModal"]
