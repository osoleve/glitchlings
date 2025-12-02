from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass, field, is_dataclass, replace
from typing import Any, Awaitable, Callable, Generic, Literal, TypeVar

from ..preferences import Preferences
from .events import StatusTone

DEFAULT_DIFF_TOKENIZER = "cl100k_base"
DiffMode = Literal["label", "id"]


@dataclass
class ScanResult:
    """Results from a scan operation."""

    token_count_out: list[int] = field(default_factory=list)
    token_delta: list[int] = field(default_factory=list)
    jsd: list[float] = field(default_factory=list)
    ned: list[float] = field(default_factory=list)
    sr: list[float] = field(default_factory=list)
    char_count_out: list[int] = field(default_factory=list)


@dataclass(slots=True)
class StatusLine:
    message: str = "Ready"
    tone: StatusTone = "info"


@dataclass(slots=True)
class WorkspaceState:
    input_text: str = ""
    output_text: str = ""
    diff_mode: DiffMode = "label"
    diff_tokenizer: str = DEFAULT_DIFF_TOKENIZER


@dataclass(slots=True)
class SelectionState:
    glitchlings: list[tuple[type[Any], dict[str, Any]]] = field(default_factory=list)
    tokenizers: list[str] = field(default_factory=list)
    seed: int = 151
    auto_update: bool = True
    multi_seed_mode: bool = False
    multi_seed_count: int = 10


@dataclass(slots=True)
class DatasetState:
    running: bool = False
    total: int = 0
    processed: int = 0
    results: dict[str, ScanResult] = field(default_factory=dict)


@dataclass(slots=True)
class AppState:
    selections: SelectionState = field(default_factory=SelectionState)
    workspace: WorkspaceState = field(default_factory=WorkspaceState)
    dataset: DatasetState = field(default_factory=DatasetState)
    status: StatusLine = field(default_factory=StatusLine)
    metrics: dict[str, dict[str, str]] = field(default_factory=dict)
    preferences: Preferences = field(default_factory=Preferences)
    busy: bool = False
    last_error: str | None = None


S = TypeVar("S")
StateListener = Callable[[S], Awaitable[None] | None]


class StateStore(Generic[S]):
    """Simple state container with subscription and thread-safe updates."""

    def __init__(self, initial: S, *, loop: asyncio.AbstractEventLoop | None = None):
        self._state = initial
        self._loop: asyncio.AbstractEventLoop | None = None
        try:
            self._loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            self._loop = loop
        self._listeners: list[StateListener[S]] = []
        self._lock = asyncio.Lock()
        self._log = logging.getLogger(__name__)

    @property
    def snapshot(self) -> S:
        return self._state

    def subscribe(self, listener: StateListener[S]) -> Callable[[], None]:
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                return

        return _unsubscribe

    async def set_state(self, state: S) -> S:
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._log.debug("StateStore set_state called without running loop")
        async with self._lock:
            self._state = state
        await self._notify(state)
        return state

    async def patch(self, **fields: Any) -> S:
        if not is_dataclass(self._state):
            raise TypeError("patch() requires a dataclass-backed state")

        return await self.update(
            lambda current: replace(current, **fields)  # type: ignore[type-var]
        )

    async def update(self, mutate: Callable[[S], S]) -> S:
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._log.debug("StateStore update called without running loop")
        async with self._lock:
            next_state = mutate(self._state)
            self._state = next_state
        await self._notify(next_state)
        return next_state

    def update_from_thread(self, mutate: Callable[[S], S]) -> None:
        if self._loop is None:
            # No event loop yet - apply mutation synchronously (during compose)
            self._state = mutate(self._state)
            return

        asyncio.run_coroutine_threadsafe(self.update(mutate), self._loop)

    async def _notify(self, state: S) -> None:
        if not self._listeners:
            return

        for listener in list(self._listeners):
            try:
                result = listener(state)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self._log.exception("State listener failed")
