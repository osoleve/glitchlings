#!/usr/bin/env python3
"""Benchmark comparing homogeneous vs heterogeneous mask performance.

This benchmark measures the overhead of using per-glitchling masks
versus a single unified mask pattern, using the Gutenberg corpus.
"""

from __future__ import annotations

import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Support running as script
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    sys.path.insert(0, str(Path(__file__).parent.parent))

from glitchlings import Gaggle, Typogre
from benchmarks.constants import (
    MASTER_SEED,
    load_gutenberg_books,
    resolve_corpus,
)


@dataclass(frozen=True)
class BenchmarkStats:
    """Aggregate timing metrics for a benchmark run."""

    mean_ms: float
    stdev_ms: float
    min_ms: float
    max_ms: float
    total_chars: int
    chars_per_sec: float


@dataclass(frozen=True)
class ComparisonResult:
    """Results comparing homogeneous vs heterogeneous masks."""

    label: str
    char_count: int
    homogeneous: BenchmarkStats
    heterogeneous: BenchmarkStats
    overhead_ratio: float


def _time_gaggle(
    gaggle: Gaggle,
    text: str,
    iterations: int,
) -> BenchmarkStats:
    """Time a gaggle's corruption over multiple iterations."""
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        gaggle.corrupt(text)
        samples.append(time.perf_counter() - start)

    mean_s = statistics.mean(samples)
    return BenchmarkStats(
        mean_ms=mean_s * 1000,
        stdev_ms=statistics.pstdev(samples) * 1000,
        min_ms=min(samples) * 1000,
        max_ms=max(samples) * 1000,
        total_chars=len(text),
        chars_per_sec=len(text) / mean_s if mean_s > 0 else 0,
    )


def run_comparison(
    texts: Sequence[tuple[str, str]],
    iterations: int,
    rate: float,
) -> list[ComparisonResult]:
    """Run homogeneous vs heterogeneous mask comparison."""
    results: list[ComparisonResult] = []

    # Create gaggles once, reuse for all texts
    # Homogeneous: Single Typogre targeting words starting with E OR S
    homo_gaggle = Gaggle(
        [Typogre(rate=rate, include_only_patterns=[r"\b[ES]\w+"])],
        seed=MASTER_SEED,
    )

    # Heterogeneous: Two Typogres with different masks
    hetero_gaggle = Gaggle(
        [
            Typogre(rate=rate, include_only_patterns=[r"\bE\w+"]),
            Typogre(rate=rate, include_only_patterns=[r"\bS\w+"]),
        ],
        seed=MASTER_SEED,
    )

    # Verify heterogeneous detection
    assert hetero_gaggle._has_heterogeneous_masks(), "Should detect heterogeneous masks"
    assert not homo_gaggle._has_heterogeneous_masks(), "Should not detect homogeneous"

    for label, text in texts:
        print(f"  Benchmarking: {label} ({len(text):,} chars)...", flush=True)

        homo_stats = _time_gaggle(homo_gaggle, text, iterations)
        hetero_stats = _time_gaggle(hetero_gaggle, text, iterations)

        overhead = hetero_stats.mean_ms / homo_stats.mean_ms if homo_stats.mean_ms > 0 else 0

        results.append(
            ComparisonResult(
                label=label,
                char_count=len(text),
                homogeneous=homo_stats,
                heterogeneous=hetero_stats,
                overhead_ratio=overhead,
            )
        )

    return results


def _print_header(title: str, width: int = 80) -> None:
    """Print a styled section header."""
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_results(results: list[ComparisonResult], iterations: int, rate: float) -> None:
    """Print formatted benchmark results."""
    _print_header(f"Heterogeneous Mask Benchmark ({iterations} iterations, {rate:.0%} rate)")

    print()
    print("  Configuration:")
    print(f"    Homogeneous:   1x Typogre(include_only_patterns=[r\"\\b[ES]\\w+\"])")
    print(f"    Heterogeneous: 2x Typogre (E-words + S-words separately)")
    print()

    # Table header
    label_w = max(len("Text"), max(len(r.label) for r in results))
    chars_w = max(len("Chars"), max(len(f"{r.char_count:,}") for r in results))

    border = (
        f"  +{'-' * (label_w + 2)}+{'-' * (chars_w + 2)}+"
        f"{'-' * 14}+{'-' * 14}+{'-' * 12}+"
    )

    print(border)
    print(
        f"  | {'Text':<{label_w}} | {'Chars':>{chars_w}} |"
        f" {'Homogeneous':>12} | {'Heterogeneous':>12} | {'Overhead':>10} |"
    )
    print(border)

    for r in results:
        print(
            f"  | {r.label:<{label_w}} | {r.char_count:>{chars_w},} |"
            f" {r.homogeneous.mean_ms:>9.2f} ms |"
            f" {r.heterogeneous.mean_ms:>9.2f} ms |"
            f" {r.overhead_ratio:>9.2f}x |"
        )

    print(border)

    # Summary statistics
    print()
    print("  Summary:")
    avg_overhead = statistics.mean(r.overhead_ratio for r in results)
    min_overhead = min(r.overhead_ratio for r in results)
    max_overhead = max(r.overhead_ratio for r in results)
    print(f"    Average overhead: {avg_overhead:.2f}x")
    print(f"    Range: {min_overhead:.2f}x - {max_overhead:.2f}x")

    # Throughput comparison
    print()
    print("  Throughput (chars/sec):")
    print(f"  +{'-' * (label_w + 2)}+{'-' * 18}+{'-' * 18}+")
    print(f"  | {'Text':<{label_w}} | {'Homogeneous':>16} | {'Heterogeneous':>16} |")
    print(f"  +{'-' * (label_w + 2)}+{'-' * 18}+{'-' * 18}+")

    for r in results:
        print(
            f"  | {r.label:<{label_w}} |"
            f" {r.homogeneous.chars_per_sec:>13,.0f}/s |"
            f" {r.heterogeneous.chars_per_sec:>13,.0f}/s |"
        )

    print(f"  +{'-' * (label_w + 2)}+{'-' * 18}+{'-' * 18}+")

    # Standard deviation details
    print()
    print("  Timing variance (stdev ms):")
    for r in results:
        print(
            f"    {r.label}: homo={r.homogeneous.stdev_ms:.3f}, "
            f"hetero={r.heterogeneous.stdev_ms:.3f}"
        )


def main() -> int:
    """Run the heterogeneous mask benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of timing iterations per text (default: 100)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=0.10,
        help="Corruption rate for each Typogre (default: 0.10)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use default texts instead of Gutenberg corpus for quick testing",
    )
    args = parser.parse_args()

    print()
    print("=" * 80)
    print("  Glitchlings Heterogeneous Mask Benchmark")
    print("=" * 80)

    if args.quick:
        from benchmarks.constants import DEFAULT_TEXTS

        print("\n  Loading default texts (quick mode)...")
        texts = resolve_corpus(DEFAULT_TEXTS)
    else:
        print("\n  Loading Project Gutenberg corpus...")
        texts = resolve_corpus(load_gutenberg_books)

    print(f"  Loaded {len(texts)} texts")
    print(f"  Running {args.iterations} iterations at {args.rate:.0%} rate each")
    print()

    results = run_comparison(texts, args.iterations, args.rate)
    _print_results(results, args.iterations, args.rate)

    print()
    print("=" * 80)
    print("  Benchmark complete")
    print("=" * 80)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
