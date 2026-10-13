"""Backwards-compatible entry point. Prefer ``python -m aiforus``."""

from aiforus.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
