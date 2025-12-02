from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections import defaultdict
from concurrent.futures import Future
from typing import Any, Awaitable, Callable, DefaultDict, TypeVar

E = TypeVar("E")
Handler = Callable[[E], Awaitable[None] | None]


class MessageBus:
    """Lightweight pub/sub bus that works on the Textual event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None):
        self._loop = loop
        self._handlers: DefaultDict[type[Any], list[Handler[Any]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._log = logging.getLogger(__name__)

    def subscribe(self, event_type: type[E], handler: Handler[E]) -> Callable[[], None]:
        """Register a handler for an event type. Returns an unsubscribe callable."""
        with self._lock:
            self._handlers[event_type].append(handler)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    return

        return _unsubscribe

    async def publish(self, event: Any) -> None:
        """Dispatch an event to all subscribed handlers."""
        with self._lock:
            targets: list[Handler[Any]] = []
            for cls in type(event).mro():
                targets.extend(self._handlers.get(cls, ()))

        if not targets:
            return

        for handler in targets:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self._log.exception("Handler failed for %s", type(event).__name__)

    def post(self, event: Any) -> asyncio.Future[Any] | Future[Any]:
        """Schedule dispatch on the configured loop (thread-safe)."""
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        loop = self._loop or running
        if loop is None:
            raise RuntimeError("MessageBus.post requires an active event loop")

        if self._loop is None:
            self._loop = loop

        if running is loop:
            return loop.create_task(self.publish(event))

        return asyncio.run_coroutine_threadsafe(self.publish(event), loop)
