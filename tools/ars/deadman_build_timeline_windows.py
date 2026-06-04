#!/usr/bin/env python3
"""Build timestamped Deadman ARS source windows from local drama artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_ANALYSIS_DIR = REPO_ROOT / "tmp/ars_huangnian_analysis"
DEFAULT_OUT_DIR = DEFAULT_ANALYSIS_DIR / "candidates"
WINDOW_MS = 20_000


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def episode_number(episode_id: str) -> int:
    match = re.search(r"ep(\d+)", episode_id)
    return int(match.group(1)) if match else 0


def frame_time_ms(path: Path) -> int:
    match = re.search(r"frame_(\d+)", path.stem)
    index = int(match.group(1)) if match else 1
    return max(0, (index - 1) * 10_000)


def load_transcript(asr_dir: Path, episode_id: str) -> dict[str, Any] | None:
    path = asr_dir / f"{episode_id}.normalized.json"
    if not path.exists():
        return None
    data = read_json(path)
    data["_path"] = repo_relative(path)
    return data


def normalize_utterance(utterance: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "index": index,
        "start_ms": int(utterance.get("start_time") or utterance.get("start_ms") or 0),
        "end_ms": int(utterance.get("end_time") or utterance.get("end_ms") or 0),
        "text": str(utterance.get("text") or "").strip(),
    }


def overlapping_utterances(utterances: list[dict[str, Any]], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for utterance in utterances:
        midpoint = (utterance["start_ms"] + utterance["end_ms"]) / 2
        if start_ms <= midpoint < end_ms:
            selected.append(utterance)
    return selected


def keyframe_refs(keyframe_dir: Path, episode_id: str, start_ms: int, end_ms: int) -> list[str]:
    ep = f"ep{episode_number(episode_id):02d}"
    refs: list[str] = []
    for path in sorted((keyframe_dir / ep).glob("frame_*.jpg")):
        time_ms = frame_time_ms(path)
        if start_ms <= time_ms < end_ms:
            refs.append(repo_relative(path))
    return refs


def build_windows(media_index: list[dict[str, Any]], analysis_dir: Path) -> list[dict[str, Any]]:
    asr_dir = analysis_dir / "volc_asr/normalized"
    keyframe_dir = analysis_dir / "keyframes_10s"
    contact_sheet_dir = analysis_dir / "contact_sheets"
    windows: list[dict[str, Any]] = []

    for episode in media_index:
        episode_id = episode["episode_id"]
        ep_number = episode_number(episode_id)
        transcript = load_transcript(asr_dir, episode_id)
        utterances = [
            normalize_utterance(utterance, index)
            for index, utterance in enumerate((transcript or {}).get("utterances") or [])
        ]
        duration_ms = int(episode.get("duration_ms") or 0)
        if transcript and transcript.get("duration"):
            duration_ms = max(duration_ms, int(float(transcript["duration"])))
        contact_sheet = contact_sheet_dir / f"ep{ep_number:02d}_sheet.jpg"

        start_ms = 0
        local_index = 1
        while start_ms < duration_ms:
            end_ms = min(duration_ms, start_ms + WINDOW_MS)
            selected_utterances = overlapping_utterances(utterances, start_ms, end_ms)
            transcript_text = " ".join(item["text"] for item in selected_utterances if item["text"]).strip()
            refs = keyframe_refs(keyframe_dir, episode_id, start_ms, end_ms)
            windows.append(
                {
                    "window_id": f"{episode_id}_w{local_index:03d}",
                    "episode_id": episode_id,
                    "episode_title": episode.get("episode_title", ""),
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": end_ms - start_ms,
                    "transcript_text": transcript_text,
                    "transcript_refs": [
                        {
                            "path": (transcript or {}).get("_path", ""),
                            "utterance_index": item["index"],
                            "start_ms": item["start_ms"],
                            "end_ms": item["end_ms"],
                            "text": item["text"],
                        }
                        for item in selected_utterances
                    ],
                    "keyframe_refs": refs,
                    "contact_sheet_ref": repo_relative(contact_sheet) if contact_sheet.exists() else "",
                    "source_quality": {
                        "asr_available": transcript is not None,
                        "utterance_count": len(selected_utterances),
                        "keyframe_count": len(refs),
                    },
                }
            )
            start_ms += WINDOW_MS
            local_index += 1
    return windows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--out", help="Exact output JSON path. Overrides --out-dir.")
    parser.add_argument("--drama-id", default="huangnian")
    parser.add_argument("--drama-title", default="荒年全村啃树皮，我有系统满仓肉")
    parser.add_argument("--version", default="v0.1")
    args = parser.parse_args()

    analysis_dir = resolve_path(args.analysis_dir)
    output_path = resolve_path(args.out) if args.out else resolve_path(args.out_dir) / f"{args.drama_id}_windows.{args.version}.json"
    media_index_path = analysis_dir / "media_index.json"
    media_index = read_json(media_index_path)
    windows = build_windows(media_index, analysis_dir)
    output = {
        "version": args.version,
        "drama_id": args.drama_id,
        "source_drama": args.drama_title,
        "window_ms": WINDOW_MS,
        "media_index_ref": repo_relative(media_index_path),
        "window_count": len(windows),
        "windows": windows,
    }
    write_json(output_path, output)
    print(json.dumps({"window_count": len(windows), "out": repo_relative(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
