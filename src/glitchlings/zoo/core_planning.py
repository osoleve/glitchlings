"""Pure orchestration planning functions.

This module contains the deterministic, side-effect-free logic for building
glitchling execution plans. It converts glitchling metadata into structured
plans that can be executed by the impure dispatch layer.

**Design Philosophy:**

All functions in this module are *pure* - they perform plan construction
based solely on their inputs, without side effects. They do not:
- Import or invoke Rust FFI
- Read configuration files
- Create RNG instances
- Perform I/O of any kind

The separation allows:
- Plan verification without Rust dependencies
- Unit testing of orchestration logic in isolation
- Clear boundaries between planning and execution

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, Union, cast, runtime_checkable

# ---------------------------------------------------------------------------
# Type Definitions
# ---------------------------------------------------------------------------


class PlanSpecification(TypedDict):
    """Raw mapping describing glitchling orchestration metadata."""

    name: str
    scope: int
    order: int


class PipelineOperationPayload(TypedDict, total=False):
    """Typed mapping describing a Rust pipeline operation."""

    type: str


class PipelineDescriptor(TypedDict):
    """Typed mapping representing a glitchling's Rust pipeline descriptor."""

    name: str
    operation: PipelineOperationPayload
    seed: int


PlanEntry = Union["GlitchlingProtocol", Mapping[str, Any]]


@runtime_checkable
class GlitchlingProtocol(Protocol):
    """Protocol describing the glitchling attributes needed for planning."""

    name: str
    level: Any  # AttackWave enum
    order: Any  # AttackOrder enum
    seed: int | None

    def pipeline_operation(self) -> PipelineOperationPayload | None:
        """Return the Rust pipeline descriptor or None."""
        ...

    def corrupt(self, text: Any) -> Any:
        """Apply corruption to text (may handle str or Transcript)."""
        ...


# ---------------------------------------------------------------------------
# Plan Specification Normalization
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class NormalizedPlanSpec:
    """Concrete representation of orchestration metadata consumed by Rust.

    This dataclass normalizes glitchling metadata into a form suitable for
    the Rust orchestration planner. It can be constructed from either a
    Glitchling instance or a raw mapping specification.
    """

    name: str
    scope: int
    order: int

    @classmethod
    def from_glitchling(cls, glitchling: GlitchlingProtocol) -> NormalizedPlanSpec:
        """Create a plan spec from a Glitchling instance.

        Args:
            glitchling: A glitchling with name, level, and order attributes.

        Returns:
            Normalized plan specification.
        """
        return cls(glitchling.name, int(glitchling.level), int(glitchling.order))

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> NormalizedPlanSpec:
        """Create a plan spec from a raw mapping.

        Args:
            mapping: Dictionary with 'name', 'scope', and 'order' keys.

        Returns:
            Normalized plan specification.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        try:
            name = str(mapping["name"])
            scope_value = int(mapping["scope"])
            order_value = int(mapping["order"])
        except KeyError as exc:
            raise ValueError(f"Plan specification missing required field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError("Plan specification fields must be coercible to integers") from exc

        return cls(name, scope_value, order_value)

    @classmethod
    def from_entry(cls, entry: PlanEntry) -> NormalizedPlanSpec:
        """Create a plan spec from either a Glitchling or mapping.

        Args:
            entry: A Glitchling instance or raw specification mapping.

        Returns:
            Normalized plan specification.

        Raises:
            TypeError: If entry is neither a Glitchling nor a mapping.
        """
        if isinstance(entry, GlitchlingProtocol):
            return cls.from_glitchling(entry)
        if not isinstance(entry, Mapping):
            message = "Expected Glitchling instances or mapping specifications"
            raise TypeError(message)
        return cls.from_mapping(entry)

    def as_mapping(self) -> PlanSpecification:
        """Convert to a raw mapping for Rust consumption.

        Returns:
            Dictionary with name, scope, and order keys.
        """
        return {"name": self.name, "scope": self.scope, "order": self.order}


def normalize_plan_entries(entries: Sequence[PlanEntry]) -> list[NormalizedPlanSpec]:
    """Normalize a collection of orchestration plan entries.

    Args:
        entries: Sequence of Glitchling instances or raw specifications.

    Returns:
        List of normalized plan specifications.
    """
    return [NormalizedPlanSpec.from_entry(entry) for entry in entries]


def normalize_plan_specs(specs: Sequence[Mapping[str, Any]]) -> list[NormalizedPlanSpec]:
    """Normalize raw plan specification mappings.

    Args:
        specs: Sequence of raw specification mappings.

    Returns:
        List of normalized plan specifications.
    """
    return [NormalizedPlanSpec.from_mapping(spec) for spec in specs]


# ---------------------------------------------------------------------------
# Pipeline Descriptor Construction
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PipelineDescriptorModel:
    """In-memory representation of a glitchling pipeline descriptor.

    This model captures the data needed to invoke a glitchling through
    the Rust pipeline: its name, computed seed, and operation payload.
    """

    name: str
    seed: int
    operation: PipelineOperationPayload

    def as_mapping(self) -> PipelineDescriptor:
        """Convert to a dictionary for Rust consumption.

        Returns:
            Dictionary with name, operation, and seed keys.
        """
        return {"name": self.name, "operation": self.operation, "seed": self.seed}


def build_pipeline_descriptor(
    glitchling: GlitchlingProtocol,
    *,
    master_seed: int | None,
    derive_seed_fn: Any,  # Callable[[int, str, int], int]
) -> PipelineDescriptorModel | None:
    """Materialise the Rust pipeline descriptor for a glitchling when available.

    This is a pure function that constructs the descriptor data without
    invoking Rust. The actual Rust dispatch happens in core_execution.

    Args:
        glitchling: The glitchling to build a descriptor for.
        master_seed: Master seed for the enclosing Gaggle.
        derive_seed_fn: Function to derive child seeds from master seed.
            Signature: (master_seed: int, name: str, index: int) -> int

    Returns:
        PipelineDescriptorModel if the glitchling supports pipeline execution,
        None otherwise.

    Raises:
        RuntimeError: If seed cannot be determined for a pipeline-enabled glitchling.
    """
    operation = glitchling.pipeline_operation()
    if operation is None:
        return None

    if not isinstance(operation, Mapping):
        raise TypeError("Pipeline operations must be mappings or None")

    operation_payload = dict(operation)
    operation_type = operation_payload.get("type")
    if not isinstance(operation_type, str):
        message = f"Pipeline operation for {glitchling.name} is missing a string 'type'"
        raise RuntimeError(message)

    seed = glitchling.seed
    if seed is None:
        index = getattr(glitchling, "_gaggle_index", None)
        if index is None or master_seed is None:
            raise RuntimeError(
                "Glitchling %s is missing deterministic seed configuration" % glitchling.name
            )
        seed = derive_seed_fn(master_seed, glitchling.name, index)

    payload = cast(PipelineOperationPayload, operation_payload)
    return PipelineDescriptorModel(glitchling.name, int(seed), payload)


# ---------------------------------------------------------------------------
# Execution Plan Construction
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ExecutionStep:
    """A single step in the execution plan.

    Represents either a batch of pipeline descriptors (for Rust execution)
    or a single glitchling for fallback Python execution.

    Attributes:
        descriptors: List of pipeline descriptors for batch Rust execution.
            Empty when this step is a fallback.
        fallback_glitchling: Glitchling to execute via Python when
            pipeline execution is not available. None when using pipeline.
    """

    descriptors: tuple[PipelineDescriptor, ...]
    fallback_glitchling: GlitchlingProtocol | None

    @property
    def is_pipeline_step(self) -> bool:
        """Return True if this step uses the Rust pipeline."""
        return len(self.descriptors) > 0

    @property
    def is_fallback_step(self) -> bool:
        """Return True if this step uses Python fallback."""
        return self.fallback_glitchling is not None


@dataclass(slots=True, frozen=True)
class ExecutionPlan:
    """Complete execution plan for a Gaggle's text corruption.

    The plan consists of ordered steps that can be either:
    - Pipeline batches: Multiple glitchlings executed together via Rust
    - Fallback steps: Single glitchlings executed via Python

    Consecutive pipeline-enabled glitchlings are batched together to
    minimize tokenization overhead.

    Attributes:
        steps: Ordered sequence of execution steps.
        all_pipeline: True if all glitchlings support pipeline execution.
    """

    steps: tuple[ExecutionStep, ...]
    all_pipeline: bool

    @property
    def step_count(self) -> int:
        """Return the number of execution steps."""
        return len(self.steps)

    @property
    def pipeline_step_count(self) -> int:
        """Return the number of pipeline batch steps."""
        return sum(1 for step in self.steps if step.is_pipeline_step)

    @property
    def fallback_step_count(self) -> int:
        """Return the number of fallback steps."""
        return sum(1 for step in self.steps if step.is_fallback_step)


def build_execution_plan(
    apply_order: Sequence[GlitchlingProtocol],
    *,
    master_seed: int | None,
    derive_seed_fn: Any,  # Callable[[int, str, int], int]
) -> ExecutionPlan:
    """Build an execution plan that batches consecutive pipeline-supported glitchlings.

    This is a pure function that analyzes glitchlings and constructs an
    optimal execution plan. The plan batches consecutive pipeline-enabled
    glitchlings to reduce tokenization overhead, while isolating fallback
    glitchlings that require Python execution.

    Args:
        apply_order: Ordered sequence of glitchlings to execute.
        master_seed: Master seed for seed derivation.
        derive_seed_fn: Function to derive child seeds.

    Returns:
        ExecutionPlan containing ordered execution steps.

    Example:
        If glitchlings A, B (pipeline), C (fallback), D, E (pipeline):
        Plan: [(A, B descriptors), (C fallback), (D, E descriptors)]
    """
    steps: list[ExecutionStep] = []
    current_batch: list[PipelineDescriptor] = []

    for glitchling in apply_order:
        descriptor = build_pipeline_descriptor(
            glitchling,
            master_seed=master_seed,
            derive_seed_fn=derive_seed_fn,
        )
        if descriptor is not None:
            current_batch.append(descriptor.as_mapping())
        else:
            # Flush any accumulated batch before the fallback item
            if current_batch:
                steps.append(ExecutionStep(tuple(current_batch), None))
                current_batch = []
            # Add the fallback step
            steps.append(ExecutionStep((), glitchling))

    # Flush any remaining batch
    if current_batch:
        steps.append(ExecutionStep(tuple(current_batch), None))

    all_pipeline = len(steps) == 1 and steps[0].fallback_glitchling is None if steps else True

    return ExecutionPlan(tuple(steps), all_pipeline)


# ---------------------------------------------------------------------------
# Plan Validation Helpers
# ---------------------------------------------------------------------------


def validate_plan_coverage(
    plan: Sequence[tuple[int, int]],
    expected_count: int,
) -> set[int]:
    """Validate that an orchestration plan covers all expected indices.

    Args:
        plan: Sequence of (index, seed) tuples from Rust planner.
        expected_count: Number of glitchlings that should be covered.

    Returns:
        Set of missing indices (empty if plan is complete).
    """
    covered = {index for index, _ in plan}
    expected = set(range(expected_count))
    return expected - covered


def extract_plan_ordering(plan: Sequence[tuple[int, int]]) -> list[int]:
    """Extract the execution order from an orchestration plan.

    Args:
        plan: Sequence of (index, seed) tuples.

    Returns:
        List of indices in execution order.
    """
    return [index for index, _ in plan]


def extract_plan_seeds(plan: Sequence[tuple[int, int]]) -> dict[int, int]:
    """Extract the seed assignments from an orchestration plan.

    Args:
        plan: Sequence of (index, seed) tuples.

    Returns:
        Dictionary mapping index to assigned seed.
    """
    return {index: seed for index, seed in plan}


__all__ = [
    # Types
    "PlanSpecification",
    "PipelineOperationPayload",
    "PipelineDescriptor",
    "PlanEntry",
    "GlitchlingProtocol",
    # Normalization
    "NormalizedPlanSpec",
    "normalize_plan_entries",
    "normalize_plan_specs",
    # Descriptors
    "PipelineDescriptorModel",
    "build_pipeline_descriptor",
    # Execution planning
    "ExecutionStep",
    "ExecutionPlan",
    "build_execution_plan",
    # Validation
    "validate_plan_coverage",
    "extract_plan_ordering",
    "extract_plan_seeds",
]
