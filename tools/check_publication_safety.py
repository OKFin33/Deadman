#!/usr/bin/env python3
"""Fail-fast publication safety checks for the Deadman repo."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED_PARTS = {
    ".agent",
    ".cache",
    ".cab",
    ".claude",
    ".codex",
    ".langgraph",
    "dist",
    "local_artifacts",
    "node_modules",
    "tmp",
}
FORBIDDEN_SUFFIXES = {
    ".aab",
    ".aac",
    ".apk",
    ".avi",
    ".cer",
    ".crt",
    ".db",
    ".gz",
    ".ipa",
    ".key",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".p12",
    ".pem",
    ".sqlite",
    ".tar",
    ".tgz",
    ".wav",
    ".zip",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ark-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[op]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"oauth2:[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(
        r"\b[A-Z0-9_]*(?:API_KEY|ACCESS_KEY|SECRET_KEY|ACCESS_TOKEN|SECRET_TOKEN|AUTH_TOKEN)\b"
        r"\s*[:=]\s*['\"]?(?!args\.|os\.|self\.|api_key\b|api_key_env\b)"
        r"[A-Za-z0-9._-]{16,}",
        re.IGNORECASE,
    ),
]
LOCAL_PATH_PATTERNS = [
    re.compile(r"/@fs/Users/"),
    re.compile(r"OKFin33/OSeria-Alter/tmp/"),
    re.compile(r"/var/folders/"),
]


def iter_files(root: Path) -> list[Path]:
    if (root / ".git").exists():
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        return [root / line for line in proc.stdout.splitlines() if line.strip()]
    files: list[Path] = []
    for current_root, dirs, names in os.walk(root):
        rel_parts = Path(current_root).relative_to(root).parts
        dirs[:] = [
            item
            for item in dirs
            if item not in FORBIDDEN_TRACKED_PARTS
            and item not in {"__pycache__", ".pytest_cache", ".ruff_cache"}
        ]
        if any(part in FORBIDDEN_TRACKED_PARTS for part in rel_parts):
            continue
        for name in names:
            files.append(Path(current_root) / name)
    return files


def is_binary_or_large(path: Path) -> bool:
    try:
        if path.stat().st_size > 2_000_000:
            return True
        sample = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Deadman publication hygiene.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    checked = 0

    for path in iter_files(root):
        if not path.exists() or path.is_dir():
            continue
        rel = path.relative_to(root)
        parts = set(rel.parts)
        suffix = path.suffix.lower()
        if parts & FORBIDDEN_TRACKED_PARTS:
            errors.append(f"forbidden tracked path: {rel}")
        if suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden tracked suffix: {rel}")
        if rel.name in {".env", "credentials.json", "secrets.json", "secret.json"}:
            errors.append(f"forbidden tracked secret file: {rel}")
        if not is_binary_or_large(path):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if rel.name == "media_registry.v0.1.json" and "local_media_path" in text:
                errors.append(f"producer local_media_path in tracked registry: {rel} (move to gitignored media_local.v0.1.json sidecar)")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"possible secret literal in {rel}: {pattern.pattern}")
                    break
            if rel != Path("tools/check_publication_safety.py"):
                for pattern in LOCAL_PATH_PATTERNS:
                    if pattern.search(text):
                        errors.append(f"machine-specific local path in {rel}: {pattern.pattern}")
                        break
        checked += 1

    if errors:
        print("PUBLICATION SAFETY CHECK FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"PUBLICATION SAFETY CHECK PASSED ({checked} candidate files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
