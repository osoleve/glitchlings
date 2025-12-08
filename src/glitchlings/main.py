"""Command line interface for summoning and running glitchlings."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections.abc import Sequence
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

MAX_NAME_WIDTH = max(len(glitchling.name) for glitchling in BUILTIN_GLITCHLINGS.values())


def build_parser(
    *,
    exit_on_error: bool = True,
    include_text: bool = True,
) -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    Returns:
        argparse.ArgumentParser: The configured argument parser instance.

    """
    parser = argparse.ArgumentParser(
        description=(
            "Summon glitchlings to corrupt text. Provide input text as an argument, "
            "via --input-file, or pipe it on stdin."
        ),
        exit_on_error=exit_on_error,
    )
    if include_text:
        parser.add_argument(
            "text",
            nargs="*",
            help="Text to corrupt. If omitted, stdin is used or --sample provides fallback text.",
        )
    parser.add_argument(
        "-g",
        "--glitchling",
        dest="glitchlings",
        action="append",
        metavar="SPEC",
        help=(
            "Glitchling to apply, optionally with parameters like "
            "Typogre(rate=0.05). Repeat for multiples; defaults to all built-ins."
        ),
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=None,
        help="Seed controlling deterministic corruption order (default: 151).",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=Path,
        help="Read input text from a file instead of the command line argument.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        type=Path,
        help="Write output to a file instead of stdout.",
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
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Load glitchlings from a YAML configuration file.",
    )
    parser.add_argument(
        "--attack",
        action="store_true",
        help=("Output an Attack summary. Includes metrics and counts without full token lists."),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help=("Output a full Attack report. Includes tokens, token IDs, metrics, and counts."),
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="output_format",
        choices=["json", "yaml", "yml"],
        default="json",
        help="Output format for --attack or --report (default: json).",
    )
    parser.add_argument(
        "-t",
        "--tokenizer",
        dest="tokenizer",
        help=(
            "Tokenizer to use for --attack or --report. "
            "Checks tiktoken first, then HuggingFace tokenizers library. "
            "Examples: cl100k_base, gpt-4, bert-base-uncased."
        ),
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

    parser.error(
        "No input text provided. Supply text as an argument, use --input-file, pipe input, or "
        "pass --sample."
    )
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
                parser.error(str(exc))
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

    wants_attack = bool(getattr(args, "attack", False))
    wants_report = bool(getattr(args, "report", False))

    if wants_attack and wants_report:
        parser.error("Cannot combine --attack with --report. Use one or the other.")
        raise AssertionError("parser.error should exit")

    wants_metrics = wants_attack or wants_report
    if wants_metrics and args.diff:
        parser.error("--diff cannot be combined with --report/--attack output.")
        raise AssertionError("parser.error should exit")

    # Normalize output format
    output_format = cast(str, args.output_format)
    normalized_format = "yaml" if output_format == "yml" else output_format

    # Get output file path
    output_file = cast(Path | None, getattr(args, "output_file", None))

    # Validate tokenizer is only used with --attack or --report
    tokenizer_spec = cast(str | None, getattr(args, "tokenizer", None))
    if tokenizer_spec and not wants_metrics:
        parser.error("--tokenizer requires --attack or --report.")
        raise AssertionError("parser.error should exit")

    text = read_text(args, parser)
    gaggle = summon_glitchlings(
        args.glitchlings,
        parser,
        args.seed,
        config_path=args.config,
    )

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

    if args.diff:
        show_diff(text, corrupted)
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
