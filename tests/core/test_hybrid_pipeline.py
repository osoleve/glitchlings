"""Tests for hybrid pipeline execution in Gaggle.

These tests verify that the optimized pipeline batching works correctly
when mixing glitchlings with and without pipeline support.
"""

from __future__ import annotations

from glitchlings.zoo.core import AttackWave, Gaggle, Glitchling
from glitchlings.zoo.core_planning import build_execution_plan


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


def _build_plan(gaggle: Gaggle):
    return build_execution_plan(
        gaggle.apply_order,
        master_seed=gaggle.seed,
        derive_seed_fn=Gaggle.derive_seed,
    )


class TestHybridPipelineExecution:
    """Tests for hybrid pipeline execution strategy."""

    def test_all_pipeline_supported_uses_fast_path(self) -> None:
        """When all glitchlings support pipeline, use the optimized path."""
        from glitchlings import Rushmore, Typogre

        gaggle = Gaggle([Typogre(rate=0.01), Rushmore(rate=0.01)], seed=42)
        plan = _build_plan(gaggle)

        assert plan.step_count == 1
        step = plan.steps[0]
        assert step.is_pipeline_step
        assert len(step.descriptors) == 2
        assert step.fallback_glitchling is None

    def test_single_fallback_creates_single_item_plan(self) -> None:
        """A single glitchling without pipeline support creates a single-item plan."""
        glitchling = NoPipelineGlitchling()
        gaggle = Gaggle([glitchling], seed=42)
        plan = _build_plan(gaggle)

        assert plan.step_count == 1
        step = plan.steps[0]
        assert step.is_fallback_step
        assert step.descriptors == ()
        fallback = step.fallback_glitchling
        assert fallback is not None
        # Gaggle clones glitchlings, so we check by name instead of identity
        assert fallback.name == glitchling.name

    def test_mixed_pipeline_and_fallback_batches_pipeline_sequences(self) -> None:
        """Fallback glitchlings split batching, but pipeline descriptors still group."""
        from glitchlings import Rushmore, Typogre

        no_pipeline = NoPipelineGlitchling()
        # Order by scope: NoPipeline is DOCUMENT, others are WORD/CHARACTER
        gaggle = Gaggle([no_pipeline, Typogre(rate=0.01), Rushmore(rate=0.01)], seed=42)
        plan = _build_plan(gaggle)

        assert plan.step_count == 2
        assert plan.pipeline_step_count == 1
        assert plan.fallback_step_count == 1

        fallback_step, pipeline_step = plan.steps
        assert fallback_step.is_fallback_step
        assert pipeline_step.is_pipeline_step
        descriptor_names = {descriptor["name"] for descriptor in pipeline_step.descriptors}
        assert {"Rushmore", "Typogre"} == descriptor_names

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
        plan = _build_plan(gaggle)

        # Each fallback should be its own item since they can't be batched
        assert plan.step_count == 3
        for step in plan.steps:
            assert step.descriptors == ()
            assert step.fallback_glitchling is not None

    def test_empty_gaggle_produces_empty_plan(self) -> None:
        """An empty gaggle should produce an empty execution plan."""
        gaggle = Gaggle([], seed=42)
        plan = _build_plan(gaggle)
        assert plan.steps == ()
        assert plan.all_pipeline

    def test_execution_plan_contains_all_glitchlings(self) -> None:
        """Verify the execution plan accounts for all glitchlings."""
        from glitchlings import Rushmore, Typogre

        no_pipeline = NoPipelineGlitchling()
        members = [Typogre(rate=0.01), no_pipeline, Rushmore(rate=0.01)]
        gaggle = Gaggle(members, seed=42)
        plan = _build_plan(gaggle)

        # Count total items in plan
        total_descriptors = sum(len(step.descriptors) for step in plan.steps)
        total_fallbacks = sum(1 for step in plan.steps if step.fallback_glitchling is not None)

        # We have 3 glitchlings: 2 with pipeline support, 1 without
        assert total_descriptors + total_fallbacks == 3


class TestPipelineDescriptorsLegacy:
    """Tests for the legacy _pipeline_descriptors method."""

    def test_pipeline_descriptors_still_works(self) -> None:
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
