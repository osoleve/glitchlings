#!/usr/bin/env python3
"""Benchmark helpers for the glitchling pipeline."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import types
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


def _ensure_datasets_stub() -> None:
    """Install a minimal `datasets` stub so imports remain lightweight."""

    if "datasets" in sys.modules:
        return

    module = types.ModuleType("datasets")
    module.Dataset = type("Dataset", (), {})  # type: ignore[assignment]
    sys.modules["datasets"] = module


_ensure_datasets_stub()

import importlib
import random

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
zeedub_module = importlib.import_module("glitchlings.zoo.zeedub")
typogre_module = importlib.import_module("glitchlings.zoo.typogre")
core_module = importlib.import_module("glitchlings.zoo.core")

try:  # pragma: no cover - optional dependency
    zoo_rust = importlib.import_module("glitchlings._zoo_rust")
except ImportError:  # pragma: no cover - optional dependency
    zoo_rust = None


Descriptor = dict[str, object]


BASE_DESCRIPTORS: list[Descriptor] = [
    {
        "name": "Reduple",
        "operation": {"type": "reduplicate", "reduplication_rate": 0.01},
    },
    {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.01}},
    {
        "name": "Redactyl",
        "operation": {
            "type": "redact",
            "replacement_char": redactyl_module.FULL_BLOCK,
            "redaction_rate": 0.05,
            "merge_adjacent": True,
        },
    },
    {"name": "Scannequin", "operation": {"type": "ocr", "error_rate": 0.02}},
    # {"name": "Zeedub", "operation": {"type": "zwj", "rate": 0.1}},
    # {"name": "Typogre", "operation": {"type": "typo", "rate": 0.05}},
]


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


SHORT_TEXT = "One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin."
MEDIUM_TEXT = " ".join([SHORT_TEXT] * 32)
LONG_TEXT = " ".join([SHORT_TEXT] * 256)


DEFAULT_TEXTS: tuple[tuple[str, str], ...] = (
    ("short", SHORT_TEXT),
    ("medium", MEDIUM_TEXT),
    ("long", LONG_TEXT),
)
DEFAULT_ITERATIONS = 25
MASTER_SEED = 151


def _python_pipeline(text: str, descriptors: list[Descriptor], master_seed: int) -> str:
    current = text
    for index, descriptor in enumerate(descriptors):
        seed = core_module.Gaggle.derive_seed(master_seed, descriptor["name"], index)
        rng = random.Random(seed)
        operation = descriptor["operation"]
        op_type = operation["type"]
        if op_type == "reduplicate":
            current = reduple_module._python_reduplicate_words(
                current,
                rate=operation["reduplication_rate"],
                rng=rng,
            )
        elif op_type == "delete":
            current = rushmore_module._python_delete_random_words(
                current,
                rate=operation["max_deletion_rate"],
                rng=rng,
            )
        elif op_type == "redact":
            current = redactyl_module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                rate=operation["redaction_rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            current = scannequin_module._python_ocr_artifacts(
                current,
                rate=operation["error_rate"],
                rng=rng,
            )
        elif op_type == "zwj":
            current = zeedub_module._python_insert_zero_widths(
                current,
                rate=operation["rate"],
                rng=rng,
                characters=zeedub_module._DEFAULT_ZERO_WIDTH_CHARACTERS,
            )
        elif op_type == "typo":
            current = typogre_module._fatfinger_python(
                current,
                rate=operation["rate"],
                rng=rng,
                layout=typogre_module.KEYNEIGHBORS.CURATOR_QWERTY,  # type: ignore[attr-defined]
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


def _print_results(results: Sequence[BenchmarkResult]) -> None:
    for result in results:
        print(f"\nText size: {result.label} ({result.char_count} chars)")
        print(f"  Python pipeline : {_format_stats(result.python)}")
        if result.rust is None:
            print("  Rust pipeline   : unavailable (extension not built)")
        else:
            print(f"  Rust pipeline   : {_format_stats(result.rust)}")


def collect_benchmark_results(
    texts: Iterable[tuple[str, str]] | None = None,
    iterations: int = DEFAULT_ITERATIONS,
) -> list[BenchmarkResult]:
    """Return structured benchmark results without printing to stdout."""

    samples = tuple(DEFAULT_TEXTS if texts is None else texts)

    results: list[BenchmarkResult] = []
    for label, text in samples:
        python_subject = lambda text=text: _python_pipeline(
            text, BASE_DESCRIPTORS, MASTER_SEED
        )
        python_stats = _time_subject(python_subject, iterations)
        rust_stats: BenchmarkStatistics | None = None
        if zoo_rust is not None:
            rust_subject = lambda text=text: zoo_rust.compose_glitchlings(
                text,
                _seeded_descriptors(MASTER_SEED, BASE_DESCRIPTORS),
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


def run_benchmarks(texts: Iterable[tuple[str, str]], iterations: int) -> None:
    _print_results(collect_benchmark_results(texts, iterations))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Number of timing samples to collect for each text size (default: {DEFAULT_ITERATIONS})",
    )
    args = parser.parse_args(argv)
    run_benchmarks(DEFAULT_TEXTS, args.iterations)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
