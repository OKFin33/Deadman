#!/usr/bin/env python3
"""Run Volcano Engine Doubao Speech standard submit/query ASR.

Standard ASR expects an audio URL. This adapter keeps credentials in
environment variables and writes only provider results to local tmp artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import requests


DEFAULT_SUBMIT_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
DEFAULT_QUERY_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
DEFAULT_RESOURCE_ID = "volc.seedasr.auc"
DEFAULT_MODEL_NAME = "bigmodel"
API_KEY_ENV_CANDIDATES = ("DOUBAO_SPEECH_API_KEY", "VOLC_ASR_API_KEY", "VOLC_API_KEY")
UID_ENV_CANDIDATES = ("DOUBAO_SPEECH_UID", "VOLC_ASR_UID", "VOLC_UID")


def _first_env(candidates: tuple[str, ...]) -> tuple[str, str]:
    for name in candidates:
        value = os.environ.get(name, "")
        if value:
            return name, value
    return candidates[0], ""


def _headers(*, api_key: str, resource_id: str, request_id: str, sequence: str = "-1") -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": sequence,
    }


def _submit(
    *,
    audio_url: str,
    audio_format: str,
    api_key: str,
    uid: str,
    resource_id: str,
    submit_endpoint: str,
    show_utterances: bool,
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    payload = {
        "user": {"uid": uid},
        "audio": {
            "url": audio_url,
            "format": audio_format,
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1,
        },
        "request": {
            "model_name": DEFAULT_MODEL_NAME,
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "enable_speaker_info": False,
            "enable_channel_split": False,
            "show_utterances": show_utterances,
            "vad_segment": False,
            "sensitive_words_filter": "",
        },
    }
    response = requests.post(
        submit_endpoint,
        json=payload,
        headers=_headers(api_key=api_key, resource_id=resource_id, request_id=request_id),
        timeout=120,
    )
    body: dict[str, Any]
    try:
        body = response.json() if response.text else {}
    except Exception:
        body = {"raw_text": response.text}
    return {
        "phase": "submit",
        "request_id": request_id,
        "status_code": response.status_code,
        "provider_status_code": response.headers.get("X-Api-Status-Code"),
        "provider_message": response.headers.get("X-Api-Message"),
        "provider_logid": response.headers.get("X-Tt-Logid"),
        "body": body,
    }


def _query(*, request_id: str, api_key: str, resource_id: str, query_endpoint: str) -> dict[str, Any]:
    response = requests.post(
        query_endpoint,
        json={},
        headers=_headers(api_key=api_key, resource_id=resource_id, request_id=request_id, sequence="-1"),
        timeout=120,
    )
    body: dict[str, Any]
    try:
        body = response.json() if response.text else {}
    except Exception:
        body = {"raw_text": response.text}
    return {
        "phase": "query",
        "request_id": request_id,
        "status_code": response.status_code,
        "provider_status_code": response.headers.get("X-Api-Status-Code"),
        "provider_message": response.headers.get("X-Api-Message"),
        "provider_logid": response.headers.get("X-Tt-Logid"),
        "body": body,
    }


def _normalize(query: dict[str, Any], *, audio_url: str) -> dict[str, Any]:
    body = query.get("body") or {}
    result = body.get("result") or {}
    if isinstance(result, list):
        result_obj = result[0] if result else {}
    else:
        result_obj = result
    return {
        "provider": "volcengine_doubao_speech",
        "api": "bigmodel_recording_file_standard",
        "audio_url": audio_url,
        "request_id": query.get("request_id"),
        "status_code": query.get("status_code"),
        "provider_status_code": query.get("provider_status_code"),
        "provider_message": query.get("provider_message"),
        "provider_logid": query.get("provider_logid"),
        "text": result_obj.get("text", ""),
        "utterances": result_obj.get("utterances") or [],
        "raw_result_type": type(result).__name__,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-url", required=True)
    parser.add_argument("--format", default="mp3")
    parser.add_argument("--out-dir", default="tmp/ars_huangnian_analysis/volc_asr_standard")
    parser.add_argument("--resource-id", default=DEFAULT_RESOURCE_ID)
    parser.add_argument("--submit-endpoint", default=DEFAULT_SUBMIT_ENDPOINT)
    parser.add_argument("--query-endpoint", default=DEFAULT_QUERY_ENDPOINT)
    parser.add_argument("--api-key-env", default="", help="Override API key env var. Default checks DOUBAO_SPEECH_API_KEY, then VOLC_ASR_API_KEY, then VOLC_API_KEY.")
    parser.add_argument("--uid-env", default="", help="Override uid env var. Default checks DOUBAO_SPEECH_UID, then VOLC_ASR_UID, then VOLC_UID.")
    parser.add_argument("--show-utterances", action="store_true")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--max-polls", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.api_key_env:
        api_key_env, api_key = args.api_key_env, os.environ.get(args.api_key_env, "")
    else:
        api_key_env, api_key = _first_env(API_KEY_ENV_CANDIDATES)
    if args.uid_env:
        uid_env, uid = args.uid_env, os.environ.get(args.uid_env, "")
    else:
        uid_env, uid = _first_env(UID_ENV_CANDIDATES)
    uid = uid or "deadman-ars"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "audio_url": args.audio_url,
                    "format": args.format,
                    "resource_id": args.resource_id,
                    "api_key_env": api_key_env,
                    "api_key_present": bool(api_key),
                    "uid_env": uid_env,
                    "submit_endpoint": args.submit_endpoint,
                    "query_endpoint": args.query_endpoint,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not api_key:
        print("Missing API key env var. Set DOUBAO_SPEECH_API_KEY, VOLC_ASR_API_KEY, or VOLC_API_KEY.", file=sys.stderr)
        return 2

    submit = _submit(
        audio_url=args.audio_url,
        audio_format=args.format,
        api_key=api_key,
        uid=uid,
        resource_id=args.resource_id,
        submit_endpoint=args.submit_endpoint,
        show_utterances=args.show_utterances,
    )
    request_id = submit["request_id"]
    (out_dir / f"{request_id}.submit.json").write_text(json.dumps(submit, ensure_ascii=False, indent=2), encoding="utf-8")

    queries: list[dict[str, Any]] = []
    final_query: dict[str, Any] | None = None
    poll_count = args.max_polls if args.poll else 1
    for index in range(poll_count):
        if index:
            time.sleep(args.poll_interval)
        query = _query(
            request_id=request_id,
            api_key=api_key,
            resource_id=args.resource_id,
            query_endpoint=args.query_endpoint,
        )
        queries.append(query)
        if query.get("provider_status_code") == "20000000":
            final_query = query
            break
        if query.get("provider_status_code") not in {"20000001", "20000002"}:
            final_query = query
            break
    if final_query is None and queries:
        final_query = queries[-1]

    (out_dir / f"{request_id}.queries.json").write_text(json.dumps(queries, ensure_ascii=False, indent=2), encoding="utf-8")
    normalized = _normalize(final_query or {}, audio_url=args.audio_url)
    (out_dir / f"{request_id}.normalized.json").write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "request_id": request_id,
                "submit_status": submit.get("provider_status_code"),
                "submit_message": submit.get("provider_message"),
                "query_status": (final_query or {}).get("provider_status_code"),
                "query_message": (final_query or {}).get("provider_message"),
                "text_chars": len(normalized.get("text") or ""),
                "utterance_count": len(normalized.get("utterances") or []),
                "out_dir": str(out_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
