"""Command line interface for summoning and running glitchlings."""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path
import sys

from . import SAMPLE_TEXT
from .zoo import (
    Glitchling,
    Gaggle,
    jargoyle,
    mim1c,
    typogre,
    reduple,
    rushmore,
    redactyl,
    scannequin,
    summon,
)


BUILTIN_GLITCHLINGS: dict[str, Glitchling] = {
    g.name.lower(): g
    for g in [
        typogre,
        mim1c,
        jargoyle,
        reduple,
        rushmore,
        redactyl,
        scannequin,
    ]
}

DEFAULT_GLITCHLING_NAMES: list[str] = list(BUILTIN_GLITCHLINGS.keys())
MAX_NAME_WIDTH = max(len(glitchling.name) for glitchling in BUILTIN_GLITCHLINGS.values())


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    Returns:
        argparse.ArgumentParser: The configured argument parser instance.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Summon glitchlings to corrupt text. Provide input text as an argument, "
            "via --file, or pipe it on stdin."
        )
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Text to corrupt. If omitted, stdin is used or --sample provides fallback text.",
    )
    parser.add_argument(
        "-g",
        "--glitchling",
        dest="glitchlings",
        action="append",
        metavar="NAME",
        help="Glitchling to apply (repeat for multiples). Defaults to all built-ins.",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=151,
        help="Seed controlling deterministic corruption order (default: 151).",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Read input text from a file instead of the command line argument.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use the included SAMPLE_TEXT when no other input is provided.",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show a unified diff between the original and corrupted text.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available glitchlings and exit.",
    )
    return parser


def list_glitchlings() -> None:
    """Print information about the available built-in glitchlings."""

    for key in DEFAULT_GLITCHLING_NAMES:
        glitchling = BUILTIN_GLITCHLINGS[key]
        display_name = glitchling.name
        scope = glitchling.level.name.title()
        order = glitchling.order.name.lower()
        print(f"{display_name:>{MAX_NAME_WIDTH}} — scope: {scope}, order: {order}")


def read_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    """Resolve the input text based on CLI arguments.

    Args:
        args: Parsed arguments from the CLI.
        parser: The argument parser used for emitting user-facing errors.

    Returns:
        str: The text to corrupt.

    Raises:
        SystemExit: Raised indirectly via ``parser.error`` on failure.
    """

    if args.file is not None:
        try:
            return args.file.read_text(encoding="utf-8")
        except OSError as exc:
            filename = getattr(exc, "filename", None) or args.file
            reason = exc.strerror or str(exc)
            parser.error(f"Failed to read file {filename}: {reason}")

    if args.text:
        return args.text

    if not sys.stdin.isatty():
        return sys.stdin.read()

    if args.sample:
        return SAMPLE_TEXT

    parser.error(
        "No input text provided. Supply text as an argument, use --file, pipe input, or pass --sample."
    )
    raise AssertionError("parser.error should exit")


def summon_glitchlings(
    names: list[str] | None, parser: argparse.ArgumentParser, seed: int
) -> Gaggle:
    """Instantiate the requested glitchlings and bundle them in a ``Gaggle``.

    Args:
        names: Optional list of glitchling names provided by the user.
        parser: The argument parser used for emitting user-facing errors.
        seed: Master seed controlling deterministic corruption order.

    Returns:
        Gaggle: A ready-to-use collection of glitchlings.

    Raises:
        SystemExit: Raised indirectly via ``parser.error`` when a provided glitchling
        name is invalid.
    """

    if names:
        normalized = [name.lower() for name in names]
    else:
        normalized = DEFAULT_GLITCHLING_NAMES

    try:
        return summon(normalized, seed=seed)
    except ValueError as exc:
        parser.error(str(exc))
        raise AssertionError("parser.error should exit")


def show_diff(original: str, corrupted: str) -> None:
    """Display a unified diff between the original and corrupted text."""

    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            corrupted.splitlines(keepends=True),
            fromfile="original",
            tofile="corrupted",
            lineterm="",
        )
    )
    if diff_lines:
        for line in diff_lines:
            print(line)
    else:
        print("No changes detected.")


def run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Execute the CLI workflow using the provided arguments.

    Args:
        args: Parsed CLI arguments.
        parser: Argument parser used for error reporting.

    Returns:
        int: Exit code for the process (``0`` on success).
    """

    if args.list:
        list_glitchlings()
        return 0

    text = read_text(args, parser)
    gaggle = summon_glitchlings(args.glitchlings, parser, args.seed)

    corrupted = gaggle(text)

    if args.diff:
        show_diff(text, corrupted)
    else:
        print(corrupted)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``glitchlings`` command line interface.

    Args:
        argv: Optional list of command line arguments. Defaults to ``sys.argv``.

    Returns:
        int: Exit code suitable for use with ``sys.exit``.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    return run_cli(args, parser)


if __name__ == "__main__":
    sys.exit(main())
