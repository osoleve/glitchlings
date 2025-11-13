"""Acceptance tests for metrics framework - Milestone 1.

These tests validate all metrics against hand-computed ground truth values
on toy sequences. This is the primary acceptance criterion for Milestone 1.

All tests must pass before proceeding to production implementations.
"""

from __future__ import annotations

import math

import pytest

from glitchlings.metrics.metrics.defaults import create_default_registry
from glitchlings.metrics.metrics.registry import MetricRegistry

from .fixtures.toy_sequences import TOY_SEQUENCES


@pytest.fixture
def registry() -> MetricRegistry:
    """Provide default metric registry."""
    return create_default_registry()


@pytest.mark.parametrize("case", TOY_SEQUENCES, ids=lambda c: c.name)
def test_metric_acceptance(registry: MetricRegistry, case) -> None:
    """Validate all metrics against hand-computed ground truth.

    This is the PRIMARY acceptance test for Milestone 1.
    """
    results = registry.compute_all(before=case.before, after=case.after, context={})

    # Test each expected metric
    for metric_key, expected in case.expected.items():
        # Handle both direct keys and nested keys (e.g., "ned" vs "ned.value")
        actual = results.get(metric_key)
        if actual is None:
            # Try with .value suffix
            actual = results.get(f"{metric_key}.value")

        # Also try aliased keys (e.g., lr.ratio, lr.delta)
        if actual is None and "." in metric_key:
            # Already has suffix, try as-is from results
            base_metric, suffix = metric_key.rsplit(".", 1)
            actual = results.get(f"{base_metric}.{suffix}")

        assert actual is not None, (
            f"{case.name}: Metric {metric_key!r} not computed. "
            f"Available: {sorted(results.keys())}"
        )

        if math.isfinite(expected) and math.isfinite(actual):
            assert actual == pytest.approx(expected, abs=case.tolerance), (
                f"{case.name}: {metric_key} = {actual:.6f}, "
                f"expected {expected:.6f} (±{case.tolerance})\n"
                f"Notes: {case.notes}"
            )
        else:
            # Handle inf/nan
            if math.isnan(expected):
                assert math.isnan(actual), f"{case.name}: {metric_key} should be NaN"
            elif math.isinf(expected):
                assert math.isinf(actual), f"{case.name}: {metric_key} should be inf"


def test_invariant_identity(registry: MetricRegistry) -> None:
    """INVARIANT: All distance metrics return 0 for identical sequences."""
    test_sequences = [
        [0, 1, 2, 3, 4],
        [5, 5, 5],
        [99],
        [],  # Empty
    ]

    for seq in test_sequences:
        results = registry.compute_all(seq, seq, {})

        for metric_key, value in results.items():
            # Skip non-distance metrics
            if any(
                skip in metric_key
                for skip in ["lr.ratio", "lr.delta", "h_delta", "c_delta"]
            ):
                continue

            # For retention/match rate metrics, expect 1.0 (not 0.0)
            if "lcsr" in metric_key or "pmr" in metric_key:
                # Skip empty sequences - retention is undefined
                if len(seq) == 0:
                    continue
                assert value == pytest.approx(1.0, abs=1e-6), (
                    f"Identity invariant failed for retention metric: "
                    f"{metric_key} = {value} (expected 1.0) on {seq}"
                )
            else:
                # Distance metrics should be 0
                assert value == pytest.approx(0.0, abs=1e-6), (
                    f"Identity invariant failed: {metric_key} = {value} on {seq}"
                )


def test_invariant_bounds(registry: MetricRegistry) -> None:
    """INVARIANT: All normalized metrics stay in [0, 1]."""
    test_pairs = [
        ([0, 1, 2], [3, 4, 5]),  # Zero overlap
        ([0, 0, 0], [1, 1, 1]),  # Total substitution
        ([0, 1], [1, 0]),  # Swap
        ([0, 1, 2, 3], [3, 2, 1, 0]),  # Reversal
        ([], [0]),  # Empty to single
        ([0], []),  # Single to empty
    ]

    for before, after in test_pairs:
        results = registry.compute_all(before, after, {})

        for metric_key, value in results.items():
            # Skip unbounded metrics and sub-metrics (only check .value metrics)
            if any(
                unbounded in metric_key
                for unbounded in [
                    "lr.ratio",
                    "lr.delta",
                    "h_delta",
                    "c_delta",
                    ".before",
                    ".after",
                    ".num_spans",
                    ".mean_span_length",
                    ".merges",
                    ".splits",
                    ".before_size",
                    ".after_size",
                ]
            ):
                continue

            assert 0.0 <= value <= 1.0, (
                f"Bounds violation: {metric_key} = {value} "
                f"for {before} → {after} (expected [0,1])"
            )


def test_invariant_symmetry(registry: MetricRegistry) -> None:
    """INVARIANT: Symmetric metrics give same result for (x,y) and (y,x)."""
    symmetric_metrics = ["ned", "jsdset", "jsdbag"]

    test_pairs = [
        ([0, 1, 2], [3, 4, 5]),
        ([0, 1], [1, 0]),
        ([0, 0, 0], [1, 1, 1]),
    ]

    for metric_id in symmetric_metrics:
        for before, after in test_pairs:
            result_forward = registry.compute(metric_id, before, after, {})
            result_backward = registry.compute(metric_id, after, before, {})

            # Compare all values in result dicts
            for key in result_forward:
                forward_val = result_forward[key]
                backward_val = result_backward.get(key)

                assert backward_val is not None, (
                    f"Symmetry test: {key} missing in backward result"
                )

                assert forward_val == pytest.approx(backward_val, abs=1e-6), (
                    f"Symmetry violation: {metric_id}.{key} "
                    f"forward={forward_val}, backward={backward_val} "
                    f"for {before} ↔ {after}"
                )


def test_edge_case_empty_sequences(registry: MetricRegistry) -> None:
    """Edge case: Empty sequences should not crash."""
    # Both empty
    results = registry.compute_all([], [], {})
    assert len(results) > 0, "Should compute metrics even for empty sequences"

    # One empty
    results = registry.compute_all([], [0, 1, 2], {})
    assert len(results) > 0

    results = registry.compute_all([0, 1, 2], [], {})
    assert len(results) > 0


def test_edge_case_single_token(registry: MetricRegistry) -> None:
    """Edge case: Single-token sequences should work."""
    # Identity
    results = registry.compute_all([5], [5], {})
    assert results["ned.value"] == pytest.approx(0.0)
    assert results["lcsr.value"] == pytest.approx(1.0)

    # Substitution
    results = registry.compute_all([5], [9], {})
    assert results["ned.value"] == pytest.approx(1.0)
    assert results["lcsr.value"] == pytest.approx(0.0)


def test_metric_registry_operations(registry: MetricRegistry) -> None:
    """Test registry operations: register, unregister, get, list."""
    # Check initial state
    assert len(registry) > 0
    assert "ned" in registry
    assert "jsdset" in registry

    # Get metric
    ned_spec = registry.get("ned")
    assert ned_spec is not None
    assert ned_spec.id == "ned"

    # List metrics
    all_metrics = list(registry.list_metrics())
    assert len(all_metrics) == len(registry)

    # Unregister (note: modifies registry, so do this last)
    registry.unregister("ned")
    assert "ned" not in registry
    assert len(registry) == len(all_metrics) - 1


def test_metric_registry_compute_single() -> None:
    """Test computing a single metric via registry.compute()."""
    registry = create_default_registry()

    result = registry.compute("ned", [0, 1, 2], [0, 2, 1], {})

    assert "ned.value" in result
    assert result["ned.value"] == pytest.approx(1 / 3, abs=1e-6)


def test_metric_registry_missing_dependency() -> None:
    """Test graceful handling of missing context dependencies."""
    from glitchlings.metrics.metrics.registry import MetricRegistry, MetricSpec

    def metric_needs_lm(before, after, context):
        lm = context["lm"]  # Requires "lm" key
        _ = lm  # Use the lm value
        return {"value": 0.5}

    registry = MetricRegistry()
    registry.register(
        MetricSpec(
            id="ppl", name="Perplexity", fn=metric_needs_lm, requires=["lm"]
        )
    )

    # Should raise KeyError when computing without context
    with pytest.raises(KeyError, match="requires context key 'lm'"):
        registry.compute("ppl", [0, 1, 2], [0, 2, 1], {})

    # Should skip gracefully in compute_all
    results = registry.compute_all([0, 1, 2], [0, 2, 1], {})
    assert "ppl.value" not in results  # Skipped due to missing dependency


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
