#!/usr/bin/env python3
"""Register local Deadman short-drama media without copying raw video files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_MEDIA_INDEX = REPO_ROOT / "tmp/ars_huangnian_analysis/media_index.json"
DEFAULT_OUT = REPO_ROOT / "data/dramas/huangnian/media_registry.v0.1.json"
DEFAULT_DRAMA_ID = "huangnian"
DEFAULT_TITLE = "荒年全村啃树皮，我有系统满仓肉"


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def load_media_index(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    episodes = data.get("episodes") if isinstance(data, dict) else data
    if not isinstance(episodes, list):
        raise ValueError(f"{path} must contain a media-index list or episodes list")
    return [episode for episode in episodes if isinstance(episode, dict)]


def parse_episode_filter(raw: str) -> set[str]:
    return {part.strip() for part in raw.split(",") if part.strip()}


def register_media(
    *,
    drama_id: str,
    title: str,
    media_index: list[dict[str, Any]],
    episode_ids: set[str],
    runtime_base: str,
    checksum: bool,
    include_vite_dev_url: bool,
) -> dict[str, Any]:
    episodes: list[dict[str, Any]] = []
    for item in media_index:
        episode_id = str(item.get("episode_id", "")).strip()
        if not episode_id:
            continue
        if episode_ids and episode_id not in episode_ids:
            continue
        local_path = resolve_path(str(item.get("video_path", "")))
        if not local_path.exists():
            status = "missing_local_file"
            size_bytes = int(item.get("size_bytes") or 0)
            digest = ""
        else:
            status = "registered"
            size_bytes = int(local_path.stat().st_size)
            digest = sha256_file(local_path) if checksum else ""

        producer_media = {
            "local_media_path": repo_relative(local_path),
            "checksum": digest,
            "size_bytes": size_bytes,
            "policy": "producer-only local metadata; runtime should use runtime_video_url",
        }
        if include_vite_dev_url:
            producer_media["vite_dev_video_url"] = f"/@fs{local_path.resolve(strict=False)}"

        episodes.append(
            {
                "episode_id": episode_id,
                "title": str(item.get("episode_title") or episode_id),
                "runtime_video_url": f"{runtime_base.rstrip('/')}/{episode_id}.mp4",
                "duration_seconds": round(float(item.get("duration_s") or item.get("duration_ms", 0) / 1000), 3),
                "width": item.get("width"),
                "height": item.get("height"),
                "video_codec": item.get("video_codec"),
                "audio_codec": item.get("audio_codec"),
                "fps": item.get("fps"),
                "status": status,
                "producer_media": producer_media,
            }
        )

    return {
        "schema_version": "deadman_media_registry.v0.1",
        "drama_id": drama_id,
        "title": title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "media_policy": {
            "raw_media_storage": "local_ignored_path_only",
            "runtime_video_url": "deployment_slot_or_dev_operator_supplied_asset; raw MP4 is not committed",
            "producer_media": "local path, checksum, and size are producer-only metadata",
        },
        "episode_count": len(episodes),
        "episodes": episodes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-id", default=DEFAULT_DRAMA_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--media-index", default=str(DEFAULT_MEDIA_INDEX))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--episode-ids",
        default="",
        help="Comma-separated episode ids to register. Defaults to all media-index episodes.",
    )
    parser.add_argument(
        "--runtime-base",
        default="",
        help="Logical runtime media base. Defaults to /api/deadman/media/{drama_id}.",
    )
    parser.add_argument("--skip-checksum", action="store_true", help="Write metadata without hashing local MP4 files.")
    parser.add_argument(
        "--include-vite-dev-url",
        action="store_true",
        help="Include machine-specific Vite /@fs URLs. Use only for ignored local output, not tracked registries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    media_index_path = resolve_path(args.media_index)
    out_path = resolve_path(args.out)
    registry = register_media(
        drama_id=args.drama_id,
        title=args.title,
        media_index=load_media_index(media_index_path),
        episode_ids=parse_episode_filter(args.episode_ids),
        runtime_base=args.runtime_base or f"/api/deadman/media/{args.drama_id}",
        checksum=not args.skip_checksum,
        include_vite_dev_url=args.include_vite_dev_url,
    )
    write_json(out_path, registry)
    print(
        json.dumps(
            {
                "episode_count": registry["episode_count"],
                "registered": sum(1 for item in registry["episodes"] if item["status"] == "registered"),
                "out": repo_relative(out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
