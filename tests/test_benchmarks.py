"""Regression checks for the benchmarking utilities."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.pipeline_benchmark import (
    BenchmarkResult,
    collect_benchmark_results,
)


@pytest.fixture(scope="module")
def benchmark_results() -> Mapping[str, BenchmarkResult]:
    """Collect a small sample of benchmark data once per test run."""

    results = collect_benchmark_results(iterations=5)
    return {result.label: result for result in results}


def test_collect_benchmark_results_structure(
    benchmark_results: Mapping[str, BenchmarkResult],
) -> None:
    """Top-level sanity check that the benchmark harness returns populated results."""

    assert benchmark_results
    assert {"short", "medium", "long"}.issubset(benchmark_results.keys())
    for result in benchmark_results.values():
        assert result.char_count > 0
        assert result.python.mean_seconds >= 0
        assert result.python.stdev_seconds >= 0


@pytest.mark.parametrize(
    ("label", "threshold"),
    [
        ("short", 0.01),
        ("medium", 0.03),
        ("long", 0.1),
    ],
)
def test_python_pipeline_regression_guard(
    benchmark_results: Mapping[str, BenchmarkResult],
    label: str,
    threshold: float,
) -> None:
    """Fail fast if the Python pipeline slows down dramatically on canonical samples."""

    mean_seconds = benchmark_results[label].python.mean_seconds
    assert mean_seconds <= threshold, (
        f"Python pipeline mean for '{label}' text exceeded {threshold:.3f}s: {mean_seconds:.3f}s"
    )
