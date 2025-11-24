"""Command line interface for summoning and running glitchlings."""

from __future__ import annotations

import argparse
import difflib
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from . import SAMPLE_TEXT
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
    include_subcommands: bool = False,
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
            "via --file, or pipe it on stdin."
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
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Load glitchlings from a YAML configuration file.",
    )

    if include_subcommands:
        subparsers = parser.add_subparsers(dest="command")
        if hasattr(subparsers, "required"):
            subparsers.required = False  # allow top-level invocation without subcommand
        add_build_lexicon_subparser(subparsers)

    return parser


def _configure_build_lexicon_parser(builder: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach ``build-lexicon`` options to ``builder`` and return it."""
    builder.add_argument(
        "--source",
        required=True,
        help=(
            "Vector source specification. Use 'spacy:<model>' for spaCy pipelines "
            "or provide a path to a gensim KeyedVectors/word2vec file."
        ),
    )
    builder.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to the JSON file that will receive the synonym cache.",
    )
    builder.add_argument(
        "--tokens",
        type=Path,
        help="Optional newline-delimited vocabulary file to restrict generation.",
    )
    builder.add_argument(
        "--max-neighbors",
        type=int,
        default=50,
        help="Number of nearest neighbours to cache per token (default: 50).",
    )
    builder.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="Minimum cosine similarity required to keep a synonym (default: 0.0).",
    )
    builder.add_argument(
        "--seed",
        type=int,
        help="Optional deterministic seed to bake into the resulting cache.",
    )
    builder.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Preserve original casing instead of lower-casing cache keys.",
    )
    builder.add_argument(
        "--normalizer",
        choices=["lower", "identity"],
        default="lower",
        help="Token normalization strategy for cache keys (default: lower).",
    )
    builder.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of tokens to process.",
    )
    builder.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing cache file.",
    )
    return builder


def add_build_lexicon_subparser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """Create the ``build-lexicon`` subcommand parser with vector cache options."""
    builder = subparsers.add_parser(
        "build-lexicon",
        description=(
            "Generate deterministic synonym caches using vector embeddings so "
            "they can be distributed without bundling large models."
        ),
        help="Generate synonym caches backed by vector embeddings.",
    )
    _configure_build_lexicon_parser(builder)
    builder.set_defaults(handler=run_build_lexicon)
    return builder


def build_lexicon_parser() -> argparse.ArgumentParser:
    """Standalone parser matching the ``build-lexicon`` subcommand."""
    builder = argparse.ArgumentParser(
        prog="glitchlings build-lexicon",
        description=(
            "Generate deterministic synonym caches using vector embeddings so "
            "they can be distributed without bundling large models."
        ),
    )
    return _configure_build_lexicon_parser(builder)


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
    file_path = cast(Path | None, getattr(args, "file", None))
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
        "No input text provided. Supply text as an argument, use --file, pipe input, or "
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
    gaggle = summon_glitchlings(
        args.glitchlings,
        parser,
        args.seed,
        config_path=args.config,
    )

    corrupted = gaggle.corrupt(text)
    if not isinstance(corrupted, str):
        message = "Gaggle returned non-string output for string input"
        raise TypeError(message)

    if args.diff:
        show_diff(text, corrupted)
    else:
        print(corrupted)

    return 0


def run_build_lexicon(args: argparse.Namespace) -> int:
    """Delegate to the vector lexicon cache builder using CLI arguments."""
    from glitchlings.lexicon.vector import main as vector_main

    vector_args = [
        "--source",
        args.source,
        "--output",
        str(args.output),
        "--max-neighbors",
        str(args.max_neighbors),
        "--min-similarity",
        str(args.min_similarity),
        "--normalizer",
        args.normalizer,
    ]
    if args.tokens is not None:
        vector_args.extend(["--tokens", str(args.tokens)])
    if args.seed is not None:
        vector_args.extend(["--seed", str(args.seed)])
    if args.case_sensitive:
        vector_args.append("--case-sensitive")
    if args.limit is not None:
        vector_args.extend(["--limit", str(args.limit)])
    if args.overwrite:
        vector_args.append("--overwrite")

    return vector_main(vector_args)


def _exit_code(exc: SystemExit) -> int:
    """Normalize ``SystemExit.code`` to an integer suitable for returning."""

    code = exc.code
    if isinstance(code, int):
        return code
    if isinstance(code, str):
        try:
            return int(code)
        except ValueError:
            return 1
    return 0 if code is None else 1


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

    if any(arg in {"-h", "--help"} for arg in raw_args):
        first_non_option = next((arg for arg in raw_args if not arg.startswith("-")), None)
        if first_non_option is None:
            help_parser = build_parser(include_subcommands=True)
            help_parser.print_help()
            return 0

    first_non_option_index = None
    first_non_option = None
    for index, argument in enumerate(raw_args):
        if argument == "--":
            break
        if argument.startswith("-"):
            continue
        first_non_option_index = index
        first_non_option = argument
        break

    if first_non_option_index is not None and first_non_option == "build-lexicon":
        builder = build_lexicon_parser()
        try:
            subcommand_args = builder.parse_args(raw_args[first_non_option_index + 1 :])
        except SystemExit as exc:
            return _exit_code(exc)
        return run_build_lexicon(subcommand_args)

    parser = build_parser(include_subcommands=False)
    args = parser.parse_args(raw_args)
    return run_cli(args, parser)


if __name__ == "__main__":
    sys.exit(main())
