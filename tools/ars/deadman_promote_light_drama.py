#!/usr/bin/env python3
"""Drama-agnostic LIGHT promote (Step 1 of the multi-drama sprint).

Reviewed mined candidates -> a *playable, schema-valid* runtime pack under
data/dramas/<drama>/, by cloning huangnian's gold pack structure and swapping in
the new drama's windows. The producer-bridge validator enforces full P0
completeness, so companion_exchange is filled with NEUTRAL PLACEHOLDER content
(flagged `content_status: placeholder_pending_cab`) that Step 3 (CAB authoring)
replaces with real taste content. No provider calls; deterministic.

Usage:
  python3 tools/ars/deadman_promote_light_drama.py \
      --drama-id yunmiao --title "云渺1：我修仙多年强亿点怎么了" \
      --reviewed tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json \
      --video-subdir 云渺 --max-moments 3
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HN = REPO / "data" / "dramas" / "huangnian"

# Sibling module: backfill the judgment fields so promoted moments survive the runtime adapter.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deadman_backfill_judgment_fields import backfill_moment  # noqa: E402

# Neutral, drama-agnostic placeholder stances: (display_text, action_text, semantic_role, emotion_role, echo)
NEUTRAL_STANCES = [
    ("想替他接一句", "接住眼前这个人此刻的情绪", "stand_with_person", "替他着急", "嗯，这一下我也想替他说一句。"),
    ("这事得有人吭声", "为眼前这件事说一句公道话", "name_the_issue", "替场面发声", "对，这场面不能没人吭声。"),
    ("先稳一下别急", "先把火气压一压，看眼前怎么落地", "soften_first", "先稳住", "我懂，这一下先别急着把话说满。"),
]


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def dump(p: Path, d) -> None:
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ep_int(episode_id: str) -> int | None:
    m = re.search(r"ep0*([0-9]+)", str(episode_id or ""))
    return int(m.group(1)) if m else None


def window_seconds(time_ms) -> tuple[int, int]:
    if isinstance(time_ms, dict):
        start = int(time_ms.get("start") or 0)
        end = int(time_ms.get("end") or start + 20000)
    else:
        start = int(time_ms or 0)
        end = start + 20000
    return max(0, start // 1000), max(0, end // 1000)


def placeholder_candidates(mid: str, trig: str) -> list[dict]:
    refs = [f"{mid}_u001", "current_scene_window"]
    cons = ["current_scene_only", "no_branch_rewrite", "source_window_grounding"]
    out = []
    for i, (disp, action_text, sem, emo, echo) in enumerate(NEUTRAL_STANCES):
        out.append({
            "candidate_id": f"preset_{i}",
            "display_text": disp,
            "action_payload": {"text": action_text, "action_type": trig, "intent": sem,
                               "target_actors": ["scene_focus"], "risk_posture": "balanced"},
            "emotion_role": emo, "semantic_role": sem,
            "distinctness_rationale": "placeholder pending CAB authoring (Step 3)",
            "evidence_refs": refs, "constraint_refs": cons,
            "friend_voice_seed": echo, "selected_echo": echo,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drama-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--reviewed", required=True)
    ap.add_argument("--video-subdir", required=True, help="folder name under tmp/视频素材/")
    ap.add_argument("--max-moments", type=int, default=3)
    a = ap.parse_args()

    drama = a.drama_id
    out = REPO / "data" / "dramas" / drama
    (out / "evidence").mkdir(parents=True, exist_ok=True)

    reviewed = load(Path(a.reviewed))
    keep = [c for c in reviewed["reviewed_candidates"] if str(c.get("label")) == "keep"]
    chosen, seen_eps = [], set()
    for c in keep:
        ep = c.get("episode_id")
        if ep in seen_eps:
            continue
        seen_eps.add(ep)
        chosen.append(c)
        if len(chosen) >= a.max_moments:
            break

    base_moment = load(HN / "moments.v0.1.json")["moments"][0]
    hn_manifest = load(HN / "manifest.v0.1.json")

    moments, nodes, media_eps, moment_ids = [], [], [], []
    for c in chosen:
        ep_id = str(c.get("episode_id") or f"{drama}_ep01")
        n = ep_int(ep_id) or 1
        mid = f"{drama}_ep{n:02d}_m001"
        start_s, end_s = window_seconds(c.get("time_ms"))
        video_url = f"/api/deadman/media/{drama}/{ep_id}.mp4"
        hook = str(c.get("hook") or "这一下，真有点想接一句。")
        excerpt = str(c.get("evidence_excerpt") or hook)
        trig = str(c.get("trigger_type") or "other")
        lead = "这一下我有点想替他说一句。"  # neutral; real lead comes from CAB (Step 3)
        moment_ids.append(mid)
        cands = placeholder_candidates(mid, trig)
        ref_ids = [f"{mid}_u001", "current_scene_window"]

        m = copy.deepcopy(base_moment)
        m["pack_id"] = mid
        m["moment_id"] = mid
        m["drama_id"] = drama
        m["title"] = a.title
        m["source_drama"] = {
            "title": a.title, "episode_id": ep_id,
            "source_policy": "reviewed mined candidate (light promote); companion content pending CAB authoring",
            "time_range_seconds": [start_s, end_s], "runtime_video_url": video_url,
            "media_registry_ref": f"data/dramas/{drama}/media_registry.v0.1.json#{ep_id}",
        }
        m["source_window"] = {
            "start_ms": start_s * 1000, "end_ms": end_s * 1000,
            "transcript_refs": [{"id": f"{mid}_u001", "episode_id": ep_id, "start_ms": start_s * 1000,
                                 "end_ms": end_s * 1000, "text": excerpt, "source": "sanitized_asr_snippet"}],
            "keyframe_refs": [], "provenance_status": "publish_safe_sanitized",
        }
        m["companion_surface"] = {
            "notice_marker": "!", "hook": lead, "viewer_impulse": "要是我来，我想接一句。",
            "scene_specificity_check": "must name an object, relation, witness, rule, or decision pressure from the source window",
            "companion_lead": lead,
        }
        m["action_space"] = {
            "action_type": trig,
            "default_options": [c["action_payload"]["text"] for c in cands],
            "mouthpiece_candidates_schema_version": "mouthpiece_candidates.v0.1",
            "mouthpiece_candidates": cands,
        }
        m["interaction_window"] = {
            "notice_at_seconds": start_s, "start_seconds": start_s, "end_seconds": end_s,
            "source": "reviewed_ars", "confidence": "medium",
            "pause_policy": "pause_on_invite", "expire_behavior": "return_to_idle",
        }
        m["companion_exchange"] = {
            "schema_version": "companion_exchange_pack.v0.1",
            "scene_signal": hook, "window_rationale": excerpt, "notice_marker": "!",
            "companion_lead": lead, "reply_candidates": cands,
            "custom_reply_policy": {"allowed": True, "scope": "local credible consequence only",
                "reject_or_soften": ["continuous branch rewrite", "unbounded system/power escalation",
                                     "claims not grounded in source window"],
                "runtime_personalization": "bounded"},
            "evidence_refs": ref_ids,
            "constraint_refs": ["current_scene_only", "no_branch_rewrite", "source_window_grounding", "no_future_episode_claim"],
            "blocked_claims": ["Do not claim what happens in later episodes.",
                               "Do not infer hidden motives from visual context alone.",
                               "Do not turn the reply into a new story branch."],
            "review_status": "reviewed",
            "content_status": "placeholder_pending_cab",
        }
        m["review_state"] = {
            "status": "demo_candidate", "reviewed_at": "2026-06-08", "evidence_grade": "medium",
            "evidence_notes": excerpt,
            "evidence_vs_inference": "window is mined+reviewed evidence; companion content pending CAB authoring",
        }
        m["evidence"] = {"grade": "medium", "notes": excerpt, "excerpt": excerpt}
        m["original_plot_note"] = "原剧情按当前场景推进；互动只接当下这一口气。"
        m["provenance"] = {
            "candidate_id": c.get("candidate_id"), "reviewed_candidate_ref": c.get("candidate_id"),
            "source_artifact": f"data/dramas/{drama}/evidence/reviewed_demo_nodes.v0.1.json#{mid}",
        }
        m["source_refs"] = {
            "reviewed_demo_node": f"data/dramas/{drama}/evidence/reviewed_demo_nodes.v0.1.json#{mid}",
            "transcript_snippets": m["source_window"]["transcript_refs"], "keyframe_refs": [],
        }
        m["producer_refs"] = {"policy": "light promote; producer evidence under ignored tmp/ars_<drama>_analysis; runtime refs sanitized"}
        # Strip the template's drama-specific judgment fields, then backfill neutral-but-valid
        # equivalents (NOT huangnian's values) so the runtime judgment adapter runs cleanly.
        # The viewer surface for a preset tap is the authored echo, so the computed verdict is
        # internal; these fields only need to be valid, not genre-tuned. See
        # deadman_backfill_judgment_fields for the full rationale.
        for k in ("optional_modules", "required_pack_fields", "actor_context", "local_constraints",
                  "canon_baseline", "result_media", "judgment_policy", "outcome_response_contract",
                  "visual_result_policy", "score_axes", "producer_review_fields"):
            m.pop(k, None)
        backfill_moment(m, base_moment)
        moments.append(m)

        nodes.append({
            "moment_id": mid, "candidate_id": c.get("candidate_id"), "review_status": "demo_candidate",
            "corrected_trigger_type": trig, "source_window": m["source_window"],
            "companion_hook": lead, "viewer_impulse": "要是我来，我想接一句。",
            "default_options": [c["action_payload"]["text"] for c in cands],
            "evidence": {"grade": "medium", "notes": excerpt},
            "evidence_vs_inference": "source_window and excerpt are evidence; companion content is reviewed product inference (placeholder pending CAB authoring).",
        })
        media_eps.append({
            "episode_id": ep_id, "title": f"第{n}集", "runtime_video_url": video_url, "status": "registered",
            "producer_media": {"local_media_path": f"tmp/视频素材/{a.video_subdir}/第{n}集.mp4",
                               "policy": "producer-only local metadata; runtime should use runtime_video_url"},
        })

    dump(out / "moments.v0.1.json", {
        "schema_version": "moment_causality_pack.v0.1",
        "collection_schema_version": "moment_causality_pack_collection.v0.1",
        "drama_id": drama, "title": a.title, "drama_context_ref": "context.v0.1.json",
        "source_policy": "light promote from reviewed mined candidates; companion content pending CAB authoring",
        "moment_count": len(moments), "moments": moments,
    })

    manifest = copy.deepcopy(hn_manifest)
    manifest["drama_id"] = drama
    manifest["title"] = a.title
    manifest["moment_packs"]["count"] = len(moment_ids)
    manifest["moment_packs"]["moment_ids"] = moment_ids
    manifest["media_registry"]["episode_count"] = len(media_eps)
    manifest["media_registry"]["registered_count"] = len(media_eps)
    manifest["source_artifacts"] = {
        "reviewed_demo_nodes": f"data/dramas/{drama}/evidence/reviewed_demo_nodes.v0.1.json",
        "allowed_summary": hn_manifest.get("source_artifacts", {}).get("allowed_summary", ""),
    }
    manifest["promoted_dir"] = f"data/dramas/{drama}"
    dump(out / "manifest.v0.1.json", manifest)

    dump(out / "context.v0.1.json", {
        "schema_version": "drama_context_pack.v0.1", "drama_id": drama, "title": a.title,
        "source_scope": {"episode_scope": "reviewed_demo_windows",
                         "basis": ["reviewed_candidates", "asr_snippets", "keyframe_contact_sheet_refs"],
                         "evidence_status": "reviewed_bridge_artifact"},
        "premise": a.title,
        "genre_contract": [{"claim": "P0 interaction answers local credible consequences, then lets the viewer keep watching.",
                            "evidence_ids": ["light-promote-001"], "confidence": "high"}],
        "evidence_map": [{"id": "light-promote-001",
                          "claim": "windows are mined+reviewed; companion content pending CAB authoring",
                          "evidence": "reviewed_candidates", "confidence": "medium"}],
        "global_constraints": {"hard_constraints": ["answer only current scene or immediate aftermath",
                                                    "do not claim continuous branch rewrite"]},
    })

    dump(out / "media_registry.v0.1.json", {
        "schema_version": "deadman_media_registry.v0.1", "drama_id": drama, "title": a.title,
        "media_policy": "local producer media; runtime serves via runtime_video_url; raw mp4 not committed",
        "episode_count": len(media_eps), "registered_count": len(media_eps), "episodes": media_eps,
    })

    dump(out / "evidence" / "reviewed_demo_nodes.v0.1.json", {
        "schema_version": "deadman_reviewed_demo_nodes_evidence.v0.1",
        "evidence_policy": "sanitized tracked evidence; no runtime dereference of ignored tmp artifacts",
        "demo_node_count": len(nodes), "demo_nodes": nodes,
    })

    print(f"promoted {drama}: {len(moments)} moments / {len(media_eps)} episodes -> data/dramas/{drama}")
    print("moment_ids:", moment_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
