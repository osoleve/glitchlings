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
from typing import Callable, Iterable, Sequence

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


SCENARIOS: dict[str, Callable[[], list[Descriptor]]] = {
    "baseline": _baseline_descriptors,
    "shuffle_mix": _shuffle_mix_descriptors,
    "aggressive_cleanup": _aggressive_cleanup_descriptors,
    "stealth_noise": _stealth_noise_descriptors,
}


def _seeded_descriptors(
    master_seed: int, descriptors: Sequence[Descriptor]
) -> list[Descriptor]:
    """Return pipeline descriptors enriched with per-glitchling seeds."""
    seeded: list[Descriptor] = []
    for index, descriptor in enumerate(descriptors):
        seeded.append(
            {
                "name": descriptor["name"],
                "operation": dict(descriptor["operation"]),
                "seed": int(
                    core_module.Gaggle.derive_seed(
                        master_seed, descriptor["name"], index
                    )
                ),
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
    return f"{stats.mean_ms:7.3f} ms (σ={stats.stdev_ms:5.3f})"


def _print_results(scenario: str, results: Sequence[BenchmarkResult]) -> None:
    print(f"\n=== Scenario: {scenario} ===")
    header = (
        "| Text size | Characters | Runtime (ms)          |\n"
        "| ---       | ---:       | ---:                  |"
    )
    print(header)
    for result in results:
        row = "| {label:<9} | {char_count:10d} | {runtime:<21} |".format(
            label=result.label,
            char_count=result.char_count,
            runtime=_format_table_stats(result.runtime),
        )
        print(row)


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
    scenarios: Sequence[str], texts: Iterable[tuple[str, str]], iterations: int
) -> None:
    for scenario in scenarios:
        builder = SCENARIOS.get(scenario)
        if builder is None:
            raise KeyError(f"Unknown scenario: {scenario}")
        descriptor_set = builder()
        results = collect_benchmark_results(texts, iterations, descriptor_set)
        _print_results(scenario, results)


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
    args = parser.parse_args(argv)

    if args.list_scenarios:
        for key in SCENARIOS:
            print(key)
        return 0

    selected_scenarios = args.scenarios or list(SCENARIOS.keys())
    run_benchmarks(selected_scenarios, DEFAULT_TEXTS, args.iterations)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
