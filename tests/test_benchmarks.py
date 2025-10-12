"""Regression checks for the benchmarking utilities."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
import datetime as dt
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.pipeline_benchmark import (
    BenchmarkResult,
    BenchmarkStatistics,
    SCENARIOS,
    collect_benchmark_results,
    main,
    run_benchmarks,
)
import benchmarks.pipeline_benchmark as pipeline_module

STRICT_ENV_VAR = "GLITCHLINGS_BENCHMARK_STRICT"
SAFETY_FACTOR_ENV_VAR = "GLITCHLINGS_BENCHMARK_SAFETY_FACTOR"
BASELINE_PYTHON_MEAN_SECONDS: dict[str, float] = {
    "short": 0.01,
    "medium": 0.03,
    "long": 0.1,
}
DEFAULT_SAFETY_FACTOR = 12.0
PYTHON_BENCHMARK_LABELS = tuple(BASELINE_PYTHON_MEAN_SECONDS.keys())
RUST_PARITY_ENV_VAR = "GLITCHLINGS_RUST_PARITY_THRESHOLD"
DEFAULT_RUST_PARITY_THRESHOLD = 1.25


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


def _resolve_rust_parity_threshold() -> float:
    raw_value = os.environ.get(RUST_PARITY_ENV_VAR)
    if raw_value is None:
        return DEFAULT_RUST_PARITY_THRESHOLD
    try:
        threshold = float(raw_value)
    except ValueError:
        return DEFAULT_RUST_PARITY_THRESHOLD
    if threshold < 1.0:
        return 1.0
    return threshold


RUST_PARITY_THRESHOLD = _resolve_rust_parity_threshold()


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


def test_pipeline_benchmark_main_lists_scenarios(capsys) -> None:
    exit_code = main(["--list-scenarios"])
    captured = capsys.readouterr()

    assert exit_code == 0
    for key in SCENARIOS:
        assert key in captured.out


def test_run_benchmarks_supports_stub_scenario(monkeypatch) -> None:
    stub_called: dict[str, bool] = {}

    def _stub_builder():
        stub_called["built"] = True
        return ()

    monkeypatch.setitem(SCENARIOS, "stub", _stub_builder)

    fake_result = BenchmarkResult(
        label="tiny",
        char_count=4,
        python=BenchmarkStatistics(mean_seconds=0.001, stdev_seconds=0.0),
        rust=None,
    )

    monkeypatch.setattr(
        "benchmarks.pipeline_benchmark.collect_benchmark_results",
        lambda texts, iterations, descriptors: [fake_result],
    )

    captured: dict[str, object] = {}

    def _capture_results(scenario: str, results: list[BenchmarkResult]) -> None:
        captured["scenario"] = scenario
        captured["results"] = results

    monkeypatch.setattr("benchmarks.pipeline_benchmark._print_results", _capture_results)

    run_benchmarks(["stub"], [("tiny", "data")], iterations=1)

    assert stub_called.get("built") is True
    assert captured["scenario"] == "stub"
    assert captured["results"] == [fake_result]


@pytest.mark.skipif(
    getattr(pipeline_module, "zoo_rust", None) is None,
    reason="Rust acceleration unavailable",
)
def test_rust_pipeline_within_parity_threshold() -> None:
    """Ensure the Rust pipeline stays reasonably close to the Python timings."""

    results = collect_benchmark_results(iterations=5)
    assert all(result.rust is not None for result in results), (
        "Rust-backed benchmarks returned no results; ensure glitchlings._zoo_rust is importable."
    )
    for result in results:
        assert result.rust is not None  # for type checkers
        assert result.rust.mean_seconds <= result.python.mean_seconds * RUST_PARITY_THRESHOLD, (
            "Rust pipeline slower than Python beyond allowed threshold; "
            f"adjust via {RUST_PARITY_ENV_VAR} if this is expected."
        )


def test_performance_report_documentation_matches_builder(monkeypatch) -> None:
    """Ensure the performance documentation stays in sync with the generator."""

    import docs.build_performance_report as builder

    scenario_names = ["baseline", "shuffle_mix", "aggressive_cleanup", "stealth_noise"]
    sentinel_key = "__scenario__"

    fixed_timestamp = dt.datetime(
        2025, 10, 12, 14, 21, 51, 882961, tzinfo=dt.timezone.utc
    )

    class _FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> dt.datetime:
            if tz is None:
                return fixed_timestamp
            return fixed_timestamp.astimezone(tz)

    monkeypatch.setattr(builder.dt, "datetime", _FixedDateTime)
    monkeypatch.setattr(builder.platform, "python_version", lambda: "3.12.3")
    monkeypatch.setattr(builder.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(builder.platform, "system", lambda: "Windows")
    monkeypatch.setattr(builder.platform, "release", lambda: "11")
    monkeypatch.setattr(builder.platform, "machine", lambda: "AMD64")

    monkeypatch.setattr(
        builder,
        "SCENARIOS",
        OrderedDict(
            (name, (lambda name=name: [{sentinel_key: name}])) for name in scenario_names
        ),
    )

    def _stats(mean_ms: float, stdev_ms: float) -> BenchmarkStatistics:
        return BenchmarkStatistics(
            mean_seconds=mean_ms / 1000,
            stdev_seconds=stdev_ms / 1000,
        )

    stub_results = {
        "baseline": [
            BenchmarkResult(
                label="short",
                char_count=121,
                python=_stats(0.314, 1.480),
                rust=_stats(0.102, 0.078),
            ),
            BenchmarkResult(
                label="medium",
                char_count=3903,
                python=_stats(6.066, 0.374),
                rust=_stats(1.051, 0.131),
            ),
            BenchmarkResult(
                label="long",
                char_count=31231,
                python=_stats(245.037, 15.462),
                rust=_stats(35.543, 2.227),
            ),
        ],
        "shuffle_mix": [
            BenchmarkResult(
                label="short",
                char_count=121,
                python=_stats(0.223, 0.022),
                rust=_stats(0.110, 0.014),
            ),
            BenchmarkResult(
                label="medium",
                char_count=3903,
                python=_stats(7.701, 0.790),
                rust=_stats(1.186, 0.138),
            ),
            BenchmarkResult(
                label="long",
                char_count=31231,
                python=_stats(271.504, 16.501),
                rust=_stats(40.106, 2.213),
            ),
        ],
        "aggressive_cleanup": [
            BenchmarkResult(
                label="short",
                char_count=121,
                python=_stats(0.149, 0.022),
                rust=_stats(0.0975, 0.011),
            ),
            BenchmarkResult(
                label="medium",
                char_count=3903,
                python=_stats(8.706, 1.110),
                rust=_stats(1.411, 0.125),
            ),
            BenchmarkResult(
                label="long",
                char_count=31231,
                python=_stats(427.002, 27.374),
                rust=_stats(66.710, 4.058),
            ),
        ],
        "stealth_noise": [
            BenchmarkResult(
                label="short",
                char_count=121,
                python=_stats(0.108, 0.036),
                rust=_stats(0.0412, 0.004),
            ),
            BenchmarkResult(
                label="medium",
                char_count=3903,
                python=_stats(5.786, 1.074),
                rust=_stats(0.586, 0.088),
            ),
            BenchmarkResult(
                label="long",
                char_count=31231,
                python=_stats(230.450, 22.247),
                rust=_stats(21.800, 3.067),
            ),
        ],
    }

    def _fake_collect(
        texts: object, iterations: int, descriptors: list[dict[str, object]]
    ) -> list[BenchmarkResult]:
        del texts, iterations
        scenario = descriptors[0][sentinel_key]
        return stub_results[str(scenario)]

    monkeypatch.setattr(builder, "collect_benchmark_results", _fake_collect)

    expected = builder.build_report_content(iterations=100)
    doc_path = ROOT / "docs" / "performance-comparison.md"
    actual = doc_path.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/performance-comparison.md is out of date. "
        "Regenerate it via docs/build_performance_report.py."
    )
