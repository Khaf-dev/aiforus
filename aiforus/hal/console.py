"""Windows console quirks."""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Iterator

logger = logging.getLogger(__name__)

_STD_INPUT_HANDLE = -10
_ENABLE_QUICK_EDIT_MODE = 0x0040
_ENABLE_EXTENDED_FLAGS = 0x0080


@contextlib.contextmanager
def quick_edit_disabled() -> Iterator[None]:
    """Turn off the Windows console's QuickEdit mode while the assistant runs.

    With QuickEdit on, a single click in the console window starts a text
    selection, and Windows then *pauses every write to the console* until
    Enter or Esc is pressed. Because the assistant logs and prints from its
    worker threads, those threads block and the assistant looks frozen —
    exactly the "it only answers after I press Enter" symptom. The original
    mode is restored on exit. No-op on other platforms.
    """
    if sys.platform != "win32":
        yield
        return

    kernel32 = handle = None
    original = None
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(_STD_INPUT_HANDLE)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            original = mode.value
            new_mode = (original & ~_ENABLE_QUICK_EDIT_MODE) | _ENABLE_EXTENDED_FLAGS
            kernel32.SetConsoleMode(handle, new_mode)
    except Exception:  # not a real console (IDE, redirected input, ...)
        logger.debug("Could not change the console mode", exc_info=True)
        original = None
    try:
        yield
    finally:
        if original is not None:
            with contextlib.suppress(Exception):
                kernel32.SetConsoleMode(handle, original)
