"""Command palette commands for Glitchlings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.command import Hit, Hits, Provider

if TYPE_CHECKING:
    from .app import GlitchlingsTextualApp


class GlitchlingCommands(Provider):  # type: ignore[misc]
    """Command provider for glitchling operations."""

    @property
    def _app(self) -> "GlitchlingsTextualApp":
        from .app import GlitchlingsTextualApp

        assert isinstance(self.app, GlitchlingsTextualApp)
        return self.app

    async def search(self, query: str) -> Hits:
        """Search for commands matching the query."""
        matcher = self.matcher(query)

        commands = [
            # Transform commands
            ("Transform", "Apply glitchlings to input text (F5)", "run_transform"),
            ("Randomize Seed", "Generate a new random seed", "randomize_seed"),
            # Edit commands
            ("Copy Output", "Copy transformed text to clipboard", "copy_output"),
            ("Paste Input", "Paste from clipboard to input", "paste_input"),
            ("Clear Input", "Clear the input text area", "clear_input"),
            ("Copy Input", "Copy input text to clipboard", "copy_input"),
            # Toggle commands
            ("Toggle Auto-Update", "Toggle auto transform", "toggle_auto_update"),
            ("Toggle Multi-Seed", "Toggle multi-seed mode", "toggle_multi_seed"),
            # Session commands
            ("New Session", "Clear and start fresh", "new_session"),
            # File commands
            ("Import Text", "Load text from a file", "import_text"),
            ("Export Text", "Save output to a file", "export_text"),
            ("Export Report", "Generate a report", "export_report"),
        ]

        for name, description, action in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    partial=lambda a=action: self._run_action(a),
                    help=description,
                )

    async def _run_action(self, action: str) -> None:
        """Run an app action."""
        if action == "clear_input":
            if self._app._workspace_panel:
                self._app._workspace_panel.action_clear_input()
        elif action == "toggle_auto_update":
            if self._app._auto_update_checkbox:
                self._app._auto_update_checkbox.toggle()
        elif action == "toggle_multi_seed":
            if self._app._seed_control and self._app._seed_control._multi_checkbox:
                self._app._seed_control._multi_checkbox.toggle()
        elif action == "copy_input":
            if self._app._workspace_panel:
                try:
                    import pyperclip

                    pyperclip.copy(self._app._workspace_panel.input_text)
                    self._app.notify("Input copied to clipboard", severity="information")
                except ImportError:
                    self._app.notify("Clipboard not available", severity="warning")
        elif action == "new_session":
            if self._app._workspace_panel:
                self._app._workspace_panel.action_clear_input()
                self._app._workspace_panel.set_output("")
            self._app.notify("New session started", severity="information")
        elif action == "import_text":
            self._app.notify("File import not yet implemented", severity="warning")
        elif action == "export_text":
            self._app.notify("File export not yet implemented", severity="warning")
        elif action == "export_report":
            self._app.notify("Report export not yet implemented", severity="warning")
        else:
            await self._app.run_action(action)
