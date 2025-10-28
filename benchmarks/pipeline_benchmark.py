#!/usr/bin/env python3
"""Benchmark helpers for the glitchling pipeline."""

from __future__ import annotations

import argparse
import importlib
import random
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
    OPERATION_MODULES,
    Descriptor,
    module_for_operation,
    redactyl_full_block,
    zero_width_characters,
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

try:  # pragma: no cover - optional dependency
    zoo_rust = importlib.import_module("glitchlings._zoo_rust")
except ImportError:  # pragma: no cover - optional dependency
    zoo_rust = None


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
            "name": "Adjax",
            "operation": {"type": "swap_adjacent", "rate": 0.35},
        },
    )
    return descriptors


def _aggressive_cleanup_descriptors() -> list[Descriptor]:
    return [
        _make_descriptor("Rushmore", rate=0.03),
        {
            "name": "Adjax-Deep",
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
            "name": "Adjax-Lite",
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


def _python_pipeline(text: str, descriptors: list[Descriptor], master_seed: int) -> str:
    operation_modules = {key: module_for_operation(key) for key in OPERATION_MODULES}
    current = text
    for index, descriptor in enumerate(descriptors):
        seed = core_module.Gaggle.derive_seed(master_seed, descriptor["name"], index)
        rng = random.Random(seed)
        operation = descriptor["operation"]
        op_type = operation["type"]
        if op_type == "reduplicate":
            module = operation_modules["reduplicate"]
            current = module._python_reduplicate_words(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "delete":
            module = operation_modules["delete"]
            current = module._python_delete_random_words(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "redact":
            module = operation_modules["redact"]
            current = module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                rate=operation["rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            module = operation_modules["ocr"]
            current = module._python_ocr_artifacts(
                current,
                rate=operation["rate"],
                rng=rng,
            )
        elif op_type == "zwj":
            characters = operation.get("characters")
            if characters is None:
                characters = tuple(zero_width_characters())
            else:
                characters = tuple(characters)
            module = operation_modules["zwj"]
            current = module._python_insert_zero_widths(
                current,
                rate=operation["rate"],
                rng=rng,
                characters=characters,
            )
        elif op_type == "typo":
            keyboard = operation.get("keyboard", "CURATOR_QWERTY")
            layout_override = operation.get("layout")
            if layout_override is None:
                layout = getattr(operation_modules["typo"].KEYNEIGHBORS, keyboard)
            else:
                layout = {key: list(value) for key, value in layout_override.items()}
            module = operation_modules["typo"]
            current = module._fatfinger_python(
                current,
                rate=operation["rate"],
                rng=rng,
                layout=layout,
            )
        elif op_type == "swap_adjacent":
            module = operation_modules["swap_adjacent"]
            current = module._python_swap_adjacent_words(
                current,
                rate=float(operation.get("rate", 0.5)),
                rng=rng,
            )
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unsupported operation type: {op_type!r}")
    return current


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
    python: BenchmarkStatistics
    rust: BenchmarkStatistics | None


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
        "| Text size | Characters | Python (ms)           | Rust (ms)             | Speedup |\n"
        "| ---       | ---:       | ---:                  | ---:                  | ---:    |"
    )
    print(header)
    for result in results:
        python_cell = _format_table_stats(result.python)
        if result.rust is None:
            rust_cell = "unavailable"
            speedup_cell = "N/A"
        else:
            rust_cell = _format_table_stats(result.rust)
            speedup_value = (
                result.python.mean_seconds / result.rust.mean_seconds
                if result.rust.mean_seconds > 0
                else float("inf")
            )
            speedup_cell = f"{speedup_value:5.2f}x"
        row = (
            "| {label:<9} | {char_count:10d} | {python:<21} | "
            "{rust:<21} | {speedup:>6} |"
        ).format(
            label=result.label,
            char_count=result.char_count,
            python=python_cell,
            rust=rust_cell,
            speedup=speedup_cell,
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
        def python_subject(text: str = text) -> str:
            return _python_pipeline(
                text,
                _clone_descriptors(descriptor_template),
                MASTER_SEED,
            )

        python_stats = _time_subject(python_subject, iterations)
        rust_stats: BenchmarkStatistics | None = None
        if zoo_rust is not None:
            def rust_subject(text: str = text) -> str:
                return zoo_rust.compose_glitchlings(
                    text,
                    _seeded_descriptors(MASTER_SEED, descriptor_template),
                    MASTER_SEED,
                )

            rust_stats = _time_subject(rust_subject, iterations)
        results.append(
            BenchmarkResult(
                label=label,
                char_count=len(text),
                python=python_stats,
                rust=rust_stats,
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
