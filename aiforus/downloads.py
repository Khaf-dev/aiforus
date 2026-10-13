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


def download_and_extract_zip(
    url: str,
    dest_dir: Path,
    folder: str,
    *,
    session: Any = None,
    timeout_s: float = 120.0,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download a zip and extract it so ``dest_dir / folder`` exists.

    Skips the download when the folder is already there. Members that would
    land outside ``dest_dir`` ("zip slip") are refused. Extraction happens in
    a temporary folder that is renamed at the end, so an interrupted run never
    leaves a half-extracted model behind.
    """
    import shutil
    import tempfile
    import zipfile

    target = dest_dir / folder
    if target.is_dir() and any(target.iterdir()):
        return target
    dest_dir.mkdir(parents=True, exist_ok=True)
    archive = download_file(
        url, dest_dir / f"{folder}.zip", session=session, timeout_s=timeout_s, progress=progress
    )
    with tempfile.TemporaryDirectory(dir=dest_dir, ignore_cleanup_errors=True) as tmp:
        root = Path(tmp).resolve()
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                if not (root / member).resolve().is_relative_to(root):
                    raise ValueError(f"Unsafe path in {archive.name}: {member}")
            zf.extractall(root)
        extracted = root / folder
        if not extracted.is_dir():  # zip without a top-level folder
            extracted = root
        shutil.move(str(extracted), str(target))
    archive.unlink()
    return target
