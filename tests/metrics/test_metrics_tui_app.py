import asyncio

from glitchlings.metrics.cli.tui.app import MetricsApp
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
