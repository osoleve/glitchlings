"""Core data structures used to model glitchlings and their interactions."""

import inspect
import random
from collections.abc import Mapping, Sequence
from enum import IntEnum, auto
from hashlib import blake2s
from typing import TYPE_CHECKING, Any, Callable, Protocol, cast

from glitchlings.internal.rust_ffi import plan_glitchlings_rust

from ..compat.loaders import get_datasets_dataset, require_datasets
from ..compat.types import Dataset as DatasetProtocol
from ..util.transcripts import (
    Transcript,
    TranscriptTarget,
    is_transcript,
)
from .core_execution import execute_plan
from .core_planning import (
    PipelineDescriptor,
    PipelineOperationPayload,
    build_execution_plan,
    build_pipeline_descriptor,
    normalize_plan_entries,
)
from .core_planning import (
    PlanEntry as _PlanEntry,
)
from .corrupt_dispatch import (
    StringCorruptionTarget,
    assemble_corruption_result,
    resolve_corruption_target,
)

_DatasetsDataset = get_datasets_dataset()

_is_transcript = is_transcript


def plan_glitchlings(
    entries: Sequence[_PlanEntry],
    master_seed: int | None,
) -> list[tuple[int, int]]:
    """Normalize glitchling instances or specs and compute an orchestration plan.

    Notes
    -----
    The Rust extension is required for orchestration.
    """
    if master_seed is None:
        message = "Gaggle orchestration requires a master seed"
        raise ValueError(message)

    normalized_specs = [spec.as_mapping() for spec in normalize_plan_entries(entries)]
    master_seed_int = int(master_seed)
    return plan_glitchlings_rust(list(normalized_specs), master_seed_int)


if TYPE_CHECKING:  # pragma: no cover - typing only
    from datasets import Dataset
elif _DatasetsDataset is not None:
    Dataset = _DatasetsDataset
else:
    Dataset = DatasetProtocol


class CorruptionCallable(Protocol):
    """Protocol describing a callable capable of corrupting text."""

    def __call__(self, text: str, *args: Any, **kwargs: Any) -> str: ...


# Text levels for glitchlings, to enforce a sort order
# Work from highest level down, because e.g.
# duplicating a word then adding a typo is potentially different than
# adding a typo then duplicating a word
class AttackWave(IntEnum):
    """Granularity of text that a glitchling corrupts."""

    DOCUMENT = auto()
    PARAGRAPH = auto()
    SENTENCE = auto()
    WORD = auto()
    CHARACTER = auto()


# Modifier for within the same attack wave
class AttackOrder(IntEnum):
    """Relative execution order for glitchlings within the same wave."""

    FIRST = auto()
    EARLY = auto()
    NORMAL = auto()
    LATE = auto()
    LAST = auto()


class Glitchling:
    """A single text corruption agent with deterministic behaviour."""

    def __init__(
        self,
        name: str,
        corruption_function: CorruptionCallable,
        scope: AttackWave,
        order: AttackOrder = AttackOrder.NORMAL,
        seed: int | None = None,
        pipeline_operation: Callable[["Glitchling"], Mapping[str, Any] | None] | None = None,
        transcript_target: TranscriptTarget = "last",
        **kwargs: Any,
    ) -> None:
        """Initialize a glitchling.

        Args:
            name: Human readable glitchling name.
            corruption_function: Callable used to transform text.
            scope: Text granularity on which the glitchling operates.
            order: Relative ordering within the same scope.
            seed: Optional seed for deterministic random behaviour.
            pipeline_operation: Optional factory for Rust pipeline descriptors.
            transcript_target: Which transcript turns to corrupt. Accepts:
                - ``"last"`` (default): corrupt only the last turn
                - ``"all"``: corrupt all turns
                - ``"assistant"``: corrupt only assistant turns
                - ``"user"``: corrupt only user turns
                - ``int``: corrupt a specific index (negative indexing supported)
                - ``Sequence[int]``: corrupt specific indices
            **kwargs: Additional parameters forwarded to the corruption callable.

        """
        # Each Glitchling maintains its own RNG for deterministic yet isolated behavior.
        # If no seed is supplied, we fall back to Python's default entropy.
        self.seed = seed
        self.rng: random.Random = random.Random(seed)
        self.name: str = name
        self.corruption_function: CorruptionCallable = corruption_function
        self.level: AttackWave = scope
        self.order: AttackOrder = order
        self._pipeline_descriptor_factory = pipeline_operation
        self.transcript_target: TranscriptTarget = transcript_target
        self.kwargs: dict[str, Any] = {}
        self._cached_rng_callable: CorruptionCallable | None = None
        self._cached_rng_expectation: bool | None = None
        for kw, val in kwargs.items():
            self.set_param(kw, val)

    def set_param(self, key: str, value: Any) -> None:
        """Persist a parameter for use by the corruption callable."""
        aliases = getattr(self, "_param_aliases", {})
        canonical = aliases.get(key, key)

        # Drop stale alias keys so we only forward canonical kwargs.
        self.kwargs.pop(key, None)
        for alias, target in aliases.items():
            if target == canonical:
                self.kwargs.pop(alias, None)

        self.kwargs[canonical] = value
        setattr(self, canonical, value)

        if canonical == "seed":
            self.reset_rng(value)

        for alias, target in aliases.items():
            if target == canonical:
                setattr(self, alias, value)

    def pipeline_operation(self) -> PipelineOperationPayload | None:
        """Return the Rust pipeline descriptor or ``None`` when unavailable.

        Glitchlings that cannot provide a compiled pipeline (for example the
        lightweight helpers used in tests) should override this hook or supply
        a ``pipeline_operation`` factory that returns ``None`` to indicate that
        Python orchestration must be used instead. When a descriptor mapping is
        returned it is validated and forwarded to the Rust pipeline.
        """

        factory = self._pipeline_descriptor_factory
        if factory is None:
            return None

        descriptor = factory(self)
        if descriptor is None:
            return None

        if not isinstance(descriptor, Mapping):  # pragma: no cover - defensive
            raise TypeError("Pipeline descriptor factories must return a mapping or None")

        payload = dict(descriptor)
        payload_type = payload.get("type")
        if not isinstance(payload_type, str):
            message = f"Pipeline descriptor for {self.name} is missing a string 'type' field"
            raise RuntimeError(message)

        return cast(PipelineOperationPayload, payload)

    def _corruption_expects_rng(self) -> bool:
        """Return `True` when the corruption function accepts an rng keyword."""
        cached_callable = self._cached_rng_callable
        cached_expectation = self._cached_rng_expectation
        corruption_function = self.corruption_function

        if cached_callable is corruption_function and cached_expectation is not None:
            return cached_expectation

        expects_rng = False
        try:
            signature = inspect.signature(corruption_function)
        except (TypeError, ValueError):
            signature = None

        if signature is not None:
            expects_rng = "rng" in signature.parameters

        self._cached_rng_callable = corruption_function
        self._cached_rng_expectation = expects_rng
        return expects_rng

    def __corrupt(self, text: str, *args: Any, **kwargs: Any) -> str:
        """Execute the corruption callable, injecting the RNG when required."""
        # Pass rng to underlying corruption function if it expects it.
        expects_rng = self._corruption_expects_rng()

        if expects_rng:
            corrupted = self.corruption_function(text, *args, rng=self.rng, **kwargs)
        else:
            corrupted = self.corruption_function(text, *args, **kwargs)
        return corrupted

    def _execute_corruption(self, text: str) -> str:
        """Execute the actual corruption on a single text string.

        This is the impure execution point that invokes the corruption callable.
        All corruption for this glitchling flows through this single method.

        Args:
            text: The text to corrupt.

        Returns:
            The corrupted text.
        """
        return self.__corrupt(text, **self.kwargs)

    def corrupt(self, text: str | Transcript) -> str | Transcript:
        """Apply the corruption function to text or conversational transcripts.

        This method uses a pure dispatch pattern:
        1. Resolve the corruption target (pure - what to corrupt)
        2. Execute corruption (impure - single isolated point)
        3. Assemble the result (pure - combine results)

        When the input is a transcript, the ``transcript_target`` setting
        controls which turns are corrupted:

        - ``"last"``: corrupt only the last turn (default)
        - ``"all"``: corrupt all turns
        - ``"assistant"``: corrupt only turns with ``role="assistant"``
        - ``"user"``: corrupt only turns with ``role="user"``
        - ``int``: corrupt a specific turn by index
        - ``Sequence[int]``: corrupt specific turns by index
        """
        # Step 1: Pure dispatch - determine what to corrupt
        target = resolve_corruption_target(text, self.transcript_target)

        # Step 2: Impure execution - apply corruption via isolated method
        if isinstance(target, StringCorruptionTarget):
            corrupted: str | dict[int, str] = self._execute_corruption(target.text)
        else:
            # TranscriptCorruptionTarget
            corrupted = {
                turn.index: self._execute_corruption(turn.content) for turn in target.turns
            }

        # Step 3: Pure assembly - combine results
        return assemble_corruption_result(target, corrupted)

    def corrupt_dataset(self, dataset: Dataset, columns: list[str]) -> Dataset:
        """Apply corruption lazily across dataset columns."""
        require_datasets("datasets is not installed")

        def __corrupt_row(row: dict[str, Any]) -> dict[str, Any]:
            row = dict(row)
            for column in columns:
                value = row[column]
                if _is_transcript(
                    value,
                    allow_empty=False,
                    require_all_content=True,
                ):
                    row[column] = self.corrupt(value)
                elif isinstance(value, list):
                    row[column] = [self.corrupt(item) for item in value]
                else:
                    row[column] = self.corrupt(value)
            return row

        return dataset.with_transform(__corrupt_row)

    def __call__(self, text: str, *args: Any, **kwds: Any) -> str | Transcript:
        """Allow a glitchling to be invoked directly like a callable."""
        return self.corrupt(text, *args, **kwds)

    def reset_rng(self, seed: int | None = None) -> None:
        """Reset the glitchling's RNG to its initial seed."""
        if seed is not None:
            self.seed = seed
        if self.seed is not None:
            self.rng = random.Random(self.seed)

    def clone(self, seed: int | None = None) -> "Glitchling":
        """Create a copy of this glitchling, optionally with a new seed."""
        cls = self.__class__
        filtered_kwargs = {k: v for k, v in self.kwargs.items() if k != "seed"}
        clone_seed = seed if seed is not None else self.seed

        if cls is Glitchling:
            if clone_seed is not None:
                filtered_kwargs["seed"] = clone_seed
            return Glitchling(
                self.name,
                self.corruption_function,
                self.level,
                self.order,
                pipeline_operation=self._pipeline_descriptor_factory,
                transcript_target=self.transcript_target,
                **filtered_kwargs,
            )

        # Check which kwargs subclass accepts via **kwargs or explicit params
        try:
            signature = inspect.signature(cls.__init__)
            params = signature.parameters
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        except (TypeError, ValueError):
            # If we can't introspect, play it safe and pass nothing extra
            return cls(**filtered_kwargs)

        # Only include seed if subclass accepts it
        if clone_seed is not None:
            if has_var_keyword or "seed" in params:
                filtered_kwargs["seed"] = clone_seed

        # Only include transcript_target if subclass accepts it
        if "transcript_target" not in filtered_kwargs:
            if has_var_keyword or "transcript_target" in params:
                filtered_kwargs["transcript_target"] = self.transcript_target

        return cls(**filtered_kwargs)


class Gaggle(Glitchling):
    """A collection of glitchlings executed in a deterministic order."""

    def __init__(
        self,
        glitchlings: list[Glitchling],
        seed: int = 151,
        transcript_target: TranscriptTarget = "last",
    ):
        """Initialize the gaggle and derive per-glitchling RNG seeds.

        Args:
            glitchlings: Glitchlings to orchestrate.
            seed: Master seed used to derive per-glitchling seeds.
            transcript_target: Which transcript turns to corrupt. Accepts:
                - ``"last"`` (default): corrupt only the last turn
                - ``"all"``: corrupt all turns
                - ``"assistant"``: corrupt only assistant turns
                - ``"user"``: corrupt only user turns
                - ``int``: corrupt a specific index (negative indexing supported)
                - ``Sequence[int]``: corrupt specific indices

        """
        super().__init__(
            "Gaggle",
            self._corrupt_text,
            AttackWave.DOCUMENT,
            seed=seed,
            transcript_target=transcript_target,
        )
        self._clones_by_index: list[Glitchling] = []
        for idx, glitchling in enumerate(glitchlings):
            clone = glitchling.clone()
            setattr(clone, "_gaggle_index", idx)
            self._clones_by_index.append(clone)

        self.glitchlings: dict[AttackWave, list[Glitchling]] = {level: [] for level in AttackWave}
        self.apply_order: list[Glitchling] = []
        self._plan: list[tuple[int, int]] = []
        self.sort_glitchlings()

    def clone(self, seed: int | None = None) -> "Gaggle":
        """Create a copy of this gaggle, cloning member glitchlings."""
        clone_seed = seed if seed is not None else self.seed
        if clone_seed is None:
            clone_seed = 151  # Default seed for Gaggle
        cloned_members = [glitchling.clone() for glitchling in self._clones_by_index]
        return Gaggle(cloned_members, seed=clone_seed, transcript_target=self.transcript_target)

    @staticmethod
    def derive_seed(master_seed: int, glitchling_name: str, index: int) -> int:
        """Derive a deterministic seed for a glitchling based on the master seed."""

        def _int_to_bytes(value: int) -> bytes:
            if value == 0:
                return b"\x00"

            abs_value = abs(value)
            length = max(1, (abs_value.bit_length() + 7) // 8)

            if value < 0:
                while True:
                    try:
                        return value.to_bytes(length, "big", signed=True)
                    except OverflowError:
                        length += 1

            return abs_value.to_bytes(length, "big", signed=False)

        hasher = blake2s(digest_size=8)
        hasher.update(_int_to_bytes(master_seed))
        hasher.update(b"\x00")
        hasher.update(glitchling_name.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(_int_to_bytes(index))
        return int.from_bytes(hasher.digest(), "big")

    def sort_glitchlings(self) -> None:
        """Sort glitchlings by wave then order to produce application order."""
        plan = plan_glitchlings(self._clones_by_index, self.seed)
        self._plan = plan

        self.glitchlings = {level: [] for level in AttackWave}
        for clone in self._clones_by_index:
            self.glitchlings[clone.level].append(clone)

        missing = set(range(len(self._clones_by_index)))
        apply_order: list[Glitchling] = []
        for index, derived_seed in plan:
            clone = self._clones_by_index[index]
            clone.reset_rng(int(derived_seed))
            apply_order.append(clone)
            missing.discard(index)

        if missing:
            missing_indices = ", ".join(str(idx) for idx in sorted(missing))
            message = f"Orchestration plan missing glitchlings at indices: {missing_indices}"
            raise RuntimeError(message)

        self.apply_order = apply_order

    def _pipeline_descriptors(self) -> tuple[list[PipelineDescriptor], list[Glitchling]]:
        """Collect pipeline descriptors and track glitchlings missing them."""
        descriptors: list[PipelineDescriptor] = []
        missing: list[Glitchling] = []
        master_seed = self.seed
        for glitchling in self.apply_order:
            descriptor = build_pipeline_descriptor(
                glitchling,
                master_seed=master_seed,
                derive_seed_fn=Gaggle.derive_seed,
            )
            if descriptor is None:
                missing.append(glitchling)
                continue
            descriptors.append(descriptor.as_mapping())

        return descriptors, missing

    def _corrupt_text(self, text: str) -> str:
        """Apply each glitchling to string input sequentially.

        This method uses a batched execution strategy to minimize tokenization
        overhead. Consecutive glitchlings with pipeline support are grouped and
        executed together via the Rust pipeline, while glitchlings without
        pipeline support are executed individually. This hybrid approach ensures
        the text is tokenized fewer times compared to executing every glitchling
        individually.
        """
        master_seed = self.seed
        if master_seed is None:
            message = "Gaggle orchestration requires a master seed"
            raise RuntimeError(message)

        # Build the pure execution plan
        plan = build_execution_plan(
            self.apply_order,
            master_seed=master_seed,
            derive_seed_fn=Gaggle.derive_seed,
        )

        # Execute via the impure dispatch layer
        return execute_plan(text, plan, master_seed)

    def corrupt(self, text: str | Transcript) -> str | Transcript:
        """Apply each glitchling to the provided text sequentially.

        This method uses a pure dispatch pattern:
        1. Resolve the corruption target (pure - what to corrupt)
        2. Execute corruption (impure - single isolated point)
        3. Assemble the result (pure - combine results)

        When the input is a transcript, the ``transcript_target`` setting
        controls which turns are corrupted:

        - ``"last"``: corrupt only the last turn (default)
        - ``"all"``: corrupt all turns
        - ``"assistant"``: corrupt only turns with ``role="assistant"``
        - ``"user"``: corrupt only turns with ``role="user"``
        - ``int``: corrupt a specific turn by index
        - ``Sequence[int]``: corrupt specific turns by index
        """
        # Step 1: Pure dispatch - determine what to corrupt
        target = resolve_corruption_target(text, self.transcript_target)

        # Step 2: Impure execution - apply corruption via isolated method
        if isinstance(target, StringCorruptionTarget):
            corrupted: str | dict[int, str] = self._corrupt_text(target.text)
        else:
            # TranscriptCorruptionTarget
            corrupted = {turn.index: self._corrupt_text(turn.content) for turn in target.turns}

        # Step 3: Pure assembly - combine results
        return assemble_corruption_result(target, corrupted)


__all__ = [
    # Enums
    "AttackWave",
    "AttackOrder",
    # Core classes
    "Glitchling",
    "Gaggle",
    # Planning functions
    "plan_glitchlings",
    "PipelineOperationPayload",
    "PipelineDescriptor",
]
