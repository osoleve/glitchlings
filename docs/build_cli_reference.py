"""Regenerate README CLI examples so the documented outputs stay current."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MARKER_START = "<!-- BEGIN: CLI_USAGE -->"
MARKER_END = "<!-- END: CLI_USAGE -->"


def run_cli(command: list[str]) -> str:
    """Execute a CLI command and return its stdout, stripped of trailing space."""

    def execute(argv: list[str]) -> str:
        result = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        return result.stdout.rstrip()

    try:
        return execute(command)
    except FileNotFoundError:
        if command and command[0] == "glitchlings":
            fallback = [sys.executable, "-m", "glitchlings", *command[1:]]
            return execute(fallback)
        raise


def build_cli_usage_block() -> str:
    """Construct the Markdown block inserted into the README."""
    glitchling_list = run_cli(["glitchlings", "--list"])
    help_lines = run_cli(["glitchlings", "--help"]).splitlines()

    help_preview = "\n".join(help_lines[:30]).rstrip()
    if len(help_lines) > 30:
        help_preview += "\n…"

    block = f"""
```bash
# Discover which glitchlings are currently on the loose.
glitchlings --list
```

```text
{glitchling_list}
```

```bash
# Review the full CLI contract.
glitchlings --help
```

```text
{help_preview}
```
""".strip()
    return textwrap.dedent(block)


def replace_section(content: str, replacement: str) -> str:
    """Replace the block between sentinel markers with the new content."""
    if MARKER_START not in content or MARKER_END not in content:
        raise RuntimeError(
            "README is missing CLI usage markers. Expected "
            f"{MARKER_START!r} and {MARKER_END!r}."
        )

    before, _, remainder = content.partition(MARKER_START)
    _, _, after = remainder.partition(MARKER_END)

    return f"{before}{MARKER_START}\n{replacement}\n{MARKER_END}{after}"


def main() -> None:
    block = build_cli_usage_block()
    current = README.read_text(encoding="utf-8")
    updated = replace_section(current, block)
    README.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
