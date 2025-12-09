"""Centralized Rust FFI operations module.

This module is the **single entry point** for all Rust FFI calls in the codebase.
All glitchling transformations that delegate to Rust must go through this module.

**Design Philosophy:**

This module is explicitly *impure* - it loads and invokes compiled Rust functions
which are stateful operations. By centralizing all FFI here:

1. Pure modules (validation.py, transforms.py, rng.py) never import Rust
2. The Rust dependency is explicit and traceable
3. Testing can mock this module to verify Python-only paths
4. Side effects from FFI are isolated to one location

**Usage Pattern:**

    # In a glitchling module (e.g., typogre.py)
    from glitchlings.internal.rust_ffi import fatfinger_rust

    def fatfinger(text: str, rate: float, ...) -> str:
        # ... validation and setup ...
        return fatfinger_rust(text, rate, layout, seed)

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping, Sequence, cast

from .rust import get_rust_operation, load_rust_module, resolve_seed

# Re-export resolve_seed for backward compatibility
__all__ = [
    # Seed resolution (re-exported from rust.py)
    "resolve_seed",
    # Orchestration operations
    "plan_glitchlings_rust",
    "compose_glitchlings_rust",
    "build_pipeline_rust",
    "RustPipeline",
    # Character-level operations
    "fatfinger_rust",
    "slip_modifier_rust",
    "mim1c_rust",
    "ocr_artifacts_rust",
    "inject_zero_widths_rust",
    "hokey_rust",
    # Word-level operations
    "delete_random_words_rust",
    "reduplicate_words_rust",
    "swap_adjacent_words_rust",
    "redact_words_rust",
    "jargoyle_drift_rust",
    "list_lexeme_dictionaries_rust",
    "wherewolf_homophones_rust",
    # Grammar operations
    "pedant_rust",
]


# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------

# Orchestration types
PlanResult = list[tuple[int, int]]
PipelineDescriptor = Mapping[str, Any]


# ---------------------------------------------------------------------------
# Pipeline wrapper
# ---------------------------------------------------------------------------


class RustPipeline:
    """Thin wrapper around the compiled Rust Pipeline class."""

    def __init__(
        self,
        descriptors: Sequence[PipelineDescriptor],
        master_seed: int,
        *,
        include_only_patterns: Sequence[str] | None = None,
        exclude_patterns: Sequence[str] | None = None,
    ) -> None:
        module = load_rust_module()
        pipeline_cls = getattr(module, "Pipeline")
        include_patterns_list = (
            list(include_only_patterns) if include_only_patterns is not None else None
        )
        exclude_patterns_list = list(exclude_patterns) if exclude_patterns is not None else None
        self._pipeline = pipeline_cls(
            list(descriptors), int(master_seed), include_patterns_list, exclude_patterns_list
        )

    def run(self, text: str) -> str:
        return cast(str, self._pipeline.run(text))


# ---------------------------------------------------------------------------
# Orchestration Operations
# ---------------------------------------------------------------------------


def plan_glitchlings_rust(
    specs: Sequence[Mapping[str, Any]],
    master_seed: int,
) -> PlanResult:
    """Invoke Rust orchestration planner.

    Args:
        specs: Sequence of glitchling specifications with name/scope/order.
        master_seed: Master seed for deterministic ordering.

    Returns:
        List of (index, derived_seed) tuples defining execution order.
    """
    plan_fn = get_rust_operation("plan_glitchlings")
    plan = plan_fn(specs, int(master_seed))
    return [(int(index), int(seed)) for index, seed in plan]


def compose_glitchlings_rust(
    text: str,
    descriptors: Sequence[PipelineDescriptor],
    master_seed: int,
    *,
    include_only_patterns: Sequence[str] | None = None,
    exclude_patterns: Sequence[str] | None = None,
) -> str:
    """Execute a sequence of glitchlings through the Rust pipeline.

    Args:
        text: Input text to transform.
        descriptors: Pipeline descriptors for each glitchling.
        master_seed: Master seed for determinism.
        include_only_patterns: Regex patterns limiting mutations to matching spans.
        exclude_patterns: Regex patterns that should not be modified.

    Returns:
        Transformed text.
    """
    pipeline = RustPipeline(
        descriptors,
        int(master_seed),
        include_only_patterns=include_only_patterns,
        exclude_patterns=exclude_patterns,
    )
    return pipeline.run(text)


def build_pipeline_rust(
    descriptors: Sequence[PipelineDescriptor],
    master_seed: int,
    *,
    include_only_patterns: Sequence[str] | None = None,
    exclude_patterns: Sequence[str] | None = None,
) -> RustPipeline:
    """Instantiate a Rust pipeline for reuse across calls."""
    return RustPipeline(
        descriptors,
        master_seed,
        include_only_patterns=include_only_patterns,
        exclude_patterns=exclude_patterns,
    )


# ---------------------------------------------------------------------------
# Character-Level Operations
# ---------------------------------------------------------------------------


def fatfinger_rust(
    text: str,
    rate: float,
    layout: Mapping[str, Sequence[str]],
    seed: int,
    *,
    shift_slip_rate: float | None = None,
    shift_slip_exit_rate: float | None = None,
    shift_map: Mapping[str, str] | None = None,
    motor_weighting: str | None = None,
) -> str:
    """Introduce keyboard typos via Rust.

    Args:
        text: Input text.
        rate: Probability of corrupting each character.
        layout: Keyboard neighbor mapping.
        seed: Deterministic seed.
        shift_slip_rate: Probability of entering a shifted burst before fat-fingering.
        shift_slip_exit_rate: Probability of releasing shift during a burst.
        shift_map: Mapping of unshifted -> shifted keys for the active layout.
        motor_weighting: Weighting mode for error sampling ('uniform', 'wet_ink',
            'hastily_edited').

    Returns:
        Text with simulated typing errors.
    """
    fn = get_rust_operation("fatfinger")
    return cast(
        str,
        fn(
            text,
            rate,
            layout,
            seed,
            shift_slip_rate,
            shift_slip_exit_rate,
            shift_map,
            motor_weighting,
        ),
    )


def slip_modifier_rust(
    text: str,
    enter_rate: float,
    exit_rate: float,
    shift_map: Mapping[str, str],
    seed: int | None,
) -> str:
    """Apply a modifier slippage burst using Rust.

    Args:
        text: Input text.
        enter_rate: Probability of starting a shift burst.
        exit_rate: Probability of ending a burst once started.
        shift_map: Mapping of unshifted -> shifted characters.
        seed: Deterministic seed.

    Returns:
        Text with modifier slippage applied.
    """
    fn = get_rust_operation("slip_modifier")
    return cast(str, fn(text, enter_rate, exit_rate, shift_map, seed))


def mim1c_rust(
    text: str,
    rate: float,
    classes: list[str] | Literal["all"] | None,
    banned: list[str] | None,
    seed: int,
) -> str:
    """Replace characters with homoglyphs via Rust.

    Args:
        text: Input text.
        rate: Probability of swapping each character.
        classes: Homoglyph classes to use, or "all".
        banned: Characters to never replace with.
        seed: Deterministic seed.

    Returns:
        Text with homoglyph substitutions.
    """
    fn = get_rust_operation("mim1c")
    return cast(str, fn(text, rate, classes, banned, seed))


def ocr_artifacts_rust(
    text: str,
    rate: float,
    seed: int,
) -> str:
    """Introduce OCR-like artifacts via Rust.

    Args:
        text: Input text.
        rate: Probability of introducing artifacts.
        seed: Deterministic seed.

    Returns:
        Text with simulated OCR errors.
    """
    fn = get_rust_operation("ocr_artifacts")
    return cast(str, fn(text, rate, seed))


def inject_zero_widths_rust(
    text: str,
    rate: float,
    characters: list[str],
    seed: int | None,
) -> str:
    """Inject zero-width characters via Rust.

    Args:
        text: Input text.
        rate: Probability of injection between characters.
        characters: Palette of zero-width characters to use.
        seed: Deterministic seed.

    Returns:
        Text with injected zero-width characters.
    """
    fn = get_rust_operation("inject_zero_widths")
    return cast(str, fn(text, rate, characters, seed))


def hokey_rust(
    text: str,
    rate: float,
    extension_min: int,
    extension_max: int,
    word_length_threshold: int,
    base_p: float,
    seed: int | None,
) -> str:
    """Extend expressive segments via Rust.

    Args:
        text: Input text.
        rate: Selection rate for candidate words.
        extension_min: Minimum extra repetitions.
        extension_max: Maximum extra repetitions.
        word_length_threshold: Preferred max word length.
        base_p: Base probability for sampler.
        seed: Deterministic seed.

    Returns:
        Text with extended expressive segments.
    """
    fn = get_rust_operation("hokey")
    return cast(
        str,
        fn(text, rate, extension_min, extension_max, word_length_threshold, base_p, seed),
    )


# ---------------------------------------------------------------------------
# Word-Level Operations
# ---------------------------------------------------------------------------


def delete_random_words_rust(
    text: str,
    rate: float,
    unweighted: bool,
    seed: int,
) -> str:
    """Delete random words via Rust.

    Args:
        text: Input text.
        rate: Probability of deleting each word.
        unweighted: If True, use uniform selection; else weight by length.
        seed: Deterministic seed.

    Returns:
        Text with words deleted.
    """
    fn = get_rust_operation("delete_random_words")
    return cast(str, fn(text, rate, unweighted, seed))


def reduplicate_words_rust(
    text: str,
    rate: float,
    unweighted: bool,
    seed: int,
) -> str:
    """Reduplicate random words via Rust.

    Args:
        text: Input text.
        rate: Probability of duplicating each word.
        unweighted: If True, use uniform selection; else weight by length.
        seed: Deterministic seed.

    Returns:
        Text with words duplicated.
    """
    fn = get_rust_operation("reduplicate_words")
    return cast(str, fn(text, rate, unweighted, seed))


def swap_adjacent_words_rust(
    text: str,
    rate: float,
    seed: int,
) -> str:
    """Swap adjacent words via Rust.

    Args:
        text: Input text.
        rate: Probability of swapping adjacent word pairs.
        seed: Deterministic seed.

    Returns:
        Text with adjacent words swapped.
    """
    fn = get_rust_operation("swap_adjacent_words")
    return cast(str, fn(text, rate, seed))


def redact_words_rust(
    text: str,
    replacement: str,
    rate: float,
    merge: bool,
    unweighted: bool,
    seed: int,
) -> str:
    """Redact random words via Rust.

    Args:
        text: Input text.
        replacement: Character to replace word characters with.
        rate: Probability of redacting each word.
        merge: If True, merge adjacent redactions.
        unweighted: If True, use uniform selection; else weight by length.
        seed: Deterministic seed.

    Returns:
        Text with words redacted.
    """
    fn = get_rust_operation("redact_words")
    return cast(str, fn(text, replacement, rate, merge, unweighted, seed))


def jargoyle_drift_rust(
    text: str,
    lexemes: str,
    mode: str,
    rate: float,
    seed: int | None,
) -> str:
    """Apply Jargoyle dictionary-based word drift via Rust.

    Args:
        text: Input text.
        lexemes: Name of the dictionary to use (colors, synonyms, corporate, academic, cyberpunk,
            lovecraftian, or any custom dictionary discovered in the lexemes directory).
        mode: Drift mode ("literal" or "drift").
        rate: Probability of transforming each matching word.
        seed: Deterministic seed (only used for "drift" mode).

    Returns:
        Text with word substitutions applied.
    """
    fn = get_rust_operation("jargoyle_drift")
    return cast(str, fn(text, lexemes, mode, rate, seed))


def list_lexeme_dictionaries_rust() -> list[str]:
    """List available lexeme dictionaries.

    Returns:
        List of dictionary names available for Jargoyle.
    """
    fn = get_rust_operation("list_lexeme_dictionaries")
    return cast(list[str], fn())


def wherewolf_homophones_rust(
    text: str,
    rate: float,
    weighting: str,
    seed: int | None,
) -> str:
    """Substitute words with homophones via Rust.

    Args:
        text: Input text.
        rate: Probability of substituting each word.
        weighting: Weighting mode for selection.
        seed: Deterministic seed.

    Returns:
        Text with homophone substitutions.
    """
    fn = get_rust_operation("wherewolf_homophones")
    return cast(str, fn(text, rate, weighting, seed))


# ---------------------------------------------------------------------------
# Grammar Operations
# ---------------------------------------------------------------------------


def pedant_rust(
    text: str,
    *,
    stone: str,
    seed: int,
) -> str:
    """Apply pedant grammar transformation via Rust.

    Args:
        text: Input text.
        stone: Pedant stone label defining transformation type.
        seed: Deterministic seed.

    Returns:
        Text with grammar transformation applied.
    """
    fn = get_rust_operation("pedant")
    return cast(str, fn(text, stone=stone, seed=seed))
