"""CLI entry point for the metrics TUI."""

from __future__ import annotations

import argparse
from pathlib import Path

from glitchlings.util import SAMPLE_TEXT

from .controller import DEFAULT_METRIC_KEYS
from .launcher import launch_metrics_tui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive TUI for inspecting glitchling metrics."
    )
    parser.add_argument(
        "--text",
        help="Literal text to corrupt. Defaults to the built-in SAMPLE_TEXT.",
    )
    parser.add_argument(
        "--text-file",
        help="Path to a text file. Overrides --text when provided.",
    )
    parser.add_argument(
        "--glitchling",
        action="append",
        dest="glitchlings",
        default=[],
        help="Glitchling specification (repeatable), e.g. 'typogre(rate=0.1)'.",
    )
    parser.add_argument(
        "--tokenizer",
        action="append",
        default=[],
        help=(
            "Tokenizer specification (repeatable). "
            "Examples: simple, hf:gpt2, tiktoken:cl100k_base"
        ),
    )
    parser.add_argument(
        "--metric",
        action="append",
        dest="metrics",
        default=[],
        help="Metric key to display (repeatable). Defaults to a curated subset.",
    )
    parser.add_argument(
        "--input-type",
        default="adhoc",
        help="Label recorded in the session metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    text = args.text.strip() if args.text else SAMPLE_TEXT
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")

    tokenizers = args.tokenizer or ["simple"]
    glitchlings = args.glitchlings or ["typogre"]
    metrics = args.metrics or DEFAULT_METRIC_KEYS

    launch_metrics_tui(
        text=text,
        glitchlings=glitchlings,
        tokenizers=tokenizers,
        metrics=metrics,
        input_type=args.input_type,
    )


if __name__ == "__main__":
    main()
