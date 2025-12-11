"""Impure execution dispatch for Gaggle orchestration.

This module handles the actual execution of glitchling plans, including
Rust FFI calls and Python fallback execution. It is the impure counterpart
to core_planning.py.

**Design Philosophy:**

This module is explicitly *impure* - it invokes compiled Rust functions
and executes Python corruption functions with side effects. All Rust
dispatch for Gaggle orchestration flows through this module.

The separation allows:
- Pure planning logic to be tested without Rust
- Clear boundaries between plan construction and execution
- Mocking execution for integration tests

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from glitchlings.internal.rust_ffi import compose_operations_rust

if TYPE_CHECKING:
    from .core_planning import ExecutionPlan, PipelineDescriptor


# ---------------------------------------------------------------------------
# Plan Execution
# ---------------------------------------------------------------------------


def execute_plan(
    text: str,
    plan: ExecutionPlan,
    master_seed: int,
    *,
    include_only_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    pipeline: Any | None = None,
) -> str:
    """Execute an orchestration plan against input text.

    This function dispatches plan steps to either the Rust pipeline or
    Python fallback execution as appropriate.

    Args:
        text: Input text to transform.
        plan: Execution plan from build_execution_plan().
        master_seed: Master seed for Rust pipeline.

    Returns:
        Transformed text after all plan steps complete.
    """
    # Fast path: all glitchlings support pipeline
    if plan.all_pipeline and plan.step_count == 1:
        if pipeline is not None:
            return compose_with_pipeline(
                pipeline,
                text,
                include_only_patterns=include_only_patterns,
                exclude_patterns=exclude_patterns,
            )
        descriptors = list(plan.steps[0].descriptors)
        return compose_operations_rust(
            text,
            descriptors,
            master_seed,
            include_only_patterns=include_only_patterns,
            exclude_patterns=exclude_patterns,
        )

    # Hybrid path: mix of pipeline batches and individual fallbacks
    result = text

    for step in plan.steps:
        if step.is_pipeline_step:
            # Execute the batch through the Rust pipeline
            descriptors = list(step.descriptors)
            result = compose_operations_rust(
                result,
                descriptors,
                master_seed,
                include_only_patterns=include_only_patterns,
                exclude_patterns=exclude_patterns,
            )
        elif step.fallback_glitchling is not None:
            # Execute single glitchling via Python fallback
            result = cast(str, step.fallback_glitchling.corrupt(result))

    return result


def execute_descriptors(
    text: str,
    descriptors: list[PipelineDescriptor],
    master_seed: int,
    *,
    include_only_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    pipeline: Any | None = None,
) -> str:
    """Execute a list of pipeline descriptors through Rust.

    This is a thin wrapper over compose_operations_rust for cases
    where the caller has already constructed descriptors directly.

    Args:
        text: Input text to transform.
        descriptors: Pipeline descriptors for each glitchling.
        master_seed: Master seed for Rust pipeline.

    Returns:
        Transformed text.
    """
    if pipeline is not None:
        return compose_with_pipeline(
            pipeline,
            text,
            include_only_patterns=include_only_patterns,
            exclude_patterns=exclude_patterns,
        )

    return compose_operations_rust(
        text,
        descriptors,
        master_seed,
        include_only_patterns=include_only_patterns,
        exclude_patterns=exclude_patterns,
    )


def compose_with_pipeline(
    pipeline: Any,
    text: str,
    *,
    include_only_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> str:
    """Run a pre-built Rust pipeline while preserving masking kwargs."""
    if include_only_patterns or exclude_patterns:
        raise RuntimeError(
            "Cached pipelines already embed masking patterns; overrides are not supported."
        )
    return cast(str, pipeline.run(text))


__all__ = [
    "execute_plan",
    "execute_descriptors",
]
