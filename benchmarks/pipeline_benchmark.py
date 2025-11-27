#!/usr/bin/env python3
"""Benchmark helpers for the glitchling pipeline."""

from __future__ import annotations

import argparse
import importlib
import statistics
import sys
import time
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

# Support running as script or as module
if __name__ == "__main__" and __package__ is None:
    # Add parent directory to path when run as script
    sys.path.insert(0, str(Path(__file__).parent))
    from constants import (
        BASE_DESCRIPTORS,
        DEFAULT_ITERATIONS,
        DEFAULT_TEXTS,
        MASTER_SEED,
        Descriptor,
        redactyl_full_block,
    )
else:
    from benchmarks.constants import (
        BASE_DESCRIPTORS,
        DEFAULT_ITERATIONS,
        DEFAULT_TEXTS,
        MASTER_SEED,
        Descriptor,
        redactyl_full_block,
    )


def _ensure_datasets_stub() -> None:
    """Install a minimal `datasets` stub so imports remain lightweight."""
    if "datasets" in sys.modules:
        return

    module = types.ModuleType("datasets")
    module.Dataset = type("Dataset", (), {})  # type: ignore[assignment]
    sys.modules["datasets"] = module


_ensure_datasets_stub()

core_module = importlib.import_module("glitchlings.zoo.core")

zoo_rust = importlib.import_module("glitchlings._zoo_rust")


def _clone_descriptors(descriptors: Sequence[Descriptor]) -> list[Descriptor]:
    """Return a deep-ish copy of descriptor templates suitable for reuse."""
    return [
        {
            "name": descriptor["name"],
            "operation": dict(descriptor["operation"]),
        }
        for descriptor in descriptors
    ]


def _descriptor_template(name: str) -> Descriptor:
    """Fetch a descriptor template by name from the baseline set."""
    for descriptor in BASE_DESCRIPTORS:
        if descriptor["name"] == name:
            return {
                "name": name,
                "operation": dict(descriptor["operation"]),
            }
    raise KeyError(f"Unknown descriptor template: {name}")


def _make_descriptor(name: str, **operation_overrides: object) -> Descriptor:
    descriptor = _descriptor_template(name)
    descriptor["operation"].update(operation_overrides)
    return descriptor


def _baseline_descriptors() -> list[Descriptor]:
    return _clone_descriptors(BASE_DESCRIPTORS)


def _shuffle_mix_descriptors() -> list[Descriptor]:
    descriptors = _clone_descriptors(BASE_DESCRIPTORS)
    descriptors.insert(
        2,
        {
            "name": "Rushmore-Swap",
            "operation": {"type": "swap_adjacent", "rate": 0.35},
        },
    )
    return descriptors


def _aggressive_cleanup_descriptors() -> list[Descriptor]:
    return [
        _make_descriptor("Rushmore", rate=0.03),
        {
            "name": "Rushmore-Swap-Deep",
            "operation": {"type": "swap_adjacent", "rate": 0.6},
        },
        {
            "name": "Redactyl-Deep",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_full_block(),
                "rate": 0.12,
                "merge_adjacent": True,
            },
        },
        _make_descriptor("Scannequin", rate=0.03),
        _make_descriptor("Typogre", rate=0.03),
    ]


def _stealth_noise_descriptors() -> list[Descriptor]:
    return [
        _make_descriptor("Typogre", rate=0.025),
        _make_descriptor("Zeedub", rate=0.035),
        {
            "name": "Rushmore-Swap-Lite",
            "operation": {"type": "swap_adjacent", "rate": 0.25},
        },
        {
            "name": "Redactyl-Lite",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_full_block(),
                "rate": 0.02,
                "merge_adjacent": False,
            },
        },
    ]


# Individual glitchling scenarios
def _typogre_only_descriptors() -> list[Descriptor]:
    return [_make_descriptor("Typogre", rate=0.05)]


def _rushmore_delete_descriptors() -> list[Descriptor]:
    return [{"name": "Rushmore-Delete", "operation": {"type": "delete", "rate": 0.05}}]


def _rushmore_duplicate_descriptors() -> list[Descriptor]:
    return [{"name": "Rushmore-Duplicate", "operation": {"type": "reduplicate", "rate": 0.05}}]


def _rushmore_swap_descriptors() -> list[Descriptor]:
    return [{"name": "Rushmore-Swap", "operation": {"type": "swap_adjacent", "rate": 0.35}}]


def _redactyl_only_descriptors() -> list[Descriptor]:
    return [
        {
            "name": "Redactyl",
            "operation": {
                "type": "redact",
                "replacement_char": redactyl_full_block(),
                "rate": 0.05,
                "merge_adjacent": True,
            },
        }
    ]


def _scannequin_only_descriptors() -> list[Descriptor]:
    return [_make_descriptor("Scannequin", rate=0.05)]


def _zeedub_only_descriptors() -> list[Descriptor]:
    return [_make_descriptor("Zeedub", rate=0.05)]


def _mim1c_only_descriptors() -> list[Descriptor]:
    return [{"name": "Mim1c", "operation": {"type": "mimic", "rate": 0.05}}]


def _ekkokin_only_descriptors() -> list[Descriptor]:
    return [{"name": "Ekkokin", "operation": {"type": "ekkokin", "rate": 0.05}}]


def _hokey_only_descriptors() -> list[Descriptor]:
    return [
        {
            "name": "Hokey",
            "operation": {
                "type": "hokey",
                "rate": 0.3,
                "extension_min": 2,
                "extension_max": 5,
                "word_length_threshold": 6,
                "base_p": 0.45,
            },
        }
    ]


def _jargoyle_only_descriptors() -> list[Descriptor]:
    return [
        {
            "name": "Jargoyle",
            "operation": {
                "type": "jargoyle",
                "lexemes": "synonyms",
                "mode": "drift",
                "rate": 0.05,
            },
        }
    ]


# Pedant evolution scenarios
def _pedant_whomst_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Whomst", "operation": {"type": "pedant", "stone": "Whom Stone"}}]


def _pedant_fewerling_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Fewerling", "operation": {"type": "pedant", "stone": "Fewerite"}}]


def _pedant_aetheria_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Aetheria", "operation": {"type": "pedant", "stone": "Coeurite"}}]


def _pedant_apostrofae_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Apostrofae", "operation": {"type": "pedant", "stone": "Curlite"}}]


def _pedant_subjunic_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Subjunic", "operation": {"type": "pedant", "stone": "Subjunctite"}}]


def _pedant_commama_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Commama", "operation": {"type": "pedant", "stone": "Oxfordium"}}]


def _pedant_kiloa_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Kiloa", "operation": {"type": "pedant", "stone": "Metricite"}}]


def _pedant_correctopus_descriptors() -> list[Descriptor]:
    return [{"name": "Pedant-Correctopus", "operation": {"type": "pedant", "stone": "Orthogonite"}}]


SCENARIOS: dict[str, Callable[[], list[Descriptor]]] = {
    # Multi-glitchling scenarios
    "baseline": _baseline_descriptors,
    "shuffle_mix": _shuffle_mix_descriptors,
    "aggressive_cleanup": _aggressive_cleanup_descriptors,
    "stealth_noise": _stealth_noise_descriptors,
    # Individual glitchling scenarios
    "typogre_only": _typogre_only_descriptors,
    "rushmore_delete": _rushmore_delete_descriptors,
    "rushmore_duplicate": _rushmore_duplicate_descriptors,
    "rushmore_swap": _rushmore_swap_descriptors,
    "redactyl_only": _redactyl_only_descriptors,
    "scannequin_only": _scannequin_only_descriptors,
    "zeedub_only": _zeedub_only_descriptors,
    "mim1c_only": _mim1c_only_descriptors,
    "ekkokin_only": _ekkokin_only_descriptors,
    "hokey_only": _hokey_only_descriptors,
    "jargoyle_only": _jargoyle_only_descriptors,
    # Pedant evolution scenarios
    "pedant_whomst": _pedant_whomst_descriptors,
    "pedant_fewerling": _pedant_fewerling_descriptors,
    "pedant_aetheria": _pedant_aetheria_descriptors,
    "pedant_apostrofae": _pedant_apostrofae_descriptors,
    "pedant_subjunic": _pedant_subjunic_descriptors,
    "pedant_commama": _pedant_commama_descriptors,
    "pedant_kiloa": _pedant_kiloa_descriptors,
    "pedant_correctopus": _pedant_correctopus_descriptors,
}

# Categorize scenarios for display purposes
MULTI_GLITCHLING_SCENARIOS = {"baseline", "shuffle_mix", "aggressive_cleanup", "stealth_noise"}
INDIVIDUAL_GLITCHLING_SCENARIOS = {
    "typogre_only",
    "rushmore_delete",
    "rushmore_duplicate",
    "rushmore_swap",
    "redactyl_only",
    "scannequin_only",
    "zeedub_only",
    "mim1c_only",
    "ekkokin_only",
    "hokey_only",
    "jargoyle_only",
    "pedant_whomst",
    "pedant_fewerling",
    "pedant_aetheria",
    "pedant_apostrofae",
    "pedant_subjunic",
    "pedant_commama",
    "pedant_kiloa",
    "pedant_correctopus",
}

# Display names for individual glitchlings
INDIVIDUAL_DISPLAY_NAMES = {
    "typogre_only": "Typogre",
    "rushmore_delete": "Rush-Del",
    "rushmore_duplicate": "Rush-Dup",
    "rushmore_swap": "Rush-Swap",
    "redactyl_only": "Redactyl",
    "scannequin_only": "Scannequin",
    "zeedub_only": "Zeedub",
    "mim1c_only": "Mim1c",
    "ekkokin_only": "Ekkokin",
    "hokey_only": "Hokey",
    "jargoyle_only": "Jargoyle",
    "pedant_whomst": "Whomst",
    "pedant_fewerling": "Fewerling",
    "pedant_aetheria": "Aetheria",
    "pedant_apostrofae": "Apostrofae",
    "pedant_subjunic": "Subjunic",
    "pedant_commama": "Commama",
    "pedant_kiloa": "Kiloa",
    "pedant_correctopus": "Correctopus",
}

# Grouped display order for individual glitchlings
INDIVIDUAL_GROUPS: list[tuple[str, list[str]]] = [
    ("Character-Level Mutations", ["typogre_only", "mim1c_only", "zeedub_only", "scannequin_only"]),
    ("Word-Level Operations", ["redactyl_only", "ekkokin_only", "hokey_only", "jargoyle_only"]),
    ("Rushmore Variants", ["rushmore_delete", "rushmore_duplicate", "rushmore_swap"]),
    (
        "Pedant Evolutions",
        [
            "pedant_whomst",
            "pedant_fewerling",
            "pedant_aetheria",
            "pedant_apostrofae",
            "pedant_subjunic",
            "pedant_commama",
            "pedant_kiloa",
            "pedant_correctopus",
        ],
    ),
]


def _seeded_descriptors(master_seed: int, descriptors: Sequence[Descriptor]) -> list[Descriptor]:
    """Return pipeline descriptors enriched with per-glitchling seeds."""
    seeded: list[Descriptor] = []
    for index, descriptor in enumerate(descriptors):
        seeded.append(
            {
                "name": descriptor["name"],
                "operation": dict(descriptor["operation"]),
                "seed": int(core_module.Gaggle.derive_seed(master_seed, descriptor["name"], index)),
            }
        )
    return seeded


BenchmarkSubject = Callable[[], None]


@dataclass(frozen=True)
class BenchmarkStatistics:
    """Aggregate timing metrics for a single benchmark subject."""

    mean_seconds: float
    stdev_seconds: float

    @property
    def mean_ms(self) -> float:
        return self.mean_seconds * 1000

    @property
    def stdev_ms(self) -> float:
        return self.stdev_seconds * 1000


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing results for a single text sample."""

    label: str
    char_count: int
    runtime: BenchmarkStatistics


def _time_subject(subject: BenchmarkSubject, iterations: int) -> BenchmarkStatistics:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        subject()
        samples.append(time.perf_counter() - start)
    return BenchmarkStatistics(statistics.mean(samples), statistics.pstdev(samples))


def _format_stats(stats: BenchmarkStatistics) -> str:
    return f"{stats.mean_ms:8.3f} ms (σ={stats.stdev_ms:5.3f} ms)"


def _format_table_stats(stats: BenchmarkStatistics) -> str:
    return f"{stats.mean_ms:7.3f} (σ={stats.stdev_ms:5.3f})"


def _format_compact_stats(stats: BenchmarkStatistics) -> str:
    return f"{stats.mean_ms:6.2f}"


def _print_header(title: str, width: int = 60) -> None:
    """Print a styled section header."""
    print()
    print("═" * width)
    print(f"  {title}")
    print("═" * width)


def _print_subheader(title: str, width: int = 60) -> None:
    """Print a styled subsection header."""
    print()
    print(f"  ┌{'─' * (len(title) + 2)}┐")
    print(f"  │ {title} │")
    print(f"  └{'─' * (len(title) + 2)}┘")


def _print_results(scenario: str, results: Sequence[BenchmarkResult]) -> None:
    _print_subheader(f"Scenario: {scenario}")
    print()
    print("  ┌───────────┬──────────┬────────────────────────┐")
    print("  │ Text Size │    Chars │ Runtime (ms)           │")
    print("  ├───────────┼──────────┼────────────────────────┤")
    for result in results:
        row = "  │ {label:<9} │ {char_count:>8,} │ {runtime:<22} │".format(
            label=result.label,
            char_count=result.char_count,
            runtime=_format_table_stats(result.runtime),
        )
        print(row)
    print("  └───────────┴──────────┴────────────────────────┘")


def _print_grouped_individual_table(
    group_name: str,
    scenario_keys: list[str],
    scenario_results: dict[str, list[BenchmarkResult]],
) -> None:
    """Print a single grouped table for related glitchlings."""
    # Filter to scenarios that were actually run
    available = [s for s in scenario_keys if s in scenario_results]
    if not available:
        return

    col_names = [INDIVIDUAL_DISPLAY_NAMES.get(s, s) for s in available]
    col_width = 10

    _print_subheader(group_name)
    print()

    # Top border
    top = "  ┌───────────┬──────────┬"
    for _ in col_names:
        top += "─" * (col_width + 2) + "┬"
    top = top[:-1] + "┐"
    print(top)

    # Header row
    header = "  │ Text Size │    Chars │"
    for name in col_names:
        header += f" {name:^{col_width}} │"
    print(header)

    # Separator
    sep = "  ├───────────┼──────────┼"
    for _ in col_names:
        sep += "─" * (col_width + 2) + "┼"
    sep = sep[:-1] + "┤"
    print(sep)

    # Get text labels from first scenario's results
    first_results = scenario_results[available[0]]

    # Data rows
    for i, result in enumerate(first_results):
        row = "  │ {label:<9} │ {chars:>8,} │".format(
            label=result.label,
            chars=result.char_count,
        )
        for scenario in available:
            stats = scenario_results[scenario][i].runtime
            cell = f"{stats.mean_ms:>6.2f} ms"
            row += f" {cell:^{col_width}} │"
        print(row)

    # Footer
    footer = "  └───────────┴──────────┴"
    for _ in col_names:
        footer += "─" * (col_width + 2) + "┴"
    footer = footer[:-1] + "┘"
    print(footer)


def _print_combined_individual_results(
    scenario_results: dict[str, list[BenchmarkResult]],
    scenarios: Sequence[str],
) -> None:
    """Print grouped tables for individual glitchling benchmarks."""
    _print_header("Individual Glitchling Benchmarks")

    # Filter to only requested scenarios
    available_scenarios = set(scenarios) & INDIVIDUAL_GLITCHLING_SCENARIOS
    if not available_scenarios:
        return

    for group_name, group_scenarios in INDIVIDUAL_GROUPS:
        # Only print groups that have at least one requested scenario
        group_available = [s for s in group_scenarios if s in available_scenarios]
        if group_available:
            _print_grouped_individual_table(group_name, group_scenarios, scenario_results)

    # Print standard deviation summary
    print()
    print("  σ (standard deviation) in ms:")

    ordered_scenarios = [
        s for s in scenarios if s in INDIVIDUAL_GLITCHLING_SCENARIOS and s in scenario_results
    ]
    stdev_content_width = 56
    print("  ┌" + "─" * stdev_content_width + "┐")
    for scenario in ordered_scenarios:
        name = INDIVIDUAL_DISPLAY_NAMES.get(scenario, scenario)
        results = scenario_results[scenario]
        stdevs = ", ".join(f"{r.runtime.stdev_ms:.3f}" for r in results)
        content = f" {name:<10}: [{stdevs}]"
        print(f"  │{content:<{stdev_content_width}}│")
    print("  └" + "─" * stdev_content_width + "┘")


def collect_benchmark_results(
    texts: Iterable[tuple[str, str]] | None = None,
    iterations: int = DEFAULT_ITERATIONS,
    descriptors: Sequence[Descriptor] | None = None,
) -> list[BenchmarkResult]:
    """Return structured benchmark results without printing to stdout."""
    samples = tuple(DEFAULT_TEXTS if texts is None else texts)
    descriptor_template: tuple[Descriptor, ...] = tuple(
        _clone_descriptors(descriptors if descriptors is not None else BASE_DESCRIPTORS)
    )

    results: list[BenchmarkResult] = []
    for label, text in samples:

        def runtime_subject(text: str = text) -> str:
            return zoo_rust.compose_glitchlings(
                text,
                _seeded_descriptors(MASTER_SEED, descriptor_template),
                MASTER_SEED,
            )

        runtime_stats = _time_subject(runtime_subject, iterations)
        results.append(
            BenchmarkResult(
                label=label,
                char_count=len(text),
                runtime=runtime_stats,
            )
        )
    return results


def run_benchmarks(
    scenarios: Sequence[str],
    texts: Iterable[tuple[str, str]],
    iterations: int,
    output_file: str | None = None,
) -> None:
    output_lines: list[str] = []
    texts_tuple = tuple(texts)

    # Separate multi-glitchling and individual scenarios
    multi_scenarios = [s for s in scenarios if s in MULTI_GLITCHLING_SCENARIOS]
    individual_scenarios = [s for s in scenarios if s in INDIVIDUAL_GLITCHLING_SCENARIOS]

    # Collect all results first
    all_results: dict[str, list[BenchmarkResult]] = {}
    for scenario in scenarios:
        builder = SCENARIOS.get(scenario)
        if builder is None:
            raise KeyError(f"Unknown scenario: {scenario}")
        descriptor_set = builder()
        all_results[scenario] = collect_benchmark_results(texts_tuple, iterations, descriptor_set)

    # Print individual glitchling scenarios first as grouped tables
    if individual_scenarios:
        _print_combined_individual_results(all_results, individual_scenarios)
        if output_file:
            output_lines.append("\n=== Individual Glitchling Comparison ===")
            for group_name, group_scenarios in INDIVIDUAL_GROUPS:
                available = [s for s in group_scenarios if s in individual_scenarios]
                if not available:
                    continue
                output_lines.append(f"\n{group_name}:")
                col_names = [INDIVIDUAL_DISPLAY_NAMES.get(s, s) for s in available]
                header = "| Text size | Characters | " + " | ".join(col_names) + " |"
                output_lines.append(header)
                sep = "| --- | ---: | " + " | ".join(["---:" for _ in col_names]) + " |"
                output_lines.append(sep)
                first_results = all_results[available[0]]
                for i, result in enumerate(first_results):
                    row_parts = [result.label, str(result.char_count)]
                    for scenario in available:
                        stats = all_results[scenario][i].runtime
                        row_parts.append(f"{stats.mean_ms:.2f} ms")
                    output_lines.append("| " + " | ".join(row_parts) + " |")

    # Print multi-glitchling scenarios
    if multi_scenarios:
        _print_header("Multi-Glitchling Pipeline Benchmarks")
        for scenario in multi_scenarios:
            _print_results(scenario, all_results[scenario])
            if output_file:
                output_lines.append(f"\n=== Scenario: {scenario} ===")
                output_lines.append("| Text size | Characters | Runtime (ms) |")
                output_lines.append("| --- | ---: | ---: |")
                for result in all_results[scenario]:
                    stats = _format_table_stats(result.runtime)
                    output_lines.append(f"| {result.label} | {result.char_count} | {stats} |")

    # Summary
    print()
    print("═" * 60)
    print(f"  Benchmark complete: {len(scenarios)} scenario(s), {iterations} iterations each")
    print("═" * 60)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\n  Results written to: {output_file}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=(
            "Number of timing samples to collect for each text size "
            f"(default: {DEFAULT_ITERATIONS})"
        ),
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        choices=sorted(SCENARIOS.keys()),
        help="Scenario(s) to benchmark (can be passed multiple times; default: all).",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available benchmark scenarios and exit.",
    )
    parser.add_argument(
        "--singles-only",
        action="store_true",
        help="Run only individual glitchling scenarios (excludes multi-glitchling pipelines).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write benchmark results to FILE in addition to stdout.",
    )
    args = parser.parse_args(argv)

    if args.list_scenarios:
        for key in SCENARIOS:
            print(key)
        return 0

    if args.singles_only:
        selected_scenarios = sorted(INDIVIDUAL_GLITCHLING_SCENARIOS)
    else:
        selected_scenarios = args.scenarios or list(SCENARIOS.keys())
    run_benchmarks(selected_scenarios, DEFAULT_TEXTS, args.iterations, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
