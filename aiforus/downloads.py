"""Download model files (voices, face models) safely."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def download_file(
    url: str,
    dest: Path,
    *,
    session: Any = None,
    timeout_s: float = 60.0,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download ``url`` to ``dest`` unless it already exists.

    The data is written to ``dest.part`` and renamed when complete, so an
    interrupted download never leaves a truncated model behind.
    """
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    import requests

    session = session or requests.Session()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if progress is not None:
        progress(f"downloading {url}")
    partial = dest.with_name(dest.name + ".part")
    with session.get(url, stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with partial.open("wb") as fh:
            for block in response.iter_content(chunk_size=1 << 16):
                if block:
                    fh.write(block)
    partial.replace(dest)
    return dest
