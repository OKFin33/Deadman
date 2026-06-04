"""Print local Vite recording URLs from a Deadman media registry.

The script only reads tracked producer metadata. It does not copy media and it
does not promote local file paths into runtime-facing pack fields.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_REGISTRY = REPO_ROOT / "data/dramas/huangnian/media_registry.v0.1.json"
DEFAULT_BASE_URL = "http://127.0.0.1:5175/"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print Deadman local recording URLs.")
    parser.add_argument("--media-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--deadman-api-base",
        default="",
        help="Optional API base for Vite-only recording, e.g. http://127.0.0.1:7860/api/deadman.",
    )
    parser.add_argument("--episode-id", action="append", default=[])
    args = parser.parse_args()

    registry = json.loads(args.media_registry.read_text())
    selected_episode_ids = set(args.episode_id)
    base_url = args.base_url.rstrip("/") + "/"

    for episode in registry.get("episodes", []):
        if not isinstance(episode, dict):
            continue
        episode_id = str(episode.get("episode_id", ""))
        if selected_episode_ids and episode_id not in selected_episode_ids:
            continue
        producer_media = episode.get("producer_media", {})
        if not isinstance(producer_media, dict):
            producer_media = {}
        vite_dev_video_url = str(producer_media.get("vite_dev_video_url", ""))
        if not episode_id or not vite_dev_video_url:
            continue
        query_params = {
            "branch3_player": "1",
            "episodeId": episode_id,
            "videoUrl": vite_dev_video_url,
        }
        if args.deadman_api_base:
            query_params["deadmanApiBase"] = args.deadman_api_base.rstrip("/")
        query = urlencode(query_params)
        print(f"{episode_id}\t{base_url}?{query}")


if __name__ == "__main__":
    main()
