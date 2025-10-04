#!/usr/bin/env python3
"""Benchmark helpers for the glitchling pipeline."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import types
from typing import Callable, Iterable


def _ensure_datasets_stub() -> None:
    """Install a minimal ``datasets`` stub so imports remain lightweight."""

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
core_module = importlib.import_module("glitchlings.zoo.core")

try:  # pragma: no cover - optional dependency
    zoo_rust = importlib.import_module("glitchlings._zoo_rust")
except ImportError:  # pragma: no cover - optional dependency
    zoo_rust = None


Descriptor = dict[str, object]


DESCRIPTORS: list[Descriptor] = [
    {"name": "Reduple", "operation": {"type": "reduplicate", "reduplication_rate": 0.4}},
    {"name": "Rushmore", "operation": {"type": "delete", "max_deletion_rate": 0.3}},
    {
        "name": "Redactyl",
        "operation": {
            "type": "redact",
            "replacement_char": redactyl_module.FULL_BLOCK,
            "redaction_rate": 0.6,
            "merge_adjacent": True,
        },
    },
    {"name": "Scannequin", "operation": {"type": "ocr", "error_rate": 0.25}},
]


SHORT_TEXT = "Guard the vault at midnight."
MEDIUM_TEXT = " ".join([SHORT_TEXT] * 8)
LONG_TEXT = " ".join([SHORT_TEXT] * 32)


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
                reduplication_rate=operation["reduplication_rate"],
                rng=rng,
            )
        elif op_type == "delete":
            current = rushmore_module._python_delete_random_words(
                current,
                max_deletion_rate=operation["max_deletion_rate"],
                rng=rng,
            )
        elif op_type == "redact":
            current = redactyl_module._python_redact_words(
                current,
                replacement_char=operation["replacement_char"],
                redaction_rate=operation["redaction_rate"],
                merge_adjacent=operation["merge_adjacent"],
                rng=rng,
            )
        elif op_type == "ocr":
            current = scannequin_module._python_ocr_artifacts(
                current,
                error_rate=operation["error_rate"],
                rng=rng,
            )
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unsupported operation type: {op_type!r}")
    return current


BenchmarkSubject = Callable[[], None]


def _time_subject(subject: BenchmarkSubject, iterations: int) -> tuple[float, float]:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        subject()
        samples.append(time.perf_counter() - start)
    return statistics.mean(samples), statistics.pstdev(samples)


def _format_stats(mean_seconds: float, stdev_seconds: float) -> str:
    mean_ms = mean_seconds * 1000
    stdev_ms = stdev_seconds * 1000
    return f"{mean_ms:8.3f} ms (σ={stdev_ms:5.3f} ms)"


def run_benchmarks(texts: Iterable[tuple[str, str]], iterations: int) -> None:
    for label, text in texts:
        print(f"\nText size: {label} ({len(text)} chars)")
        python_subject = lambda: _python_pipeline(text, DESCRIPTORS, 151)
        mean_py, stdev_py = _time_subject(python_subject, iterations)
        print(f"  Python pipeline : {_format_stats(mean_py, stdev_py)}")
        if zoo_rust is None:
            print("  Rust pipeline   : unavailable (extension not built)")
            continue
        rust_subject = lambda: zoo_rust.compose_glitchlings(text, DESCRIPTORS, 151)
        mean_rust, stdev_rust = _time_subject(rust_subject, iterations)
        print(f"  Rust pipeline   : {_format_stats(mean_rust, stdev_rust)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=25,
        help="Number of timing samples to collect for each text size (default: 25)",
    )
    args = parser.parse_args(argv)
    texts = [
        ("short", SHORT_TEXT),
        ("medium", MEDIUM_TEXT),
        ("long", LONG_TEXT),
    ]
    run_benchmarks(texts, args.iterations)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
