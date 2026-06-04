#!/usr/bin/env python3
"""Check Deadman P0 submission readiness without starting a network server."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any

REPO_ROOT = find_deadman_root(__file__)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402


SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|ark-[A-Za-z0-9-]{20,}|x-api-key\\s*[:=]\\s*[0-9a-f-]{20,})",
    re.IGNORECASE,
)
MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v"}
SKIP_DIRS = {
    ".agent",
    ".git",
    "__pycache__",
    "build",
    "dist",
    "local_artifacts",
    "node_modules",
    "output",
    "tmp",
}
SCAN_ROOTS = [
    "assets",
    "backend",
    "data",
    "docs",
    "frontend",
    "studio",
    "tools",
    "ms_deploy.json",
    "server.py",
]
PUBLIC_FORBIDDEN_FRAGMENTS = ("producer_media", "producer_refs", "tmp/", "/@fs", "/Users/", "local_media_path", "checksum")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drama-id", default="huangnian")
    parser.add_argument("--episode-id", default="huangnian_ep12")
    parser.add_argument("--require-external-media-base", action="store_true")
    parser.add_argument(
        "--judgment-engine",
        choices=("demo_deterministic", "cab_runtime"),
        help="Set DEADMAN_JUDGMENT_ENGINE before importing server:app.",
    )
    parser.add_argument(
        "--require-cab-runtime",
        action="store_true",
        help="Shortcut for --judgment-engine cab_runtime plus strict CABRuntime readiness checks.",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    expected_engine = args.judgment_engine or "cab_runtime"
    if args.require_cab_runtime:
        expected_engine = "cab_runtime"
    import os

    os.environ["DEADMAN_JUDGMENT_ENGINE"] = expected_engine

    from server import app as deployment_app  # noqa: PLC0415

    client = TestClient(deployment_app)
    checks = [
        check_ms_deploy(require_external_media_base=args.require_external_media_base),
        check_no_media_or_env_files(),
        check_no_secret_literals(),
        check_deadman_health(
            client,
            require_external_media_base=args.require_external_media_base,
            expected_judgment_engine=expected_engine,
        ),
        check_public_redaction(client, args.drama_id),
        check_media_route(client, args.drama_id, args.episode_id),
        check_judgment_loop(client, args.drama_id, expected_engine=expected_engine),
        check_runtime_session_loop(client, args.drama_id, expected_engine=expected_engine),
    ]

    report = render_report(checks)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0 if all(check.passed for check in checks) else 1


def check_ms_deploy(*, require_external_media_base: bool) -> Check:
    path = REPO_ROOT / "ms_deploy.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    env = {
        str(item.get("name")): str(item.get("value", ""))
        for item in data.get("environment_variables", [])
        if isinstance(item, dict)
    }
    problems: list[str] = []
    if env.get("RUNTIME_LLM_API_KEY"):
        problems.append("RUNTIME_LLM_API_KEY must be empty in tracked ms_deploy.json")
    if "DEADMAN_MEDIA_BASE_URL" not in env:
        problems.append("DEADMAN_MEDIA_BASE_URL is missing from ms_deploy.json")
    if "DEADMAN_JUDGMENT_ENGINE" not in env:
        problems.append("DEADMAN_JUDGMENT_ENGINE is missing from ms_deploy.json")
    elif env.get("DEADMAN_JUDGMENT_ENGINE") not in {"", "demo_deterministic", "cab_runtime"}:
        problems.append("DEADMAN_JUDGMENT_ENGINE must be empty, demo_deterministic, or cab_runtime")
    if require_external_media_base and not env.get("DEADMAN_MEDIA_BASE_URL"):
        problems.append("DEADMAN_MEDIA_BASE_URL must be configured for clean shareable deployment")
    return Check(
        "ms_deploy environment contract",
        not problems,
        "; ".join(problems)
        if problems
        else "provider key is empty; DEADMAN_MEDIA_BASE_URL and DEADMAN_JUDGMENT_ENGINE are declared",
    )


def check_no_media_or_env_files() -> Check:
    offenders: list[str] = []
    for root in ("assets", "backend", "data", "docs", "frontend", "studio", "tools"):
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if should_skip(path):
                continue
            if path.is_file() and (path.suffix.lower() in MEDIA_SUFFIXES or path.name.startswith(".env")):
                offenders.append(repo_relative(path))
    return Check(
        "tracked work-area media/env scan",
        not offenders,
        "no MP4/MOV/M4V or .env files found" if not offenders else ", ".join(offenders[:12]),
    )


def check_no_secret_literals() -> Check:
    offenders: list[str] = []
    for raw_root in SCAN_ROOTS:
        root = REPO_ROOT / raw_root
        if not root.exists():
            continue
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in paths:
            if should_skip(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if SECRET_PATTERN.search(text):
                offenders.append(repo_relative(path))
    return Check(
        "literal secret scan",
        not offenders,
        "no literal key patterns found" if not offenders else ", ".join(offenders[:12]),
    )


def check_deadman_health(
    client: TestClient,
    *,
    require_external_media_base: bool,
    expected_judgment_engine: str | None,
) -> Check:
    response = client.get("/api/deadman/health")
    if response.status_code != 200:
        return Check("deploy health", False, f"/api/deadman/health returned {response.status_code}")
    body = response.json()
    media = body.get("media", {})
    judgment = body.get("judgment", {})
    problems: list[str] = []
    if body.get("status") != "ok":
        problems.append("health status is not ok")
    if "huangnian" not in body.get("dramas", []):
        problems.append("huangnian pack is not loaded")
    if not media.get("deployment_ready"):
        problems.append("media.deployment_ready is false")
    if require_external_media_base and not media.get("external_base_url_configured"):
        problems.append("external media base is not configured")
    if expected_judgment_engine and judgment.get("engine") != expected_judgment_engine:
        problems.append(f"judgment.engine is {judgment.get('engine')}, expected {expected_judgment_engine}")
    if expected_judgment_engine == "cab_runtime":
        if not judgment.get("formal_runtime_enabled"):
            problems.append("formal_runtime_enabled is false")
        if not judgment.get("cab_runtime_config_valid"):
            problems.append(f"cab runtime config invalid: {judgment.get('cab_runtime_error')}")
        if not judgment.get("cab_runtime_root_exists"):
            problems.append("cab runtime root does not exist")
        if not judgment.get("cab_project_exists"):
            problems.append("cab runtime project does not exist")
    return Check(
        "deploy health, media readiness, and judgment engine",
        not problems,
        "; ".join(problems)
        if problems
        else (
            f"media mode={media.get('mode')}, local_available={media.get('local_available_episodes')}/"
            f"{media.get('total_registered_episodes')}, judgment={judgment.get('engine')}"
        ),
    )


def check_public_redaction(client: TestClient, drama_id: str) -> Check:
    paths = [
        f"/api/deadman/dramas/{drama_id}/media-registry",
        f"/api/deadman/dramas/{drama_id}/moments",
    ]
    problems: list[str] = []
    for path in paths:
        response = client.get(path)
        if response.status_code != 200:
            problems.append(f"{path} returned {response.status_code}")
            continue
        text = response.text
        leaked = [fragment for fragment in PUBLIC_FORBIDDEN_FRAGMENTS if fragment in text]
        if leaked:
            problems.append(f"{path} leaked {', '.join(leaked)}")
    return Check(
        "public producer-metadata redaction",
        not problems,
        "; ".join(problems) if problems else "public registry and moments expose no producer-local paths",
    )


def check_media_route(client: TestClient, drama_id: str, episode_id: str) -> Check:
    response = client.get(f"/api/deadman/media/{drama_id}/{episode_id}", headers={"Range": "bytes=0-15"})
    if response.status_code not in {200, 206}:
        return Check("registered media route", False, f"media route returned {response.status_code}: {response.text[:120]}")
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("video/"):
        return Check("registered media route", False, f"unexpected content-type {content_type}")
    return Check("registered media route", True, f"{episode_id} served as {content_type}")


def check_judgment_loop(client: TestClient, drama_id: str, *, expected_engine: str | None) -> Check:
    moments_response = client.get(f"/api/deadman/dramas/{drama_id}/moments")
    if moments_response.status_code != 200:
        return Check("viewer judgment loop", False, f"moments returned {moments_response.status_code}")
    moments = moments_response.json()
    if not moments:
        return Check("viewer judgment loop", False, "no moments returned")
    moment = moments[0]
    options = moment.get("default_options") or []
    if not options:
        return Check("viewer judgment loop", False, "first moment has no default options")
    payload = {
        "drama_id": drama_id,
        "moment_id": moment["moment_id"],
        "action": {"source": "preset", "text": options[0], "option_index": 0},
    }
    response = client.post("/api/deadman/judgment", json=payload)
    if response.status_code != 200:
        return Check("viewer judgment loop", False, f"judgment returned {response.status_code}: {response.text[:120]}")
    body = response.json()
    if not body.get("consequence", {}).get("text"):
        return Check("viewer judgment loop", False, "judgment consequence text is missing")
    actual_engine = body.get("engine", {}).get("mode")
    if expected_engine and actual_engine != expected_engine:
        return Check("viewer judgment loop", False, f"judgment engine is {actual_engine}, expected {expected_engine}")
    if expected_engine != "cab_runtime" and not body.get("aggregate_stats"):
        return Check("viewer judgment loop", False, "aggregate_stats is missing")
    detail = f"{moment['moment_id']} returns verdict via {actual_engine}"
    if body.get("aggregate_stats"):
        detail += " with aggregate_stats"
    return Check("viewer judgment loop", True, detail)


def check_runtime_session_loop(client: TestClient, drama_id: str, *, expected_engine: str | None) -> Check:
    moments_response = client.get(f"/api/deadman/dramas/{drama_id}/moments")
    if moments_response.status_code != 200:
        return Check("resident runtime session loop", False, f"moments returned {moments_response.status_code}")
    moments = moments_response.json()
    if not moments:
        return Check("resident runtime session loop", False, "no moments returned")
    moment = moments[0]
    options = moment.get("default_options") or []
    if not options:
        return Check("resident runtime session loop", False, "first moment has no default options")
    episode_id = str(moment.get("source_drama", {}).get("episode_id") or "huangnian_ep12")
    interaction_window = moment.get("interaction_window", {})
    playback_time = float(interaction_window.get("notice_at_seconds") or interaction_window.get("start_seconds") or 0)
    base_payload = {
        "viewer_session_id": "submission-readiness-session",
        "drama_id": drama_id,
        "episode_id": episode_id,
        "playback_time_seconds": playback_time,
        "moment_id": moment["moment_id"],
        "companion_state": "idle",
        "viewer_profile": {"tone": "friend", "risk_preference": "balanced"},
    }
    start = client.post(
        "/api/deadman/runtime/session/event",
        json={**base_payload, "event_id": "readiness-start", "event_type": "session_start"},
    )
    if start.status_code != 200 or start.json().get("status") != "ok":
        return Check("resident runtime session loop", False, f"session_start failed: {start.status_code} {start.text[:120]}")
    action = client.post(
        "/api/deadman/runtime/session/event",
        json={
            **base_payload,
            "event_id": "readiness-action",
            "event_type": "user_action",
            "action": {"source": "preset", "text": options[0], "option_index": 0},
        },
    )
    if action.status_code != 200:
        return Check("resident runtime session loop", False, f"user_action returned {action.status_code}: {action.text[:120]}")
    body = action.json()
    if body.get("status") != "ok":
        return Check("resident runtime session loop", False, f"user_action status={body.get('status')}: {body.get('error')}")
    if not body.get("result_surface", {}).get("text"):
        return Check("resident runtime session loop", False, "result_surface.text is missing")
    actual_engine = body.get("judgment", {}).get("engine", {}).get("mode")
    if expected_engine and actual_engine != expected_engine:
        return Check("resident runtime session loop", False, f"runtime judgment engine is {actual_engine}, expected {expected_engine}")
    return Check(
        "resident runtime session loop",
        True,
        f"{moment['moment_id']} returns companion result via {actual_engine or 'host_policy'}",
    )


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(checks: list[Check]) -> str:
    lines = ["# Deadman Submission Readiness Check", ""]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- {status}: {check.name} -- {check.detail}")
    lines.append("")
    lines.append(f"Overall: {'PASS' if all(check.passed for check in checks) else 'FAIL'}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
