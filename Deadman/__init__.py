"""Compatibility package for historical `Deadman.*` imports.

The standalone repository keeps source directories at the repo root. Older
tests and producer tools still import `Deadman.backend` and `Deadman.tools`.
Adding the repository root to this package path preserves those imports without
duplicating files.
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
__path__.append(str(_REPO_ROOT))

