"""Path helpers shared by Deadman ARS scripts."""

from __future__ import annotations

from pathlib import Path


def find_deadman_root(start: str | Path) -> Path:
    """Return the Deadman project root from either nested or standalone checkout."""
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if _looks_like_deadman_root(candidate):
            return candidate
        nested = candidate / "Deadman"
        if _looks_like_deadman_root(nested):
            return nested

    raise RuntimeError(f"Could not locate Deadman project root from {start!s}.")


def _looks_like_deadman_root(path: Path) -> bool:
    return (
        (path / "backend").is_dir()
        and (path / "data").is_dir()
        and (path / "docs").is_dir()
        and (path / "tools" / "ars").is_dir()
    )
