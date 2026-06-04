#!/usr/bin/env python3
"""Run Volcano Engine Doubao Speech flash ASR for Deadman/Branch 3 audio files.

This is a thin provider adapter for ARS node-mining dogfood. It reads API
credentials from environment variables only and writes raw + normalized ASR
artifacts to a local output directory.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests


DEFAULT_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
DEFAULT_RESOURCE_ID = "volc.bigasr.auc_turbo"
DEFAULT_MODEL_NAME = "bigmodel"
API_KEY_ENV_CANDIDATES = ("DOUBAO_SPEECH_API_KEY", "VOLC_ASR_API_KEY", "VOLC_API_KEY")
UID_ENV_CANDIDATES = ("DOUBAO_SPEECH_UID", "VOLC_ASR_UID", "VOLC_UID")


def _audio_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    for item in args.audio:
        paths.append(Path(item))
    if args.audio_dir:
        audio_dir = Path(args.audio_dir)
        paths.extend(sorted(audio_dir.glob(args.glob)))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    if args.limit:
        unique = unique[: args.limit]
    return unique


def _file_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _first_env(candidates: tuple[str, ...]) -> tuple[str, str]:
    for name in candidates:
        value = os.environ.get(name, "")
        if value:
            return name, value
    return candidates[0], ""


def _recognize(path: Path, *, api_key: str, uid: str, endpoint: str, resource_id: str) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }
    payload = {
        "user": {"uid": uid},
        "audio": {"data": _file_to_base64(path)},
        "request": {
            "model_name": DEFAULT_MODEL_NAME,
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": True,
        },
    }
    response = requests.post(endpoint, json=payload, headers=headers, timeout=300)
    body: dict[str, Any]
    try:
        body = response.json()
    except Exception:
        body = {"raw_text": response.text}
    return {
        "request_id": request_id,
        "status_code": response.status_code,
        "provider_status_code": response.headers.get("X-Api-Status-Code"),
        "provider_message": response.headers.get("X-Api-Message"),
        "provider_logid": response.headers.get("X-Tt-Logid"),
        "body": body,
    }


def _normalize(raw: dict[str, Any], *, audio_path: Path) -> dict[str, Any]:
    body = raw.get("body") or {}
    result = body.get("result") or {}
    utterances = result.get("utterances") or []
    return {
        "provider": "volcengine_doubao_speech",
        "api": "bigmodel_recording_file_flash",
        "audio_path": str(audio_path),
        "request_id": raw.get("request_id"),
        "status_code": raw.get("status_code"),
        "provider_status_code": raw.get("provider_status_code"),
        "provider_message": raw.get("provider_message"),
        "provider_logid": raw.get("provider_logid"),
        "duration": (body.get("audio_info") or {}).get("duration")
        or (result.get("additions") or {}).get("duration"),
        "text": result.get("text", ""),
        "utterances": utterances,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", action="append", default=[], help="Audio file path. Repeatable.")
    parser.add_argument("--audio-dir", help="Directory of prepared audio files.")
    parser.add_argument("--glob", default="*.mp3", help="Glob used with --audio-dir.")
    parser.add_argument("--out-dir", default="tmp/ars_huangnian_analysis/volc_asr")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--resource-id", default=DEFAULT_RESOURCE_ID)
    parser.add_argument("--api-key-env", default="", help="Override API key env var. Default checks DOUBAO_SPEECH_API_KEY, then VOLC_ASR_API_KEY, then VOLC_API_KEY.")
    parser.add_argument("--uid-env", default="", help="Override uid env var. Default checks DOUBAO_SPEECH_UID, then VOLC_ASR_UID, then VOLC_UID.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    paths = _audio_paths(args)
    if not paths:
        print("No audio files selected.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    raw_dir = out_dir / "raw"
    normalized_dir = out_dir / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    if args.api_key_env:
        api_key_env, api_key = args.api_key_env, os.environ.get(args.api_key_env, "")
    else:
        api_key_env, api_key = _first_env(API_KEY_ENV_CANDIDATES)
    if args.uid_env:
        uid_env, uid = args.uid_env, os.environ.get(args.uid_env, "")
    else:
        uid_env, uid = _first_env(UID_ENV_CANDIDATES)
    uid = uid or "deadman-ars"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "audio_count": len(paths),
                    "audio_files": [str(path) for path in paths],
                    "out_dir": str(out_dir),
                    "api_key_env": api_key_env,
                    "api_key_env_candidates": list(API_KEY_ENV_CANDIDATES),
                    "api_key_present": bool(api_key),
                    "uid_env": uid_env,
                    "uid_env_candidates": list(UID_ENV_CANDIDATES),
                    "endpoint": args.endpoint,
                    "resource_id": args.resource_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not api_key:
        print(
            "Missing API key env var. Set one of: "
            + ", ".join(API_KEY_ENV_CANDIDATES)
            + (f" or override with --api-key-env {args.api_key_env}" if args.api_key_env else ""),
            file=sys.stderr,
        )
        return 2

    summary: list[dict[str, Any]] = []
    for path in paths:
        raw = _recognize(path, api_key=api_key, uid=uid, endpoint=args.endpoint, resource_id=args.resource_id)
        stem = path.stem
        raw_path = raw_dir / f"{stem}.raw.json"
        normalized_path = normalized_dir / f"{stem}.normalized.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        normalized = _normalize(raw, audio_path=path)
        normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(
            {
                "audio_path": str(path),
                "raw_path": str(raw_path),
                "normalized_path": str(normalized_path),
                "status_code": raw.get("status_code"),
                "provider_status_code": raw.get("provider_status_code"),
                "text_chars": len(normalized.get("text") or ""),
                "utterance_count": len(normalized.get("utterances") or []),
            }
        )

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
