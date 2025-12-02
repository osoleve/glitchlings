"""Navigation panel for the Textual GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from .theme import themed_css

NavTab = Literal["workspace", "datasets", "sweeps", "charts", "compare"]

NAV_ITEMS: list[tuple[NavTab, str, str]] = [
    ("workspace", "⚡", "Workspace"),
    ("datasets", "📊", "Datasets"),
    ("sweeps", "🎚️", "Sweeps"),
    ("charts", "📈", "Charts"),
    ("compare", "🔍", "Compare"),
]


CSS = """
NavigationPanel {
    width: 100%;
    height: auto;
    max-height: 14;
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    margin-bottom: 1;
}

NavigationPanel .nav-header {
    height: 2;
    padding: 0 1;
    content-align: center middle;
    background: var(--glitch-surface);
    color: var(--glitch-accent);
    text-style: bold;
}

NavigationPanel ListView {
    background: transparent;
    padding: 0;
    height: auto;
    max-height: 10;
}

NavigationPanel ListItem {
    padding: 0 1;
    height: 2;
    color: var(--glitch-muted);
}

NavigationPanel ListItem:hover {
    background: var(--glitch-surface);
    color: var(--glitch-bright);
}

NavigationPanel ListItem.-active {
    background: var(--glitch-accent) 20%;
    color: var(--glitch-accent);
}

NavigationPanel ListItem.-active:hover {
    background: var(--glitch-accent) 30%;
}

NavigationPanel .nav-item-icon {
    width: 2;
    text-align: center;
}

NavigationPanel .nav-item-label {
    padding-left: 1;
}

NavigationPanel .nav-footer {
    height: auto;
    padding: 0 1;
    border-top: solid var(--glitch-border);
    color: var(--glitch-muted);
}
"""


@dataclass
class NavItem:
    """A navigation item in the sidebar."""

    id: NavTab
    icon: str
    label: str


class NavigationPanel(Static):  # type: ignore[misc]
    """Sidebar navigation panel for switching between major views."""

    DEFAULT_CSS = themed_css(CSS)
    BINDINGS = [
        Binding("1", "select_tab('workspace')", "Workspace", show=False),
        Binding("2", "select_tab('datasets')", "Datasets", show=False),
        Binding("3", "select_tab('sweeps')", "Sweeps", show=False),
        Binding("4", "select_tab('charts')", "Charts", show=False),
        Binding("5", "select_tab('compare')", "Compare", show=False),
    ]

    class TabSelected(Message):  # type: ignore[misc]
        """Posted when a navigation tab is selected."""

        def __init__(self, tab: NavTab) -> None:
            super().__init__()
            self.tab = tab

    def __init__(
        self,
        *,
        initial_tab: NavTab = "workspace",
        on_tab_change: Callable[[NavTab], None] | None = None,
    ) -> None:
        super().__init__()
        self._current_tab: NavTab = initial_tab
        self._on_tab_change = on_tab_change
        self._items = [NavItem(id=id_, icon=icon, label=label) for id_, icon, label in NAV_ITEMS]
        self._list_view: ListView | None = None

    def compose(self) -> ComposeResult:
        yield Static("NAVIGATION", classes="nav-header")
        self._list_view = ListView(
            *[
                ListItem(
                    Static(item.icon, classes="nav-item-icon"),
                    Static(item.label, classes="nav-item-label"),
                    id=f"nav-{item.id}",
                )
                for item in self._items
            ],
            id="nav-list",
        )
        yield self._list_view
        yield Static(
            Text.assemble(
                ("1-5 ", "dim"),
                ("switch tabs", ""),
            ),
            classes="nav-footer",
        )

    def on_mount(self) -> None:
        """Select the initial tab on mount."""
        self._highlight_current()

    def _highlight_current(self) -> None:
        """Update visual state for the current tab."""
        if not self._list_view:
            return
        for item in self._list_view.query(ListItem):
            item_id = item.id or ""
            tab_id = item_id.replace("nav-", "")
            if tab_id == self._current_tab:
                item.add_class("-active")
            else:
                item.remove_class("-active")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection."""
        if event.item.id:
            tab_id = event.item.id.replace("nav-", "")
            self._select_tab(tab_id)  # Dynamic from item.id

    def _select_tab(self, tab: NavTab) -> None:
        """Select a tab and notify listeners."""
        if tab == self._current_tab:
            return
        self._current_tab = tab
        self._highlight_current()
        if self._on_tab_change:
            self._on_tab_change(tab)
        self.post_message(self.TabSelected(tab))

    def action_select_tab(self, tab: str) -> None:
        """Action handler for keyboard shortcuts."""
        self._select_tab(tab)  # type: ignore[arg-type]

    @property
    def current_tab(self) -> NavTab:
        """The currently selected tab."""
        return self._current_tab
