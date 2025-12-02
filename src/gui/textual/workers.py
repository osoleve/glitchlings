from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from .bus import MessageBus

T = TypeVar("T")
ResultFactory = Callable[[T], Any]
ErrorFactory = Callable[[Exception], Any]


@dataclass(slots=True)
class BackgroundJob(Generic[T]):
    id: str
    label: str
    future: asyncio.Future[T]

    def cancel(self) -> bool:
        return self.future.cancel()

    @property
    def done(self) -> bool:
        return self.future.done()


class BackgroundWorker:
    """Runs blocking work off the UI thread and posts results back to the bus."""

    def __init__(
        self,
        bus: MessageBus,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        max_workers: int = 4,
    ):
        self._bus = bus
        self._loop = loop
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._log = logging.getLogger(__name__)

    def run(
        self,
        label: str,
        func: Callable[[], T],
        *,
        on_success: ResultFactory[T] | None = None,
        on_error: ErrorFactory | None = None,
    ) -> BackgroundJob[T]:
        loop = self._loop
        if loop is None:
            loop = asyncio.get_running_loop()
            self._loop = loop

        future: asyncio.Future[T] = loop.run_in_executor(self._executor, func)
        job = BackgroundJob(id=str(uuid.uuid4()), label=label, future=future)

        def _completed(fut: asyncio.Future[T]) -> None:
            try:
                result = fut.result()
            except Exception as exc:
                if on_error:
                    loop.call_soon_threadsafe(self._bus.post, on_error(exc))
                else:
                    self._log.exception("Background job %s failed", label, exc_info=exc)
                return

            if on_success:
                loop.call_soon_threadsafe(self._bus.post, on_success(result))

        future.add_done_callback(_completed)
        return job

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)
