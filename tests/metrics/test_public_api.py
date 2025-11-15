"""Public API tests for glitchlings.metrics convenience helpers."""

from __future__ import annotations

import pytest

from glitchlings.metrics import (
    MetricRegistry,
    SimpleTokenizer,
    compute_metrics,
    create_default_registry,
    create_huggingface_adapter,
    create_tiktoken_adapter,
)


class RecordingTokenizer:
    """Tokenizer that captures kwargs for assertions."""

    def __init__(self) -> None:
        self.calls: list[bool] = []

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        self.calls.append(add_special_tokens)
        # Encode as a simple length-based token for determinism
        return [len(text)]


def test_compute_metrics_returns_values() -> None:
    registry = create_default_registry()
    tokenizer = SimpleTokenizer()

    values = compute_metrics(
        text_before="hello world",
        text_after="hello brave world",
        tokenizer=tokenizer,
        registry=registry,
    )

    assert "ned.value" in values
    assert values["ned.value"] > 0.0


def test_compute_metrics_accepts_tokenize_kwargs() -> None:
    registry = create_default_registry()
    tokenizer = RecordingTokenizer()

    compute_metrics(
        text_before="alpha",
        text_after="beta",
        tokenizer=tokenizer,
        registry=registry,
        tokenize_kwargs={"add_special_tokens": False},
    )

    assert tokenizer.calls == [False, False]


def test_compute_metrics_infers_default_registry() -> None:
    values = compute_metrics(
        text_before="same text",
        text_after="same text",
        tokenizer=SimpleTokenizer(),
    )

    assert pytest.approx(0.0, abs=1e-6) == values["ned.value"]


def test_compute_metrics_rejects_invalid_tokenizer() -> None:
    class BadTokenizer:
        pass

    registry = create_default_registry()

    with pytest.raises(TypeError):
        compute_metrics("a", "b", BadTokenizer(), registry=registry)


def test_public_api_exports_are_instantiable() -> None:
    # MetricRegistry is importable and can register metrics manually
    registry = MetricRegistry()
    assert len(list(registry.list_metrics())) == 0

    # Optional adapter factories should be callable (actual invocation would
    # require third-party packages, so we do not call them here).
    assert callable(create_huggingface_adapter)
    assert callable(create_tiktoken_adapter)
