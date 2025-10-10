"""Regression checks for the benchmarking utilities."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.pipeline_benchmark import (
    BenchmarkResult,
    collect_benchmark_results,
)

STRICT_ENV_VAR = "GLITCHLINGS_BENCHMARK_STRICT"
SAFETY_FACTOR_ENV_VAR = "GLITCHLINGS_BENCHMARK_SAFETY_FACTOR"
BASELINE_PYTHON_MEAN_SECONDS: dict[str, float] = {
    "short": 0.01,
    "medium": 0.03,
    "long": 0.1,
}
DEFAULT_SAFETY_FACTOR = 12.0
PYTHON_BENCHMARK_LABELS = tuple(BASELINE_PYTHON_MEAN_SECONDS.keys())


def _resolve_thresholds() -> dict[str, float]:
    if os.environ.get(STRICT_ENV_VAR, "").lower() in {"1", "true", "yes"}:
        return dict(BASELINE_PYTHON_MEAN_SECONDS)

    factor_value = os.environ.get(SAFETY_FACTOR_ENV_VAR)
    try:
        safety_factor = float(factor_value) if factor_value is not None else DEFAULT_SAFETY_FACTOR
    except ValueError:
        safety_factor = DEFAULT_SAFETY_FACTOR

    if safety_factor < 1:
        safety_factor = 1.0

    return {
        label: BASELINE_PYTHON_MEAN_SECONDS[label] * safety_factor
        for label in PYTHON_BENCHMARK_LABELS
    }


PYTHON_THRESHOLD_SECONDS = _resolve_thresholds()


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


@pytest.mark.parametrize("label", PYTHON_BENCHMARK_LABELS)
def test_python_pipeline_regression_guard(
    benchmark_results: Mapping[str, BenchmarkResult],
    label: str,
) -> None:
    """Fail fast if the Python pipeline slows down dramatically on canonical samples."""

    threshold = PYTHON_THRESHOLD_SECONDS[label]
    mean_seconds = benchmark_results[label].python.mean_seconds
    assert mean_seconds <= threshold, (
        "Python pipeline mean for "
        f"'{label}' text exceeded {threshold:.3f}s: {mean_seconds:.3f}s. "
        f"Set {SAFETY_FACTOR_ENV_VAR} or {STRICT_ENV_VAR} to adjust the guard."
    )
