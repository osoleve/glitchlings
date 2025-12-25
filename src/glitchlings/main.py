"""Command line interface for summoning and running glitchlings."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from collections.abc import Sequence
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Any, cast

import yaml

from . import SAMPLE_TEXT
from .attack import Attack
from .conf import DEFAULT_ATTACK_SEED, build_gaggle, load_attack_config
from .zoo import (
    BUILTIN_GLITCHLINGS,
    DEFAULT_GLITCHLING_NAMES,
    Gaggle,
    Glitchling,
    parse_glitchling_spec,
    summon,
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MAX_NAME_WIDTH = max(len(glitchling.name) for glitchling in BUILTIN_GLITCHLINGS.values())

# ANSI color codes
_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}


def _supports_color() -> bool:
    """Check if the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


class _ColorFormatter:
    """Simple color formatter that respects --no-color and NO_COLOR env."""

    def __init__(self, *, enabled: bool = True):
        self.enabled = enabled and _supports_color()

    def _wrap(self, text: str, *codes: str) -> str:
        if not self.enabled:
            return text
        prefix = "".join(_COLORS.get(c, "") for c in codes)
        return f"{prefix}{text}{_COLORS['reset']}"

    def bold(self, text: str) -> str:
        return self._wrap(text, "bold")

    def dim(self, text: str) -> str:
        return self._wrap(text, "dim")

    def red(self, text: str) -> str:
        return self._wrap(text, "red")

    def green(self, text: str) -> str:
        return self._wrap(text, "green")

    def yellow(self, text: str) -> str:
        return self._wrap(text, "yellow")

    def cyan(self, text: str) -> str:
        return self._wrap(text, "cyan")

    def magenta(self, text: str) -> str:
        return self._wrap(text, "magenta")


# Global color formatter, initialized based on args
_color = _ColorFormatter(enabled=True)


# -----------------------------------------------------------------------------
# Argument Parser
# -----------------------------------------------------------------------------

_EXAMPLES = """\
Examples:
  glitchlings "Hello world"                      Corrupt text with defaults
  glitchlings -g Typogre -g Mim1c "text"         Apply specific glitchlings
  glitchlings -g "Typogre(rate=0.1)" "text"      Configure parameters
  glitchlings -dS                                Diff the sample text
  glitchlings -i input.txt -o output.txt         File I/O
  echo "text" | glitchlings                      Pipe input
  glitchlings -l                                 List available glitchlings
  glitchlings -arS                               Attack report on sample
"""


def build_parser(
    *,
    exit_on_error: bool = True,
    include_text: bool = True,
) -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    Returns:
        argparse.ArgumentParser: The configured argument parser instance.

    """
    try:
        pkg_version = get_version("glitchlings")
    except Exception:
        pkg_version = "unknown"

    parser = argparse.ArgumentParser(
        prog="glitchlings",
        description=(
            "Summon glitchlings to corrupt text. Provide input text as an argument, "
            "via --input-file, or pipe it on stdin."
        ),
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        exit_on_error=exit_on_error,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"glitchlings {pkg_version}",
    )

    # -------------------------------------------------------------------------
    # Input/Output group
    # -------------------------------------------------------------------------
    io_group = parser.add_argument_group("Input/Output")

    if include_text:
        io_group.add_argument(
            "text",
            nargs="*",
            help="Text to corrupt. If omitted, reads from stdin or uses --sample.",
        )

    io_group.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=Path,
        metavar="FILE",
        help="Read input text from FILE.",
    )
    io_group.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        type=Path,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    io_group.add_argument(
        "-S",
        "--sample",
        action="store_true",
        help="Use built-in sample text (Kafka's Metamorphosis excerpt).",
    )

    # -------------------------------------------------------------------------
    # Glitchling Selection group
    # -------------------------------------------------------------------------
    glit_group = parser.add_argument_group("Glitchling Selection")

    glit_group.add_argument(
        "-g",
        "--glitchling",
        dest="glitchlings",
        action="append",
        metavar="SPEC",
        help=(
            "Glitchling to apply, e.g. Typogre or 'Typogre(rate=0.05)'. "
            "Repeat -g for multiples. Defaults to Typogre+Scannequin."
        ),
    )
    glit_group.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="FILE",
        help="Load glitchlings from a YAML config file.",
    )
    glit_group.add_argument(
        "-s",
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help=f"Seed for deterministic corruption (default: {DEFAULT_ATTACK_SEED}).",
    )
    glit_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all available glitchlings and exit.",
    )

    # -------------------------------------------------------------------------
    # Output Format group
    # -------------------------------------------------------------------------
    out_group = parser.add_argument_group("Output Format")

    out_group.add_argument(
        "-d",
        "--diff",
        action="store_true",
        help="Show unified diff between original and corrupted text.",
    )
    out_group.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        help="Disable colored output.",
    )

    # -------------------------------------------------------------------------
    # Analysis group
    # -------------------------------------------------------------------------
    analysis_group = parser.add_argument_group("Analysis")

    analysis_group.add_argument(
        "-a",
        "--attack",
        action="store_true",
        help="Output attack summary with metrics (no token lists).",
    )
    analysis_group.add_argument(
        "-r",
        "--report",
        action="store_true",
        help="Output full attack report with tokens and metrics.",
    )
    analysis_group.add_argument(
        "-f",
        "--format",
        dest="output_format",
        choices=["json", "yaml", "yml"],
        default="json",
        metavar="FMT",
        help="Output format for -a/-r: json, yaml (default: json).",
    )
    analysis_group.add_argument(
        "-t",
        "--tokenizer",
        dest="tokenizer",
        metavar="NAME",
        help="Tokenizer for analysis (e.g. cl100k_base, gpt-4, bert-base-uncased).",
    )

    # -------------------------------------------------------------------------
    # Verbosity group
    # -------------------------------------------------------------------------
    verb_group = parser.add_argument_group("Verbosity")

    verb_group.add_argument(
        "-V",
        "--verbose",
        action="store_true",
        help="Show detailed processing information.",
    )
    verb_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-essential output.",
    )

    return parser


# -----------------------------------------------------------------------------
# Listing Glitchlings
# -----------------------------------------------------------------------------


def _get_glitchling_description(glitchling: Glitchling) -> str:
    """Extract a short description from a glitchling's docstring."""
    cls = type(glitchling)
    doc = cls.__doc__
    if not doc:
        return ""
    # Get first sentence from first line
    first_line = doc.strip().split("\n")[0].strip()
    # Remove "Glitchling that" prefix if present for brevity
    if first_line.lower().startswith("glitchling that "):
        first_line = first_line[16:].capitalize()
    # Truncate if too long
    max_desc_len = 50
    if len(first_line) > max_desc_len:
        first_line = first_line[: max_desc_len - 3].rsplit(" ", 1)[0] + "..."
    return first_line


def list_glitchlings(*, color: _ColorFormatter | None = None) -> None:
    """Print information about all available built-in glitchlings."""
    c = color or _color

    # Sort alphabetically for consistent display
    sorted_names = sorted(BUILTIN_GLITCHLINGS.keys())

    for key in sorted_names:
        glitchling = BUILTIN_GLITCHLINGS[key]
        display_name = glitchling.name
        scope = glitchling.level.name.title()
        order = glitchling.order.name.lower()
        desc = _get_glitchling_description(glitchling)

        name_str = c.bold(f"{display_name:>{MAX_NAME_WIDTH}}")
        scope_str = c.cyan(scope)
        order_str = c.dim(order)
        desc_str = c.dim(desc) if desc else ""

        if desc:
            print(f"{name_str} — {desc_str}")
            pad = " " * MAX_NAME_WIDTH
            print(f"{pad}   {c.dim('scope:')} {scope_str}, {c.dim('order:')} {order_str}")
        else:
            print(f"{name_str} — {c.dim('scope:')} {scope_str}, {c.dim('order:')} {order_str}")


# -----------------------------------------------------------------------------
# Input Handling
# -----------------------------------------------------------------------------


def _suggest_glitchling(name: str) -> str | None:
    """Suggest a similar glitchling name if one exists."""
    available = list(BUILTIN_GLITCHLINGS.keys())
    matches = difflib.get_close_matches(name.lower(), available, n=1, cutoff=0.6)
    if matches:
        # Return with proper casing
        return BUILTIN_GLITCHLINGS[matches[0]].name
    return None


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
    file_path = cast(Path | None, getattr(args, "input_file", None))
    if file_path is not None:
        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as exc:
            filename = getattr(exc, "filename", None) or file_path
            reason = exc.strerror or str(exc)
            parser.error(f"Failed to read file {filename}: {reason}")

    text_argument = cast(str | list[str] | None, getattr(args, "text", None))
    if isinstance(text_argument, list):
        if text_argument:
            return " ".join(text_argument)
        text_argument = None
    if isinstance(text_argument, str) and text_argument:
        return text_argument

    if not sys.stdin.isatty():
        return sys.stdin.read()

    if bool(getattr(args, "sample", False)):
        return SAMPLE_TEXT

    # Friendly error message with examples
    error_lines = [
        "No input text provided.",
        "",
        "Try one of:",
        '  glitchlings "your text here"',
        "  glitchlings -S                 (use sample text)",
        "  glitchlings -i FILE            (read from file)",
        "  cat file.txt | glitchlings     (pipe input)",
    ]
    parser.error("\n".join(error_lines))
    raise AssertionError("parser.error should exit")


def summon_glitchlings(
    names: list[str] | None,
    parser: argparse.ArgumentParser,
    seed: int | None,
    *,
    config_path: Path | None = None,
) -> Gaggle:
    """Instantiate the requested glitchlings and bundle them in a ``Gaggle``."""
    if config_path is not None:
        if names:
            parser.error("Cannot combine --config with --glitchling.")
            raise AssertionError("parser.error should exit")

        try:
            config = load_attack_config(config_path)
        except (TypeError, ValueError) as exc:
            parser.error(str(exc))
            raise AssertionError("parser.error should exit")

        return build_gaggle(config, seed_override=seed)

    normalized: Sequence[str | Glitchling]
    if names:
        parsed: list[str | Glitchling] = []
        for specification in names:
            try:
                parsed.append(parse_glitchling_spec(specification))
            except ValueError as exc:
                # Try to suggest a correction
                error_msg = str(exc)
                if "not found" in error_msg.lower():
                    # Extract the name from the error
                    match = re.search(r"'([^']+)'", error_msg)
                    if match:
                        bad_name = match.group(1)
                        suggestion = _suggest_glitchling(bad_name)
                        if suggestion:
                            error_msg = f"{error_msg} Did you mean '{suggestion}'?"
                parser.error(error_msg)
                raise AssertionError("parser.error should exit")
        normalized = parsed
    else:
        normalized = list(DEFAULT_GLITCHLING_NAMES)

    effective_seed = seed if seed is not None else DEFAULT_ATTACK_SEED

    try:
        return summon(list(normalized), seed=effective_seed)
    except ValueError as exc:
        parser.error(str(exc))
        raise AssertionError("parser.error should exit")


# -----------------------------------------------------------------------------
# Diff Output
# -----------------------------------------------------------------------------


def show_diff(
    original: str,
    corrupted: str,
    *,
    color: _ColorFormatter | None = None,
) -> None:
    """Display a unified diff between the original and corrupted text."""
    c = color or _color

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
            if line.startswith("---") or line.startswith("+++"):
                print(c.bold(line))
            elif line.startswith("@@"):
                print(c.cyan(line))
            elif line.startswith("-"):
                print(c.red(line))
            elif line.startswith("+"):
                print(c.green(line))
            else:
                print(line)
    else:
        print(c.dim("No changes detected."))


# -----------------------------------------------------------------------------
# Report Formatting
# -----------------------------------------------------------------------------


def _format_report_json(payload: dict[str, Any]) -> str:
    """Format a report payload as JSON with compact token arrays.

    Token lists are formatted on a single line for readability, while
    other structures retain standard indented formatting.
    """
    # Keys whose values should be formatted compactly (single line)
    compact_keys = {
        "input_tokens",
        "output_tokens",
        "input_token_ids",
        "output_token_ids",
    }

    # First, serialize with standard formatting
    raw = json.dumps(payload, indent=2)

    # Then compact token arrays: find multi-line arrays for compact_keys
    for key in compact_keys:
        # Pattern matches: "key": [\n    items...\n  ]
        # and replaces with: "key": [items...]
        pattern = rf'("{key}":\s*)\[\s*\n((?:\s+.*?\n)*?)\s*\]'

        def compact_array(match: re.Match[str]) -> str:
            prefix = match.group(1)
            content = match.group(2)
            # Extract items from the multi-line content
            items = re.findall(r"(?:^\s+)(.+?)(?:,?\s*$)", content, re.MULTILINE)
            return f"{prefix}[{', '.join(items)}]"

        raw = re.sub(pattern, compact_array, raw)

    return raw


def _write_output(content: str, output_file: Path | None) -> None:
    """Write content to output file or stdout."""
    if output_file is not None:
        output_file.write_text(content, encoding="utf-8")
    else:
        print(content, end="" if content.endswith("\n") else "\n")


# -----------------------------------------------------------------------------
# Verbose Output
# -----------------------------------------------------------------------------


def _log_verbose(message: str, *, verbose: bool, quiet: bool) -> None:
    """Print a message if verbose mode is enabled and not quiet."""
    if verbose and not quiet:
        print(f"{_color.dim('[verbose]')} {message}", file=sys.stderr)


# -----------------------------------------------------------------------------
# Main CLI Logic
# -----------------------------------------------------------------------------


def run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Execute the CLI workflow using the provided arguments.

    Args:
        args: Parsed CLI arguments.
        parser: Argument parser used for error reporting.

    Returns:
        int: Exit code for the process (``0`` on success).

    """
    global _color

    # Initialize color formatter based on args
    no_color = getattr(args, "no_color", False)
    _color = _ColorFormatter(enabled=not no_color)

    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)

    if verbose and quiet:
        parser.error("Cannot combine --verbose with --quiet.")
        raise AssertionError("parser.error should exit")

    if args.list:
        list_glitchlings(color=_color)
        return 0

    wants_attack = bool(getattr(args, "attack", False))
    wants_report = bool(getattr(args, "report", False))

    if wants_attack and wants_report:
        parser.error("Cannot combine --attack with --report. Use one or the other.")
        raise AssertionError("parser.error should exit")

    wants_metrics = wants_attack or wants_report
    if wants_metrics and args.diff:
        parser.error("--diff cannot be combined with --report/--attack output.")
        raise AssertionError("parser.error should exit")

    # Get output file path
    output_file = cast(Path | None, getattr(args, "output_file", None))

    # Validate --diff and --output-file are not combined
    if args.diff and output_file:
        parser.error("--diff cannot be combined with --output-file.")
        raise AssertionError("parser.error should exit")

    # Normalize output format
    output_format = cast(str, args.output_format)
    normalized_format = "yaml" if output_format == "yml" else output_format

    # Validate --format is only used with --attack or --report
    if output_format != "json" and not wants_metrics:
        parser.error("--format requires --attack or --report.")
        raise AssertionError("parser.error should exit")

    # Validate tokenizer is only used with --attack or --report
    tokenizer_spec = cast(str | None, getattr(args, "tokenizer", None))
    if tokenizer_spec and not wants_metrics:
        parser.error("--tokenizer requires --attack or --report.")
        raise AssertionError("parser.error should exit")

    text = read_text(args, parser)
    _log_verbose(f"Input text: {len(text)} characters", verbose=verbose, quiet=quiet)

    gaggle = summon_glitchlings(
        args.glitchlings,
        parser,
        args.seed,
        config_path=args.config,
    )

    if verbose and not quiet:
        # Use _clones_by_index to get the actual glitchling instances
        clones = getattr(gaggle, "_clones_by_index", [])
        glitchling_names = [g.name for g in clones]
        seed_info = getattr(gaggle, "seed", "unknown")
        _log_verbose(f"Glitchlings: {', '.join(glitchling_names)}", verbose=True, quiet=False)
        _log_verbose(f"Seed: {seed_info}", verbose=True, quiet=False)

    if wants_metrics:
        attack_seed = args.seed if args.seed is not None else getattr(gaggle, "seed", None)
        attack = Attack(gaggle, tokenizer=tokenizer_spec, seed=attack_seed)
        result = attack.run(text)

        if wants_attack:
            # --attack: output summary only (metrics and counts, no token lists)
            full_report = result.to_report()
            payload = {
                k: v
                for k, v in full_report.items()
                if k
                not in {
                    "input_tokens",
                    "output_tokens",
                    "input_token_ids",
                    "output_token_ids",
                }
            }
        else:
            # --report: output full report (no summary)
            payload = result.to_report()

        if normalized_format == "json":
            if wants_attack:
                # Summary is a dict, format with standard indentation
                output_content = json.dumps(payload, indent=2)
            else:
                # Full report - use compact token formatting
                output_content = _format_report_json(payload)
        else:
            output_content = yaml.safe_dump(payload, sort_keys=False)

        _write_output(output_content, output_file)
        return 0

    corrupted = gaggle.corrupt(text)
    if not isinstance(corrupted, str):
        message = "Gaggle returned non-string output for string input"
        raise TypeError(message)

    _log_verbose(f"Output text: {len(corrupted)} characters", verbose=verbose, quiet=quiet)

    if args.diff:
        show_diff(text, corrupted, color=_color)
    else:
        _write_output(corrupted, output_file)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``glitchlings`` command line interface.

    Args:
        argv: Optional list of command line arguments. Defaults to ``sys.argv``.

    Returns:
        int: Exit code suitable for use with ``sys.exit``.

    """
    if argv is None:
        raw_args = sys.argv[1:]
    else:
        raw_args = list(argv)

    parser = build_parser()
    args = parser.parse_args(raw_args)
    return run_cli(args, parser)


if __name__ == "__main__":
    sys.exit(main())
