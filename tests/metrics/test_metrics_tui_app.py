import asyncio

from glitchlings.metrics.cli.tui.app import HELP_SHORTCUTS, MetricsApp
from glitchlings.metrics.cli.tui.components import InfoDialog
from glitchlings.metrics.cli.tui.controller import ControllerOptions, MetricsTUIController
from glitchlings.metrics.core.session import MetricsSession


def test_help_overlay_renders() -> None:
    async def _run() -> None:
        controller = MetricsTUIController(MetricsSession(), ControllerOptions(text="demo"))
        app = MetricsApp(controller)
        async with app.run_test() as pilot:
            await pilot.press("?")
            assert any(isinstance(screen, InfoDialog) for screen in app.screen_stack)

    asyncio.run(_run())


def test_metrics_app_bindings_omit_unused_tab_actions() -> None:
    binding_actions = {binding.action for binding in MetricsApp.BINDINGS}
    assert "tab_next" not in binding_actions
    assert "tab_previous" not in binding_actions
    binding_keys = {binding.key for binding in MetricsApp.BINDINGS}
    assert "t" in binding_keys
    assert "b" in binding_keys


def test_help_shortcuts_cover_context_picker_and_quit() -> None:
    shortcut_keys = {keys for keys, _ in HELP_SHORTCUTS}
    assert "c" in shortcut_keys
    assert "q / Esc" in shortcut_keys
