#!/usr/bin/env python3
"""Prepare local Deadman ARS media assets for one short-drama folder.

The script writes only ignored analysis artifacts:

- media_index.json
- mono 16 kHz mp3 files for ASR
- 10-second keyframe refs
- lightweight contact sheets
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def episode_number(path: Path) -> int:
    match = re.search(r"第\s*(\d+)\s*集", path.stem)
    if match:
        return int(match.group(1))
    numbers = re.findall(r"\d+", path.stem)
    return int(numbers[-1]) if numbers else 0


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    duration_s = float((data.get("format") or {}).get("duration") or video.get("duration") or 0)
    return {
        "duration_ms": int(round(duration_s * 1000)),
        "duration_s": round(duration_s, 3),
        "size_bytes": int((data.get("format") or {}).get("size") or path.stat().st_size),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "fps": video.get("r_frame_rate") or video.get("avg_frame_rate"),
    }


def extract_audio(video_path: Path, audio_path: Path, force: bool) -> bool:
    if audio_path.exists() and not force:
        return False
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            str(audio_path),
        ]
    )
    return True


def extract_keyframes(video_path: Path, out_dir: Path, force: bool) -> int:
    existing = sorted(out_dir.glob("frame_*.jpg"))
    if existing and not force:
        return len(existing)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in existing:
        old.unlink()
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "fps=1/10,scale=270:-1",
            "-q:v",
            "3",
            str(out_dir / "frame_%03d.jpg"),
        ]
    )
    return len(list(out_dir.glob("frame_*.jpg")))


def make_contact_sheet(video_path: Path, out_path: Path, force: bool) -> bool:
    if out_path.exists() and not force:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "fps=1/20,scale=216:-1,tile=5x4",
            "-frames:v",
            "1",
            str(out_path),
        ]
    )
    return True


def build_media_index(video_dir: Path, drama_id: str) -> list[dict[str, Any]]:
    videos = sorted(video_dir.glob("*.mp4"), key=episode_number)
    index: list[dict[str, Any]] = []
    for video_path in videos:
        number = episode_number(video_path)
        episode_id = f"{drama_id}_ep{number:02d}"
        item = {
            "episode_id": episode_id,
            "episode_title": f"第{number}集",
            "video_path": repo_relative(video_path),
            **probe_video(video_path),
        }
        index.append(item)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-id", required=True)
    parser.add_argument("--drama-title", required=True)
    parser.add_argument("--video-dir", required=True)
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-keyframes", action="store_true")
    parser.add_argument("--skip-contact-sheets", action="store_true")
    args = parser.parse_args()

    video_dir = resolve_path(args.video_dir)
    analysis_dir = resolve_path(args.analysis_dir)
    media_index = build_media_index(video_dir, args.drama_id)
    if args.limit:
        media_index = media_index[: args.limit]

    audio_written = 0
    keyframe_count = 0
    contact_written = 0
    for item in media_index:
        video_path = resolve_path(item["video_path"])
        episode_id = item["episode_id"]
        ep_suffix = episode_id.rsplit("_", 1)[-1]
        if not args.skip_audio:
            audio_path = analysis_dir / "audio_mp3" / f"{episode_id}.mp3"
            audio_written += int(extract_audio(video_path, audio_path, args.force))
        if not args.skip_keyframes:
            keyframe_count += extract_keyframes(video_path, analysis_dir / "keyframes_10s" / ep_suffix, args.force)
        if not args.skip_contact_sheets:
            contact_path = analysis_dir / "contact_sheets" / f"{ep_suffix}_sheet.jpg"
            contact_written += int(make_contact_sheet(video_path, contact_path, args.force))

    media_index_path = analysis_dir / "media_index.json"
    write_json(media_index_path, media_index)
    report = {
        "drama_id": args.drama_id,
        "drama_title": args.drama_title,
        "episode_count": len(media_index),
        "duration_minutes": round(sum(item["duration_ms"] for item in media_index) / 60000, 2),
        "media_index": repo_relative(media_index_path),
        "audio_written": audio_written,
        "keyframe_count": keyframe_count,
        "contact_sheets_written": contact_written,
    }
    write_json(analysis_dir / "prepare_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
