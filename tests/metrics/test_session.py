"""Tests for the interactive metrics session helpers."""

from __future__ import annotations

import pytest

from glitchlings.metrics.core.session import MetricsSession


def test_metrics_session_runs_glitchling_callable() -> None:
    session = MetricsSession()

    result = session.compute_once(
        text_before="hello world",
        glitchling_fn=lambda text: text.upper(),
        glitchling_id="upper",
    )

    assert result.text_after == "HELLO WORLD"
    assert result.glitchling_id == "upper"
    assert len(result.observations) == 1

    observation = result.observations[0]
    assert observation.tokenizer_id == "simple-whitespace"
    assert "ned.value" in observation.metrics
    assert observation.metrics["ned.value"] > 0.0


def test_metrics_session_rejects_missing_tokenizers() -> None:
    session = MetricsSession()

    with pytest.raises(ValueError):
        session.compute_once(text_before="hello", glitchling_id="identity", tokenizers=[])
