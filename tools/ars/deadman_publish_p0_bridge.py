#!/usr/bin/env python3
"""Publish Deadman P0 packs with runtime-safe provenance and media slots."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_DRAMA_DIR = REPO_ROOT / "data/dramas/huangnian"
DEFAULT_REVIEWED_DEMO_NODES = REPO_ROOT / "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json"
DEFAULT_REVIEWED_CANDIDATES = REPO_ROOT / "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json"


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_demo_nodes(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    nodes = data.get("demo_nodes")
    if not isinstance(nodes, list):
        raise ValueError(f"{path} does not contain demo_nodes")
    return {str(node["moment_id"]): node for node in nodes if isinstance(node, dict) and node.get("moment_id")}


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"episodes": []}
    data = read_json(path)
    if not isinstance(data.get("episodes"), list):
        raise ValueError(f"{path} has no episodes list")
    return data


def episode_id_for_moment(moment: dict[str, Any], node: dict[str, Any] | None) -> str:
    source_drama = moment.get("source_drama", {}) if isinstance(moment.get("source_drama"), dict) else {}
    if source_drama.get("episode_id"):
        return str(source_drama["episode_id"])
    candidate_id = str((node or {}).get("candidate_id", ""))
    match = re.match(r"(huangnian_ep\d+)_", candidate_id)
    return match.group(1) if match else "huangnian_unknown_episode"


def frame_time_seconds(path: str) -> int:
    match = re.search(r"frame_(\d+)", Path(path).stem)
    index = int(match.group(1)) if match else 1
    return max(0, (index - 1) * 10)


def source_window_for(moment: dict[str, Any], node: dict[str, Any] | None) -> dict[str, Any]:
    node_window = (node or {}).get("source_window")
    if isinstance(node_window, dict):
        return node_window
    moment_window = moment.get("source_window")
    return moment_window if isinstance(moment_window, dict) else {}


def evidence_grade(moment: dict[str, Any], node: dict[str, Any] | None) -> str:
    node_grade = ((node or {}).get("evidence") or {}).get("grade")
    if node_grade:
        return str(node_grade)
    return str((moment.get("review_state", {}) or {}).get("evidence_grade") or "medium")


def transcript_snippets(episode_id: str, source_window: dict[str, Any]) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    for index, ref in enumerate(source_window.get("transcript_refs", []) or [], start=1):
        if not isinstance(ref, dict):
            continue
        text = str(ref.get("text", "")).strip()
        snippets.append(
            {
                "id": f"{episode_id}_u{index:03d}",
                "episode_id": episode_id,
                "start_ms": int(ref.get("start_ms") or ref.get("start_time") or 0),
                "end_ms": int(ref.get("end_ms") or ref.get("end_time") or 0),
                "text": text,
                "source": "sanitized_asr_snippet",
            }
        )
    return snippets


def keyframe_refs(episode_id: str, source_window: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for index, raw_ref in enumerate(source_window.get("keyframe_refs", []) or [], start=1):
        raw = str(raw_ref)
        refs.append(
            {
                "id": f"{episode_id}_k{index:03d}",
                "episode_id": episode_id,
                "time_seconds": frame_time_seconds(raw),
                "description": "keyframe reference only; not psychological proof",
                "source": "sanitized_keyframe_ref",
            }
        )
    return refs


def contact_sheet_ref(episode_id: str, source_window: dict[str, Any]) -> dict[str, Any] | None:
    raw_ref = source_window.get("contact_sheet_ref")
    if not raw_ref:
        return None
    return {
        "id": f"{episode_id}_contact_sheet",
        "episode_id": episode_id,
        "description": "contact sheet reference only; not runtime-dereferenced evidence",
        "source": "sanitized_contact_sheet_ref",
    }


def safe_source_window(episode_id: str, source_window: dict[str, Any]) -> dict[str, Any]:
    contact_ref = contact_sheet_ref(episode_id, source_window)
    return {
        "start_ms": int(source_window.get("start_ms") or 0),
        "end_ms": int(source_window.get("end_ms") or 0),
        "transcript_refs": transcript_snippets(episode_id, source_window),
        "keyframe_refs": keyframe_refs(episode_id, source_window),
        "contact_sheet_ref": contact_ref,
        "provenance_status": "publish_safe_sanitized",
    }


def producer_refs(
    *,
    reviewed_demo_nodes_path: Path,
    reviewed_candidates_path: Path,
    source_window: dict[str, Any],
) -> dict[str, Any]:
    return {
        "reviewed_demo_nodes": repo_relative(reviewed_demo_nodes_path),
        "reviewed_candidates": repo_relative(reviewed_candidates_path),
        "raw_transcript_paths": sorted(
            {
                str(ref.get("path"))
                for ref in source_window.get("transcript_refs", []) or []
                if isinstance(ref, dict) and ref.get("path")
            }
        ),
        "raw_keyframe_refs": [str(ref) for ref in source_window.get("keyframe_refs", []) or []],
        "raw_contact_sheet_ref": str(source_window.get("contact_sheet_ref") or ""),
        "policy": "producer-only local refs; runtime source_refs and source_window are sanitized",
    }


def interaction_window(source_window: dict[str, Any], grade: str) -> dict[str, Any]:
    start_ms = int(source_window.get("start_ms") or 0)
    end_ms = int(source_window.get("end_ms") or 0)
    if end_ms <= start_ms:
        start_seconds = 0
        end_seconds = 20
        source = "manual_p0_fallback"
        confidence = "low"
    else:
        start_seconds = max(0, math.floor(start_ms / 1000))
        end_seconds = max(start_seconds + 8, math.ceil(end_ms / 1000))
        source = "reviewed_ars"
        confidence = "high" if grade == "high" else "medium"
    return {
        "notice_at_seconds": start_seconds,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "source": source,
        "confidence": confidence,
        "pause_policy": "pause_on_invite",
        "expire_behavior": "return_to_idle",
    }


def result_media(moment_id: str, options: list[str]) -> dict[str, Any]:
    preset_options = []
    for index, option in enumerate(options):
        preset_options.append(
            {
                "option_index": index,
                "status": "placeholder",
                "image_url": "",
                "prompt": f"{moment_id} option {index}: {option}",
                "source": "manual_placeholder",
                "fallback_text": "P0 result image slot reserved; render text consequence when no image is available.",
            }
        )
    return {
        "preset_options": preset_options,
        "custom_action": {
            "status": "not_requested",
            "mode": "realtime_generate_or_text_only_fallback",
            "timeout_ms": 8000,
        },
    }


def mouthpiece_action_space(moment: dict[str, Any], node: dict[str, Any] | None) -> dict[str, Any]:
    action_space = dict(moment.get("action_space", {}) or {})
    node_candidates = (node or {}).get("mouthpiece_candidates")
    if isinstance(node_candidates, list) and node_candidates:
        action_space["mouthpiece_candidates_schema_version"] = str(
            (node or {}).get("mouthpiece_candidates_schema_version")
            or action_space.get("mouthpiece_candidates_schema_version")
            or "mouthpiece_candidates.v0.1"
        )
        action_space["mouthpiece_candidates"] = node_candidates
    elif isinstance(action_space.get("mouthpiece_candidates"), list) and action_space.get("mouthpiece_candidates"):
        action_space["mouthpiece_candidates_schema_version"] = str(
            action_space.get("mouthpiece_candidates_schema_version") or "mouthpiece_candidates.v0.1"
        )
    return action_space


def display_options_for_result_media(action_space: dict[str, Any]) -> list[str]:
    candidates = action_space.get("mouthpiece_candidates")
    if isinstance(candidates, list) and candidates:
        options = [
            str(candidate.get("display_text"))
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("display_text")
        ]
        if options:
            return options[:3]
    return [str(option) for option in action_space.get("default_options", []) if isinstance(option, str)]


def companion_exchange_pack(
    *,
    moment_id: str,
    moment: dict[str, Any],
    node: dict[str, Any] | None,
    action_space: dict[str, Any],
) -> dict[str, Any]:
    existing = moment.get("companion_exchange") if isinstance(moment.get("companion_exchange"), dict) else {}
    node_exchange = (node or {}).get("companion_exchange")
    if isinstance(node_exchange, dict) and node_exchange.get("reply_candidates"):
        existing = node_exchange

    candidates = existing.get("reply_candidates") if isinstance(existing, dict) else None
    if not isinstance(candidates, list) or not candidates:
        candidates = action_space.get("mouthpiece_candidates")
    if not isinstance(candidates, list):
        candidates = []
    candidates = [normalized_reply_candidate(candidate, index, moment_id) for index, candidate in enumerate(candidates[:3])]

    companion_surface = moment.get("companion_surface") if isinstance(moment.get("companion_surface"), dict) else {}
    lead = str(
        (existing or {}).get("companion_lead")
        or companion_surface.get("companion_lead")
        or companion_surface.get("hook")
        or (node or {}).get("companion_hook")
        or "这段我真忍不了。"
    ).strip()
    scene_signal = str(
        (existing or {}).get("scene_signal")
        or (node or {}).get("viewer_impulse")
        or companion_surface.get("hook")
        or "这个窗口值得搭子介入"
    ).strip()
    return {
        "schema_version": "companion_exchange_pack.v0.1",
        "scene_signal": scene_signal,
        "window_rationale": str(
            (existing or {}).get("window_rationale")
            or (node or {}).get("why_now_reviewed")
            or (node or {}).get("evidence_vs_inference")
            or "Reviewed P0 window selected for companion interruption."
        ).strip(),
        "notice_marker": str((existing or {}).get("notice_marker") or "!"),
        "companion_lead": lead,
        "reply_candidates": candidates,
        "custom_reply_policy": (existing or {}).get("custom_reply_policy")
        or {
            "allowed": True,
            "runtime_personalization": "bounded",
            "reject_or_soften": [
                "future branch claim",
                "unbounded revenge",
                "source-window-unsupported fact",
            ],
        },
        "evidence_refs": normalized_string_list((existing or {}).get("evidence_refs")) or [moment_id],
        "constraint_refs": normalized_string_list((existing or {}).get("constraint_refs"))
        or ["current_scene_only", "no_future_episode_claim"],
        "blocked_claims": normalized_string_list((existing or {}).get("blocked_claims"))
        or [
            "Do not claim what happens in later episodes.",
            "Do not infer hidden motives from visual context alone.",
            "Do not turn the reply into a new story branch.",
        ],
        "review_status": str((existing or {}).get("review_status") or "reviewed"),
    }


def normalized_reply_candidate(candidate: Any, index: int, moment_id: str) -> dict[str, Any]:
    raw = candidate if isinstance(candidate, dict) else {}
    action_payload = raw.get("action_payload") if isinstance(raw.get("action_payload"), dict) else {}
    display_text = str(raw.get("display_text") or action_payload.get("text") or f"这句先接住{index + 1}").strip()[:14]
    selected_echo = str(raw.get("selected_echo") or raw.get("friend_voice_seed") or f"这句我懂，{display_text}。").strip()
    return {
        "candidate_id": str(raw.get("candidate_id") or f"preset_{index}"),
        "display_text": display_text,
        "action_payload": {
            **action_payload,
            "text": str(action_payload.get("text") or display_text),
        },
        "selected_echo": selected_echo[:80],
        "emotion_role": str(raw.get("emotion_role") or f"reviewed_emotion_{index}"),
        "semantic_role": str(raw.get("semantic_role") or f"reviewed_semantic_{index}"),
        "distinctness_rationale": str(
            raw.get("distinctness_rationale") or "Reviewed distinct expression path for this scene."
        ),
        "evidence_refs": normalized_string_list(raw.get("evidence_refs")) or [moment_id],
        "constraint_refs": normalized_string_list(raw.get("constraint_refs")) or ["current_scene_only"],
    }


def normalized_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def safe_source_refs(
    *,
    drama_dir: Path,
    moment_id: str,
    episode_id: str,
    source_window: dict[str, Any],
) -> dict[str, Any]:
    return {
        "reviewed_demo_node": f"{repo_relative(drama_dir / 'evidence/reviewed_demo_nodes.v0.1.json')}#{moment_id}",
        "transcript_snippets": transcript_snippets(episode_id, source_window),
        "keyframe_refs": keyframe_refs(episode_id, source_window),
        "contact_sheet_ref": contact_sheet_ref(episode_id, source_window),
    }


def media_entry(registry: dict[str, Any], episode_id: str) -> dict[str, Any] | None:
    for item in registry.get("episodes", []):
        if isinstance(item, dict) and item.get("episode_id") == episode_id:
            return item
    return None


def publish_moments(
    *,
    drama_dir: Path,
    moments_collection: dict[str, Any],
    demo_nodes_by_id: dict[str, dict[str, Any]],
    media_registry: dict[str, Any],
    reviewed_demo_nodes_path: Path,
    reviewed_candidates_path: Path,
) -> dict[str, Any]:
    next_collection = dict(moments_collection)
    next_moments = []
    for moment in moments_collection.get("moments", []):
        if not isinstance(moment, dict):
            continue
        moment_id = str(moment.get("moment_id") or moment.get("pack_id"))
        node = demo_nodes_by_id.get(moment_id)
        episode_id = episode_id_for_moment(moment, node)
        source_window = source_window_for(moment, node)
        grade = evidence_grade(moment, node)
        action_space = mouthpiece_action_space(moment, node)
        options = display_options_for_result_media(action_space)
        registry_entry = media_entry(media_registry, episode_id)

        next_moment = dict(moment)
        next_moment["action_space"] = action_space
        next_moment["companion_exchange"] = companion_exchange_pack(
            moment_id=moment_id,
            moment=moment,
            node=node,
            action_space=action_space,
        )
        source_drama = dict(next_moment.get("source_drama", {}) or {})
        source_drama["episode_id"] = episode_id
        source_drama["time_range_seconds"] = [
            int(source_window.get("start_ms") or 0) // 1000,
            math.ceil(int(source_window.get("end_ms") or 0) / 1000),
        ]
        if registry_entry:
            source_drama["runtime_video_url"] = registry_entry.get("runtime_video_url", "")
            source_drama["media_registry_ref"] = f"{repo_relative(drama_dir / 'media_registry.v0.1.json')}#{episode_id}"
        next_moment["source_drama"] = source_drama
        next_moment["interaction_window"] = interaction_window(source_window, grade)
        next_moment["source_window"] = safe_source_window(episode_id, source_window)
        next_moment["source_refs"] = safe_source_refs(
            drama_dir=drama_dir,
            moment_id=moment_id,
            episode_id=episode_id,
            source_window=source_window,
        )
        next_moment["producer_refs"] = producer_refs(
            reviewed_demo_nodes_path=reviewed_demo_nodes_path,
            reviewed_candidates_path=reviewed_candidates_path,
            source_window=source_window,
        )
        next_moment["result_media"] = result_media(moment_id, options)
        provenance = dict(next_moment.get("provenance", {}) or {})
        provenance["source_artifact"] = f"{repo_relative(drama_dir / 'evidence/reviewed_demo_nodes.v0.1.json')}#{moment_id}"
        next_moment["provenance"] = provenance
        next_moments.append(next_moment)
    next_collection["moments"] = next_moments
    next_collection["moment_count"] = len(next_moments)
    next_collection["source_policy"] = (
        "reviewed demo nodes only; runtime evidence is sanitized under data/; "
        "producer_refs may point to ignored local artifacts"
    )
    return next_collection


def sanitized_demo_node(moment_id: str, node: dict[str, Any]) -> dict[str, Any]:
    episode_id = episode_id_for_moment({}, node)
    source_window = source_window_for({}, node)
    return {
        "moment_id": moment_id,
        "candidate_id": node.get("candidate_id"),
        "review_status": node.get("review_status"),
        "corrected_trigger_type": node.get("corrected_trigger_type"),
        "source_window": safe_source_window(episode_id, source_window),
        "companion_hook": node.get("companion_hook"),
        "viewer_impulse": node.get("viewer_impulse"),
        "companion_exchange": node.get("companion_exchange"),
        "mouthpiece_candidates_schema_version": node.get("mouthpiece_candidates_schema_version"),
        "mouthpiece_candidates": node.get("mouthpiece_candidates", []),
        "default_options": node.get("default_options", []),
        "canon_baseline_reviewed": node.get("canon_baseline_reviewed", {}),
        "original_plot_note_reviewed": node.get("original_plot_note_reviewed", ""),
        "evidence": node.get("evidence", {}),
        "required_pack_fields": node.get("required_pack_fields", []),
        "evidence_vs_inference": node.get("evidence_vs_inference", ""),
        "producer_ref": "tmp review artifact; see runtime moment producer_refs for local-only provenance",
    }


def write_evidence_file(drama_dir: Path, demo_nodes_by_id: dict[str, dict[str, Any]]) -> Path:
    evidence_path = drama_dir / "evidence/reviewed_demo_nodes.v0.1.json"
    payload = {
        "schema_version": "deadman_reviewed_demo_nodes_evidence.v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_policy": "sanitized tracked evidence; no runtime dereference of ignored tmp artifacts",
        "demo_node_count": len(demo_nodes_by_id),
        "demo_nodes": [
            sanitized_demo_node(moment_id, demo_nodes_by_id[moment_id])
            for moment_id in sorted(demo_nodes_by_id)
        ],
    }
    write_json(evidence_path, payload)
    return evidence_path


def sanitize_context(context: dict[str, Any], drama_dir: Path, demo_nodes_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    next_context = dict(context)
    evidence_map = []
    for entry in context.get("evidence_map", []):
        if not isinstance(entry, dict):
            continue
        next_entry = dict(entry)
        source = str(next_entry.get("source", ""))
        for moment_id, node in demo_nodes_by_id.items():
            if moment_id in source:
                suffix = ".source_window" if source.endswith(".source_window") else ""
                next_entry["source"] = f"{repo_relative(drama_dir / 'evidence/reviewed_demo_nodes.v0.1.json')}#{moment_id}{suffix}"
                if "source_refs" in next_entry:
                    episode_id = episode_id_for_moment({}, node)
                    source_window = source_window_for({}, node)
                    next_entry["source_refs"] = {
                        "transcript_snippet_count": len(transcript_snippets(episode_id, source_window)),
                        "keyframe_refs": [item["id"] for item in keyframe_refs(episode_id, source_window)],
                        "contact_sheet_ref": (contact_sheet_ref(episode_id, source_window) or {}).get("id", ""),
                    }
                break
        evidence_map.append(next_entry)
    next_context["evidence_map"] = evidence_map
    return next_context


def update_manifest(
    *,
    manifest: dict[str, Any],
    drama_dir: Path,
    media_registry: dict[str, Any],
    moment_collection: dict[str, Any],
) -> dict[str, Any]:
    next_manifest = dict(manifest)
    next_manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    next_manifest["source_artifacts"] = {
        "reviewed_demo_nodes": repo_relative(drama_dir / "evidence/reviewed_demo_nodes.v0.1.json"),
        "allowed_summary": "docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md",
    }
    next_manifest["media_registry"] = {
        "path": "media_registry.v0.1.json",
        "schema_version": media_registry.get("schema_version", "deadman_media_registry.v0.1"),
        "episode_count": media_registry.get("episode_count", len(media_registry.get("episodes", []))),
        "registered_count": sum(
            1 for item in media_registry.get("episodes", []) if isinstance(item, dict) and item.get("status") == "registered"
        ),
    }
    next_manifest["moment_packs"] = {
        "path": "moments.v0.1.json",
        "schema_version": "moment_causality_pack.v0.1",
        "count": len(moment_collection.get("moments", [])),
        "moment_ids": [moment.get("moment_id") for moment in moment_collection.get("moments", [])],
    }
    next_manifest["ingestion_status"] = {
        "producer_media_registry": "implemented_local_registry_v0.1",
        "producer_pack_publish": "implemented_reviewed_p0_publish_v0.1",
        "backend_judgment_api": "implemented_cab_runtime_default_v0.1",
        "frontend_ingestion": "implemented_pack_timing_and_result_media_v0.1",
        "runtime_video_timing": "implemented_interaction_window_v0.1",
        "source_provenance": "publish_safe_runtime_refs_with_producer_refs_for_local_tmp",
        "image_generation": "placeholder_slots_realtime_custom_fallback_v0.1",
    }
    next_manifest.pop("generated_artifacts", None)
    return next_manifest


def assert_runtime_refs_are_safe(data: Any) -> None:
    def walk(value: Any, path: str) -> None:
        if ".producer_refs" in path or ".producer_media" in path:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str) and "tmp/" in value:
            raise ValueError(f"Runtime evidence path still depends on ignored tmp at {path}: {value}")
    walk(data, "")


def write_report(path: Path, moment_collection: dict[str, Any], media_registry: dict[str, Any]) -> None:
    lines = [
        "# Deadman P0 Bridge Publish Report",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Moments published: {len(moment_collection.get('moments', []))}",
        f"- Registered media episodes: {media_registry.get('episode_count', len(media_registry.get('episodes', [])))}",
        "- Timing source: reviewed ARS source windows where available; manual fallback is explicitly labeled if needed.",
        "- Runtime evidence: sanitized under `data/dramas/huangnian/evidence/`.",
        "- Producer refs: local ignored `tmp/...` paths only; backend/player do not dereference them.",
        "- Result media: placeholder slots for preset options; custom action uses realtime-generate-or-text-only fallback seam.",
        "",
    ]
    for moment in moment_collection.get("moments", []):
        window = moment.get("interaction_window", {})
        lines.append(
            f"- `{moment.get('moment_id')}`: {window.get('start_seconds')}s-{window.get('end_seconds')}s, "
            f"{window.get('source')}, {len(moment.get('result_media', {}).get('preset_options', []))} image slots."
        )
    write_text(path, "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-dir", default=str(DEFAULT_DRAMA_DIR))
    parser.add_argument("--reviewed-demo-nodes", default=str(DEFAULT_REVIEWED_DEMO_NODES))
    parser.add_argument("--reviewed-candidates", default=str(DEFAULT_REVIEWED_CANDIDATES))
    parser.add_argument("--media-registry", help="Defaults to drama-dir/media_registry.v0.1.json")
    parser.add_argument("--report", help="Defaults to tmp/ars_huangnian_analysis/p0_bridge_publish_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    drama_dir = resolve_path(args.drama_dir)
    reviewed_demo_nodes_path = resolve_path(args.reviewed_demo_nodes)
    reviewed_candidates_path = resolve_path(args.reviewed_candidates)
    media_registry_path = resolve_path(args.media_registry) if args.media_registry else drama_dir / "media_registry.v0.1.json"
    report_path = resolve_path(args.report) if args.report else REPO_ROOT / "tmp/ars_huangnian_analysis/p0_bridge_publish_report.md"

    context = read_json(drama_dir / "context.v0.1.json")
    moments = read_json(drama_dir / "moments.v0.1.json")
    manifest = read_json(drama_dir / "manifest.v0.1.json")
    demo_nodes_by_id = load_demo_nodes(reviewed_demo_nodes_path)
    media_registry = load_registry(media_registry_path)

    evidence_path = write_evidence_file(drama_dir, demo_nodes_by_id)
    next_context = sanitize_context(context, drama_dir, demo_nodes_by_id)
    next_moments = publish_moments(
        drama_dir=drama_dir,
        moments_collection=moments,
        demo_nodes_by_id=demo_nodes_by_id,
        media_registry=media_registry,
        reviewed_demo_nodes_path=reviewed_demo_nodes_path,
        reviewed_candidates_path=reviewed_candidates_path,
    )
    next_manifest = update_manifest(
        manifest=manifest,
        drama_dir=drama_dir,
        media_registry=media_registry,
        moment_collection=next_moments,
    )

    assert_runtime_refs_are_safe(next_context)
    assert_runtime_refs_are_safe(next_moments)
    assert_runtime_refs_are_safe(next_manifest)

    write_json(drama_dir / "context.v0.1.json", next_context)
    write_json(drama_dir / "moments.v0.1.json", next_moments)
    write_json(drama_dir / "manifest.v0.1.json", next_manifest)
    write_report(report_path, next_moments, media_registry)

    print(
        json.dumps(
            {
                "moments": len(next_moments.get("moments", [])),
                "evidence": repo_relative(evidence_path),
                "report": repo_relative(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
