from __future__ import annotations

import asyncio
from typing import Any

from glitchlings import Rushmore
from glitchlings.dlc.langchain import GlitchedRunnable


class EchoRunnable:
    def __init__(self) -> None:
        self.seen: list[Any] = []

    def invoke(self, input: Any, **_: Any) -> Any:  # noqa: A003
        self.seen.append(input)
        return input

    def batch(self, inputs: list[Any], **_: Any) -> list[Any]:
        self.seen.append(inputs)
        return inputs

    def stream(self, input: Any, **_: Any):
        yield from input if isinstance(input, list) else [input]

    async def astream(self, input: Any, **_: Any):
        for chunk in (input if isinstance(input, list) else [input]):
            yield chunk


def test_glitch_runnable_invokes_with_inferred_columns() -> None:
    runnable = GlitchedRunnable(EchoRunnable(), "typogre", seed=123)
    result = runnable.invoke({"text": "patterns"})

    assert result != {"text": "patterns"}
    assert runnable._inferred_input_columns == ["text"]  # noqa: SLF001


def test_glitch_runnable_batch_and_output_glitching() -> None:
    runnable = GlitchedRunnable(EchoRunnable(), "typogre", glitch_output=True, seed=321)
    batch = [{"prompt": "hello"}, {"prompt": "world"}]

    result = runnable.batch(batch)

    assert result != batch
    assert all(item != original for item, original in zip(result, batch, strict=True))
    assert runnable._inferred_input_columns == ["prompt"]  # noqa: SLF001
    assert runnable._inferred_output_columns == ["prompt"]  # noqa: SLF001


def test_glitch_runnable_streams() -> None:
    runnable = GlitchedRunnable(
        EchoRunnable(), Rushmore(duplicate_rate=1.0, modes="duplicate"), seed=777
    )
    stream = list(runnable.stream(["glitch me", "again"]))

    assert stream[0] != "glitch me"
    assert stream[-1] != "again"


def test_glitch_runnable_astreams() -> None:
    runnable = GlitchedRunnable(
        EchoRunnable(), Rushmore(duplicate_rate=1.0, modes="duplicate"), seed=999
    )

    async def collect() -> list[Any]:
        return [chunk async for chunk in runnable.astream(["async", "stream"])]

    result = asyncio.run(collect())

    assert result[0] != "async"
    assert result[-1] != "stream"
