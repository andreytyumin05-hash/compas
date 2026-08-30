"""Очередь задач на один инстанс КОМПАС."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

log = logging.getLogger("compas.bot")


@dataclass
class Job:
    user_id: int
    description: str
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())
    position: int = 0


class BuildQueue:
    def __init__(self) -> None:
        self._q: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
        self._seq = 0
        self._stop = False

    async def start(self, worker: Callable[[Job], Awaitable[None]]) -> None:
        self._q = asyncio.Queue()
        self._stop = False

        async def _loop() -> None:
            assert self._q is not None
            while not self._stop:
                try:
                    job: Job = await asyncio.wait_for(self._q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    if self._stop:
                        break
                    continue
                try:
                    await worker(job)
                except Exception as e:
                    log.exception("job failed: %s", e)
                    if not job.future.done():
                        job.future.set_exception(e)
                finally:
                    self._q.task_done()

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def submit(self, user_id: int, description: str) -> Job:
        if self._q is None:
            raise RuntimeError("очередь не запущена")
        self._seq += 1
        loop = asyncio.get_running_loop()
        job = Job(
            user_id=user_id,
            description=description,
            future=loop.create_future(),
            position=self._q.qsize() + 1,
        )
        await self._q.put(job)
        return job


build_queue = BuildQueue()
