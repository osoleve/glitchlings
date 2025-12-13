"""LangChain integration helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Any

from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling
from ._shared import (
    corrupt_batch,
    infer_batch_targets,
    normalize_column_spec,
)


def _resolve_columns(
    sample: Any,
    explicit: list[str | int] | None,
    cached: list[str | int] | None,
) -> list[str | int] | None:
    if explicit is not None:
        return explicit

    if cached is not None:
        return cached

    inferred = infer_batch_targets(sample)
    return inferred


class GlitchedRunnable:
    """Wrap a LangChain runnable to glitch inputs (and optionally outputs)."""

    def __init__(
        self,
        runnable: Any,
        glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
        *,
        input_columns: str | int | Sequence[str | int] | None = None,
        output_columns: str | int | Sequence[str | int] | None = None,
        glitch_output: bool = False,
        seed: int = 151,
    ) -> None:
        self._runnable = runnable
        self._gaggle = coerce_gaggle(glitchlings, seed=seed)
        self._input_columns = normalize_column_spec(input_columns)
        self._output_columns = normalize_column_spec(output_columns)
        self._glitch_output = glitch_output
        self._inferred_input_columns: list[str | int] | None = None
        self._inferred_output_columns: list[str | int] | None = None

    def _glitch_single(self, payload: Any) -> Any:
        columns = _resolve_columns(
            payload, self._input_columns, self._inferred_input_columns
        )
        if self._inferred_input_columns is None:
            self._inferred_input_columns = columns
        return corrupt_batch(payload, columns, self._gaggle)

    def _glitch_many(self, values: Sequence[Any]) -> Sequence[Any]:
        if not values:
            return values

        columns = _resolve_columns(
            values[0], self._input_columns, self._inferred_input_columns
        )
        if self._inferred_input_columns is None:
            self._inferred_input_columns = columns

        glitched = [corrupt_batch(value, columns, self._gaggle) for value in values]
        if isinstance(values, tuple):
            return tuple(glitched)
        return glitched

    def _glitch_result(self, result: Any) -> Any:
        if not self._glitch_output:
            return result

        columns = _resolve_columns(
            result, self._output_columns, self._inferred_output_columns
        )
        if self._inferred_output_columns is None:
            self._inferred_output_columns = columns
        return corrupt_batch(result, columns, self._gaggle)

    def invoke(self, input: Any, config: Any | None = None, **kwargs: Any) -> Any:  # noqa: A003
        glitched_input = self._glitch_single(input)
        result = self._runnable.invoke(glitched_input, config=config, **kwargs)
        return self._glitch_result(result)

    def batch(self, inputs: Sequence[Any], config: Any | None = None, **kwargs: Any) -> Any:
        glitched_inputs = self._glitch_many(inputs)
        result = self._runnable.batch(glitched_inputs, config=config, **kwargs)

        if not self._glitch_output:
            return result

        if isinstance(result, Sequence) and result:
            columns = _resolve_columns(
                result[0], self._output_columns, self._inferred_output_columns
            )
            if self._inferred_output_columns is None:
                self._inferred_output_columns = columns
            glitched = [corrupt_batch(value, columns, self._gaggle) for value in result]
            if isinstance(result, tuple):
                return tuple(glitched)
            return glitched

        return self._glitch_result(result)

    def stream(self, input: Any, config: Any | None = None, **kwargs: Any) -> Any:
        glitched_input = self._glitch_single(input)
        for chunk in self._runnable.stream(glitched_input, config=config, **kwargs):
            yield self._glitch_result(chunk)

    async def astream(
        self, input: Any, config: Any | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        glitched_input = self._glitch_single(input)
        async for chunk in self._runnable.astream(glitched_input, config=config, **kwargs):
            yield self._glitch_result(chunk)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runnable, name)


__all__ = ["GlitchedRunnable"]
