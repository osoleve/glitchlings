"""Glitchling configuration panel for selecting and configuring glitchlings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Checkbox, Input, Label, Static

from glitchlings.zoo import BUILTIN_GLITCHLINGS, Glitchling

from .theme import themed_css

CSS = """
GlitchlingPanel {
    width: 100%;
    height: auto;
    min-height: 8;
    max-height: 18;
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    margin-bottom: 1;
}

GlitchlingPanel .panel-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    color: var(--glitch-accent);
    text-style: bold;
    content-align: left middle;
}

GlitchlingPanel .glitchling-list {
    height: 1fr;
    min-height: 6;
    padding: 0;
    background: transparent;
    overflow-y: auto;
}

GlitchlingPanel .glitchling-item {
    height: auto;
    padding: 0;
    background: transparent;
}

GlitchlingPanel .glitchling-header {
    height: 2;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
}

GlitchlingPanel .glitchling-checkbox {
    width: auto;
    padding-right: 1;
}

GlitchlingPanel .glitchling-name {
    width: 1fr;
    color: var(--glitch-ink);
}

GlitchlingPanel .glitchling-name.-enabled {
    color: var(--glitch-bright);
    text-style: bold;
}

GlitchlingPanel .glitchling-params {
    height: auto;
    padding-left: 3;
    display: none;
}

GlitchlingPanel .glitchling-params.-visible {
    display: block;
}

GlitchlingPanel .param-row {
    height: 2;
    layout: horizontal;
    align: left middle;
}

GlitchlingPanel .param-label {
    width: 12;
    color: var(--glitch-muted);
}

GlitchlingPanel .param-input {
    width: 14;
    height: 1;
}

GlitchlingPanel .param-input Input {
    height: 1;
    min-height: 1;
    background: var(--glitch-bg);
    color: var(--glitch-ink);
    border: solid var(--glitch-border);
}
"""


@dataclass
class GlitchlingConfig:
    """Configuration for a single glitchling."""

    cls: type[Glitchling]
    enabled: bool
    params: dict[str, Any]


def get_glitchling_params(cls: type[Glitchling]) -> dict[str, tuple[type, Any]]:
    """Extract configurable parameters from a glitchling class."""
    import inspect

    params: dict[str, tuple[type, Any]] = {}
    sig = inspect.signature(cls.__init__)

    for name, param in sig.parameters.items():
        if name in ("self", "seed", "kwargs"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        # Get default value
        default = param.default if param.default is not param.empty else None

        # Determine type
        if param.annotation is not param.empty:
            param_type = param.annotation
        elif default is not None:
            param_type = type(default)
        else:
            param_type = str

        # Only include numeric and boolean params for now
        if param_type in (int, float, bool) or (
            hasattr(param_type, "__origin__") and param_type.__origin__ is type
        ):
            params[name] = (param_type, default)

    return params


class GlitchlingItem(Static):  # type: ignore[misc]
    """A single glitchling with checkbox and parameter inputs."""

    class ConfigChanged(Message):  # type: ignore[misc]
        """Posted when configuration changes."""

        def __init__(self, cls: type[Glitchling], enabled: bool, params: dict[str, Any]) -> None:
            super().__init__()
            self.cls = cls
            self.enabled = enabled
            self.params = params

    def __init__(self, cls: type[Glitchling], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._cls = cls
        self._enabled = False
        self._param_specs = get_glitchling_params(cls)
        self._param_values: dict[str, Any] = {
            name: default for name, (_, default) in self._param_specs.items()
        }
        self._param_inputs: dict[str, Input] = {}
        self._checkbox: Checkbox | None = None
        self._name_label: Label | None = None
        self._params_container: Container | None = None

    def compose(self) -> ComposeResult:
        with Container(classes="glitchling-item"):
            with Horizontal(classes="glitchling-header"):
                self._checkbox = Checkbox("", id=f"check-{self._cls.__name__}")
                yield self._checkbox
                self._name_label = Label(self._cls.__name__, classes="glitchling-name")
                yield self._name_label

            self._params_container = Container(classes="glitchling-params")
            with self._params_container:
                for name, (param_type, default) in self._param_specs.items():
                    with Horizontal(classes="param-row"):
                        yield Label(f"{name}:", classes="param-label")
                        inp = Input(
                            str(default) if default is not None else "",
                            id=f"param-{self._cls.__name__}-{name}",
                            classes="param-input",
                        )
                        self._param_inputs[name] = inp
                        yield inp
            yield self._params_container

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox toggle."""
        self._enabled = event.value
        if self._name_label:
            if self._enabled:
                self._name_label.add_class("-enabled")
            else:
                self._name_label.remove_class("-enabled")
        if self._params_container:
            if self._enabled and self._param_specs:
                self._params_container.add_class("-visible")
            else:
                self._params_container.remove_class("-visible")
        self._notify_change()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle parameter input changes."""
        input_id = event.input.id or ""
        if not input_id.startswith(f"param-{self._cls.__name__}-"):
            return

        param_name = input_id.replace(f"param-{self._cls.__name__}-", "")
        if param_name not in self._param_specs:
            return

        param_type, _ = self._param_specs[param_name]
        try:
            if param_type is bool:
                self._param_values[param_name] = event.value.lower() in ("true", "1", "yes")
            elif param_type is int:
                self._param_values[param_name] = int(event.value) if event.value else 0
            elif param_type is float:
                self._param_values[param_name] = float(event.value) if event.value else 0.0
            else:
                self._param_values[param_name] = event.value
        except ValueError:
            pass  # Keep old value on parse error

        self._notify_change()

    def _notify_change(self) -> None:
        """Post a config changed message."""
        self.post_message(self.ConfigChanged(self._cls, self._enabled, dict(self._param_values)))

    @property
    def config(self) -> GlitchlingConfig:
        """Get the current configuration."""
        return GlitchlingConfig(
            cls=self._cls, enabled=self._enabled, params=dict(self._param_values)
        )


class GlitchlingPanel(Static):  # type: ignore[misc]
    """Panel for selecting and configuring glitchlings."""

    DEFAULT_CSS = themed_css(CSS)

    class SelectionChanged(Message):  # type: ignore[misc]
        """Posted when glitchling selection changes."""

        def __init__(self, configs: list[tuple[type[Glitchling], dict[str, Any]]]) -> None:
            super().__init__()
            self.configs = configs

    def __init__(
        self,
        *,
        glitchlings: Sequence[type[Glitchling]] | None = None,
        on_change: Callable[[list[tuple[type[Glitchling], dict[str, Any]]]], None] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        if glitchlings is not None:
            self._glitchlings = list(glitchlings)
        else:
            # Get types from the builtin registry
            self._glitchlings = [type(g) for g in BUILTIN_GLITCHLINGS.values()]
        self._on_change = on_change
        self._items: dict[str, GlitchlingItem] = {}

    def compose(self) -> ComposeResult:
        yield Static("GLITCHLINGS", classes="panel-header")
        with VerticalScroll(classes="glitchling-list"):
            for cls in self._glitchlings:
                item = GlitchlingItem(cls, id=f"glitchling-{cls.__name__}")
                self._items[cls.__name__] = item
                yield item

    def on_glitchling_item_config_changed(self, event: GlitchlingItem.ConfigChanged) -> None:
        """Handle individual glitchling config changes."""
        self._notify_selection_change()

    def _notify_selection_change(self) -> None:
        """Notify listeners of selection changes."""
        configs = self.get_enabled_glitchlings()
        if self._on_change:
            self._on_change(configs)
        self.post_message(self.SelectionChanged(configs))

    def get_enabled_glitchlings(self) -> list[tuple[type[Glitchling], dict[str, Any]]]:
        """Get list of enabled glitchlings with their parameters."""
        result: list[tuple[type[Glitchling], dict[str, Any]]] = []
        for item in self._items.values():
            cfg = item.config
            if cfg.enabled:
                result.append((cfg.cls, cfg.params))
        return result

    def get_all_configs(self) -> list[GlitchlingConfig]:
        """Get all glitchling configurations."""
        return [item.config for item in self._items.values()]
