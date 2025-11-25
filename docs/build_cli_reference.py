"""Regenerate the CLI reference page so it mirrors the live contract."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI_DOC = ROOT / "docs" / "cli.md"
HELP_PREVIEW_LINES = 40


def run_cli(command: list[str]) -> str:
    """Execute a CLI command and return its stdout, stripped of trailing space."""

    env = os.environ.copy()
    env["COLUMNS"] = "80"

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
        env=env,
    )
    return result.stdout.rstrip()


def _build_help_preview(help_output: str) -> str:
    """Truncate the CLI help text for a concise preview block."""

    help_lines = help_output.splitlines()
    if help_lines:
        help_lines[0] = help_lines[0].replace("__main__.py", "glitchlings")

    preview = "\n".join(help_lines[:HELP_PREVIEW_LINES]).rstrip()
    if len(help_lines) > HELP_PREVIEW_LINES:
        preview += "\n..."
    return preview


def build_cli_reference() -> str:
    """Construct the Markdown for the CLI reference page."""

    glitchling_list = run_cli(["glitchlings", "--list"])
    help_preview = _build_help_preview(run_cli(["glitchlings", "--help"]))
    quickstart = """
```bash
# Discover all built-in glitchlings.
glitchlings --list

# Glitch an entire file with Typogre and inspect the unified diff.
glitchlings -g typogre --file documents/report.txt --diff

# Configure glitchlings inline with keyword arguments.
glitchlings -g "Typogre(rate=0.05)" "Ghouls just wanna have fun"

# Pipe text through Mim1c for on-the-fly homoglyph swaps.
echo "Beware LLM-written flavor-text" | glitchlings -g mim1c
```
""".strip()

    return textwrap.dedent(
        f"""\
# Command Line Interface

The `glitchlings` CLI mirrors the Python API for corruption, configuration files, and dataset
helpers. Regenerate this page with `python -m glitchlings.dev.docs` whenever the CLI contract
changes.

## Quick commands

{quickstart}

## Built-in glitchlings

```text
{glitchling_list}
```

## Help overview

```text
{help_preview}
```
"""
    )


def main() -> None:
    CLI_DOC.write_text(build_cli_reference(), encoding="utf-8")


if __name__ == "__main__":
    main()
