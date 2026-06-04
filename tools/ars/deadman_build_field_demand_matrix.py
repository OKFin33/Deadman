#!/usr/bin/env python3
"""Build Deadman v0.3 node-level field-demand matrix from existing ARS artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/ars_multidrama_field_minimum_v0.3"

DRAMAS: dict[str, dict[str, str]] = {
    "huangnian": {
        "title": "荒年全村啃树皮，我有系统满仓肉",
        "candidates": "tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json",
        "review": "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json",
        "review_kind": "reviewed",
    },
    "yunmiao": {
        "title": "云渺",
        "candidates": "tmp/ars_yunmiao_analysis/candidates/yunmiao_candidates.v0.2.json",
        "review": "tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json",
        "review_kind": "schema_evidence",
    },
    "lihun": {
        "title": "幸得相遇离婚时",
        "candidates": "tmp/ars_lihun_analysis/candidates/lihun_candidates.v0.2.json",
        "review": "tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json",
        "review_kind": "schema_evidence",
    },
}

FIELDS: list[str] = [
    "source_window",
    "review_and_provenance",
    "companion_entry",
    "action_space",
    "response_contract",
    "visual_result_policy",
    "score_axes",
    "actor_local_state",
    "relationship_state",
    "critical_stakes_state",
    "local_constraint_state",
    "capability_rules",
    "information_asymmetry",
    "proof_state",
    "audience_reputation_state",
    "escalation_risk",
    "canon_baseline",
    "watch_flow_rationale",
]

TRIGGER_ALIASES = {
    "resource_visibility": "exposure_risk",
}

BASE_NOTES = {
    "source_window": "Every interaction needs an episode/time window before the player can show a marker or quote evidence.",
    "review_and_provenance": "The field-demand pass must keep reviewed/schema/candidate evidence separate so unreviewed facts do not become runtime truth.",
    "companion_entry": "The viewer enters through the companion hook, so the moment needs a short friend-tone prompt even when causal judgment is separate.",
    "action_space": "Preset and custom actions both need a bounded local action space before consequence judgment can be credible.",
    "response_contract": "The result must stay a short local consequence, not a continuing alternate timeline.",
    "visual_result_policy": "The product may show images, but keyframes/generated slots need a policy so visuals do not overclaim truth.",
    "score_axes": "Producer ranking and fallback selection need stable axes, but these axes are not the causal state itself.",
    "actor_local_state": "Without local actors, roles, and affected parties, the model can only produce generic commentary.",
    "local_constraint_state": "Credible consequence depends on hard scene facts, timing, available tools, and local constraints.",
    "canon_baseline": "The model needs the original action and rationale to anchor the alternative and preserve watch flow.",
    "watch_flow_rationale": "The output must explain why the viewer can return to the original short drama after seeing the alternative.",
    "critical_stakes_state": "The model must know what can be lost, spent, saved, or made worse by the chosen action.",
    "escalation_risk": "The product promise is not unconditional爽; the model needs a cost/backlash field to avoid fake catharsis.",
    "relationship_state": "Relationship pressure changes who should be protected, confronted, or trusted first.",
    "capability_rules": "Hidden powers or systems need limits; otherwise the action becomes an unbounded cheat.",
    "information_asymmetry": "Identity, secrecy, and hidden facts control when revealing information helps or burns leverage.",
    "proof_state": "Evidence, witnesses, and accounts decide whether a reversal lands or becomes reckless accusation.",
    "audience_reputation_state": "Public witnesses, village pressure, or social standing change the cost of confrontation.",
}

TRIGGER_DEMANDS: dict[str, dict[str, int]] = {
    "resource_crisis": {
        "critical_stakes_state": 3,
        "relationship_state": 2,
        "information_asymmetry": 2,
        "escalation_risk": 2,
    },
    "exposure_risk": {
        "information_asymmetry": 3,
        "capability_rules": 2,
        "critical_stakes_state": 2,
        "escalation_risk": 2,
    },
    "family_pressure": {
        "relationship_state": 3,
        "critical_stakes_state": 2,
        "escalation_risk": 2,
    },
    "village_pressure": {
        "audience_reputation_state": 3,
        "relationship_state": 2,
        "critical_stakes_state": 2,
        "escalation_risk": 3,
    },
    "humiliation_reversal": {
        "audience_reputation_state": 3,
        "relationship_state": 2,
        "proof_state": 2,
        "escalation_risk": 3,
    },
    "evidence_or_trap": {
        "proof_state": 3,
        "information_asymmetry": 2,
        "audience_reputation_state": 2,
        "escalation_risk": 2,
    },
    "system_rule": {
        "capability_rules": 3,
        "information_asymmetry": 2,
        "critical_stakes_state": 2,
        "escalation_risk": 2,
    },
    "survival_tradeoff": {
        "critical_stakes_state": 3,
        "local_constraint_state": 3,
        "relationship_state": 2,
        "escalation_risk": 3,
    },
    "nonsense_or_overpowered_break": {
        "capability_rules": 3,
        "watch_flow_rationale": 3,
        "escalation_risk": 3,
    },
    "hidden_power_rule": {
        "capability_rules": 3,
        "information_asymmetry": 2,
        "critical_stakes_state": 2,
        "watch_flow_rationale": 3,
        "escalation_risk": 2,
    },
    "identity_reveal": {
        "information_asymmetry": 3,
        "relationship_state": 2,
        "audience_reputation_state": 2,
        "watch_flow_rationale": 3,
        "escalation_risk": 2,
    },
    "relationship_betrayal": {
        "relationship_state": 3,
        "critical_stakes_state": 2,
        "proof_state": 2,
        "escalation_risk": 3,
    },
    "status_reversal": {
        "information_asymmetry": 2,
        "proof_state": 2,
        "audience_reputation_state": 3,
        "escalation_risk": 3,
        "watch_flow_rationale": 3,
    },
    "medical_or_pregnancy_risk": {
        "critical_stakes_state": 3,
        "relationship_state": 2,
        "proof_state": 2,
        "escalation_risk": 2,
    },
}


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: str | Path) -> Any:
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_trigger(trigger: str | None) -> str:
    if not trigger:
        return "unknown"
    return TRIGGER_ALIASES.get(trigger, trigger)


def candidate_lookup(candidates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["candidate_id"]: item for item in candidates.get("candidates", [])}


def review_status(item: dict[str, Any]) -> str:
    return item.get("review_status") or item.get("label") or "candidate_only"


def review_trigger(item: dict[str, Any]) -> str:
    return normalize_trigger(item.get("corrected_trigger_type") or item.get("trigger_type") or item.get("original_trigger_type"))


def review_time_window(item: dict[str, Any], candidate: dict[str, Any] | None) -> dict[str, int]:
    if item.get("source_window"):
        return {
            "start_ms": int(item["source_window"].get("start_ms") or 0),
            "end_ms": int(item["source_window"].get("end_ms") or 0),
        }
    if item.get("time_ms"):
        return {
            "start_ms": int(item["time_ms"].get("start") or 0),
            "end_ms": int(item["time_ms"].get("end") or 0),
        }
    return {
        "start_ms": int((candidate or {}).get("start_ms") or 0),
        "end_ms": int((candidate or {}).get("end_ms") or 0),
    }


def reviewed_node(
    *,
    drama_id: str,
    drama: dict[str, str],
    item: dict[str, Any],
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    source_tier = drama["review_kind"]
    status = review_status(item)
    if source_tier == "reviewed" and status == "reject":
        influence = False
    else:
        influence = source_tier in {"reviewed", "schema_evidence"}
    return {
        "node_id": item["candidate_id"],
        "candidate_id": item["candidate_id"],
        "drama_id": drama_id,
        "drama_title": drama["title"],
        "source_tier": source_tier,
        "review_status": status,
        "valid_for_minimum_set": influence,
        "trigger_type": review_trigger(item),
        "rank_score": item.get("rank_score") or (candidate or {}).get("rank_score"),
        "hook": item.get("scene_specific_hook") or item.get("hook") or (candidate or {}).get("hook") or "",
        "node_summary": item.get("why_now_reviewed") or item.get("evidence_excerpt") or (candidate or {}).get("why_now") or "",
        "field_pressure_observed": item.get("pack_field_notes") or item.get("field_pressure_observed") or [],
        "missing_if_minimal_only": item.get("missing_if_v0_1_only") or "",
        "source_window": review_time_window(item, candidate),
        "candidate_ref": drama["candidates"],
        "review_ref": drama["review"],
        "evidence_basis": item.get("evidence_basis") or item.get("evidence_notes") or ["review"],
    }


def candidate_only_node(*, drama_id: str, drama: dict[str, str], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": candidate["candidate_id"],
        "candidate_id": candidate["candidate_id"],
        "drama_id": drama_id,
        "drama_title": drama["title"],
        "source_tier": "candidate_only",
        "review_status": "candidate_only",
        "valid_for_minimum_set": False,
        "trigger_type": normalize_trigger(candidate.get("trigger_type")),
        "rank_score": candidate.get("rank_score"),
        "hook": candidate.get("hook") or "",
        "node_summary": candidate.get("why_now") or candidate.get("evidence_excerpt") or "",
        "field_pressure_observed": [],
        "missing_if_minimal_only": "",
        "source_window": {"start_ms": int(candidate.get("start_ms") or 0), "end_ms": int(candidate.get("end_ms") or 0)},
        "candidate_ref": drama["candidates"],
        "review_ref": "",
        "evidence_basis": ["candidate"],
    }


def select_candidate_only(
    *,
    drama_id: str,
    drama: dict[str, str],
    candidates: list[dict[str, Any]],
    reviewed_ids: set[str],
    reviewed_triggers: set[str],
    min_rank_score: float,
) -> list[dict[str, Any]]:
    by_trigger: dict[str, dict[str, Any]] = {}
    for candidate in sorted(candidates, key=lambda item: item.get("rank_score") or 0, reverse=True):
        if candidate["candidate_id"] in reviewed_ids:
            continue
        trigger = normalize_trigger(candidate.get("trigger_type"))
        if trigger in reviewed_triggers:
            continue
        if (candidate.get("rank_score") or 0) < min_rank_score:
            continue
        by_trigger.setdefault(trigger, candidate)
    return [candidate_only_node(drama_id=drama_id, drama=drama, candidate=item) for item in by_trigger.values()]


def score_field(field: str, trigger: str, source_tier: str, has_visual_refs: bool) -> int:
    base_scores = {
        "source_window": 3,
        "review_and_provenance": 3,
        "companion_entry": 2,
        "action_space": 3,
        "response_contract": 3,
        "visual_result_policy": 2 if has_visual_refs else 1,
        "score_axes": 2,
        "actor_local_state": 3,
        "critical_stakes_state": 2,
        "local_constraint_state": 3,
        "escalation_risk": 2,
        "canon_baseline": 3,
        "watch_flow_rationale": 2,
    }
    score = base_scores.get(field, 0)
    trigger_score = TRIGGER_DEMANDS.get(trigger, {}).get(field)
    if trigger_score is not None:
        score = max(score, trigger_score)
    if source_tier == "candidate_only" and field == "review_and_provenance":
        score = 3
    return score


def score_note(field: str, trigger: str, score: int) -> str:
    if score < 2:
        return ""
    note = BASE_NOTES.get(field, "Needed for local consequence judgment.")
    if field in TRIGGER_DEMANDS.get(trigger, {}):
        return f"{note} Trigger `{trigger}` raises this field to score {score}."
    return note


def score_node(node: dict[str, Any], candidate: dict[str, Any] | None) -> dict[str, Any]:
    trigger = node["trigger_type"]
    has_visual_refs = bool((candidate or {}).get("source_refs", {}).get("keyframe_refs"))
    field_needs: dict[str, dict[str, Any]] = {}
    for field in FIELDS:
        score = score_field(field, trigger, node["source_tier"], has_visual_refs)
        field_needs[field] = {
            "need_score": score,
            "why_needed": score_note(field, trigger, score),
            "evidence_basis": "candidate" if node["source_tier"] == "candidate_only" else node["source_tier"],
            "confidence": "low" if node["source_tier"] == "candidate_only" else ("medium" if node["source_tier"] == "schema_evidence" else "high"),
        }
    return {
        "node_id": node["node_id"],
        "drama_id": node["drama_id"],
        "drama_title": node["drama_title"],
        "source_tier": node["source_tier"],
        "review_status": node["review_status"],
        "valid_for_minimum_set": node["valid_for_minimum_set"],
        "trigger_type": trigger,
        "rank_score": node["rank_score"],
        "source_refs": {
            "candidate_ref": node["candidate_ref"],
            "review_ref": node["review_ref"],
            "source_window": node["source_window"],
        },
        "node_summary": node["node_summary"],
        "hook": node["hook"],
        "field_pressure_observed": node["field_pressure_observed"],
        "field_needs": field_needs,
    }


def build_corpus(min_candidate_score: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    corpus_summary: dict[str, Any] = {}
    for drama_id, drama in DRAMAS.items():
        candidate_data = read_json(drama["candidates"])
        review_data = read_json(drama["review"])
        lookup = candidate_lookup(candidate_data)
        reviewed_raw = review_data.get("reviewed_candidates", [])
        reviewed: list[dict[str, Any]] = []
        for item in reviewed_raw:
            reviewed.append(reviewed_node(drama_id=drama_id, drama=drama, item=item, candidate=lookup.get(item["candidate_id"])))
        reviewed_ids = {item["candidate_id"] for item in reviewed}
        reviewed_triggers = {item["trigger_type"] for item in reviewed}
        candidate_only = select_candidate_only(
            drama_id=drama_id,
            drama=drama,
            candidates=candidate_data["candidates"],
            reviewed_ids=reviewed_ids,
            reviewed_triggers=reviewed_triggers,
            min_rank_score=min_candidate_score,
        )
        for node in reviewed + candidate_only:
            nodes.append(score_node(node, lookup.get(node["candidate_id"])))
        corpus_summary[drama_id] = {
            "title": drama["title"],
            "candidate_count": len(candidate_data["candidates"]),
            "review_input_count": len(reviewed),
            "candidate_only_added": len(candidate_only),
            "review_status_counts": dict(Counter(item["review_status"] for item in reviewed)),
            "trigger_counts_in_matrix": dict(Counter(item["trigger_type"] for item in reviewed + candidate_only)),
            "candidate_only_ids": [item["candidate_id"] for item in candidate_only],
        }
    return nodes, corpus_summary


def write_csv(path: Path, nodes: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "node_id",
                "drama_id",
                "source_tier",
                "review_status",
                "valid_for_minimum_set",
                "trigger_type",
                "rank_score",
                *FIELDS,
            ],
        )
        writer.writeheader()
        for node in nodes:
            row = {
                "node_id": node["node_id"],
                "drama_id": node["drama_id"],
                "source_tier": node["source_tier"],
                "review_status": node["review_status"],
                "valid_for_minimum_set": node["valid_for_minimum_set"],
                "trigger_type": node["trigger_type"],
                "rank_score": node["rank_score"],
            }
            row.update({field: node["field_needs"][field]["need_score"] for field in FIELDS})
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--min-candidate-score", type=float, default=58.0)
    args = parser.parse_args()

    out_dir = resolve_path(args.out_dir)
    nodes, corpus_summary = build_corpus(args.min_candidate_score)
    output = {
        "schema_version": "node_field_demand_matrix.v0.3",
        "method": "deterministic_discrete_field_need_scoring",
        "score_scale": {"0": "not_needed", "1": "helpful", "2": "important", "3": "required"},
        "candidate_field_vocabulary": FIELDS,
        "corpus_summary": corpus_summary,
        "node_count": len(nodes),
        "source_tier_counts": dict(Counter(item["source_tier"] for item in nodes)),
        "valid_for_minimum_set_count": sum(1 for item in nodes if item["valid_for_minimum_set"]),
        "nodes": nodes,
    }
    write_json(out_dir / "node_field_demand_matrix.v0.3.json", output)
    write_csv(out_dir / "node_field_demand_matrix.v0.3.csv", nodes)
    print(
        json.dumps(
            {
                "out_dir": repo_relative(out_dir),
                "node_count": len(nodes),
                "source_tier_counts": output["source_tier_counts"],
                "valid_for_minimum_set_count": output["valid_for_minimum_set_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
