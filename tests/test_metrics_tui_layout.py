"""Smoke tests for the metrics TUI layout."""

import asyncio

from glitchlings.metrics.cli.tui.app import MetricsApp
from glitchlings.metrics.cli.tui.controller import ControllerOptions, MetricsTUIController
from glitchlings.metrics.core.session import MetricsSession


def test_metrics_app_mounts_and_handles_breakpoints() -> None:
    session = MetricsSession()
    controller = MetricsTUIController(
        session,
        ControllerOptions(
            text="Sample text for layout smoke test.",
            glitchling_specs=["identity"],
            tokenizer_specs=["simple"],
        ),
    )
    app = MetricsApp(controller)

    async def run() -> None:
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            app_body = app.query_one("#app-body")
            token_panel = app.query_one("#token-diff-panel")

            assert not app_body.has_class("narrow")
            assert token_panel.has_class("hidden")

            pilot.app.action_toggle_token_diff()
            await pilot.pause()
            assert not token_panel.has_class("hidden")

            await pilot.resize_terminal(80, 40)
            await pilot.pause()
            assert app_body.has_class("narrow")

            pilot.app.action_toggle_token_diff()
            await pilot.pause()
            assert token_panel.has_class("hidden")

    asyncio.run(run())
