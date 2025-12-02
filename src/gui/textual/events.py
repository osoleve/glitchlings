from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Sequence

StatusTone = Literal["info", "success", "warning", "error", "progress"]


@dataclass(slots=True)
class AppEvent:
    """Base marker for message bus events."""


@dataclass(slots=True)
class StatusEvent(AppEvent):
    message: str
    tone: StatusTone = "info"


@dataclass(slots=True)
class TransformRequested(AppEvent):
    input_text: str
    glitchlings: Sequence[tuple[type[Any], dict[str, Any]]]
    tokenizers: Sequence[str]
    seed: int
    diff_mode: str
    diff_tokenizer: str
    multi_seed_mode: bool = False
    multi_seed_count: int = 1


@dataclass(slots=True)
class TransformCompleted(AppEvent):
    output_text: str
    glitchling_names: Sequence[str]
    metrics: Dict[str, Dict[str, str]]
    diff_tokenizer: str
    diff_mode: str


@dataclass(slots=True)
class TransformFailed(AppEvent):
    message: str
    error: Exception | None = None
