from __future__ import annotations

import time


class FakeStatelessMasker:
    """Simulates the legacy stateless masking path with per-call compile cost."""

    compile_cost = 0.003

    @classmethod
    def run(cls, text: str) -> str:
        time.sleep(cls.compile_cost)
        return text.replace(" ", "_")


class FakePipeline:
    """Mocks the cached Rust pipeline with a one-time compile step."""

    compile_cost = 0.003

    def __init__(self) -> None:
        start = time.perf_counter()
        time.sleep(self.compile_cost)
        self.initialised_at = time.perf_counter() - start

    def run(self, text: str) -> str:
        return text.upper()


def _time_stateless(iterations: int, text: str) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        FakeStatelessMasker.run(text)
    return time.perf_counter() - start


def _time_pipeline(iterations: int, text: str) -> tuple[float, float]:
    pipeline = FakePipeline()
    start = time.perf_counter()
    for _ in range(iterations):
        pipeline.run(text)
    run_duration = time.perf_counter() - start
    return pipeline.initialised_at, run_duration


def test_cached_pipeline_outperforms_stateless_mock() -> None:
    iterations = 12
    sample = "alpha beta gamma delta"

    stateless_total = _time_stateless(iterations, sample)
    init_cost, cached_run = _time_pipeline(iterations, sample)

    # Cached pipeline should pay the compile cost once and win overall.
    assert stateless_total > cached_run + init_cost
    # Initialisation remains the dominant cost for the cached path.
    assert init_cost > cached_run / max(iterations / 4, 1)
