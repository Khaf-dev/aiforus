"""Test doubles for hardware and network-backed components."""

from __future__ import annotations

import threading
import time

import numpy as np


class FakeTTS:
    """Records what is spoken; each utterance 'lasts' ``duration`` seconds
    unless interrupted."""

    def __init__(self, duration: float = 0.0, fail_on: str | None = None) -> None:
        self.duration = duration
        self.fail_on = fail_on
        self.spoken: list[str] = []
        self.interrupted: list[str] = []
        self.started: list[str] = []
        self.language = "id"
        self._stop = threading.Event()

    def speak(self, text: str) -> None:
        self.started.append(text)
        self._stop.clear()
        if self.fail_on is not None and self.fail_on in text:
            raise RuntimeError("engine exploded")
        if self._stop.wait(self.duration) if self.duration else False:
            self.interrupted.append(text)
        else:
            self.spoken.append(text)

    def interrupt(self) -> None:
        self._stop.set()

    def set_language(self, language: str) -> bool:
        self.language = language
        return True

    def close(self) -> None:
        pass


class FakeCamera:
    def __init__(self, frames: list[np.ndarray | None] | None = None) -> None:
        self.frames = list(frames or [])
        self.captures = 0

    def capture(self) -> np.ndarray | None:
        self.captures += 1
        if not self.frames:
            return None
        return self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]

    def close(self) -> None:
        pass


def textured_frame(brightness: int = 128, size: tuple[int, int] = (48, 64)) -> np.ndarray:
    """A frame that passes the dark/blank checks."""
    rng = np.random.default_rng(0)
    noise = rng.integers(-40, 40, size=(*size, 3))
    return np.clip(brightness + noise, 0, 255).astype(np.uint8)


def flat_frame(brightness: int) -> np.ndarray:
    return np.full((48, 64, 3), brightness, dtype=np.uint8)


def wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False
