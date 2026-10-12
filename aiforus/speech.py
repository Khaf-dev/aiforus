"""Prioritised, interruptible speech output.

Everything the assistant says goes through :class:`SpeechQueue`:

* Utterances are spoken one at a time, most urgent first (then FIFO).
* A more urgent utterance interrupts the one being spoken. A CRITICAL
  utterance (emergency, future hazard alerts) also drops everything less
  urgent that is still waiting, so stale chatter never delays a warning.
* ``stop_all()`` silences the assistant immediately ("diam" / "stop").

The actual engine is behind the :class:`TextToSpeech` protocol, so the queue
is tested with a fake and the real engine can be swapped (pyttsx3 today,
Piper or a glasses SDK later).
"""

from __future__ import annotations

import asyncio
import contextlib
import heapq
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Protocol

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 0  # safety: emergency, (future) hazard alerts
    HIGH = 1  # the direct answer to what the user just asked
    NORMAL = 2
    LOW = 3  # hints and follow-up tips


class TextToSpeech(Protocol):
    def speak(self, text: str) -> None:
        """Speak ``text``; block until finished or interrupted."""

    def interrupt(self) -> None:
        """Stop the current utterance as soon as possible. Thread-safe."""

    def set_language(self, language: str) -> bool:
        """Switch voice; return False if no matching voice is installed."""

    def close(self) -> None: ...


@dataclass(order=True)
class _Item:
    priority: int
    seq: int
    text: str = field(compare=False)
    done: asyncio.Future[bool] = field(compare=False)


class SpeechQueue:
    def __init__(
        self,
        tts: TextToSpeech,
        *,
        on_say: Callable[[str, Priority], None] | None = None,
    ) -> None:
        self._tts = tts
        self._on_say = on_say
        self._heap: list[_Item] = []
        self._seq = itertools.count()
        self._wakeup = asyncio.Event()
        self._idle = asyncio.Event()
        self._idle.set()
        self._current: _Item | None = None
        self._current_interrupted = False
        self._worker: asyncio.Task[None] | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run(), name="speech-queue")

    async def close(self) -> None:
        self.stop_all()
        if self._worker is not None:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None

    # -- public API --------------------------------------------------------

    @property
    def is_speaking(self) -> bool:
        return self._current is not None

    def say(
        self,
        text: str,
        priority: Priority = Priority.HIGH,
        *,
        flush: bool | None = None,
    ) -> asyncio.Future[bool]:
        """Queue ``text``. The future resolves to True if it was spoken in
        full, False if it was interrupted or dropped."""
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        text = " ".join(text.split())
        if not text:
            future.set_result(True)
            return future

        if flush if flush is not None else priority is Priority.CRITICAL:
            self._drop_pending(lambda item: item.priority > priority)

        for pending in self._heap:  # identical request already waiting
            if pending.text == text and pending.priority <= priority:
                return pending.done

        heapq.heappush(self._heap, _Item(int(priority), next(self._seq), text, future))
        if self._current is not None and priority < self._current.priority:
            self._interrupt_current()
        self._idle.clear()
        self._wakeup.set()
        return future

    async def say_and_wait(self, text: str, priority: Priority = Priority.HIGH) -> bool:
        return await self.say(text, priority)

    def stop_all(self) -> None:
        """Drop everything queued and cut off the current utterance."""
        self._drop_pending(lambda item: True)
        self._interrupt_current()

    async def wait_idle(self) -> None:
        await self._idle.wait()

    # -- internals ---------------------------------------------------------

    def _drop_pending(self, predicate: Callable[[_Item], bool]) -> None:
        kept: list[_Item] = []
        for item in self._heap:
            if predicate(item):
                if not item.done.done():
                    item.done.set_result(False)
            else:
                kept.append(item)
        heapq.heapify(kept)
        self._heap = kept

    def _interrupt_current(self) -> None:
        if self._current is not None:
            self._current_interrupted = True
            self._tts.interrupt()

    async def _run(self) -> None:
        while True:
            if not self._heap:
                self._idle.set()
                self._wakeup.clear()
                await self._wakeup.wait()
                continue

            item = heapq.heappop(self._heap)
            self._current = item
            self._current_interrupted = False
            logger.info("SAY[%s]: %s", Priority(item.priority).name, item.text)
            if self._on_say is not None:
                self._on_say(item.text, Priority(item.priority))
            try:
                await asyncio.to_thread(self._tts.speak, item.text)
            except Exception:  # a broken engine must not kill the queue
                logger.exception("TTS engine failed while speaking")
                self._current_interrupted = True
            finally:
                self._current = None
            if not item.done.done():
                item.done.set_result(not self._current_interrupted)
