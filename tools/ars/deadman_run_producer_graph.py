#!/usr/bin/env python3
"""Run the Deadman Studio producer graph.

This is the first implementation of the Studio contract:

- StateGraph as the top-level workflow primitive;
- SQLite checkpointing under ignored run artifacts;
- dry-run command planning without child process execution;
- Phase A cold-resume spike;
- base producer graph nodes that wrap the existing ARS CLI scripts.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Annotated, Any, Literal, TypedDict, cast


REPO_ROOT = find_deadman_root(__file__)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_RUN_ROOT = REPO_ROOT / "tmp/deadman_producer_runs"
DEFAULT_DRAMA_ID = "huangnian"
DEFAULT_DRAMA_TITLE = "荒年全村啃树皮，我有系统满仓肉"
DEFAULT_ANALYSIS_DIR = REPO_ROOT / "tmp/ars_huangnian_analysis"
DEFAULT_VIDEO_DIR = REPO_ROOT / "tmp/视频素材/荒年"
DEFAULT_DRAMA_DIR = REPO_ROOT / "data/dramas/huangnian"
DEFAULT_SUMMARIES = REPO_ROOT / "docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md"
DEFAULT_REVIEWED_DEMO_NODES = REPO_ROOT / "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json"
DEFAULT_REVIEWED_CANDIDATES = REPO_ROOT / "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json"
SCHEMA_ROOT = REPO_ROOT / "data/schemas/producer_graph"
DEFAULT_EPISODE_IDS = "huangnian_ep03,huangnian_ep04,huangnian_ep06,huangnian_ep07,huangnian_ep12"
REVIEW_POLICY_VERSION = "deadman_studio_review_gate.v0.1"
REVIEW_REQUEST_SCHEMA = SCHEMA_ROOT / "review_request.v0.1.schema.json"
LLM_SEMANTIC_CANDIDATES_SCHEMA = SCHEMA_ROOT / "llm_semantic_candidates.v0.1.schema.json"
LLM_CANDIDATE_JUDGMENT_SCHEMA = SCHEMA_ROOT / "llm_candidate_judgment.v0.1.schema.json"
LLM_DRAMA_CONTEXT_DRAFT_SCHEMA = SCHEMA_ROOT / "llm_drama_context_draft.v0.1.schema.json"
LLM_MOMENT_PACK_DRAFTS_SCHEMA = SCHEMA_ROOT / "llm_moment_pack_drafts.v0.1.schema.json"
LLM_BATCH_MANIFEST_SCHEMA = SCHEMA_ROOT / "llm_batch_manifest.v0.1.schema.json"
ARS_CHILD_TIMEOUT_SECONDS = int(os.environ.get("ARS_CHILD_TIMEOUT_SECONDS", "600"))
LLM_PROVIDER_MAX_ATTEMPTS_DEFAULT = 3
LLM_PROVIDER_RETRY_BASE_SECONDS_DEFAULT = 1.0
DEFAULT_CANDIDATE_RECALL_FALLBACK_SOURCE_COUNT = 20
DEFAULT_CANDIDATE_RECALL_PER_SOURCE = 4.0
DEFAULT_CANDIDATE_RECALL_MIN = 20
DEFAULT_CANDIDATE_RECALL_MAX = 400
DEFAULT_LLM_CACHE_ROOT = REPO_ROOT / "tmp/deadman_llm_cache/v0.1"
DEFAULT_LLM_CACHE_MODE = "read_write"
DEFAULT_LLM_CHUNK_CONCURRENCY = 1
DEFAULT_SEMANTIC_MINER_WINDOW_CAP = 40
DEFAULT_CANDIDATE_JUDGE_BATCH_SIZE = 40
LLM_CACHE_ENTRY_SCHEMA_VERSION = "deadman_llm_cache_entry.v0.1"
LLM_BATCH_MANIFEST_SCHEMA_VERSION = "deadman_llm_batch_manifest.v0.1"
LLM_PROMPT_CONTRACT_VERSION = "deadman_producer_graph_prompts.v0.1"
LLM_NORMALIZER_VERSION = "deadman_producer_graph_llm_normalizer.v0.1"
LLM_CACHE_IGNORED_VALUE_KEYS = {"run_id", "latency_ms", "token_usage"}

BASE_NODE_ORDER = [
    "prepare_assets",
    "register_media",
    "build_timeline_windows",
    "mine_candidates",
    "cluster_candidates",
    "prepare_human_review",
    "human_review_gate",
    "build_drama_context",
    "publish_p0_bridge",
    "validate_producer_bridge",
    "final_report",
]
ARS_ARTIFACT_VERSION = "v0.1"


ProducerRunStatus = Literal[
    "planned",
    "running",
    "waiting_for_review",
    "publishing",
    "failed",
    "validation_failed",
    "rejected_by_human_review",
    "llm_failed",
    "pass",
]
ProducerNodeStatus = Literal[
    "planned",
    "running",
    "waiting_for_review",
    "blocked_by_prior_failure",
    "skipped_by_config",
    "failed",
    "pass",
]


class ProducerRunError(TypedDict, total=False):
    node: str
    code: str
    message: str
    retryable: bool
    artifact_refs: list[str]


def merge_dict(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if left:
        merged.update(left)
    if right:
        merged.update(right)
    return merged


def append_errors(
    left: list[ProducerRunError] | None,
    right: list[ProducerRunError] | None,
) -> list[ProducerRunError]:
    return [*(left or []), *(right or [])]


class ProducerState(TypedDict, total=False):
    run_id: str
    thread_id: str
    drama_id: str
    drama_title: str
    analysis_dir: str
    video_dir: str
    drama_dir: str
    run_dir: str
    status: ProducerRunStatus
    current_node: str
    node_statuses: Annotated[dict[str, ProducerNodeStatus], merge_dict]
    artifact_paths: Annotated[dict[str, str], merge_dict]
    review_decision: Literal["pending", "approve", "reject"]
    reviewer_note: str
    llm_enabled: bool
    mock_provider: bool
    allow_llm_skip: bool
    validation_result: Literal["not_run", "pass", "failed"]
    errors: Annotated[list[ProducerRunError], append_errors]


@dataclass(frozen=True)
class ProducerConfig:
    run_id: str
    drama_id: str
    drama_title: str
    analysis_dir: Path
    video_dir: Path
    drama_dir: Path
    run_dir: Path
    thread_id: str
    reviewed_demo_nodes: Path
    reviewed_candidates: Path
    enable_llm: bool = False
    mock_provider: bool = False
    allow_llm_skip: bool = False
    review_decision: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def optional_positive_int_env(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    value = safe_int(raw, default=0)
    return value if value > 0 else None


def positive_int_env(name: str, *, default: int) -> int:
    value = safe_int(os.environ.get(name), default=default)
    return value if value > 0 else default


def positive_float_env(name: str, *, default: float) -> float:
    value = safe_float(os.environ.get(name), default=default)
    return value if value > 0 else default


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def validate_json_schema(data: Any, schema_path: Path) -> tuple[bool, str]:
    from jsonschema import Draft202012Validator

    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return True, ""
    return False, "; ".join(f"{list(error.path)} {error.message}" for error in errors[:5])


def summarize_text(text: str, *, limit: int = 2000) -> str:
    clean = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())
    return clean[:limit]


def run_dir(run_id: str) -> Path:
    return DEFAULT_RUN_ROOT / run_id


def checkpoint_path(config: ProducerConfig) -> Path:
    return config.run_dir / "checkpoint.sqlite"


def manifest_path(config: ProducerConfig) -> Path:
    return config.run_dir / "producer_job_manifest.json"


def command_log_path(config: ProducerConfig) -> Path:
    return config.run_dir / "command_log.jsonl"


def review_request_path(config: ProducerConfig) -> Path:
    return config.run_dir / "review_request.json"


def final_report_path(config: ProducerConfig) -> Path:
    return config.run_dir / "final_report.md"


def graph_node_order(config: ProducerConfig) -> list[str]:
    if not config.enable_llm:
        return list(BASE_NODE_ORDER)
    order = list(BASE_NODE_ORDER)
    order.insert(order.index("cluster_candidates"), "llm_semantic_miner")
    order.insert(order.index("prepare_human_review"), "llm_candidate_judge")
    order.insert(order.index("build_drama_context"), "llm_drama_context_draft")
    order.insert(order.index("build_drama_context"), "llm_moment_pack_draft")
    return order


def graph_mode(config: ProducerConfig) -> str:
    return "llm" if config.enable_llm else "base"


def initial_node_statuses(config: ProducerConfig) -> dict[str, ProducerNodeStatus]:
    return {node: "planned" for node in graph_node_order(config)}


def initial_state(config: ProducerConfig) -> ProducerState:
    return {
        "run_id": config.run_id,
        "thread_id": config.thread_id,
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "analysis_dir": repo_relative(config.analysis_dir),
        "video_dir": repo_relative(config.video_dir),
        "drama_dir": repo_relative(config.drama_dir),
        "run_dir": repo_relative(config.run_dir),
        "status": "planned",
        "current_node": "",
        "node_statuses": initial_node_statuses(config),
        "artifact_paths": artifact_plan(config),
        "review_decision": "pending",
        "reviewer_note": "",
        "llm_enabled": config.enable_llm,
        "mock_provider": config.mock_provider,
        "allow_llm_skip": config.allow_llm_skip,
        "validation_result": "not_run",
        "errors": [],
    }


def artifact_plan(config: ProducerConfig) -> dict[str, str]:
    analysis_dir = config.analysis_dir
    candidate_dir = analysis_dir / "candidates"
    drama_dir = config.drama_dir
    artifacts = {
        "run_dir": repo_relative(config.run_dir),
        "checkpoint": repo_relative(checkpoint_path(config)),
        "manifest": repo_relative(manifest_path(config)),
        "command_log": repo_relative(command_log_path(config)),
        "review_request": repo_relative(review_request_path(config)),
        "final_report": repo_relative(final_report_path(config)),
        "media_index": repo_relative(analysis_dir / "media_index.json"),
        "media_registry": repo_relative(drama_dir / "media_registry.v0.1.json"),
        "windows": repo_relative(candidate_dir / f"{config.drama_id}_windows.v0.1.json"),
        "candidates_json": repo_relative(candidate_dir / f"{config.drama_id}_candidates.v0.1.json"),
        "candidates_md": repo_relative(candidate_dir / f"{config.drama_id}_candidates.v0.1.md"),
        "mechanism_buckets_json": repo_relative(candidate_dir / f"{config.drama_id}_mechanism_buckets.v0.1.json"),
        "mechanism_buckets_md": repo_relative(candidate_dir / f"{config.drama_id}_mechanism_buckets.v0.1.md"),
        "field_hypotheses_md": repo_relative(candidate_dir / f"{config.drama_id}_field_hypotheses.v0.1.md"),
        "cluster_run_report": repo_relative(candidate_dir / "run_report.md"),
        "drama_context_out_dir": repo_relative(analysis_dir / "drama_context"),
        "reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
        "reviewed_candidates": repo_relative(config.reviewed_candidates),
        "validation_report": repo_relative(analysis_dir / "producer_bridge_validation_report.md"),
        "context_pack": repo_relative(drama_dir / "context.v0.1.json"),
        "moments_pack": repo_relative(drama_dir / "moments.v0.1.json"),
        "manifest_pack": repo_relative(drama_dir / "manifest.v0.1.json"),
    }
    if config.enable_llm:
        artifacts["llm_semantic_candidates"] = repo_relative(config.run_dir / "llm_semantic_candidates.json")
        artifacts["llm_candidate_judgment"] = repo_relative(config.run_dir / "llm_candidate_judgment.json")
        artifacts["llm_drama_context_draft"] = repo_relative(config.run_dir / "llm_drama_context_draft.json")
        artifacts["llm_moment_pack_drafts"] = repo_relative(config.run_dir / "llm_moment_pack_drafts.json")
        artifacts["provider_trace_redacted"] = repo_relative(config.run_dir / "provider_trace_redacted.jsonl")
        artifacts["llm_batch_manifest"] = repo_relative(config.run_dir / "llm_batch_manifest.json")
        artifacts["llm_semantic_miner_chunks_dir"] = repo_relative(config.run_dir / "llm_semantic_miner_chunks")
        artifacts["llm_candidate_judge_chunks_dir"] = repo_relative(config.run_dir / "llm_candidate_judge_chunks")
    return artifacts


def make_config(args: argparse.Namespace) -> ProducerConfig:
    run_id_value = args.run_id
    return ProducerConfig(
        run_id=run_id_value,
        drama_id=args.drama_id,
        drama_title=args.drama_title,
        analysis_dir=resolve_path(args.analysis_dir),
        video_dir=resolve_path(args.video_dir),
        drama_dir=resolve_path(args.drama_dir),
        run_dir=run_dir(run_id_value),
        thread_id=f"deadman-producer:{run_id_value}",
        reviewed_demo_nodes=resolve_path(args.reviewed_demo_nodes),
        reviewed_candidates=resolve_path(args.reviewed_candidates),
        enable_llm=bool(getattr(args, "enable_llm", False)),
        mock_provider=bool(getattr(args, "mock_provider", False)),
        allow_llm_skip=bool(getattr(args, "allow_llm_skip", False)),
        review_decision=getattr(args, "review_decision", None),
    )


def bool_from_manifest(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def path_from_manifest(mapping: Mapping[str, Any], key: str, default: Path) -> Path:
    value = mapping.get(key)
    return resolve_path(value) if isinstance(value, str) and value else default


def resume_config_from_manifest(config: ProducerConfig) -> ProducerConfig:
    path = manifest_path(config)
    if not path.exists():
        return config
    manifest = read_json(path)
    if not isinstance(manifest, dict):
        return config
    paths = manifest.get("paths")
    artifacts = manifest.get("artifacts")
    graph = manifest.get("graph")
    llm = manifest.get("llm")
    paths_map = paths if isinstance(paths, dict) else {}
    artifacts_map = artifacts if isinstance(artifacts, dict) else {}
    graph_map = graph if isinstance(graph, dict) else {}
    llm_map = llm if isinstance(llm, dict) else {}
    graph_mode = graph_map.get("mode")
    enable_llm = bool_from_manifest(llm_map.get("enabled"), config.enable_llm) or graph_mode == "llm"
    return replace(
        config,
        drama_id=str(manifest.get("drama_id") or config.drama_id),
        drama_title=str(manifest.get("drama_title") or config.drama_title),
        analysis_dir=path_from_manifest(paths_map, "analysis_dir", config.analysis_dir),
        video_dir=path_from_manifest(paths_map, "video_dir", config.video_dir),
        drama_dir=path_from_manifest(paths_map, "drama_dir", config.drama_dir),
        run_dir=path_from_manifest(paths_map, "run_dir", config.run_dir),
        thread_id=str(manifest.get("thread_id") or config.thread_id),
        reviewed_demo_nodes=path_from_manifest(artifacts_map, "reviewed_demo_nodes", config.reviewed_demo_nodes),
        reviewed_candidates=path_from_manifest(artifacts_map, "reviewed_candidates", config.reviewed_candidates),
        enable_llm=enable_llm,
        mock_provider=bool_from_manifest(llm_map.get("mock_provider"), config.mock_provider),
        allow_llm_skip=bool_from_manifest(llm_map.get("allow_skip"), config.allow_llm_skip),
    )


def child_python() -> str:
    return sys.executable


def node_update(
    node: str,
    *,
    status: ProducerRunStatus = "running",
    node_status: ProducerNodeStatus = "running",
    artifact_paths: Mapping[str, str] | None = None,
    errors: list[ProducerRunError] | None = None,
    validation_result: Literal["not_run", "pass", "failed"] | None = None,
    review_decision: Literal["pending", "approve", "reject"] | None = None,
    reviewer_note: str | None = None,
) -> ProducerState:
    update: ProducerState = {
        "status": status,
        "current_node": node,
        "node_statuses": {node: node_status},
    }
    if artifact_paths:
        update["artifact_paths"] = dict(artifact_paths)
    if errors:
        update["errors"] = errors
    if validation_result:
        update["validation_result"] = validation_result
    if review_decision:
        update["review_decision"] = review_decision
    if reviewer_note is not None:
        update["reviewer_note"] = reviewer_note
    return update


def failure_update(node: str, code: str, message: str, *, retryable: bool = False) -> ProducerState:
    return node_update(
        node,
        status="failed",
        node_status="failed",
        errors=[
            {
                "node": node,
                "code": code,
                "message": message,
                "retryable": retryable,
                "artifact_refs": [],
            }
        ],
    )


def command_record(
    *,
    config: ProducerConfig,
    node: str,
    argv: list[str],
    status: str,
    started_at: str,
    ended_at: str | None = None,
    exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    duration_ms = None
    if ended_at:
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(ended_at)
            duration_ms = int((end - start).total_seconds() * 1000)
        except ValueError:
            duration_ms = None
    return {
        "run_id": config.run_id,
        "node": node,
        "status": status,
        "argv": argv,
        "cwd": repo_relative(REPO_ROOT),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "stdout_summary": summarize_text(stdout),
        "stderr_summary": summarize_text(stderr),
        "artifact_refs": artifact_refs or [],
    }


def append_command_record(config: ProducerConfig, record: dict[str, Any]) -> None:
    path = command_log_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def output_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_child(
    *,
    config: ProducerConfig,
    node: str,
    argv: list[str],
    artifact_refs: list[str],
) -> tuple[bool, str, str, bool]:
    import subprocess

    started_at = now_iso()
    append_command_record(
        config,
        command_record(
            config=config,
            node=node,
            argv=argv,
            status="started",
            started_at=started_at,
            artifact_refs=artifact_refs,
        ),
    )
    try:
        result = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=ARS_CHILD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        ended_at = now_iso()
        append_command_record(
            config,
            command_record(
                config=config,
                node=node,
                argv=argv,
                status="timeout",
                started_at=started_at,
                ended_at=ended_at,
                stdout=output_text(exc.stdout),
                stderr=output_text(exc.stderr),
                artifact_refs=artifact_refs,
            ),
        )
        return False, f"child process timed out after {ARS_CHILD_TIMEOUT_SECONDS}s", "child_timeout", True
    ended_at = now_iso()
    append_command_record(
        config,
        command_record(
            config=config,
            node=node,
            argv=argv,
            status="completed" if result.returncode == 0 else "failed",
            started_at=started_at,
            ended_at=ended_at,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            artifact_refs=artifact_refs,
        ),
    )
    if result.returncode != 0:
        return False, summarize_text(result.stderr or result.stdout), "", False
    return True, summarize_text(result.stdout), "", False


def write_manifest(config: ProducerConfig, state: Mapping[str, Any]) -> None:
    node_statuses = state.get("node_statuses", initial_node_statuses(config))
    artifact_paths = state.get("artifact_paths", artifact_plan(config))
    manifest = {
        "run_id": config.run_id,
        "thread_id": config.thread_id,
        "status": state.get("status", "planned"),
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "generated_at": now_iso(),
        "graph": {
            "mode": graph_mode(config),
            "api": "StateGraph",
            "node_order": graph_node_order(config),
            "current_node": state.get("current_node", ""),
            "node_statuses": node_statuses,
        },
        "paths": {
            "analysis_dir": repo_relative(config.analysis_dir),
            "video_dir": repo_relative(config.video_dir),
            "drama_dir": repo_relative(config.drama_dir),
            "run_dir": repo_relative(config.run_dir),
            "checkpoint": repo_relative(checkpoint_path(config)),
            "command_log": repo_relative(command_log_path(config)),
            "review_request": repo_relative(review_request_path(config)),
            "final_report": repo_relative(final_report_path(config)),
        },
        "artifacts": artifact_paths,
        "review": {
            "decision": state.get("review_decision", "pending"),
            "request_hash": read_request_hash(config),
            "reviewer_note": state.get("reviewer_note", ""),
        },
        "llm": llm_manifest(config, node_statuses, artifact_paths),
        "validation": {
            "status": state.get("validation_result", "not_run"),
            "report": artifact_paths.get("validation_report", ""),
        },
        "errors": state.get("errors", []),
    }
    write_json(manifest_path(config), manifest)


def llm_manifest(
    config: ProducerConfig,
    node_statuses: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    artifact_provider = llm_artifact_provider(config)
    if config.enable_llm:
        nodes["llm_semantic_miner"] = {
            "status": node_statuses.get("llm_semantic_miner", "planned"),
            "artifact": artifact_paths.get("llm_semantic_candidates", ""),
            "schema": repo_relative(LLM_SEMANTIC_CANDIDATES_SCHEMA),
            "schema_validation": schema_validation_status(resolve_path(artifact_paths.get("llm_semantic_candidates", ""))),
        }
        nodes["llm_candidate_judge"] = {
            "status": node_statuses.get("llm_candidate_judge", "planned"),
            "artifact": artifact_paths.get("llm_candidate_judgment", ""),
            "schema": repo_relative(LLM_CANDIDATE_JUDGMENT_SCHEMA),
            "schema_validation": schema_validation_status(resolve_path(artifact_paths.get("llm_candidate_judgment", ""))),
        }
        nodes["llm_drama_context_draft"] = {
            "status": node_statuses.get("llm_drama_context_draft", "planned"),
            "artifact": artifact_paths.get("llm_drama_context_draft", ""),
            "schema": repo_relative(LLM_DRAMA_CONTEXT_DRAFT_SCHEMA),
            "schema_validation": schema_validation_status(resolve_path(artifact_paths.get("llm_drama_context_draft", ""))),
        }
        nodes["llm_moment_pack_draft"] = {
            "status": node_statuses.get("llm_moment_pack_draft", "planned"),
            "artifact": artifact_paths.get("llm_moment_pack_drafts", ""),
            "schema": repo_relative(LLM_MOMENT_PACK_DRAFTS_SCHEMA),
            "schema_validation": schema_validation_status(resolve_path(artifact_paths.get("llm_moment_pack_drafts", ""))),
        }
    return {
        "enabled": config.enable_llm,
        "provider": artifact_provider.get("name") or configured_llm_provider(config),
        "model": artifact_provider.get("model") or configured_llm_model(config),
        "mock_provider": config.mock_provider,
        "allow_skip": config.allow_llm_skip,
        "temperature": configured_llm_temperature(config),
        "latency_ms": artifact_provider.get("latency_ms"),
        "token_usage": artifact_provider.get("token_usage"),
        "schema_validation": "pass" if artifact_provider else "not_run",
        "redacted_trace": artifact_paths.get("provider_trace_redacted", ""),
        "nodes": nodes,
    }


def schema_validation_status(path: Path) -> str:
    return "pass" if path.exists() else "not_run"


def configured_llm_provider(config: ProducerConfig) -> str:
    if not config.enable_llm:
        return ""
    return "mock" if config.mock_provider else "ark"


def configured_llm_model(config: ProducerConfig) -> str:
    if not config.enable_llm:
        return ""
    if config.mock_provider:
        return "deadman-mock-candidate-judge-v0.1"
    return os.environ.get("ARK_MODEL_NAME") or os.environ.get("ARK_MODEL") or os.environ.get("ARK_ENDPOINT_ID") or ""


def configured_llm_temperature(config: ProducerConfig) -> float | None:
    if not config.enable_llm:
        return None
    if config.mock_provider:
        return None
    try:
        return float(os.environ.get("ARK_TEMPERATURE", "0.0"))
    except ValueError:
        return 0.0


def llm_artifact_provider(config: ProducerConfig) -> dict[str, Any]:
    for artifact_name in [
        "llm_semantic_candidates.json",
        "llm_candidate_judgment.json",
        "llm_drama_context_draft.json",
        "llm_moment_pack_drafts.json",
    ]:
        artifact = config.run_dir / artifact_name
        if not artifact.exists():
            continue
        try:
            data = read_json(artifact)
        except (json.JSONDecodeError, OSError):
            continue
        provider = data.get("provider") if isinstance(data, dict) else None
        if isinstance(provider, dict):
            return dict(provider)
    return {}


def is_interrupt_result(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    payload = result.get("__interrupt__")
    if not payload:
        return False
    InterruptType: Any
    try:
        from langgraph.types import Interrupt
        InterruptType = Interrupt
    except ImportError:
        InterruptType = None

    def is_interrupt_item(item: Any) -> bool:
        if InterruptType is not None and isinstance(item, InterruptType):
            return True
        return item.__class__.__name__ == "Interrupt"

    if isinstance(payload, (list, tuple)):
        return any(is_interrupt_item(item) for item in payload)
    return is_interrupt_item(payload)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(child) for child in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def read_request_hash(config: ProducerConfig) -> str:
    path = review_request_path(config)
    if not path.exists():
        return ""
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return ""
    return str(data.get("request_hash") or "")


def command_plan(config: ProducerConfig) -> list[dict[str, Any]]:
    py = child_python()
    artifacts = artifact_plan(config)
    return [
        {
            "node": "prepare_assets",
            "argv": [
                py,
                "tools/ars/deadman_prepare_drama_assets.py",
                "--drama-id",
                config.drama_id,
                "--drama-title",
                config.drama_title,
                "--video-dir",
                repo_relative(config.video_dir),
                "--analysis-dir",
                repo_relative(config.analysis_dir),
            ],
            "artifact_refs": [artifacts["media_index"]],
        },
        {
            "node": "register_media",
            "argv": [
                py,
                "tools/ars/deadman_register_media.py",
                "--drama-id",
                config.drama_id,
                "--title",
                config.drama_title,
                "--media-index",
                artifacts["media_index"],
                "--out",
                artifacts["media_registry"],
                "--episode-ids",
                DEFAULT_EPISODE_IDS,
                "--runtime-base",
                f"/api/deadman/media/{config.drama_id}",
            ],
            "artifact_refs": [artifacts["media_registry"]],
        },
        {
            "node": "build_timeline_windows",
            "argv": [
                py,
                "tools/ars/deadman_build_timeline_windows.py",
                "--analysis-dir",
                repo_relative(config.analysis_dir),
                "--out-dir",
                repo_relative(config.analysis_dir / "candidates"),
                "--drama-id",
                config.drama_id,
                "--drama-title",
                config.drama_title,
                "--version",
                ARS_ARTIFACT_VERSION,
            ],
            "artifact_refs": [artifacts["windows"]],
        },
        {
            "node": "mine_candidates",
            "argv": [
                py,
                "tools/ars/deadman_mine_candidates.py",
                "--candidate-dir",
                repo_relative(config.analysis_dir / "candidates"),
                "--max-candidates",
                str(candidate_recall_budget(config, artifacts)),
                "--drama-id",
                config.drama_id,
                "--drama-title",
                config.drama_title,
                "--version",
                ARS_ARTIFACT_VERSION,
                "--out-json",
                artifacts["candidates_json"],
                "--out-md",
                artifacts["candidates_md"],
            ],
            "artifact_refs": [artifacts["candidates_json"], artifacts["candidates_md"]],
        },
        {
            "node": "cluster_candidates",
            "argv": [
                py,
                "tools/ars/deadman_cluster_candidates.py",
                "--candidate-dir",
                repo_relative(config.analysis_dir / "candidates"),
                "--analysis-dir",
                repo_relative(config.analysis_dir),
                "--drama-id",
                config.drama_id,
                "--drama-title",
                config.drama_title,
                "--version",
                ARS_ARTIFACT_VERSION,
                "--windows",
                artifacts["windows"],
                "--candidates",
                artifacts["candidates_json"],
                "--out-json",
                artifacts["mechanism_buckets_json"],
                "--out-md",
                artifacts["mechanism_buckets_md"],
                "--field-md",
                artifacts["field_hypotheses_md"],
                "--run-report",
                artifacts["cluster_run_report"],
            ],
            "artifact_refs": [
                artifacts["mechanism_buckets_json"],
                artifacts["mechanism_buckets_md"],
                artifacts["field_hypotheses_md"],
                artifacts["cluster_run_report"],
            ],
        },
        {
            "node": "build_drama_context",
            "argv": [
                py,
                "tools/ars/deadman_build_drama_context.py",
                "--drama-id",
                config.drama_id,
                "--reviewed-demo-nodes",
                repo_relative(config.reviewed_demo_nodes),
                "--reviewed-candidates",
                repo_relative(config.reviewed_candidates),
                "--summaries",
                repo_relative(DEFAULT_SUMMARIES),
                "--out-dir",
                artifacts["drama_context_out_dir"],
                "--promote",
                "--promote-dir",
                repo_relative(config.drama_dir),
            ],
            "artifact_refs": [artifacts["drama_context_out_dir"], artifacts["context_pack"], artifacts["moments_pack"]],
        },
        {
            "node": "publish_p0_bridge",
            "argv": [
                py,
                "tools/ars/deadman_publish_p0_bridge.py",
                "--drama-dir",
                repo_relative(config.drama_dir),
                "--reviewed-demo-nodes",
                repo_relative(config.reviewed_demo_nodes),
                "--reviewed-candidates",
                repo_relative(config.reviewed_candidates),
                "--media-registry",
                artifacts["media_registry"],
            ],
            "artifact_refs": [artifacts["manifest_pack"], artifacts["context_pack"], artifacts["moments_pack"]],
        },
        {
            "node": "validate_producer_bridge",
            "argv": [
                py,
                "tools/ars/deadman_validate_producer_bridge.py",
                "--drama-dir",
                repo_relative(config.drama_dir),
                "--report",
                artifacts["validation_report"],
            ],
            "artifact_refs": [artifacts["validation_report"]],
        },
    ]


def candidate_recall_budget(config: ProducerConfig, artifacts: Mapping[str, str]) -> int:
    del config
    override = optional_positive_int_env("DEADMAN_CANDIDATE_RECALL_LIMIT")
    if override is not None:
        return override
    source_count = media_index_source_count(resolve_path(artifacts["media_index"]))
    if source_count <= 0:
        source_count = positive_int_env(
            "DEADMAN_CANDIDATE_RECALL_FALLBACK_SOURCE_COUNT",
            default=DEFAULT_CANDIDATE_RECALL_FALLBACK_SOURCE_COUNT,
        )
    per_source = positive_float_env("DEADMAN_CANDIDATE_RECALL_PER_SOURCE", default=DEFAULT_CANDIDATE_RECALL_PER_SOURCE)
    min_budget = positive_int_env("DEADMAN_CANDIDATE_RECALL_MIN", default=DEFAULT_CANDIDATE_RECALL_MIN)
    max_budget = positive_int_env("DEADMAN_CANDIDATE_RECALL_MAX", default=DEFAULT_CANDIDATE_RECALL_MAX)
    if max_budget < min_budget:
        max_budget = min_budget
    return min(max_budget, max(min_budget, math.ceil(source_count * per_source)))


def media_index_source_count(path: Path) -> int:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("media", "items", "videos", "episodes"):
            items = data.get(key)
            if isinstance(items, list):
                return len(items)
    return 0


def plan_for_node(config: ProducerConfig, node: str) -> dict[str, Any]:
    for item in command_plan(config):
        if item["node"] == node:
            return item
    raise KeyError(node)


def run_child_node(
    config: ProducerConfig,
    state: ProducerState,
    node: str,
    failure_code: str,
    *,
    success_status: ProducerRunStatus = "running",
) -> ProducerState:
    plan = plan_for_node(config, node)
    ok, detail, code_override, retryable = run_child(
        config=config,
        node=node,
        argv=plan["argv"],
        artifact_refs=plan["artifact_refs"],
    )
    if not ok:
        return failure_update(node, code_override or failure_code, detail, retryable=retryable)
    return node_update(node, status=success_status, node_status="pass", artifact_paths=artifact_plan(config))


def prepare_assets_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "prepare_assets", "asset_prepare_failed")

    return node


def register_media_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "register_media", "media_register_failed")

    return node


def build_timeline_windows_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "build_timeline_windows", "windows_build_failed")

    return node


def mine_candidates_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "mine_candidates", "candidate_mine_failed")

    return node


def cluster_candidates_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "cluster_candidates", "cluster_failed")

    return node


def read_json_optional(path: Path) -> dict[str, Any] | None:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def read_text_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def batch_manifest_path(config: ProducerConfig) -> Path:
    return config.run_dir / "llm_batch_manifest.json"


def empty_batch_manifest(config: ProducerConfig) -> dict[str, Any]:
    return {
        "schema_version": LLM_BATCH_MANIFEST_SCHEMA_VERSION,
        "run_id": config.run_id,
        "nodes": {},
    }


def read_batch_manifest(config: ProducerConfig) -> dict[str, Any]:
    path = batch_manifest_path(config)
    if not path.exists():
        return empty_batch_manifest(config)
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return empty_batch_manifest(config)
    if not isinstance(data, dict) or data.get("schema_version") != LLM_BATCH_MANIFEST_SCHEMA_VERSION:
        return empty_batch_manifest(config)
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        data["nodes"] = {}
    data["run_id"] = config.run_id
    return data


def update_batch_manifest(
    config: ProducerConfig,
    *,
    node: str,
    mode: str,
    chunk_count: int,
    chunk_strategy: str,
    chunk_artifacts: list[str],
    merge_artifact: str,
    merge_policy: dict[str, Any],
) -> None:
    manifest = read_batch_manifest(config)
    nodes = manifest.setdefault("nodes", {})
    if isinstance(nodes, dict):
        nodes[node] = {
            "mode": mode,
            "chunk_count": chunk_count,
            "chunk_strategy": chunk_strategy,
            "chunk_artifacts": chunk_artifacts,
            "merge_artifact": merge_artifact,
            "merge_policy": merge_policy,
        }
    write_json(batch_manifest_path(config), manifest)


def make_llm_provider(config: ProducerConfig, node: str):
    from Deadman.tools.ars.deadman_producer_graph_llm import (
        ArkDramaContextDraftProvider,
        ArkCandidateJudgeProvider,
        ArkMomentPackDraftProvider,
        ArkSemanticMinerProvider,
        LlmProviderError,
        MockDramaContextDraftProvider,
        MockCandidateJudgeProvider,
        MockMomentPackDraftProvider,
        MockSemanticMinerProvider,
    )

    mock_providers = {
        "llm_semantic_miner": MockSemanticMinerProvider,
        "llm_candidate_judge": MockCandidateJudgeProvider,
        "llm_drama_context_draft": MockDramaContextDraftProvider,
        "llm_moment_pack_draft": MockMomentPackDraftProvider,
    }
    ark_providers = {
        "llm_semantic_miner": ArkSemanticMinerProvider,
        "llm_candidate_judge": ArkCandidateJudgeProvider,
        "llm_drama_context_draft": ArkDramaContextDraftProvider,
        "llm_moment_pack_draft": ArkMomentPackDraftProvider,
    }
    if config.mock_provider:
        return mock_providers[node]()
    return ark_providers[node].from_env()


def llm_provider_identity(config: ProducerConfig, node: str) -> tuple[str, str]:
    if config.mock_provider:
        mock_models = {
            "llm_semantic_miner": "deadman-mock-semantic-miner-v0.1",
            "llm_candidate_judge": "deadman-mock-candidate-judge-v0.1",
            "llm_drama_context_draft": "deadman-mock-drama-context-draft-v0.1",
            "llm_moment_pack_draft": "deadman-mock-moment-pack-draft-v0.1",
        }
        return "mock", mock_models.get(node, "")
    return "ark", os.environ.get("ARK_MODEL_NAME") or os.environ.get("ARK_MODEL") or os.environ.get("ARK_ENDPOINT_ID") or ""


def llm_provider_max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("LLM_PROVIDER_MAX_ATTEMPTS", str(LLM_PROVIDER_MAX_ATTEMPTS_DEFAULT))))
    except ValueError:
        return LLM_PROVIDER_MAX_ATTEMPTS_DEFAULT


def llm_provider_retry_base_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("LLM_PROVIDER_RETRY_BASE_SECONDS", str(LLM_PROVIDER_RETRY_BASE_SECONDS_DEFAULT))))
    except ValueError:
        return LLM_PROVIDER_RETRY_BASE_SECONDS_DEFAULT


def llm_cache_mode() -> str:
    mode = os.environ.get("DEADMAN_LLM_CACHE_MODE", DEFAULT_LLM_CACHE_MODE).strip().lower()
    return mode if mode in {"off", "read", "write", "read_write", "refresh"} else DEFAULT_LLM_CACHE_MODE


def llm_cache_root() -> Path:
    return resolve_path(os.environ.get("DEADMAN_LLM_CACHE_ROOT") or DEFAULT_LLM_CACHE_ROOT)


def llm_chunk_concurrency() -> int:
    return positive_int_env("LLM_CHUNK_CONCURRENCY", default=DEFAULT_LLM_CHUNK_CONCURRENCY)


def semantic_miner_window_cap() -> int:
    return positive_int_env("LLM_SEMANTIC_MINER_WINDOW_CAP", default=DEFAULT_SEMANTIC_MINER_WINDOW_CAP)


def candidate_judge_batch_size() -> int:
    return positive_int_env("LLM_CANDIDATE_JUDGE_BATCH_SIZE", default=DEFAULT_CANDIDATE_JUDGE_BATCH_SIZE)


def semantic_miner_batch_mode() -> str:
    mode = os.environ.get("LLM_SEMANTIC_MINER_BATCH_MODE", "auto").strip().lower()
    return mode if mode in {"off", "auto", "on"} else "auto"


def cache_reads_enabled(mode: str) -> bool:
    return mode in {"read", "read_write"}


def cache_writes_enabled(mode: str) -> bool:
    return mode in {"write", "read_write", "refresh"}


def cache_entry_path(cache_key_hash: str) -> Path:
    return llm_cache_root() / f"{cache_key_hash.removeprefix('sha256:')}.json"


def sanitized_prompt_for_cache(prompt: dict[str, Any]) -> dict[str, Any]:
    run_id = str(prompt.get("run_id") or "")
    sanitized = normalize_cache_value(json.loads(canonical_json(prompt)), run_id)
    return sanitized if isinstance(sanitized, dict) else {}


def normalize_cache_value(value: Any, run_id: str) -> Any:
    if isinstance(value, dict):
        return {
            str(key): normalize_cache_value(child, run_id)
            for key, child in value.items()
            if str(key) not in LLM_CACHE_IGNORED_VALUE_KEYS
        }
    if isinstance(value, list):
        return [normalize_cache_value(child, run_id) for child in value]
    if isinstance(value, str):
        return normalize_cache_ref(value, run_id)
    return value


def normalize_cache_ref(value: str, run_id: str) -> str:
    normalized = re.sub(
        r"tmp/deadman_producer_runs/[^/]+/",
        "tmp/deadman_producer_runs/{run_id}/",
        value,
    )
    absolute_run_root = re.escape(str(REPO_ROOT / "tmp/deadman_producer_runs"))
    normalized = re.sub(
        rf"{absolute_run_root}/[^/]+/",
        f"{REPO_ROOT}/tmp/deadman_producer_runs/{{run_id}}/",
        normalized,
    )
    return normalized


def cache_artifact_hash(path: Path, ref: str, run_id: str) -> str:
    normalized_ref = normalize_cache_ref(ref, run_id)
    if normalized_ref == ref:
        return file_hash(path)
    try:
        data = read_json(path)
    except (json.JSONDecodeError, OSError):
        return file_hash(path)
    normalized = normalize_cache_value(data, run_id)
    return sha256_text(canonical_json(normalized))


def source_artifact_hashes(prompt: dict[str, Any]) -> dict[str, str]:
    refs: list[str] = []
    run_id = str(prompt.get("run_id") or "")

    def collect(value: Any) -> None:
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)

    collect(prompt.get("source_refs"))
    collect(prompt.get("source_candidate_ref"))
    hashes: dict[str, str] = {}
    for ref in sorted(set(refs)):
        path = resolve_path(ref)
        if path.exists() and path.is_file():
            normalized_ref = normalize_cache_ref(ref, run_id)
            hashes[sha256_text(normalized_ref).removeprefix("sha256:")] = cache_artifact_hash(path, ref, run_id)
    return hashes


def llm_cache_key_hash(
    *,
    node: str,
    chunk_id: str,
    provider: str,
    model: str,
    schema_path: Path,
    prompt: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    prompt_hash = sha256_text(canonical_json(sanitized_prompt_for_cache(prompt)))
    schema_hash = file_hash(schema_path)
    source_hashes = source_artifact_hashes(prompt)
    key_payload = {
        "node": node,
        "chunk_id": chunk_id,
        "provider": provider,
        "model": model,
        "temperature": configured_llm_temperature_for_cache(),
        "seed": os.environ.get("ARK_SEED", ""),
        "schema_hash": schema_hash,
        "prompt_hash": prompt_hash,
        "prompt_contract_version": LLM_PROMPT_CONTRACT_VERSION,
        "source_artifact_hashes": source_hashes,
        "normalizer_version": LLM_NORMALIZER_VERSION,
    }
    return sha256_text(canonical_json(key_payload)), key_payload


def configured_llm_temperature_for_cache() -> str:
    value = os.environ.get("ARK_TEMPERATURE")
    return value if value is not None else ""


def rebind_cached_llm_output(output: dict[str, Any], config: ProducerConfig) -> dict[str, Any]:
    rebound = json.loads(canonical_json(output))
    if isinstance(rebound, dict):
        rebound["run_id"] = config.run_id
        rebound["drama_id"] = config.drama_id
        rebound["drama_title"] = config.drama_title
    return rebound if isinstance(rebound, dict) else output


def read_llm_cache_entry(
    *,
    config: ProducerConfig,
    node: str,
    chunk_id: str,
    schema_path: Path,
    cache_key_hash: str,
    provider: str,
    model: str,
    artifact_ref: str,
) -> dict[str, Any] | None:
    path = cache_entry_path(cache_key_hash)
    if not path.exists():
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_miss",
            provider=provider,
            model=model,
            cache_key_hash=cache_key_hash,
            artifact_ref=artifact_ref,
        )
        return None
    try:
        entry = read_json(path)
    except json.JSONDecodeError as exc:
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_invalid",
            provider=provider,
            model=model,
            cache_key_hash=cache_key_hash,
            error=f"cache entry invalid JSON: {exc.msg}",
            artifact_ref=artifact_ref,
        )
        return None
    output = entry.get("output") if isinstance(entry, dict) else None
    if not isinstance(output, dict):
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_invalid",
            provider=provider,
            model=model,
            cache_key_hash=cache_key_hash,
            error="cache entry missing output object",
            artifact_ref=artifact_ref,
        )
        return None
    output = rebind_cached_llm_output(output, config)
    ok, message = validate_json_schema(output, schema_path)
    if not ok:
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_invalid",
            provider=provider,
            model=model,
            cache_key_hash=cache_key_hash,
            error=message,
            artifact_ref=artifact_ref,
        )
        return None
    append_provider_trace(
        config,
        node=node,
        chunk_id=chunk_id,
        status="cache_hit",
        provider=provider,
        model=model,
        cache_key_hash=cache_key_hash,
        artifact_ref=artifact_ref,
    )
    return output


def write_llm_cache_entry(
    *,
    node: str,
    chunk_id: str,
    cache_key_hash: str,
    key_payload: dict[str, Any],
    output: dict[str, Any],
) -> None:
    path = cache_entry_path(cache_key_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema_version": LLM_CACHE_ENTRY_SCHEMA_VERSION,
        "cache_key_hash": cache_key_hash,
        "created_at": now_iso(),
        "node": node,
        "chunk_id": chunk_id,
        "metadata": {
            key: value
            for key, value in key_payload.items()
            if key not in {"prompt_hash"}
        }
        | {"prompt_hash": key_payload.get("prompt_hash", "")},
        "output": output,
    }
    write_json(path, entry)


def is_retryable_provider_error(message: str) -> bool:
    lowered = message.lower()
    retry_markers = [
        "timeout",
        "timed out",
        "readtimeout",
        "connecttimeout",
        "write timeout",
        "status 429",
        "status 500",
        "status 502",
        "status 503",
        "status 504",
        "status 520",
        "status 521",
        "status 522",
        "status 523",
        "status 524",
    ]
    return any(marker in lowered for marker in retry_markers)


def run_llm_json_node(
    *,
    config: ProducerConfig,
    node: str,
    output_key: str,
    schema_path: Path,
    prompt: dict[str, Any],
    chunk_id: str = "single",
    output_path: Path | None = None,
    artifact_ref: str | None = None,
) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import LlmProviderError

    artifacts = artifact_plan(config)
    final_output_path = output_path or resolve_path(artifacts[output_key])
    final_artifact_ref = artifact_ref or repo_relative(final_output_path)
    schema = read_json(schema_path)
    mode = llm_cache_mode()
    provider_name, provider_model = llm_provider_identity(config, node)
    cache_key_hash = ""
    cache_key_payload: dict[str, Any] = {}
    if mode != "off":
        cache_key_hash, cache_key_payload = llm_cache_key_hash(
            node=node,
            chunk_id=chunk_id,
            provider=provider_name,
            model=provider_model,
            schema_path=schema_path,
            prompt=prompt,
        )
    if cache_reads_enabled(mode) and cache_key_hash:
        cached_output = read_llm_cache_entry(
            config=config,
            node=node,
            chunk_id=chunk_id,
            schema_path=schema_path,
            cache_key_hash=cache_key_hash,
            provider=provider_name,
            model=provider_model,
            artifact_ref=final_artifact_ref,
        )
        if cached_output is not None:
            write_json(final_output_path, cached_output)
            return True, ""
    elif mode in {"off", "refresh"}:
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_bypass",
            provider=provider_name,
            model=provider_model,
            cache_key_hash=cache_key_hash,
            artifact_ref=final_artifact_ref,
        )
    try:
        provider = make_llm_provider(config, node)
    except LlmProviderError as exc:
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="provider_unavailable",
            provider=provider_name,
            model=provider_model,
            error=str(exc),
            artifact_ref=final_artifact_ref,
        )
        return False, str(exc)
    max_attempts = llm_provider_max_attempts()
    output: dict[str, Any] | None = None
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        started_at = now_iso()
        try:
            output = provider.complete_json(prompt, schema)
            break
        except LlmProviderError as exc:
            last_error = str(exc)
            retryable = is_retryable_provider_error(last_error)
            if retryable and attempt < max_attempts:
                delay_seconds = llm_provider_retry_base_seconds() * (2 ** (attempt - 1))
                append_provider_trace(
                    config,
                    node=node,
                    status="provider_retry",
                    provider=provider.name,
                    model=provider.model,
                    chunk_id=chunk_id,
                    cache_key_hash=cache_key_hash,
                    started_at=started_at,
                    error=last_error,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_delay_seconds=delay_seconds,
                )
                if delay_seconds:
                    time.sleep(delay_seconds)
                continue
            append_provider_trace(
                config,
                node=node,
                status="provider_failed",
                provider=provider.name,
                model=provider.model,
                chunk_id=chunk_id,
                cache_key_hash=cache_key_hash,
                started_at=started_at,
                error=last_error,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            suffix = f" after {attempt} attempt(s)" if attempt > 1 else ""
            return False, f"{last_error}{suffix}"
    if output is None:
        return False, last_error or "provider returned no output"
    schema_ok, schema_message = validate_json_schema(output, schema_path)
    if not schema_ok:
        append_provider_trace(
            config,
            node=node,
            status="schema_invalid",
            provider=provider.name,
            model=provider.model,
            chunk_id=chunk_id,
            cache_key_hash=cache_key_hash,
            started_at=started_at,
            error=schema_message,
            artifact_ref=final_artifact_ref,
        )
        return False, f"{output_key} schema invalid: {schema_message}"
    write_json(final_output_path, output)
    if cache_writes_enabled(mode) and cache_key_hash:
        write_llm_cache_entry(
            node=node,
            chunk_id=chunk_id,
            cache_key_hash=cache_key_hash,
            key_payload=cache_key_payload,
            output=output,
        )
        append_provider_trace(
            config,
            node=node,
            chunk_id=chunk_id,
            status="cache_write",
            provider=provider.name,
            model=provider.model,
            cache_key_hash=cache_key_hash,
            artifact_ref=final_artifact_ref,
        )
    provider_metadata = output.get("provider") if isinstance(output, dict) else {}
    append_provider_trace(
        config,
        node=node,
        status="pass",
        provider=provider.name,
        model=provider.model,
        chunk_id=chunk_id,
        cache_key_hash=cache_key_hash,
        started_at=started_at,
        latency_ms=provider_metadata.get("latency_ms") if isinstance(provider_metadata, dict) else None,
        token_usage=provider_metadata.get("token_usage") if isinstance(provider_metadata, dict) else None,
        artifact_ref=final_artifact_ref,
    )
    return True, ""


def run_llm_semantic_miner(config: ProducerConfig) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import build_semantic_miner_prompt

    artifacts = artifact_plan(config)
    required_inputs = {
        "windows": resolve_path(artifacts["windows"]),
        "candidates_json": resolve_path(artifacts["candidates_json"]),
        "mechanism_buckets_json": resolve_path(artifacts["mechanism_buckets_json"]),
    }
    missing = [name for name, path in required_inputs.items() if not path.exists()]
    if missing:
        return False, f"semantic miner input missing: {', '.join(missing)}"
    window_data = read_json(required_inputs["windows"])
    candidate_data = read_json(required_inputs["candidates_json"])
    mechanism_data = read_json(required_inputs["mechanism_buckets_json"])
    field_minimum_text = read_text_optional(REPO_ROOT / "docs/Moment_Field_Minimum_Set_v0.3.md")
    windows = [window for window in window_data.get("windows", []) if isinstance(window, dict)] if isinstance(window_data, dict) else []
    batch_mode = semantic_miner_batch_mode()
    window_cap = semantic_miner_window_cap()
    if batch_mode == "on" or (batch_mode == "auto" and len(windows) > window_cap):
        return run_batched_llm_semantic_miner(
            config=config,
            source_refs={
                "windows": artifacts["windows"],
                "deterministic_candidates": artifacts["candidates_json"],
                "mechanism_buckets": artifacts["mechanism_buckets_json"],
                "field_minimum_set": repo_relative(REPO_ROOT / "docs/Moment_Field_Minimum_Set_v0.3.md"),
            },
            window_data=window_data if isinstance(window_data, dict) else {"windows": []},
            candidate_data=candidate_data if isinstance(candidate_data, dict) else {"candidates": []},
            mechanism_data=mechanism_data if isinstance(mechanism_data, dict) else {"mechanism_buckets": []},
            field_minimum_text=field_minimum_text,
            window_cap=window_cap,
        )
    prompt = build_semantic_miner_prompt(
        run_id=config.run_id,
        drama_id=config.drama_id,
        drama_title=config.drama_title,
        source_refs={
            "windows": artifacts["windows"],
            "deterministic_candidates": artifacts["candidates_json"],
            "mechanism_buckets": artifacts["mechanism_buckets_json"],
            "field_minimum_set": repo_relative(REPO_ROOT / "docs/Moment_Field_Minimum_Set_v0.3.md"),
        },
        window_data=window_data if isinstance(window_data, dict) else {"windows": []},
        candidate_data=candidate_data if isinstance(candidate_data, dict) else {"candidates": []},
        mechanism_data=mechanism_data if isinstance(mechanism_data, dict) else {"mechanism_buckets": []},
        field_minimum_text=field_minimum_text,
    )
    return run_llm_json_node(
        config=config,
        node="llm_semantic_miner",
        output_key="llm_semantic_candidates",
        schema_path=LLM_SEMANTIC_CANDIDATES_SCHEMA,
        prompt=prompt,
    )


def run_batched_llm_semantic_miner(
    *,
    config: ProducerConfig,
    source_refs: dict[str, str],
    window_data: dict[str, Any],
    candidate_data: dict[str, Any],
    mechanism_data: dict[str, Any],
    field_minimum_text: str,
    window_cap: int,
) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import build_semantic_miner_prompt

    artifacts = artifact_plan(config)
    chunk_dir = resolve_path(artifacts["llm_semantic_miner_chunks_dir"])
    reset_chunk_dir(chunk_dir)
    windows = [window for window in window_data.get("windows", []) if isinstance(window, dict)]
    candidates = [candidate for candidate in candidate_data.get("candidates", []) if isinstance(candidate, dict)]
    chunks = semantic_window_chunks(windows, window_cap)
    chunk_artifacts: list[str] = []

    def run_chunk(chunk_id: str, chunk_windows: list[dict[str, Any]]) -> tuple[bool, str, str]:
        chunk_candidates = candidates_for_windows(candidates, chunk_windows)
        chunk_prompt = build_semantic_miner_prompt(
            run_id=config.run_id,
            drama_id=config.drama_id,
            drama_title=config.drama_title,
            source_refs=source_refs | {"chunk_id": chunk_id},
            window_data={"windows": chunk_windows},
            candidate_data={"candidates": chunk_candidates},
            mechanism_data=mechanism_data,
            field_minimum_text=field_minimum_text,
        )
        output_path = chunk_dir / f"{chunk_id}.json"
        ok, message = run_llm_json_node(
            config=config,
            node="llm_semantic_miner",
            output_key="llm_semantic_candidates",
            schema_path=LLM_SEMANTIC_CANDIDATES_SCHEMA,
            prompt=chunk_prompt,
            chunk_id=chunk_id,
            output_path=output_path,
            artifact_ref=repo_relative(output_path),
        )
        return ok, message, repo_relative(output_path)

    results = run_chunk_jobs(chunks, run_chunk)
    chunk_strategy = "episode"
    for (chunk_id, _), (ok, message, artifact_ref) in zip(chunks, results, strict=True):
        if not ok:
            return False, f"chunk {chunk_id} failed: {message}"
        chunk_artifacts.append(artifact_ref)
    if any(chunk_id.startswith("semantic_window_") for chunk_id, _ in chunks):
        chunk_strategy = "window_range"
    output = merge_semantic_miner_chunks(config, source_refs, chunk_artifacts)
    ok, message = validate_json_schema(output, LLM_SEMANTIC_CANDIDATES_SCHEMA)
    if not ok:
        return False, f"merged llm_semantic_candidates schema invalid: {message}"
    write_json(resolve_path(artifacts["llm_semantic_candidates"]), output)
    update_batch_manifest(
        config,
        node="llm_semantic_miner",
        mode="batched",
        chunk_count=len(chunks),
        chunk_strategy=chunk_strategy,
        chunk_artifacts=chunk_artifacts,
        merge_artifact=artifacts["llm_semantic_candidates"],
        merge_policy={
            "window_cap": window_cap,
            "window_count": len(windows),
            "sort": "confidence_episode_start_candidate_id",
        },
    )
    return True, ""


def semantic_window_chunks(windows: list[dict[str, Any]], window_cap: int) -> list[tuple[str, list[dict[str, Any]]]]:
    by_episode: dict[str, list[dict[str, Any]]] = {}
    for window in windows:
        episode_id = str(window.get("episode_id") or "unknown_episode")
        by_episode.setdefault(episode_id, []).append(window)
    chunks: list[tuple[str, list[dict[str, Any]]]] = []
    for episode_id in sorted(by_episode):
        episode_windows = sorted(
            by_episode[episode_id],
            key=lambda item: (
                safe_int(item.get("start_ms"), default=0),
                str(item.get("window_id") or ""),
            ),
        )
        if len(episode_windows) <= window_cap:
            chunks.append((f"semantic_ep_{slug_id(episode_id)}", episode_windows))
            continue
        for start in range(0, len(episode_windows), window_cap):
            end = min(start + window_cap, len(episode_windows))
            chunks.append((f"semantic_window_{slug_id(episode_id)}_{start:04d}_{end:04d}", episode_windows[start:end]))
    return chunks


def slug_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value) or "unknown"


def candidates_for_windows(candidates: list[dict[str, Any]], windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    episode_ids = {str(window.get("episode_id") or "") for window in windows}
    window_ids = {str(window.get("window_id") or "") for window in windows}
    selected = [
        candidate
        for candidate in candidates
        if str(candidate.get("episode_id") or "") in episode_ids
        or str(candidate.get("window_id") or "") in window_ids
    ]
    return selected


def merge_semantic_miner_chunks(
    config: ProducerConfig,
    source_refs: dict[str, str],
    chunk_artifacts: list[str],
) -> dict[str, Any]:
    best_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    providers: list[dict[str, Any]] = []
    for artifact in chunk_artifacts:
        data = read_json(resolve_path(artifact))
        provider = data.get("provider") if isinstance(data, dict) else {}
        if isinstance(provider, dict):
            providers.append(provider)
        for candidate in data.get("candidates", []) if isinstance(data, dict) else []:
            if not isinstance(candidate, dict):
                continue
            if not str(candidate.get("evidence_excerpt") or "").strip():
                continue
            source_refs_value = candidate.get("source_refs")
            if not isinstance(source_refs_value, dict) or not source_refs_value:
                continue
            key = semantic_candidate_merge_key(candidate)
            current = best_by_key.get(key)
            if current is None:
                best_by_key[key] = candidate
                continue
            if safe_float(candidate.get("confidence"), default=0.0) > safe_float(current.get("confidence"), default=0.0):
                candidate["source_refs"] = merge_mapping(current.get("source_refs"), candidate.get("source_refs"))
                candidate["failure_modes"] = merge_string_lists(current.get("failure_modes"), candidate.get("failure_modes"))
                best_by_key[key] = candidate
            else:
                current["source_refs"] = merge_mapping(current.get("source_refs"), candidate.get("source_refs"))
                current["failure_modes"] = merge_string_lists(current.get("failure_modes"), candidate.get("failure_modes"))
    merged = sorted(best_by_key.values(), key=semantic_candidate_sort_key)
    return {
        "schema_version": "deadman_llm_semantic_candidates.v0.1",
        "task": "llm_semantic_miner",
        "run_id": config.run_id,
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "provider": aggregate_provider_metadata(providers),
        "source_refs": source_refs,
        "candidate_count": len(merged),
        "candidates": merged,
    }


def semantic_candidate_merge_key(candidate: dict[str, Any]) -> tuple[str, ...]:
    candidate_id = str(candidate.get("semantic_candidate_id") or "").strip()
    if candidate_id:
        return ("id", candidate_id)
    evidence_hash = sha256_text(str(candidate.get("evidence_excerpt") or "")).removeprefix("sha256:")
    return (
        "derived",
        str(candidate.get("episode_id") or ""),
        str(candidate.get("window_id") or ""),
        str(candidate.get("hook") or "").strip().lower(),
        evidence_hash,
    )


def semantic_candidate_sort_key(candidate: dict[str, Any]) -> tuple[float, str, int, str]:
    time_range = candidate.get("time_range_ms")
    start_ms = time_range[0] if isinstance(time_range, list) and time_range else 0
    return (
        -safe_float(candidate.get("confidence"), default=0.0),
        str(candidate.get("episode_id") or ""),
        safe_int(start_ms, default=0),
        str(candidate.get("semantic_candidate_id") or ""),
    )


def merge_mapping(left: Any, right: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(left, dict):
        merged.update(left)
    if isinstance(right, dict):
        merged.update(right)
    return merged


def merge_string_lists(left: Any, right: Any) -> list[str]:
    values: list[str] = []
    for source in (left, right):
        if isinstance(source, list):
            for item in source:
                if isinstance(item, str) and item not in values:
                    values.append(item)
    return values


def run_llm_candidate_judge(config: ProducerConfig) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import (
        build_candidate_judge_prompt,
    )

    artifacts = artifact_plan(config)
    candidate_path = resolve_path(artifacts["candidates_json"])
    try:
        candidate_data = read_json(candidate_path)
    except FileNotFoundError:
        return False, f"candidate artifact missing: {artifacts['candidates_json']}"
    except json.JSONDecodeError as exc:
        return False, f"candidate artifact invalid JSON: {exc.msg}"

    prompt = build_candidate_judge_prompt(
        run_id=config.run_id,
        drama_id=config.drama_id,
        drama_title=config.drama_title,
        source_candidate_ref=artifacts["candidates_json"],
        candidate_data=candidate_data,
        semantic_candidate_data=read_json_optional(resolve_path(artifacts["llm_semantic_candidates"])),
        source_window_data=read_json_optional(resolve_path(artifacts["windows"])),
    )
    candidates = [candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]
    batch_size = candidate_judge_batch_size()
    if len(candidates) > batch_size:
        return run_batched_llm_candidate_judge(config, prompt, batch_size)
    return run_llm_json_node(
        config=config,
        node="llm_candidate_judge",
        output_key="llm_candidate_judgment",
        schema_path=LLM_CANDIDATE_JUDGMENT_SCHEMA,
        prompt=prompt,
    )


def run_batched_llm_candidate_judge(
    config: ProducerConfig,
    prompt: dict[str, Any],
    batch_size: int,
) -> tuple[bool, str]:
    artifacts = artifact_plan(config)
    candidates = [candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]
    chunk_dir = resolve_path(artifacts["llm_candidate_judge_chunks_dir"])
    reset_chunk_dir(chunk_dir)
    chunks = [
        (f"judge_candidates_{start:04d}_{min(start + batch_size, len(candidates)):04d}", candidates[start : start + batch_size])
        for start in range(0, len(candidates), batch_size)
    ]
    chunk_artifacts: list[str] = []

    def run_chunk(chunk_id: str, chunk_candidates: list[dict[str, Any]]) -> tuple[bool, str, str]:
        chunk_prompt = json.loads(canonical_json(prompt))
        chunk_prompt["candidates"] = chunk_candidates
        parent_limit = safe_int(prompt.get("shortlist_limit"), default=len(chunk_candidates))
        chunk_prompt["shortlist_limit"] = min(len(chunk_candidates), max(1, parent_limit))
        selection_policy = chunk_prompt.get("selection_policy") if isinstance(chunk_prompt.get("selection_policy"), dict) else {}
        selection_policy = dict(selection_policy)
        selection_policy.update(
            {
                "batch_mode": "chunk",
                "chunk_id": chunk_id,
                "chunk_candidate_count": len(chunk_candidates),
                "parent_shortlist_target": parent_limit,
            }
        )
        chunk_prompt["selection_policy"] = selection_policy
        output_path = chunk_dir / f"{chunk_id}.json"
        ok, message = run_llm_json_node(
            config=config,
            node="llm_candidate_judge",
            output_key="llm_candidate_judgment",
            schema_path=LLM_CANDIDATE_JUDGMENT_SCHEMA,
            prompt=chunk_prompt,
            chunk_id=chunk_id,
            output_path=output_path,
            artifact_ref=repo_relative(output_path),
        )
        return ok, message, repo_relative(output_path)

    results = run_chunk_jobs([(chunk_id, chunk_candidates) for chunk_id, chunk_candidates in chunks], run_chunk)
    for (chunk_id, _), (ok, message, artifact_ref) in zip(chunks, results, strict=True):
        if not ok:
            return False, f"chunk {chunk_id} failed: {message}"
        chunk_artifacts.append(artifact_ref)

    output = merge_candidate_judge_chunks(config, prompt, chunk_artifacts)
    ok, message = validate_json_schema(output, LLM_CANDIDATE_JUDGMENT_SCHEMA)
    if not ok:
        return False, f"merged llm_candidate_judgment schema invalid: {message}"
    write_json(resolve_path(artifacts["llm_candidate_judgment"]), output)
    update_batch_manifest(
        config,
        node="llm_candidate_judge",
        mode="batched",
        chunk_count=len(chunks),
        chunk_strategy="candidate_pool",
        chunk_artifacts=chunk_artifacts,
        merge_artifact=artifacts["llm_candidate_judgment"],
        merge_policy={
            "batch_size": batch_size,
            "input_candidate_count": len(candidates),
            "shortlist_target": safe_int(prompt.get("shortlist_limit"), default=0),
            "sort": "recommend_first_confidence_rank_source_order_candidate_id",
        },
    )
    return True, ""


def reset_chunk_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.glob("*.json"):
        child.unlink()


def run_chunk_jobs(
    jobs: list[tuple[str, list[dict[str, Any]]]],
    runner,
) -> list[tuple[bool, str, str]]:
    concurrency = llm_chunk_concurrency()
    if concurrency <= 1 or len(jobs) <= 1:
        return [runner(chunk_id, items) for chunk_id, items in jobs]
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results_by_index: dict[int, tuple[bool, str, str]] = {}
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_index = {
            executor.submit(runner, chunk_id, items): index
            for index, (chunk_id, items) in enumerate(jobs)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results_by_index[index] = future.result()
            except Exception as exc:  # noqa: BLE001 - propagate as node failure detail.
                results_by_index[index] = (False, f"chunk worker failed: {exc}", "")
    return [results_by_index[index] for index in range(len(jobs))]


def merge_candidate_judge_chunks(
    config: ProducerConfig,
    prompt: dict[str, Any],
    chunk_artifacts: list[str],
) -> dict[str, Any]:
    input_candidates = [candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]
    candidate_by_id = {str(candidate.get("candidate_id") or ""): candidate for candidate in input_candidates}
    source_order = {candidate_id: index for index, candidate_id in enumerate(candidate_by_id)}
    best_by_id: dict[str, dict[str, Any]] = {}
    providers: list[dict[str, Any]] = []
    for artifact in chunk_artifacts:
        data = read_json(resolve_path(artifact))
        provider = data.get("provider") if isinstance(data, dict) else {}
        if isinstance(provider, dict):
            providers.append(provider)
        for judgment in data.get("judgments", []) if isinstance(data, dict) else []:
            if not isinstance(judgment, dict):
                continue
            candidate_id = str(judgment.get("candidate_id") or "")
            if candidate_id not in candidate_by_id:
                continue
            current = best_by_id.get(candidate_id)
            if current is None or judgment_sort_key(judgment, candidate_by_id, source_order) < judgment_sort_key(
                current,
                candidate_by_id,
                source_order,
            ):
                best_by_id[candidate_id] = judgment
    merged = sorted(
        best_by_id.values(),
        key=lambda judgment: judgment_sort_key(judgment, candidate_by_id, source_order),
    )
    shortlist_target = safe_int(prompt.get("shortlist_limit"), default=len(merged))
    final_judgments = merged[:shortlist_target]
    selection_policy = prompt.get("selection_policy") if isinstance(prompt.get("selection_policy"), dict) else {}
    shortlist_policy = dict(selection_policy)
    shortlist_policy["batch_policy"] = {
        "mode": "batched",
        "chunk_count": len(chunk_artifacts),
        "chunk_artifacts": chunk_artifacts,
        "input_candidate_count": len(input_candidates),
        "merged_candidate_count": len(merged),
        "shortlist_target": shortlist_target,
    }
    return {
        "schema_version": "deadman_llm_candidate_judgment.v0.1",
        "task": "llm_candidate_judge",
        "run_id": config.run_id,
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "provider": aggregate_provider_metadata(providers),
        "source_candidate_ref": str(prompt.get("source_candidate_ref") or ""),
        "input_candidate_count": len(input_candidates),
        "shortlist_policy": shortlist_policy,
        "judgment_count": len(final_judgments),
        "decisions_summary": summarize_judgment_decisions(final_judgments),
        "judgments": final_judgments,
    }


def judgment_sort_key(
    judgment: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
    source_order: dict[str, int],
) -> tuple[int, float, int, int, str]:
    candidate_id = str(judgment.get("candidate_id") or "")
    decision = str(judgment.get("decision") or "")
    decision_priority = {"recommend": 0, "keep_for_review": 1, "reject": 2}.get(decision, 3)
    confidence = safe_float(judgment.get("confidence"), default=0.0)
    candidate = candidate_by_id.get(candidate_id, {})
    rank = safe_int(candidate.get("rank"), default=999999)
    order = source_order.get(candidate_id, 999999)
    return (decision_priority, -confidence, rank, order, candidate_id)


def aggregate_provider_metadata(providers: list[dict[str, Any]]) -> dict[str, Any]:
    if not providers:
        return {
            "name": "merged",
            "model": "merged",
            "mock_provider": True,
            "latency_ms": 0,
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }
    first = providers[0]
    token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    latency_ms = 0
    mock_provider = True
    for provider in providers:
        latency_ms += safe_int(provider.get("latency_ms"), default=0)
        mock_provider = mock_provider and bool(provider.get("mock_provider"))
        usage = provider.get("token_usage")
        if isinstance(usage, dict):
            for key in token_usage:
                token_usage[key] += safe_int(usage.get(key), default=0)
    return {
        "name": str(first.get("name") or "merged"),
        "model": str(first.get("model") or "merged"),
        "mock_provider": mock_provider,
        "latency_ms": latency_ms,
        "token_usage": token_usage,
    }


def summarize_judgment_decisions(judgments: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"recommend": 0, "keep_for_review": 0, "reject": 0}
    for judgment in judgments:
        decision = str(judgment.get("decision") or "")
        if decision in summary:
            summary[decision] += 1
    return summary


def run_llm_drama_context_draft(config: ProducerConfig) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import build_drama_context_draft_prompt

    artifacts = artifact_plan(config)
    reviewed_demo_nodes = read_json_optional(config.reviewed_demo_nodes)
    reviewed_candidates = read_json_optional(config.reviewed_candidates)
    if reviewed_demo_nodes is None:
        return False, f"reviewed demo nodes missing or invalid: {repo_relative(config.reviewed_demo_nodes)}"
    if reviewed_candidates is None:
        return False, f"reviewed candidates missing or invalid: {repo_relative(config.reviewed_candidates)}"
    prompt = build_drama_context_draft_prompt(
        run_id=config.run_id,
        drama_id=config.drama_id,
        drama_title=config.drama_title,
        source_refs={
            "current_context": artifacts["context_pack"],
            "reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
            "reviewed_candidates": repo_relative(config.reviewed_candidates),
            "llm_semantic_candidates": artifacts["llm_semantic_candidates"],
            "llm_candidate_judgment": artifacts["llm_candidate_judgment"],
        },
        current_context=read_json_optional(resolve_path(artifacts["context_pack"])) or {},
        reviewed_demo_nodes=reviewed_demo_nodes,
        reviewed_candidates=reviewed_candidates,
        semantic_candidates=read_json_optional(resolve_path(artifacts["llm_semantic_candidates"])),
        candidate_judgment=read_json_optional(resolve_path(artifacts["llm_candidate_judgment"])),
    )
    return run_llm_json_node(
        config=config,
        node="llm_drama_context_draft",
        output_key="llm_drama_context_draft",
        schema_path=LLM_DRAMA_CONTEXT_DRAFT_SCHEMA,
        prompt=prompt,
    )


def run_llm_moment_pack_draft(config: ProducerConfig) -> tuple[bool, str]:
    from Deadman.tools.ars.deadman_producer_graph_llm import build_moment_pack_draft_prompt

    artifacts = artifact_plan(config)
    reviewed_demo_nodes = read_json_optional(config.reviewed_demo_nodes)
    reviewed_candidates = read_json_optional(config.reviewed_candidates)
    if reviewed_demo_nodes is None:
        return False, f"reviewed demo nodes missing or invalid: {repo_relative(config.reviewed_demo_nodes)}"
    if reviewed_candidates is None:
        return False, f"reviewed candidates missing or invalid: {repo_relative(config.reviewed_candidates)}"
    prompt = build_moment_pack_draft_prompt(
        run_id=config.run_id,
        drama_id=config.drama_id,
        drama_title=config.drama_title,
        source_refs={
            "current_context": artifacts["context_pack"],
            "reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
            "reviewed_candidates": repo_relative(config.reviewed_candidates),
            "llm_drama_context_draft": artifacts["llm_drama_context_draft"],
        },
        current_context=read_json_optional(resolve_path(artifacts["context_pack"])) or {},
        reviewed_demo_nodes=reviewed_demo_nodes,
        reviewed_candidates=reviewed_candidates,
        drama_context_draft=read_json_optional(resolve_path(artifacts["llm_drama_context_draft"])),
    )
    return run_llm_json_node(
        config=config,
        node="llm_moment_pack_draft",
        output_key="llm_moment_pack_drafts",
        schema_path=LLM_MOMENT_PACK_DRAFTS_SCHEMA,
        prompt=prompt,
    )


def append_provider_trace(
    config: ProducerConfig,
    *,
    node: str,
    status: str,
    provider: str,
    model: str = "",
    chunk_id: str = "single",
    cache_key_hash: str = "",
    started_at: str | None = None,
    latency_ms: Any = None,
    token_usage: Any = None,
    artifact_ref: str = "",
    error: str = "",
    attempt: int | None = None,
    max_attempts: int | None = None,
    retry_delay_seconds: float | None = None,
) -> None:
    if not config.enable_llm:
        return
    artifacts = artifact_plan(config)
    path = resolve_path(artifacts["provider_trace_redacted"])
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": config.run_id,
        "node": node,
        "chunk_id": chunk_id,
        "status": status,
        "provider": provider,
        "model": model,
        "cache_key_hash": cache_key_hash,
        "started_at": started_at,
        "recorded_at": now_iso(),
        "latency_ms": latency_ms,
        "token_usage": token_usage,
        "artifact_ref": artifact_ref,
        "error": error[:500] if error else "",
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_delay_seconds": retry_delay_seconds,
        "redaction": "provider request/response bodies and API keys are not recorded",
    }
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def llm_node_update(config: ProducerConfig, node: str, runner) -> ProducerState:
    ok, message = runner(config)
    if not ok:
        if config.allow_llm_skip:
            return node_update(
                node,
                status="running",
                node_status="skipped_by_config",
                artifact_paths=artifact_plan(config),
            )
        update = failure_update(node, f"{node}_failed", message)
        update["errors"][0]["retryable"] = is_retryable_provider_error(message)
        update["status"] = "llm_failed"
        return update
    return node_update(
        node,
        status="running",
        node_status="pass",
        artifact_paths=artifact_plan(config),
    )


def llm_semantic_miner_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return llm_node_update(config, "llm_semantic_miner", run_llm_semantic_miner)

    return node


def llm_candidate_judge_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return llm_node_update(config, "llm_candidate_judge", run_llm_candidate_judge)

    return node


def llm_drama_context_draft_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return llm_node_update(config, "llm_drama_context_draft", run_llm_drama_context_draft)

    return node


def llm_moment_pack_draft_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return llm_node_update(config, "llm_moment_pack_draft", run_llm_moment_pack_draft)

    return node


def stable_review_payload(config: ProducerConfig) -> tuple[dict[str, Any], str]:
    artifacts = artifact_plan(config)
    llm_semantic_path = resolve_path(artifacts["llm_semantic_candidates"]) if "llm_semantic_candidates" in artifacts else None
    llm_judgment_path = resolve_path(artifacts["llm_candidate_judgment"]) if "llm_candidate_judgment" in artifacts else None
    llm_batch_manifest_path = resolve_path(artifacts["llm_batch_manifest"]) if "llm_batch_manifest" in artifacts else None
    hash_inputs = {
        "run_id": config.run_id,
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "graph_mode": graph_mode(config),
        "node_order_to_gate": graph_node_order(config)[: graph_node_order(config).index("human_review_gate") + 1],
        "candidate_table": {
            "path": artifacts["candidates_json"],
            "content_hash": file_hash(resolve_path(artifacts["candidates_json"])),
        },
        "mechanism_buckets": {
            "path": artifacts["mechanism_buckets_json"],
            "content_hash": file_hash(resolve_path(artifacts["mechanism_buckets_json"])),
        },
        "field_hypotheses": {
            "path": artifacts["field_hypotheses_md"],
            "content_hash": file_hash(resolve_path(artifacts["field_hypotheses_md"])),
        },
        "deterministic_candidate_count": candidate_count(resolve_path(artifacts["candidates_json"])),
        "review_policy_version": REVIEW_POLICY_VERSION,
        "expected_reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
        "expected_reviewed_candidates": repo_relative(config.reviewed_candidates),
    }
    if llm_semantic_path and llm_semantic_path.exists():
        hash_inputs["llm_semantic_candidates"] = {
            "path": artifacts["llm_semantic_candidates"],
            "content_hash": file_hash(llm_semantic_path),
        }
        hash_inputs["llm_semantic_summary"] = llm_semantic_summary(llm_semantic_path)
    if llm_judgment_path and llm_judgment_path.exists():
        hash_inputs["llm_candidate_judgment"] = {
            "path": artifacts["llm_candidate_judgment"],
            "content_hash": file_hash(llm_judgment_path),
        }
        hash_inputs["llm_judgment_summary"] = llm_judgment_summary(llm_judgment_path)
        hash_inputs["llm_candidate_shortlist"] = llm_candidate_shortlist(llm_judgment_path)
    if llm_batch_manifest_path and llm_batch_manifest_path.exists():
        hash_inputs["llm_batch_manifest"] = {
            "path": artifacts["llm_batch_manifest"],
            "content_hash": file_hash(llm_batch_manifest_path),
        }
    request_hash = sha256_text(canonical_json(hash_inputs))
    payload = {
        "schema_version": "deadman_studio_review_request.v0.1",
        "request_hash": request_hash,
        "hash_inputs": hash_inputs,
        "run_id": config.run_id,
        "drama_id": config.drama_id,
        "drama_title": config.drama_title,
        "status": "waiting_for_review",
        "candidate_table_paths": {
            "candidates_json": artifacts["candidates_json"],
            "candidates_md": artifacts["candidates_md"],
            "mechanism_buckets_json": artifacts["mechanism_buckets_json"],
            "mechanism_buckets_md": artifacts["mechanism_buckets_md"],
            "field_hypotheses_md": artifacts["field_hypotheses_md"],
        },
        "expected_reviewed_paths": {
            "reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
            "reviewed_candidates": repo_relative(config.reviewed_candidates),
        },
        "human_instructions": [
            "Treat deterministic candidates as the audit pool; use the LLM shortlist first when present.",
            "Approve only reviewed candidates that are safe for runtime pack promotion.",
            "Reject the run if candidate evidence, hook tone, or source refs are not reviewable.",
            "Resume with --review-decision approve after reviewed artifacts exist, or --review-decision reject.",
        ],
    }
    llm_artifact_paths = {}
    if llm_semantic_path and llm_semantic_path.exists():
        llm_artifact_paths["llm_semantic_candidates"] = artifacts["llm_semantic_candidates"]
    if llm_judgment_path and llm_judgment_path.exists():
        llm_artifact_paths["llm_candidate_judgment"] = artifacts["llm_candidate_judgment"]
    if llm_batch_manifest_path and llm_batch_manifest_path.exists():
        llm_artifact_paths["llm_batch_manifest"] = artifacts["llm_batch_manifest"]
    if llm_artifact_paths:
        payload["llm_artifact_paths"] = llm_artifact_paths
    if llm_judgment_path and llm_judgment_path.exists():
        payload["llm_candidate_shortlist"] = llm_candidate_shortlist(llm_judgment_path)
    return payload, request_hash


def candidate_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return 0
    candidates = data.get("candidates") if isinstance(data, dict) else None
    return len(candidates) if isinstance(candidates, list) else 0


def llm_judgment_summary(path: Path) -> dict[str, int]:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    summary = data.get("decisions_summary") if isinstance(data, dict) else None
    if not isinstance(summary, dict):
        return {}
    return {str(key): int(value) for key, value in summary.items() if isinstance(value, int)}


def llm_candidate_shortlist(path: Path) -> dict[str, Any]:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "input_candidate_count": 0,
            "judgment_count": 0,
            "candidate_ids": [],
            "recommended_candidate_ids": [],
            "keep_for_review_candidate_ids": [],
            "shortlist_policy": {},
        }
    judgments = data.get("judgments") if isinstance(data, dict) else None
    if not isinstance(judgments, list):
        judgments = []
    candidate_ids: list[str] = []
    recommended_candidate_ids: list[str] = []
    keep_for_review_candidate_ids: list[str] = []
    for judgment in judgments:
        if not isinstance(judgment, dict):
            continue
        candidate_id = str(judgment.get("candidate_id") or "")
        if not candidate_id:
            continue
        candidate_ids.append(candidate_id)
        decision = str(judgment.get("decision") or "")
        if decision == "recommend":
            recommended_candidate_ids.append(candidate_id)
        elif decision == "keep_for_review":
            keep_for_review_candidate_ids.append(candidate_id)
    shortlist_policy = data.get("shortlist_policy") if isinstance(data, dict) else {}
    if not isinstance(shortlist_policy, dict):
        shortlist_policy = {}
    input_candidate_count = data.get("input_candidate_count") if isinstance(data, dict) else 0
    if not isinstance(input_candidate_count, int):
        input_candidate_count = 0
    return {
        "input_candidate_count": input_candidate_count,
        "judgment_count": len(candidate_ids),
        "candidate_ids": candidate_ids,
        "recommended_candidate_ids": recommended_candidate_ids,
        "keep_for_review_candidate_ids": keep_for_review_candidate_ids,
        "shortlist_policy": shortlist_policy,
    }


def llm_semantic_summary(path: Path) -> dict[str, Any]:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"candidate_count": 0, "candidate_ids": [], "origins": {}}
    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list):
        return {"candidate_count": 0, "candidate_ids": [], "origins": {}}
    candidate_ids: list[str] = []
    origins: dict[str, int] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("semantic_candidate_id") or "")
        if candidate_id:
            candidate_ids.append(candidate_id)
        origin = str(candidate.get("origin") or "unknown")
        origins[origin] = origins.get(origin, 0) + 1
    return {
        "candidate_count": len(candidates),
        "candidate_ids": sorted(candidate_ids),
        "origins": origins,
    }


def llm_candidate_count(path: Path, *, key: str) -> int:
    try:
        data = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    value = data.get(key) if isinstance(data, dict) else None
    return len(value) if isinstance(value, list) else 0


def write_or_verify_review_request(config: ProducerConfig, payload: dict[str, Any], request_hash: str) -> tuple[bool, str]:
    schema_ok, schema_message = validate_json_schema(payload, REVIEW_REQUEST_SCHEMA)
    if not schema_ok:
        return False, f"review request schema invalid: {schema_message}"
    path = review_request_path(config)
    if not path.exists():
        write_json(path, payload)
        return True, ""
    try:
        existing = read_json(path)
    except json.JSONDecodeError as exc:
        return False, f"existing review_request.json is invalid JSON: {exc.msg}"
    existing_hash = existing.get("request_hash")
    if existing_hash != request_hash:
        changed_keys = changed_hash_input_keys(existing, payload)
        suffix = f"; changed_hash_input_keys={', '.join(changed_keys)}" if changed_keys else ""
        return False, f"review request drift: existing={existing_hash}, recomputed={request_hash}{suffix}"
    return True, ""


def changed_hash_input_keys(existing: Mapping[str, Any], proposed: Mapping[str, Any]) -> list[str]:
    existing_inputs = existing.get("hash_inputs")
    proposed_inputs = proposed.get("hash_inputs")
    if not isinstance(existing_inputs, dict) or not isinstance(proposed_inputs, dict):
        return []
    keys = sorted(set(existing_inputs) | set(proposed_inputs))
    return [key for key in keys if existing_inputs.get(key) != proposed_inputs.get(key)]


def prepare_human_review_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        payload, request_hash = stable_review_payload(config)
        ok, message = write_or_verify_review_request(config, payload, request_hash)
        if not ok:
            return failure_update("prepare_human_review", "review_request_drift", message)
        update = node_update(
            "prepare_human_review",
            status="waiting_for_review",
            node_status="pass",
            artifact_paths={"review_request": repo_relative(review_request_path(config))},
            review_decision="pending",
        )
        update["current_node"] = "human_review_gate"
        update["node_statuses"] = {
            "prepare_human_review": "pass",
            "human_review_gate": "waiting_for_review",
        }
        return update

    return node


def human_review_gate_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        from langgraph.types import interrupt

        payload, request_hash = stable_review_payload(config)
        ok, message = write_or_verify_review_request(config, payload, request_hash)
        if not ok:
            return failure_update("human_review_gate", "review_request_drift", message)
        resume_payload = interrupt(
            {
                "status": "waiting_for_review",
                "review_request": repo_relative(review_request_path(config)),
                "request_hash": request_hash,
                "expected_reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
                "expected_reviewed_candidates": repo_relative(config.reviewed_candidates),
            }
        )
        if not isinstance(resume_payload, dict):
            return failure_update("human_review_gate", "review_resume_invalid", "resume payload must be an object")
        decision = str(resume_payload.get("decision") or "").strip()
        reviewer_note = str(resume_payload.get("reviewer_note") or "")
        if decision == "reject":
            return node_update(
                "human_review_gate",
                status="rejected_by_human_review",
                node_status="pass",
                review_decision="reject",
                reviewer_note=reviewer_note,
            )
        if decision != "approve":
            return failure_update("human_review_gate", "review_resume_invalid", "decision must be approve or reject")
        reviewed_demo_nodes = resolve_path(str(resume_payload.get("reviewed_demo_nodes") or config.reviewed_demo_nodes))
        reviewed_candidates = resolve_path(str(resume_payload.get("reviewed_candidates") or config.reviewed_candidates))
        if not reviewed_demo_nodes.exists():
            return failure_update(
                "human_review_gate",
                "review_artifact_missing",
                f"reviewed demo nodes missing: {repo_relative(reviewed_demo_nodes)}",
            )
        if not reviewed_candidates.exists():
            return failure_update(
                "human_review_gate",
                "review_artifact_missing",
                f"reviewed candidates missing: {repo_relative(reviewed_candidates)}",
            )
        return node_update(
            "human_review_gate",
            status="publishing",
            node_status="pass",
            review_decision="approve",
            reviewer_note=reviewer_note,
            artifact_paths={
                "reviewed_demo_nodes": repo_relative(reviewed_demo_nodes),
                "reviewed_candidates": repo_relative(reviewed_candidates),
            },
        )

    return node


def build_drama_context_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "build_drama_context", "context_build_failed", success_status="publishing")

    return node


def publish_p0_bridge_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        return run_child_node(config, state, "publish_p0_bridge", "publish_failed", success_status="publishing")

    return node


def validate_producer_bridge_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        plan = plan_for_node(config, "validate_producer_bridge")
        ok, detail, code_override, retryable = run_child(
            config=config,
            node="validate_producer_bridge",
            argv=plan["argv"],
            artifact_refs=plan["artifact_refs"],
        )
        if not ok:
            update = failure_update(
                "validate_producer_bridge",
                code_override or "validation_failed",
                detail,
                retryable=retryable,
            )
            update["status"] = "validation_failed"
            update["validation_result"] = "failed"
            return update
        return node_update(
            "validate_producer_bridge",
            status="publishing",
            node_status="pass",
            artifact_paths=artifact_plan(config),
            validation_result="pass",
        )

    return node


def final_report_node(config: ProducerConfig):
    def node(state: ProducerState) -> ProducerState:
        final_status: ProducerRunStatus
        if state.get("status") in {"failed", "validation_failed", "rejected_by_human_review", "llm_failed"}:
            final_status = cast(ProducerRunStatus, state["status"])
        elif state.get("validation_result") == "pass":
            final_status = "pass"
        else:
            final_status = "failed"

        lines = [
            "# Deadman Studio Producer Run",
            "",
            f"- run_id: `{config.run_id}`",
            f"- thread_id: `{config.thread_id}`",
            f"- status: `{final_status}`",
            f"- drama: `{config.drama_id}` / {config.drama_title}",
            f"- review_decision: `{state.get('review_decision', 'pending')}`",
            f"- validation_result: `{state.get('validation_result', 'not_run')}`",
            "",
            "## Nodes",
            "",
        ]
        report_node_statuses = dict(state.get("node_statuses") or {})
        report_node_statuses["final_report"] = "pass"
        for node_name in graph_node_order(config):
            node_status = report_node_statuses.get(node_name, "planned")
            lines.append(f"- `{node_name}`: `{node_status}`")
        lines.extend(["", "## LLM", ""])
        if config.enable_llm:
            lines.append(f"- enabled: `true`")
            lines.append(f"- provider: `{configured_llm_provider(config)}`")
            lines.append(f"- model: `{configured_llm_model(config)}`")
            for llm_node_name, artifact_key in [
                ("llm_semantic_miner", "llm_semantic_candidates"),
                ("llm_candidate_judge", "llm_candidate_judgment"),
                ("llm_drama_context_draft", "llm_drama_context_draft"),
                ("llm_moment_pack_draft", "llm_moment_pack_drafts"),
            ]:
                lines.append(f"- {llm_node_name}: `{report_node_statuses.get(llm_node_name, 'planned')}`")
                lines.append(f"- {artifact_key}: `{(state.get('artifact_paths') or {}).get(artifact_key, '')}`")
            lines.append(
                f"- redacted_trace: `{(state.get('artifact_paths') or {}).get('provider_trace_redacted', '')}`"
            )
        else:
            lines.append("- enabled: `false`")
        lines.extend(["", "## Artifacts", ""])
        for key, value in sorted((state.get("artifact_paths") or artifact_plan(config)).items()):
            lines.append(f"- `{key}`: `{value}`")
        if state.get("errors"):
            lines.extend(["", "## Errors", ""])
            for error in state["errors"]:
                lines.append(f"- `{error.get('node')}` / `{error.get('code')}`: {error.get('message')}")
        lines.append("")
        final_report_path(config).parent.mkdir(parents=True, exist_ok=True)
        final_report_path(config).write_text("\n".join(lines), encoding="utf-8")
        update = node_update(
            "final_report",
            status=final_status,
            node_status="pass",
            artifact_paths={"final_report": repo_relative(final_report_path(config))},
        )
        if final_status == "pass":
            update["validation_result"] = "pass"
        return update

    return node


def route_after_review(state: ProducerState, next_node: str = "build_drama_context") -> str:
    status = state.get("status")
    if status == "rejected_by_human_review":
        return "final_report"
    if status == "failed":
        return "final_report"
    return next_node


def route_after_node(state: ProducerState, next_node: str) -> str:
    if state.get("status") in {"failed", "validation_failed", "rejected_by_human_review", "llm_failed"}:
        return "final_report"
    return next_node


def build_graph(config: ProducerConfig):
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(ProducerState)
    builder.add_node("prepare_assets", prepare_assets_node(config))
    builder.add_node("register_media", register_media_node(config))
    builder.add_node("build_timeline_windows", build_timeline_windows_node(config))
    builder.add_node("mine_candidates", mine_candidates_node(config))
    builder.add_node("cluster_candidates", cluster_candidates_node(config))
    if config.enable_llm:
        builder.add_node("llm_semantic_miner", llm_semantic_miner_node(config))
        builder.add_node("llm_candidate_judge", llm_candidate_judge_node(config))
        builder.add_node("llm_drama_context_draft", llm_drama_context_draft_node(config))
        builder.add_node("llm_moment_pack_draft", llm_moment_pack_draft_node(config))
    builder.add_node("prepare_human_review", prepare_human_review_node(config))
    builder.add_node("human_review_gate", human_review_gate_node(config))
    builder.add_node("build_drama_context", build_drama_context_node(config))
    builder.add_node("publish_p0_bridge", publish_p0_bridge_node(config))
    builder.add_node("validate_producer_bridge", validate_producer_bridge_node(config))
    builder.add_node("final_report", final_report_node(config))

    builder.add_edge(START, "prepare_assets")
    builder.add_conditional_edges("prepare_assets", lambda state: route_after_node(state, "register_media"))
    builder.add_conditional_edges("register_media", lambda state: route_after_node(state, "build_timeline_windows"))
    builder.add_conditional_edges("build_timeline_windows", lambda state: route_after_node(state, "mine_candidates"))
    next_after_mine = "llm_semantic_miner" if config.enable_llm else "cluster_candidates"
    builder.add_conditional_edges("mine_candidates", lambda state: route_after_node(state, next_after_mine))
    if config.enable_llm:
        builder.add_conditional_edges("llm_semantic_miner", lambda state: route_after_node(state, "cluster_candidates"))
    next_after_cluster = "llm_candidate_judge" if config.enable_llm else "prepare_human_review"
    builder.add_conditional_edges("cluster_candidates", lambda state: route_after_node(state, next_after_cluster))
    if config.enable_llm:
        builder.add_conditional_edges("llm_candidate_judge", lambda state: route_after_node(state, "prepare_human_review"))
    builder.add_conditional_edges("prepare_human_review", lambda state: route_after_node(state, "human_review_gate"))
    next_after_review = "llm_drama_context_draft" if config.enable_llm else "build_drama_context"
    builder.add_conditional_edges("human_review_gate", lambda state: route_after_review(state, next_after_review))
    if config.enable_llm:
        builder.add_conditional_edges(
            "llm_drama_context_draft",
            lambda state: route_after_node(state, "llm_moment_pack_draft"),
        )
        builder.add_conditional_edges("llm_moment_pack_draft", lambda state: route_after_node(state, "build_drama_context"))
    builder.add_conditional_edges("build_drama_context", lambda state: route_after_node(state, "publish_p0_bridge"))
    builder.add_conditional_edges("publish_p0_bridge", lambda state: route_after_node(state, "validate_producer_bridge"))
    builder.add_edge("validate_producer_bridge", "final_report")
    builder.add_edge("final_report", END)
    return builder


def open_checkpointer(config: ProducerConfig):
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    config.run_dir.mkdir(parents=True, exist_ok=True)
    # LangGraph's SQLite saver can touch the connection from internal worker
    # paths during graph execution; keep the connection run-scoped and close it
    # explicitly after each start/resume command.
    conn = sqlite3.connect(checkpoint_path(config), check_same_thread=False)
    return conn, SqliteSaver(conn)


def run_graph_start(config: ProducerConfig) -> dict[str, Any]:
    conn, checkpointer = open_checkpointer(config)
    try:
        graph = build_graph(config).compile(checkpointer=checkpointer)
        state = initial_state(config)
        write_manifest(config, state)
        result = graph.invoke(state, config={"configurable": {"thread_id": config.thread_id}})
        if is_interrupt_result(result):
            waiting_state = {key: value for key, value in result.items() if key != "__interrupt__"}
            statuses = dict(waiting_state.get("node_statuses") or {})
            statuses["human_review_gate"] = "waiting_for_review"
            waiting_state["status"] = "waiting_for_review"
            waiting_state["current_node"] = "human_review_gate"
            waiting_state["node_statuses"] = statuses
            write_manifest(config, waiting_state)
        elif isinstance(result, dict):
            write_manifest(config, result)
        return result if isinstance(result, dict) else {"result": repr(result)}
    finally:
        conn.close()


def run_graph_resume(config: ProducerConfig, decision: str, reviewer_note: str = "") -> dict[str, Any]:
    from langgraph.types import Command

    conn, checkpointer = open_checkpointer(config)
    try:
        graph = build_graph(config).compile(checkpointer=checkpointer)
        resume_payload: dict[str, Any]
        if decision == "approve":
            resume_payload = {
                "decision": "approve",
                "reviewed_demo_nodes": repo_relative(config.reviewed_demo_nodes),
                "reviewed_candidates": repo_relative(config.reviewed_candidates),
                "reviewer_note": reviewer_note,
            }
        else:
            resume_payload = {"decision": "reject", "reviewer_note": reviewer_note}
        result = graph.invoke(Command(resume=resume_payload), config={"configurable": {"thread_id": config.thread_id}})
        if isinstance(result, dict):
            write_manifest(config, result)
        return result if isinstance(result, dict) else {"result": repr(result)}
    finally:
        conn.close()


class SpikeState(TypedDict, total=False):
    run_id: str
    status: str
    node_statuses: Annotated[dict[str, str], merge_dict]
    artifact_paths: Annotated[dict[str, str], merge_dict]
    errors: Annotated[list[ProducerRunError], append_errors]
    review_decision: str


def spike_review_node(config: ProducerConfig):
    def node(state: SpikeState) -> SpikeState:
        from langgraph.types import interrupt

        payload, request_hash = stable_review_payload(config)
        ok, message = write_or_verify_review_request(config, payload, request_hash)
        if not ok:
            return {
                "status": "failed",
                "errors": [
                    {
                        "node": "spike_review_gate",
                        "code": "review_request_drift",
                        "message": message,
                        "retryable": False,
                        "artifact_refs": [repo_relative(review_request_path(config))],
                    }
                ],
            }
        resume_payload = interrupt({"request_hash": request_hash, "review_request": repo_relative(review_request_path(config))})
        if isinstance(resume_payload, dict) and resume_payload.get("decision") == "approve":
            return {
                "status": "pass",
                "review_decision": "approve",
                "node_statuses": {"spike_review_gate": "pass"},
                "artifact_paths": {"review_request": repo_relative(review_request_path(config))},
            }
        return {
            "status": "rejected_by_human_review",
            "review_decision": "reject",
            "node_statuses": {"spike_review_gate": "pass"},
        }

    return node


def build_spike_graph(config: ProducerConfig):
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(SpikeState)
    builder.add_node("spike_review_gate", spike_review_node(config))
    builder.add_edge(START, "spike_review_gate")
    builder.add_edge("spike_review_gate", END)
    return builder


def run_spike_start(config: ProducerConfig) -> dict[str, Any]:
    conn, checkpointer = open_checkpointer(config)
    try:
        graph = build_spike_graph(config).compile(checkpointer=checkpointer)
        state: SpikeState = {
            "run_id": config.run_id,
            "status": "running",
            "node_statuses": {"spike_review_gate": "running"},
            "artifact_paths": artifact_plan(config),
            "errors": [],
            "review_decision": "pending",
        }
        result = graph.invoke(state, config={"configurable": {"thread_id": config.thread_id}})
        write_manifest(
            config,
            {
                **state,
                "status": "waiting_for_review",
                "current_node": "spike_review_gate",
                "node_statuses": {"spike_review_gate": "waiting_for_review"},
            },
        )
        return result if isinstance(result, dict) else {"result": repr(result)}
    finally:
        conn.close()


def run_spike_resume(config: ProducerConfig, decision: str) -> dict[str, Any]:
    from langgraph.types import Command

    conn, checkpointer = open_checkpointer(config)
    try:
        graph = build_spike_graph(config).compile(checkpointer=checkpointer)
        result = graph.invoke(
            Command(resume={"decision": decision}),
            config={"configurable": {"thread_id": config.thread_id}},
        )
        write_manifest(config, {"status": result.get("status", "pass") if isinstance(result, dict) else "pass", **(result or {})})
        return result if isinstance(result, dict) else {"result": repr(result)}
    finally:
        conn.close()


def print_json(data: Any) -> None:
    print(json.dumps(json_safe(data), ensure_ascii=False, indent=2, sort_keys=True))


def verify_command_plan(config: ProducerConfig) -> dict[str, Any]:
    errors: list[str] = []
    commands = command_plan(config)
    for item in commands:
        node = item.get("node", "")
        argv = item.get("argv", [])
        if not isinstance(argv, list) or not argv:
            errors.append(f"{node}: argv is empty")
            continue
        if len(argv) > 1 and isinstance(argv[1], str) and argv[1].endswith(".py"):
            script_path = resolve_path(argv[1])
            if not script_path.exists():
                errors.append(f"{node}: script missing: {repo_relative(script_path)}")
        if node == "register_media" and "--runtime-base" not in argv:
            errors.append("register_media: --runtime-base must be explicit")
    return {
        "status": "pass" if not errors else "failed",
        "checked_nodes": len(commands),
        "errors": errors,
    }


def dry_run(config: ProducerConfig, *, verify_argv: bool = False) -> int:
    state = initial_state(config)
    argv_verification = verify_command_plan(config) if verify_argv else None
    output = {
        "run_id": config.run_id,
        "thread_id": config.thread_id,
        "graph_api": "StateGraph",
        "graph_mode": graph_mode(config),
        "node_order": graph_node_order(config),
        "artifacts": artifact_plan(config),
        "llm": llm_manifest(config, state["node_statuses"], state["artifact_paths"]),
        "commands": [
            {
                "node": item["node"],
                "argv": item["argv"],
                "shell_preview": " ".join(shlex.quote(part) for part in item["argv"]),
                "artifact_refs": item["artifact_refs"],
            }
            for item in command_plan(config)
        ],
        "initial_state": state,
    }
    if argv_verification:
        output["argv_verification"] = argv_verification
    print_json(output)
    return 0 if not argv_verification or argv_verification["status"] == "pass" else 2


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--drama-id", default=DEFAULT_DRAMA_ID)
    parser.add_argument("--drama-title", default=DEFAULT_DRAMA_TITLE)
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--video-dir", default=str(DEFAULT_VIDEO_DIR))
    parser.add_argument("--drama-dir", default=str(DEFAULT_DRAMA_DIR))
    parser.add_argument("--reviewed-demo-nodes", default=str(DEFAULT_REVIEWED_DEMO_NODES))
    parser.add_argument("--reviewed-candidates", default=str(DEFAULT_REVIEWED_CANDIDATES))
    parser.add_argument("--enable-llm", action="store_true")
    parser.add_argument("--mock-provider", action="store_true")
    parser.add_argument("--allow-llm-skip", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    dry_run_parser = subparsers.add_parser("dry-run")
    add_common_args(dry_run_parser)
    dry_run_parser.add_argument("--verify-argv", action="store_true")
    for name in ("start", "spike-start"):
        add_common_args(subparsers.add_parser(name))
    resume_parser = subparsers.add_parser("resume")
    add_common_args(resume_parser)
    resume_parser.add_argument("--review-decision", choices=("approve", "reject"), required=True)
    resume_parser.add_argument("--reviewer-note", default="")
    spike_resume_parser = subparsers.add_parser("spike-resume")
    add_common_args(spike_resume_parser)
    spike_resume_parser.add_argument("--review-decision", choices=("approve", "reject"), default="approve")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = make_config(args)
    if args.command == "dry-run":
        return dry_run(config, verify_argv=bool(getattr(args, "verify_argv", False)))
    if args.command == "spike-start":
        print_json(run_spike_start(config))
        return 0
    if args.command == "spike-resume":
        config = resume_config_from_manifest(config)
        print_json(run_spike_resume(config, args.review_decision))
        return 0
    if args.command == "start":
        print_json(run_graph_start(config))
        return 0
    if args.command == "resume":
        config = resume_config_from_manifest(config)
        print_json(run_graph_resume(config, args.review_decision, args.reviewer_note))
        return 0
    raise AssertionError(f"unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
