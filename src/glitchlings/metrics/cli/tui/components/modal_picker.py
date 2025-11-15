"""Modal picker used for glitchling/tokenizer selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, SelectionList, Static
from textual.widgets.selection_list import Selection

from ..controller import build_glitchling_pipeline

GROUP_SENTINEL_PREFIX = "__group__"
"""Prefix applied to sentinel option values representing group headers."""

DEFAULT_HELP_TEXT = "Use ↑/↓ to browse, space to toggle, enter to apply."


@dataclass(slots=True)
class PickerRateControl:
    """Configuration for a numeric rate control."""

    key: str
    label: str
    default: float | None = None
    minimum: float = 0.0
    maximum: float = 1.0
    step: float = 0.01
    help_text: str | None = None


@dataclass(slots=True)
class PickerModeControl:
    """Configuration for a multi-select mode control."""

    key: str
    label: str
    options: Sequence[tuple[str, str]]
    default: Sequence[str] = ()
    help_text: str | None = None


PickerControl = PickerRateControl | PickerModeControl


@dataclass(slots=True)
class PickerFormDefinition:
    """Describes configurable controls for a picker entry."""

    controls: Sequence[PickerControl] = field(default_factory=tuple)


@dataclass(slots=True)
class PickerItem:
    """Represents a selectable entry inside the picker."""

    label: str
    value: str
    description: str | None = None
    group: str | None = None
    help_text: str | None = None
    form: PickerFormDefinition | None = None


class PickerModal(ModalScreen[list[dict[str, object]] | None]):  # type: ignore[misc]
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

    #picker-filter {
        margin-bottom: 1;
    }

    #picker-options {
        height: 1fr;
        border: tall $background 70%;
    }

    .picker-inline-help {
        min-height: 1;
        color: $text 70%;
        padding: 0.5 0;
    }

    #picker-form-container {
        border: heavy $background 60%;
        padding: 1;
        margin-top: 1;
        min-height: 3;
    }

    .picker-form-error {
        color: $warning;
        min-height: 1;
    }

    .picker-preview {
        border-top: heavy $background 60%;
        margin-top: 1;
        padding-top: 1;
    }
    """

    def __init__(
        self,
        title: str,
        items: Sequence[PickerItem],
        *,
        selected: Iterable[str] = (),
        form_state: Mapping[str, Mapping[str, object]] | None = None,
        extra_specs: Sequence[str] = (),
        preview_text: str | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._items = list(items)
        self._selected = set(selected)
        self._filter_text = ""
        self._option_list: SelectionList[str] | None = None
        self._filter_input: Input | None = None
        self._help_display: Static | None = None
        self._form_container: Vertical | None = None
        self._form_error_display: Static | None = None
        self._preview_display: Static | None = None
        self._preview_text = preview_text.strip() if preview_text else None
        self._extra_specs = list(extra_specs)
        self._form_definitions: dict[str, PickerFormDefinition] = {
            item.value: item.form for item in self._items if item.form
        }
        self._form_defaults: dict[str, dict[str, object]] = {
            key: _build_form_defaults(definition)
            for key, definition in self._form_definitions.items()
        }
        form_state = form_state or {}
        self._form_state: dict[str, dict[str, object]] = {
            key: dict(form_state.get(key, {})) for key in self._form_definitions
        }
        self._active_form_value: str | None = None
        self._form_errors: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-modal"):
            yield Static(self._title, classes="picker-title")
            filter_input = Input(placeholder="Filter choices", id="picker-filter")
            self._filter_input = filter_input
            yield filter_input
            option_list: SelectionList[str] = SelectionList(id="picker-options")
            self._option_list = option_list
            yield option_list
            self._help_display = Static(DEFAULT_HELP_TEXT, classes="picker-inline-help")
            yield self._help_display
            self._form_container = Vertical(id="picker-form-container")
            yield self._form_container
            self._form_error_display = Static("", classes="picker-form-error")
            yield self._form_error_display
            if self._preview_text:
                self._preview_display = Static(
                    "Preview updates as you toggle glitchlings.",
                    classes="picker-preview",
                )
                yield self._preview_display
            yield Static("Space = toggle • Enter = apply • Esc = cancel", classes="picker-help")

    def on_mount(self) -> None:
        self._rebuild_options()
        if self._option_list is not None:
            self._option_list.focus()
        self._show_form_for(None)
        self._update_preview()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
            return
        if event.key in {"enter", "return"}:
            event.stop()
            self.dismiss(self._selection())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "picker-filter":
            self._filter_text = event.value
            self._rebuild_options()
        elif event.input.id and event.input.id.startswith("form-input-"):
            self._handle_form_input(event)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox = event.checkbox
        checkbox_id = checkbox.id or ""
        if not checkbox_id.startswith("form-checkbox-"):
            return
        _, value, key, option = checkbox_id.split("|", 3)
        selection = self._form_state.setdefault(value, {})
        stored = selection.get(key)
        current = list(stored) if isinstance(stored, list) else []
        if checkbox.value and option not in current:
            current.append(option)
        elif not checkbox.value and option in current:
            current.remove(option)
        selection[key] = current
        self._clear_form_error(value)
        self._update_preview()

    def on_selection_list_selection_highlighted(
        self, message: SelectionList.SelectionHighlighted[str]
    ) -> None:
        value = message.selection.value
        if value.startswith(GROUP_SENTINEL_PREFIX):
            self._update_help_text(DEFAULT_HELP_TEXT)
            self._show_form_for(None)
            return
        item = self._find_item(value)
        if item is None:
            return
        self._update_help_text(item.help_text or DEFAULT_HELP_TEXT)
        self._show_form_for(value)

    def on_selection_list_selected_changed(
        self, _message: SelectionList.SelectedChanged[str]
    ) -> None:
        self._sync_selected_from_widget()
        self._update_preview()

    def _selection(self) -> list[dict[str, object]]:
        option_list = self._option_list
        if option_list is None:
            return []
        selected_values = self._current_selected_values()
        entries: list[dict[str, object]] = []
        for item in self._items:
            if item.value not in selected_values:
                continue
            entry: dict[str, object] = {
                "label": item.label,
                "value": item.value,
            }
            if item.description:
                entry["description"] = item.description
            params = self._effective_params(item.value)
            if params:
                entry["params"] = params
            entries.append(entry)
        return entries

    def _rebuild_options(self) -> None:
        option_list = self._option_list
        if option_list is None:
            return
        option_list.clear_options()
        last_group: str | None = None
        group_index = 0
        for item in self._filtered_items():
            group = item.group or "Choices"
            if group != last_group:
                last_group = group
                group_index += 1
                option_list.add_option(
                    Selection(
                        f"[b]{group}[/b]",
                        f"{GROUP_SENTINEL_PREFIX}:{group_index}",
                        disabled=True,
                    )
                )
            label = (
                f"{item.label} — {item.description}"
                if item.description
                else item.label
            )
            option_list.add_option((label, item.value, item.value in self._selected))
        self._sync_selected_from_widget()

    def _filtered_items(self) -> Iterable[PickerItem]:
        if not self._filter_text:
            return list(self._items)
        needle = self._filter_text.lower()
        return [
            item
            for item in self._items
            if needle in item.label.lower()
            or (item.description and needle in item.description.lower())
        ]

    def _sync_selected_from_widget(self) -> None:
        option_list = self._option_list
        if option_list is None:
            return
        values = {
            value
            for value in option_list.selected
            if not value.startswith(GROUP_SENTINEL_PREFIX)
        }
        self._selected = values

    def _current_selected_values(self) -> set[str]:
        option_list = self._option_list
        if option_list is None:
            return set()
        return {
            value
            for value in option_list.selected
            if not value.startswith(GROUP_SENTINEL_PREFIX)
        }

    def _find_item(self, value: str) -> PickerItem | None:
        for item in self._items:
            if item.value == value:
                return item
        return None

    def _show_form_for(self, value: str | None) -> None:
        container = self._form_container
        if container is None:
            return
        container.remove_children()
        self._active_form_value = value
        if value is None:
            container.mount(Static("Select an entry to view configuration."))
            return
        definition = self._form_definitions.get(value)
        if definition is None:
            container.mount(Static("This glitchling does not expose parameters."))
            return
        state = self._form_state.setdefault(value, {})
        for control in definition.controls:
            if isinstance(control, PickerRateControl):
                container.mount(Static(control.label))
                placeholder = (
                    f"Default: {control.default:.3f}"
                    if isinstance(control.default, (int, float))
                    else "Uses built-in defaults"
                )
                current_value = state.get(control.key)
                if isinstance(current_value, (int, float)):
                    display_value = f"{float(current_value):g}"
                else:
                    display_value = ""
                container.mount(
                    Input(
                        value=display_value,
                        placeholder=placeholder,
                        id=f"form-input-{value}-{control.key}",
                    )
                )
                if control.help_text:
                    container.mount(Static(control.help_text, classes="picker-inline-help"))
            elif isinstance(control, PickerModeControl):
                container.mount(Static(control.label))
                stored_modes = state.get(control.key)
                if isinstance(stored_modes, list):
                    selected_modes = set(stored_modes)
                else:
                    selected_modes = set(control.default)
                for option_label, option_value in control.options:
                    checkbox = Checkbox(
                        option_label,
                        value=option_value in selected_modes,
                        id=f"form-checkbox-{value}|{value}|{control.key}|{option_value}",
                        button_first=False,
                    )
                    container.mount(checkbox)
                if control.help_text:
                    container.mount(Static(control.help_text, classes="picker-inline-help"))

    def _handle_form_input(self, event: Input.Changed) -> None:
        if self._active_form_value is None:
            return
        _, _, rest = event.input.id.partition("form-input-")
        value, _, key = rest.partition("-")
        if not key:
            return
        text = event.value.strip()
        state = self._form_state.setdefault(value, {})
        if not text:
            state.pop(key, None)
            self._clear_form_error(value)
            self._update_preview()
            return
        try:
            numeric = float(text)
        except ValueError:
            self._form_errors.pop(value, None)
            self._form_errors[value] = "Rates must be numeric."
            self._update_form_error()
            return
        state[key] = numeric
        self._clear_form_error(value)
        self._update_preview()

    def _clear_form_error(self, value: str) -> None:
        if value in self._form_errors:
            self._form_errors.pop(value, None)
            self._update_form_error()

    def _update_form_error(self) -> None:
        display = self._form_error_display
        if display is None:
            return
        if not self._form_errors:
            display.update("")
            return
        # Show the most recent error message
        _, message = next(reversed(self._form_errors.items()))
        display.update(message)

    def _update_help_text(self, text: str) -> None:
        if self._help_display is None:
            return
        self._help_display.update(text)

    def _effective_params(self, value: str) -> dict[str, object] | None:
        state = self._form_state.get(value)
        if not state:
            return None
        defaults = self._form_defaults.get(value, {})
        overrides: dict[str, object] = {}
        for key, current in state.items():
            default_value = defaults.get(key)
            if _param_matches_default(current, default_value):
                continue
            if isinstance(current, list) and not current:
                continue
            overrides[key] = current
        return overrides or None

    def _update_preview(self) -> None:
        if not self._preview_text or self._preview_display is None:
            return
        specs = self._current_spec_strings(include_manual=True)
        try:
            glitch_id, runner = build_glitchling_pipeline(specs)
            before = self._preview_text
            after = runner(before)
            self._preview_display.update(
                f"[b]Preview ({glitch_id}):[/b]\n[b]Before:[/b] {before}\n[b]After:[/b] {after}"
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._preview_display.update(f"[b]Preview error:[/b] {exc}")

    def _current_spec_strings(self, *, include_manual: bool = False) -> list[str]:
        specs: list[str] = []
        for item in self._items:
            if item.value not in self._selected:
                continue
            params = self._effective_params(item.value)
            if params:
                specs.append(_format_spec(item.value, params))
            else:
                specs.append(item.value)
        if include_manual:
            specs.extend(self._extra_specs)
        return specs


def _build_form_defaults(definition: PickerFormDefinition) -> dict[str, object]:
    defaults: dict[str, object] = {}
    for control in definition.controls:
        if isinstance(control, PickerRateControl):
            defaults[control.key] = control.default
        elif isinstance(control, PickerModeControl):
            defaults[control.key] = list(control.default)
    return defaults


def _param_matches_default(value: object, default: object | None) -> bool:
    if isinstance(value, list) and isinstance(default, list):
        return value == default
    if isinstance(value, (float, int)) and isinstance(default, (float, int)):
        return abs(float(value) - float(default)) < 1e-9
    return value == default


def _format_spec(name: str, params: Mapping[str, object]) -> str:
    rendered = ", ".join(
        f"{key}={_format_value(value)}" for key, value in sorted(params.items())
    )
    return f"{name}({rendered})"


def _format_value(value: object) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (float, int)):
        return repr(value)
    if isinstance(value, list):
        inner = ", ".join(_format_value(entry) for entry in value)
        return f"[{inner}]"
    if value is None:
        return "None"
    return repr(value)


__all__ = [
    "PickerFormDefinition",
    "PickerItem",
    "PickerModal",
    "PickerModeControl",
    "PickerRateControl",
]
