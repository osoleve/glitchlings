"""Interactive metrics session helpers.

The session layer keeps tokenizer adapters, caching, and registry wiring out of
the TUI so that other UIs (e.g. notebooks) can reuse the workflow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping

from ..metrics.defaults import create_default_registry
from ..metrics.registry import MetricRegistry
from .schema import Observation
from .tokenizers import SimpleTokenizer, TokenizerAdapter

TextTransformer = Callable[[str], str]


@dataclass(slots=True)
class SessionResult:
    """Container for a single metrics run."""

    run_id: str
    glitchling_id: str
    text_before: str
    text_after: str
    observations: list[Observation] = field(default_factory=list)

    def metrics_by_tokenizer(self) -> Dict[str, Mapping[str, float]]:
        """Return metrics grouped by tokenizer ID."""
        return {obs.tokenizer_id: dict(obs.metrics) for obs in self.observations}


class MetricsSession:
    """Stateful helper that caches tokenizations and orchestrates metrics runs."""

    def __init__(
        self,
        registry: MetricRegistry | None = None,
        tokenizers: Iterable[TokenizerAdapter] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        self.registry = registry or create_default_registry()
        self.tokenizers = list(tokenizers) if tokenizers else [SimpleTokenizer()]
        self.context: dict[str, Any] = dict(context or {})
        self._token_cache: dict[tuple[str, str], list[int]] = {}

    def register_tokenizer(self, tokenizer: TokenizerAdapter) -> None:
        """Append a tokenizer to the session."""
        self.tokenizers.append(tokenizer)

    def clear_cache(self) -> None:
        """Drop cached tokenizations."""
        self._token_cache.clear()

    def compute_once(
        self,
        *,
        text_before: str,
        glitchling_fn: TextTransformer | None = None,
        glitchling_id: str = "identity",
        tokenizers: Iterable[TokenizerAdapter] | None = None,
        input_type: str = "adhoc",
        store_text: bool = True,
    ) -> SessionResult:
        """Compute metrics for a single text/glitchling combination."""
        adapters = list(tokenizers) if tokenizers is not None else self.tokenizers

        if not adapters:
            raise ValueError("MetricsSession requires at least one tokenizer")

        glitch_fn = glitchling_fn or (lambda text: text)
        text_after = glitch_fn(text_before)
        run_id = f"session-{uuid.uuid4().hex}"

        observations: list[Observation] = []

        for adapter in adapters:
            tokenizer_id = self._tokenizer_id(adapter)
            tokens_before = self._encode(adapter, text_before)
            tokens_after = self._encode(adapter, text_after)
            metrics = self.registry.compute_all(tokens_before, tokens_after, self.context)

            observation = Observation(
                run_id=run_id,
                observation_id=f"{run_id}_{tokenizer_id}",
                input_id="input_0",
                input_type=input_type,
                glitchling_id=glitchling_id,
                tokenizer_id=tokenizer_id,
                tokens_before=list(tokens_before),
                tokens_after=list(tokens_after),
                m=len(tokens_before),
                n=len(tokens_after),
                metrics=dict(metrics),
                text_before=text_before if store_text else None,
                text_after=text_after if store_text else None,
                context={"tokenizer_name": tokenizer_id},
            )

            observations.append(observation)

        return SessionResult(
            run_id=run_id,
            glitchling_id=glitchling_id,
            text_before=text_before,
            text_after=text_after,
            observations=observations,
        )

    def _encode(self, tokenizer: TokenizerAdapter, text: str) -> list[int]:
        key = (self._tokenizer_id(tokenizer), text)
        cached = self._token_cache.get(key)
        if cached is None:
            cached = list(tokenizer.encode(text))
            self._token_cache[key] = cached
        return list(cached)

    @staticmethod
    def _tokenizer_id(tokenizer: TokenizerAdapter) -> str:
        name = getattr(tokenizer, "name", None)
        if isinstance(name, str) and name:
            return name
        return tokenizer.__class__.__name__


__all__ = [
    "MetricsSession",
    "SessionResult",
    "TextTransformer",
]
