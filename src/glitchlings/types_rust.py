"""Typed contracts describing the boundary between Python and the Rust extension."""

from __future__ import annotations

import inspect
from typing import (
    Any,
    Callable,
    Literal,
    Mapping,
    Protocol,
    Sequence,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

__all__ = [
    "RngLike",
    "PlanInputDict",
    "PlanInputLike",
    "ReduplicateOperation",
    "DeleteOperation",
    "SwapAdjacentOperation",
    "RedactOperation",
    "OcrOperation",
    "TypoOperation",
    "ZeroWidthOperation",
    "GlitchDescriptor",
    "ComposeGlitchlingsFn",
    "PlanGlitchlingsFn",
    "ReduplicateWordsFn",
    "DeleteRandomWordsFn",
    "SwapAdjacentWordsFn",
    "RedactWordsFn",
    "OcrArtifactsFn",
    "FatfingerFn",
    "InjectZeroWidthsFn",
    "expected_signatures",
]


_T = TypeVar("_T")


@runtime_checkable
class RngLike(Protocol):
    """Protocol for the RNG adapter expected by the Rust extension."""

    def random(self) -> float: ...

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int: ...

    def sample(self, population: Sequence[_T], k: int) -> list[_T]: ...

    def choice(self, population: Sequence[_T]) -> _T: ...


class PlanInputDict(TypedDict):
    """Dictionary-based representation of a glitchling planning entry."""

    name: str
    scope: int
    order: int


@runtime_checkable
class PlanInputProtocol(Protocol):
    """Objects accepted by the planner when describing glitchlings."""

    name: str
    scope: int
    order: int


PlanInputLike = Union[PlanInputDict, PlanInputProtocol]


class _UnweightedOpt(TypedDict, total=False):
    unweighted: bool


class ReduplicateOperation(_UnweightedOpt, TypedDict):
    type: Literal["reduplicate"]
    reduplication_rate: float


class DeleteOperation(_UnweightedOpt, TypedDict):
    type: Literal["delete"]
    max_deletion_rate: float


class SwapAdjacentOperation(TypedDict):
    type: Literal["swap_adjacent"]
    swap_rate: float


class _RedactOptional(_UnweightedOpt, TypedDict, total=False):
    pass


class RedactOperation(_RedactOptional, TypedDict):
    type: Literal["redact"]
    replacement_char: str
    redaction_rate: float
    merge_adjacent: bool


class OcrOperation(TypedDict):
    type: Literal["ocr"]
    error_rate: float


class TypoOperation(TypedDict):
    type: Literal["typo"]
    rate: float
    layout: Mapping[str, Sequence[str]]


class _ZeroWidthOptional(TypedDict, total=False):
    characters: Sequence[str]


class ZeroWidthOperation(_ZeroWidthOptional, TypedDict):
    type: Literal["zwj"]
    rate: float


Operation = Union[
    ReduplicateOperation,
    DeleteOperation,
    SwapAdjacentOperation,
    RedactOperation,
    OcrOperation,
    TypoOperation,
    ZeroWidthOperation,
]


class GlitchDescriptor(TypedDict):
    name: str
    seed: int
    operation: Operation


ComposeGlitchlingsFn = Callable[[str, Sequence[GlitchDescriptor], int], str]
PlanGlitchlingsFn = Callable[[Sequence[PlanInputLike], int], list[tuple[int, int]]]
ReduplicateWordsFn = Callable[[str, float, bool, RngLike], str]
DeleteRandomWordsFn = Callable[[str, float, bool, RngLike], str]
SwapAdjacentWordsFn = Callable[[str, float, RngLike], str]
RedactWordsFn = Callable[[str, str, float, bool, bool, RngLike], str]
OcrArtifactsFn = Callable[[str, float, RngLike], str]
FatfingerFn = Callable[[str, float, Mapping[str, Sequence[str]], RngLike], str]
InjectZeroWidthsFn = Callable[[str, float, Sequence[str], RngLike], str]


def _sig_reduplicate_words(
    text: str,
    reduplication_rate: float,
    unweighted: bool,
    rng: RngLike,
) -> str:
    raise NotImplementedError


def _sig_delete_random_words(
    text: str,
    max_deletion_rate: float,
    unweighted: bool,
    rng: RngLike,
) -> str:
    raise NotImplementedError


def _sig_swap_adjacent_words(text: str, swap_rate: float, rng: RngLike) -> str:
    raise NotImplementedError


def _sig_ocr_artifacts(text: str, error_rate: float, rng: RngLike) -> str:
    raise NotImplementedError


def _sig_redact_words(
    text: str,
    replacement_char: str,
    redaction_rate: float,
    merge_adjacent: bool,
    unweighted: bool,
    rng: RngLike,
) -> str:
    raise NotImplementedError


def _sig_plan_glitchlings(
    glitchlings: Sequence[PlanInputLike],
    master_seed: int,
) -> list[tuple[int, int]]:
    raise NotImplementedError


def _sig_compose_glitchlings(
    text: str,
    descriptors: Sequence[GlitchDescriptor],
    master_seed: int,
) -> str:
    raise NotImplementedError


def _sig_fatfinger(
    text: str,
    max_change_rate: float,
    layout: Mapping[str, Sequence[str]],
    rng: RngLike,
) -> str:
    raise NotImplementedError


def _sig_inject_zero_widths(
    text: str,
    rate: float,
    characters: Sequence[str],
    rng: RngLike,
) -> str:
    raise NotImplementedError


_SIGNATURE_SOURCES: dict[str, Callable[..., Any]] = {
    "reduplicate_words": _sig_reduplicate_words,
    "delete_random_words": _sig_delete_random_words,
    "swap_adjacent_words": _sig_swap_adjacent_words,
    "ocr_artifacts": _sig_ocr_artifacts,
    "redact_words": _sig_redact_words,
    "plan_glitchlings": _sig_plan_glitchlings,
    "compose_glitchlings": _sig_compose_glitchlings,
    "fatfinger": _sig_fatfinger,
    "inject_zero_widths": _sig_inject_zero_widths,
}


def expected_signatures() -> dict[str, inspect.Signature]:
    """Return the canonical Python signatures for the Rust API surface."""

    return {name: inspect.signature(function) for name, function in _SIGNATURE_SOURCES.items()}
