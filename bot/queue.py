"""Очередь задач: один КОМПАС — строго по одной задаче."""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class Job:
    user_id: int
    description: str
    future: asyncio.Future
    position: int = 0


class BuildQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._counter = itertools.count(1)
        self._pending = 0
        self._worker_started = False

    def size(self) -> int:
        return self._queue.qsize() + (1 if self._pending else 0)

    async def start(self, worker: Callable[[Job], Awaitable[None]]) -> None:
        if self._worker_started:
            return
        self._worker_started = True

        async def _loop() -> None:
            while True:
                job = await self._queue.get()
                self._pending = 1
                try:
                    await worker(job)
                except Exception as e:
                    if not job.future.done():
                        job.future.set_exception(e)
                finally:
                    self._pending = 0
                    self._queue.task_done()

        asyncio.create_task(_loop())

    async def submit(self, user_id: int, description: str) -> Job:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        job = Job(user_id=user_id, description=description, future=fut)
        job.position = self._queue.qsize() + 1
        await self._queue.put(job)
        return job


# singleton
build_queue = BuildQueue()
