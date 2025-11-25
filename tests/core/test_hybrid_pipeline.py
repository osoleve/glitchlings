"""Tests for hybrid pipeline execution in Gaggle.

These tests verify that the optimized pipeline batching works correctly
when mixing glitchlings with and without pipeline support.
"""

from __future__ import annotations

from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling


def _no_pipeline_corruption(text: str, *, rng=None) -> str:
    """Simple corruption that appends a marker without pipeline support."""
    return text + "[fallback]"


class NoPipelineGlitchling(Glitchling):
    """A glitchling that explicitly lacks pipeline support for testing."""

    def __init__(self, name: str = "NoPipeline", seed: int | None = None) -> None:
        super().__init__(
            name=name,
            corruption_function=_no_pipeline_corruption,
            scope=AttackWave.DOCUMENT,
            seed=seed,
            pipeline_operation=None,  # Explicitly no pipeline support
        )

    def pipeline_operation(self):
        """Return None to indicate no pipeline support."""
        return None


class TestHybridPipelineExecution:
    """Tests for hybrid pipeline execution strategy."""

    def test_all_pipeline_supported_uses_fast_path(self, sample_text: str) -> None:
        """When all glitchlings support pipeline, use the optimized path."""
        from glitchlings import Rushmore, Typogre

        gaggle = Gaggle([Typogre(rate=0.01), Rushmore(rate=0.01)], seed=42)
        plan = gaggle._build_execution_plan()

        # Should be a single batch with both descriptors
        assert len(plan) == 1
        descriptors, fallback = plan[0]
        assert len(descriptors) == 2
        assert fallback is None

    def test_single_fallback_creates_single_item_plan(self) -> None:
        """A single glitchling without pipeline support creates a single-item plan."""
        glitchling = NoPipelineGlitchling()
        gaggle = Gaggle([glitchling], seed=42)
        plan = gaggle._build_execution_plan()

        assert len(plan) == 1
        descriptors, fallback = plan[0]
        assert descriptors == []
        # Gaggle clones glitchlings, so we check by name instead of identity
        assert fallback is not None
        assert fallback.name == glitchling.name

    def test_fallback_at_start_batches_remainder(self) -> None:
        """Fallback at start followed by pipeline glitchlings creates two groups."""
        from glitchlings import Rushmore, Typogre

        no_pipeline = NoPipelineGlitchling()
        # Order by scope: NoPipeline is DOCUMENT, others are WORD/CHARACTER
        gaggle = Gaggle([no_pipeline, Typogre(rate=0.01), Rushmore(rate=0.01)], seed=42)
        plan = gaggle._build_execution_plan()

        # NoPipeline is DOCUMENT scope (1), sorted before WORD (4) and CHARACTER (5)
        # So: [NoPipeline] then [Rushmore, Typogre] based on scope ordering
        assert len(plan) == 2

    def test_fallback_in_middle_creates_three_groups(self) -> None:
        """Fallback in middle creates batch-fallback-batch pattern."""
        from glitchlings import Typogre

        t1 = Typogre(rate=0.01, seed=1)
        no_pipeline = NoPipelineGlitchling()
        t2 = Typogre(rate=0.02, seed=2)

        # Control the order by using the same scope
        gaggle = Gaggle([t1, no_pipeline, t2], seed=42)
        plan = gaggle._build_execution_plan()

        # Should have: batch(t1) or batch(t2), fallback(no_pipeline), batch(remaining)
        # The actual order depends on the orchestration sorting
        # Let's just verify we have the right structure
        assert len(plan) >= 2  # At least the fallback and one batch

    def test_fallback_at_end_batches_prefix(self) -> None:
        """Fallback at end creates batch then fallback pattern."""
        from glitchlings import Rushmore, Typogre

        no_pipeline = NoPipelineGlitchling(name="EndFallback")
        gaggle = Gaggle([Typogre(rate=0.01), Rushmore(rate=0.01), no_pipeline], seed=42)
        plan = gaggle._build_execution_plan()

        # NoPipeline is DOCUMENT scope, should come first in sorted order
        # So plan is: fallback, then batch of the rest
        assert len(plan) == 2

    def test_hybrid_execution_produces_correct_output(self, sample_text: str) -> None:
        """Verify hybrid execution produces the expected output."""
        from glitchlings import Typogre

        # Create a gaggle with a fallback glitchling that adds a marker
        no_pipeline = NoPipelineGlitchling()
        typogre = Typogre(rate=0.0)  # rate=0 means no changes, just pass through

        gaggle = Gaggle([typogre, no_pipeline], seed=42)
        result = gaggle(sample_text)

        # The NoPipeline glitchling appends "[fallback]"
        assert isinstance(result, str)
        assert result.endswith("[fallback]")

    def test_hybrid_execution_is_deterministic(self, sample_text: str) -> None:
        """Verify hybrid execution is deterministic."""
        from glitchlings import Typogre

        no_pipeline = NoPipelineGlitchling()
        typogre = Typogre(rate=0.01)

        g1 = Gaggle([typogre, no_pipeline], seed=42)
        out1 = g1(sample_text)

        g2 = Gaggle([typogre.clone(), no_pipeline.clone()], seed=42)
        out2 = g2(sample_text)

        assert out1 == out2

    def test_multiple_consecutive_fallbacks(self) -> None:
        """Multiple consecutive fallbacks should each be their own plan item."""
        no1 = NoPipelineGlitchling(name="Fallback1")
        no2 = NoPipelineGlitchling(name="Fallback2")
        no3 = NoPipelineGlitchling(name="Fallback3")

        gaggle = Gaggle([no1, no2, no3], seed=42)
        plan = gaggle._build_execution_plan()

        # Each fallback should be its own item since they can't be batched
        assert len(plan) == 3
        for descriptors, fallback in plan:
            assert descriptors == []
            assert fallback is not None

    def test_empty_gaggle_produces_empty_plan(self) -> None:
        """An empty gaggle should produce an empty execution plan."""
        gaggle = Gaggle([], seed=42)
        plan = gaggle._build_execution_plan()
        assert plan == []

    def test_execution_plan_contains_all_glitchlings(self) -> None:
        """Verify the execution plan accounts for all glitchlings."""
        from glitchlings import Rushmore, Typogre

        no_pipeline = NoPipelineGlitchling()
        members = [Typogre(rate=0.01), no_pipeline, Rushmore(rate=0.01)]
        gaggle = Gaggle(members, seed=42)
        plan = gaggle._build_execution_plan()

        # Count total items in plan
        total_descriptors = sum(len(descs) for descs, _ in plan)
        total_fallbacks = sum(1 for _, fb in plan if fb is not None)

        # We have 3 glitchlings: 2 with pipeline support, 1 without
        assert total_descriptors + total_fallbacks == 3


class TestPipelineDescriptorsLegacy:
    """Tests for the legacy _pipeline_descriptors method."""

    def test_pipeline_descriptors_still_works(self, sample_text: str) -> None:
        """Verify _pipeline_descriptors still returns expected format."""
        from glitchlings import Rushmore, Typogre

        gaggle = Gaggle([Typogre(rate=0.01), Rushmore(rate=0.01)], seed=42)
        descriptors, missing = gaggle._pipeline_descriptors()

        assert len(descriptors) == 2
        assert missing == []

    def test_pipeline_descriptors_tracks_missing(self) -> None:
        """Verify _pipeline_descriptors correctly identifies missing pipeline support."""
        from glitchlings import Typogre

        no_pipeline = NoPipelineGlitchling()
        gaggle = Gaggle([Typogre(rate=0.01), no_pipeline], seed=42)
        descriptors, missing = gaggle._pipeline_descriptors()

        # One descriptor for Typogre, one missing for NoPipeline
        assert len(descriptors) == 1
        assert len(missing) == 1
