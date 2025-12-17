"""Core data structures used to model glitchlings and their interactions."""

import inspect
import random
from collections.abc import Mapping, Sequence
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any, Callable, Protocol, cast

from glitchlings.internal.rust_ffi import build_pipeline_rust, plan_operations_rust
from glitchlings.zoo.rng import SEED_MASK, _fnv1a_hash, _splitmix64

from ..compat.loaders import get_datasets_dataset, require_datasets
from ..compat.types import Dataset as DatasetProtocol
from ..util.transcripts import (
    Transcript,
    TranscriptTarget,
    TranscriptTurn,
    is_transcript,
    resolve_transcript_indices,
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

_DatasetsDataset = get_datasets_dataset()

_is_transcript = is_transcript


def plan_operations(
    entries: Sequence[_PlanEntry],
    master_seed: int | None,
) -> list[tuple[int, int]]:
    """Normalize operation entries and compute an orchestration plan.

    Notes
    -----
    The Rust extension is required for orchestration.
    """
    if master_seed is None:
        message = "Gaggle orchestration requires a master seed"
        raise ValueError(message)

    normalized_specs = [spec.as_mapping() for spec in normalize_plan_entries(entries)]
    master_seed_int = int(master_seed)
    return plan_operations_rust(list(normalized_specs), master_seed_int)


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
        exclude_patterns: list[str] | None = None,
        include_only_patterns: list[str] | None = None,
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
            exclude_patterns: Regex patterns marking text that must not be
                modified by pipeline-backed glitchlings.
            include_only_patterns: Regex patterns restricting corruption to the
                matched regions; text outside these matches is treated as immutable.
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
        self._pipeline: object | None = None
        mask_kwargs = dict(kwargs)
        if "exclude_patterns" not in mask_kwargs:
            mask_kwargs["exclude_patterns"] = (
                list(exclude_patterns) if exclude_patterns is not None else None
            )
        if "include_only_patterns" not in mask_kwargs:
            mask_kwargs["include_only_patterns"] = (
                list(include_only_patterns) if include_only_patterns is not None else None
            )
        for kw, val in mask_kwargs.items():
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

    def __corrupt(self, text: str, *args: Any, **kwargs: Any) -> str:
        """Execute the corruption callable, injecting the RNG."""
        return self.corruption_function(text, *args, rng=self.rng, **kwargs)

    def _execute_corruption(self, text: str) -> str:
        """Execute the actual corruption on a single text string.

        This is the impure execution point that invokes the corruption callable.
        All corruption for this glitchling flows through this single method.

        Args:
            text: The text to corrupt.

        Returns:
            The corrupted text.
        """
        call_kwargs = {
            key: value
            for key, value in self.kwargs.items()
            if key not in {"exclude_patterns", "include_only_patterns"}
        }
        return self.__corrupt(text, **call_kwargs)

    def corrupt(self, text: str | Transcript) -> str | Transcript:
        """Apply the corruption function to text or conversational transcripts.

        When the input is a transcript, the ``transcript_target`` setting
        controls which turns are corrupted:

        - ``"last"``: corrupt only the last turn (default)
        - ``"all"``: corrupt all turns
        - ``"assistant"``: corrupt only turns with ``role="assistant"``
        - ``"user"``: corrupt only turns with ``role="user"``
        - ``int``: corrupt a specific turn by index
        - ``Sequence[int]``: corrupt specific turns by index
        """
        # Fast path for strings (most common case)
        if isinstance(text, str):
            return self._execute_corruption(text)

        # Handle transcripts
        if _is_transcript(text):
            indices = resolve_transcript_indices(text, self.transcript_target)
            result: list[TranscriptTurn] = [dict(turn) for turn in text]
            for idx in indices:
                turn = text[idx]
                content = turn.get("content")
                if isinstance(content, str):
                    result[idx]["content"] = self._execute_corruption(content)
            return result

        # Fallback: cast to string for backwards compatibility
        return self._execute_corruption(str(text))

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

        for key in ("exclude_patterns", "include_only_patterns"):
            if key in filtered_kwargs and not (has_var_keyword or key in params):
                filtered_kwargs.pop(key)

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
        exclude_patterns: list[str] | None = None,
        include_only_patterns: list[str] | None = None,
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
            exclude_patterns: Regex patterns that should be treated as immutable for all members.
            include_only_patterns: Regex patterns restricting corruption to the matched regions.

        """
        super().__init__(
            "Gaggle",
            self._corrupt_text,
            AttackWave.DOCUMENT,
            seed=seed,
            transcript_target=transcript_target,
            exclude_patterns=exclude_patterns,
            include_only_patterns=include_only_patterns,
        )
        self._clones_by_index: list[Glitchling] = []
        for idx, glitchling in enumerate(glitchlings):
            clone = glitchling.clone()
            merged_exclude = self._merge_pattern_lists(
                exclude_patterns, clone.kwargs.get("exclude_patterns")
            )
            merged_include = self._merge_pattern_lists(
                include_only_patterns, clone.kwargs.get("include_only_patterns")
            )
            if merged_exclude is not None:
                clone.set_param("exclude_patterns", merged_exclude)
            if merged_include is not None:
                clone.set_param("include_only_patterns", merged_include)
            setattr(clone, "_gaggle_index", idx)
            self._clones_by_index.append(clone)

        self.glitchlings: dict[AttackWave, list[Glitchling]] = {level: [] for level in AttackWave}
        self.apply_order: list[Glitchling] = []
        self._plan: list[tuple[int, int]] = []
        self._pipeline_descriptors_cache: list[PipelineDescriptor] | None = None
        self._missing_pipeline_glitchlings: list[Glitchling] = []
        self._cached_include_patterns: list[str] = []
        self._cached_exclude_patterns: list[str] = []
        self.sort_glitchlings()
        self._initialize_pipeline_cache()

    def clone(self, seed: int | None = None) -> "Gaggle":
        """Create a copy of this gaggle, cloning member glitchlings."""
        clone_seed = seed if seed is not None else self.seed
        if clone_seed is None:
            clone_seed = 151  # Default seed for Gaggle
        cloned_members = [glitchling.clone() for glitchling in self._clones_by_index]
        return Gaggle(
            cloned_members,
            seed=clone_seed,
            transcript_target=self.transcript_target,
            exclude_patterns=self.kwargs.get("exclude_patterns"),
            include_only_patterns=self.kwargs.get("include_only_patterns"),
        )

    @staticmethod
    def derive_seed(master_seed: int, glitchling_name: str, index: int) -> int:
        """Derive a deterministic seed for a glitchling based on the master seed.

        Uses FNV-1a for string hashing and SplitMix64 for mixing. This provides
        stable, deterministic derivation without cryptographic overhead.
        """
        state = master_seed & SEED_MASK

        # Mix in glitchling name via FNV-1a
        state ^= _fnv1a_hash(glitchling_name.encode("utf-8"))
        state = _splitmix64(state)

        # Mix in index
        state ^= abs(index) & SEED_MASK
        state = _splitmix64(state)

        return state

    def sort_glitchlings(self) -> None:
        """Sort glitchlings by wave then order to produce application order."""
        plan = plan_operations(self._clones_by_index, self.seed)
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

    def _initialize_pipeline_cache(self) -> None:
        self._cached_include_patterns, self._cached_exclude_patterns = (
            self._collect_masking_patterns()
        )
        descriptors, missing = self._pipeline_descriptors()
        self._pipeline_descriptors_cache = descriptors
        self._missing_pipeline_glitchlings = missing
        if missing:
            self._pipeline = None
            return

        master_seed = self.seed
        if master_seed is None:  # pragma: no cover - defensive, should be set by __init__
            message = "Gaggle orchestration requires a master seed"
            raise RuntimeError(message)

        self._pipeline = build_pipeline_rust(
            descriptors,
            int(master_seed),
            include_only_patterns=self._cached_include_patterns or None,
            exclude_patterns=self._cached_exclude_patterns or None,
        )

    def _invalidate_pipeline_cache(self) -> None:
        """Clear cached pipeline state so it will be rebuilt on next use."""
        self._pipeline = None
        self._pipeline_descriptors_cache = None
        self._missing_pipeline_glitchlings = []

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

    def _corrupt_text(self, text: str, **kwargs: Any) -> str:
        """Apply each glitchling to string input sequentially.

        This method uses a batched execution strategy to minimize tokenization
        overhead. Consecutive glitchlings with pipeline support are grouped and
        executed together via the Rust pipeline, while glitchlings without
        pipeline support are executed individually. This hybrid approach ensures
        the text is tokenized fewer times compared to executing every glitchling
        individually.
        """
        self._ensure_pipeline_ready()

        if self._pipeline is not None and not self._missing_pipeline_glitchlings:
            pipeline = cast(Any, self._pipeline)
            return cast(str, pipeline.run(text))

        master_seed = self.seed
        if master_seed is None:  # pragma: no cover - validated by _ensure_pipeline_ready
            message = "Gaggle orchestration requires a master seed"
            raise RuntimeError(message)

        # Build the pure execution plan
        plan = build_execution_plan(
            self.apply_order,
            master_seed=master_seed,
            derive_seed_fn=Gaggle.derive_seed,
        )

        # Execute via the impure dispatch layer
        return execute_plan(
            text,
            plan,
            master_seed,
            include_only_patterns=self._cached_include_patterns,
            exclude_patterns=self._cached_exclude_patterns,
        )

    def corrupt(self, text: str | Transcript) -> str | Transcript:
        """Apply each glitchling to the provided text sequentially.

        When the input is a transcript, the ``transcript_target`` setting
        controls which turns are corrupted:

        - ``"last"``: corrupt only the last turn (default)
        - ``"all"``: corrupt all turns
        - ``"assistant"``: corrupt only turns with ``role="assistant"``
        - ``"user"``: corrupt only turns with ``role="user"``
        - ``int``: corrupt a specific turn by index
        - ``Sequence[int]``: corrupt specific turns by index
        """
        # Fast path for strings (most common case)
        if isinstance(text, str):
            return self._corrupt_text(text)

        # Handle transcripts
        if _is_transcript(text):
            indices = resolve_transcript_indices(text, self.transcript_target)
            result: list[TranscriptTurn] = [dict(turn) for turn in text]
            for idx in indices:
                turn = text[idx]
                content = turn.get("content")
                if isinstance(content, str):
                    result[idx]["content"] = self._corrupt_text(content)
            return result

        # Fallback: cast to string for backwards compatibility
        return self._corrupt_text(str(text))

    def corrupt_dataset(self, dataset: Dataset, columns: list[str]) -> Dataset:
        """Apply corruption across dataset columns with batch optimization.

        When all glitchlings support the Rust pipeline and columns contain
        simple strings, this method uses batched parallel processing for
        improved throughput. Falls back to row-by-row processing for
        transcripts or when Python fallback is required.

        Args:
            dataset: The HuggingFace Dataset to corrupt.
            columns: List of column names to corrupt.

        Returns:
            A new dataset with the specified columns corrupted.
        """
        require_datasets("datasets is not installed")

        # Check if we can use batch optimization
        self._ensure_pipeline_ready()
        can_batch = self._pipeline is not None and not self._missing_pipeline_glitchlings

        if not can_batch:
            # Fall back to base class row-by-row processing
            return super().corrupt_dataset(dataset, columns)

        def __corrupt_batch(batch: dict[str, list[Any]]) -> dict[str, list[Any]]:
            result = dict(batch)
            for column in columns:
                values = batch[column]
                if not values:
                    continue

                # Check if all values are simple strings (batchable)
                if all(isinstance(v, str) for v in values):
                    result[column] = self.corrupt_batch(values)
                else:
                    # Mixed types or transcripts - process individually
                    corrupted_values: list[Any] = []
                    for value in values:
                        if _is_transcript(value, allow_empty=False, require_all_content=True):
                            corrupted_values.append(self.corrupt(value))
                        elif isinstance(value, list) and all(
                            isinstance(item, str) for item in value
                        ):
                            corrupted_values.append(self.corrupt_batch(value))
                        elif isinstance(value, str):
                            corrupted_values.append(self._corrupt_text(value))
                        else:
                            corrupted_values.append(value)
                    result[column] = corrupted_values
            return result

        return dataset.map(__corrupt_batch, batched=True)

    @staticmethod
    def _merge_pattern_lists(base: list[str] | None, extra: list[str] | None) -> list[str] | None:
        if base is None and extra is None:
            return None

        merged: list[str] = []
        for source in (base, extra):
            if source is None:
                continue
            for pattern in source:
                if pattern not in merged:
                    merged.append(pattern)
        return merged

    def _collect_masking_patterns(self) -> tuple[list[str], list[str]]:
        def _extend_unique(target: list[str], source: list[str] | None) -> None:
            if not source:
                return
            for pattern in source:
                if pattern not in target:
                    target.append(pattern)

        include_patterns: list[str] = []
        exclude_patterns: list[str] = []

        _extend_unique(include_patterns, self.kwargs.get("include_only_patterns"))
        _extend_unique(exclude_patterns, self.kwargs.get("exclude_patterns"))

        for clone in self._clones_by_index:
            _extend_unique(include_patterns, clone.kwargs.get("include_only_patterns"))
            _extend_unique(exclude_patterns, clone.kwargs.get("exclude_patterns"))

        return include_patterns, exclude_patterns

    def _ensure_pipeline_ready(self) -> None:
        """Ensure the pipeline cache is initialized and patterns are current."""
        master_seed = self.seed
        if master_seed is None:
            message = "Gaggle orchestration requires a master seed"
            raise RuntimeError(message)

        include_patterns, exclude_patterns = self._collect_masking_patterns()
        if (
            include_patterns != self._cached_include_patterns
            or exclude_patterns != self._cached_exclude_patterns
        ):
            self._cached_include_patterns = include_patterns
            self._cached_exclude_patterns = exclude_patterns
            self._pipeline = None
            self._pipeline_descriptors_cache = None
            self._missing_pipeline_glitchlings = []

        if self._pipeline is None and not self._missing_pipeline_glitchlings:
            self._initialize_pipeline_cache()

    def _can_use_batch_pipeline(self) -> bool:
        """Return True if all glitchlings support the Rust pipeline."""
        self._ensure_pipeline_ready()
        return self._pipeline is not None and not self._missing_pipeline_glitchlings

    def corrupt_batch(self, texts: Sequence[str]) -> list[str]:
        """Apply corruptions to multiple texts, using parallel Rust execution when possible.

        When all glitchlings support the Rust pipeline, this method releases the GIL
        and processes all texts concurrently using rayon. This provides significant
        speedups for large batches compared to sequential processing.

        When any glitchling requires Python fallback, texts are processed sequentially.

        Args:
            texts: Sequence of text strings to corrupt.

        Returns:
            List of corrupted texts in the same order as inputs.

        Example:
            >>> gaggle = Gaggle([Typogre(rate=0.05), Mim1c(rate=0.01)], seed=42)
            >>> results = gaggle.corrupt_batch(["Hello world", "How are you?"])
        """
        if not texts:
            return []

        self._ensure_pipeline_ready()

        # Fast path: use parallel Rust pipeline when available
        if self._pipeline is not None and not self._missing_pipeline_glitchlings:
            pipeline = cast(Any, self._pipeline)
            return cast(list[str], pipeline.run_batch(list(texts)))

        # Fallback: sequential processing
        return [self._corrupt_text(text) for text in texts]


__all__ = [
    # Enums
    "AttackWave",
    "AttackOrder",
    # Core classes
    "Glitchling",
    "Gaggle",
    # Planning functions
    "plan_operations",
    "PipelineOperationPayload",
    "PipelineDescriptor",
]
