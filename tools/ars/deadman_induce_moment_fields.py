#!/usr/bin/env python3
"""Induce Deadman Moment Causality Pack v0.2 docs/schema from multi-drama ARS evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)


DRAMA_TITLES = {
    "huangnian": "荒年全村啃树皮，我有系统满仓肉",
    "yunmiao": "云渺",
    "lihun": "幸得相遇离婚时",
}

FIELD_DECISIONS: list[dict[str, Any]] = [
    {
        "field": "source_window",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Every moment needs episode/time/provenance before backend judgment or frontend marker rendering.",
        "consumer": "producer+backend+frontend",
    },
    {
        "field": "review_state",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "ARS outputs are bridge evidence; every promoted node needs review status and evidence/inference separation.",
        "consumer": "producer+backend",
    },
    {
        "field": "companion_surface",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "The frontstage companion needs marker, hook, and friend-tone entry copy.",
        "consumer": "frontend",
    },
    {
        "field": "viewer_impulse",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "All genres use the same product emotion: validating '要是我来' instinct before judging cost.",
        "consumer": "backend+LLM",
    },
    {
        "field": "actor_context",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Without local actors and roles, outputs become generic analysis rather than scene consequence.",
        "consumer": "backend+LLM",
    },
    {
        "field": "local_constraints",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "The core product promise is credible consequence, which requires hard local constraints.",
        "consumer": "backend+LLM",
    },
    {
        "field": "canon_baseline",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Needed to preserve watch flow and explain why original writing remains acceptable.",
        "consumer": "backend+LLM+frontend",
    },
    {
        "field": "action_space",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Preset and custom action routing both need typed, bounded action space.",
        "consumer": "backend+frontend",
    },
    {
        "field": "judgment_policy",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Prevents continuous timeline promises, unsupported facts, and unbounded power escalation.",
        "consumer": "backend+LLM",
    },
    {
        "field": "outcome_response_contract",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Keeps output to short local consequence plus optional original-plot note.",
        "consumer": "backend+LLM+frontend",
    },
    {
        "field": "score_axes",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "Ranking, review, and fallback judgment need stable axes; keep `watch_flow_fit`, not `return_to_plot_fit`.",
        "consumer": "producer+backend",
    },
    {
        "field": "visual_result_policy",
        "category": "CoreEnvelope",
        "decision": "core",
        "reason": "The product wants图文结合, but keyframes are refs, not visual truth.",
        "consumer": "producer+backend+frontend",
    },
    {
        "field": "resource_scarcity",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Strong in 荒年, not universal across cultivation/divorce genres.",
        "consumer": "backend+LLM",
    },
    {
        "field": "exposure_and_secrecy",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Appears in system, hidden-power, and status scenes, but not every moment.",
        "consumer": "backend+LLM",
    },
    {
        "field": "relationship_pressure",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Common in family/divorce scenes; still absent from pure evidence or power-rule moments.",
        "consumer": "backend+LLM",
    },
    {
        "field": "village_or_public_reputation",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Covers public witnesses in famine/village and social humiliation scenes.",
        "consumer": "backend+LLM",
    },
    {
        "field": "evidence_or_trap_logic",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Needed whenever反打 depends on proof, accounts, witnesses, or legal/business evidence.",
        "consumer": "backend+LLM",
    },
    {
        "field": "system_or_hidden_power_rule",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Shared by system and cultivation-like scenes; not needed for ordinary relationship beats.",
        "consumer": "backend+LLM",
    },
    {
        "field": "humiliation_reversal",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Short-drama爽感 staple, but its cost differs by scene mechanism.",
        "consumer": "backend+LLM",
    },
    {
        "field": "survival_tradeoff",
        "category": "OptionalCausalityModules",
        "decision": "optional",
        "reason": "Core to famine/survival moments; too specific for universal core.",
        "consumer": "backend+LLM",
    },
    {
        "field": "hidden_power_rule",
        "category": "GenreExtensions",
        "decision": "genre_extension",
        "reason": "Needed for 云渺-style hidden power/cultivation constraints.",
        "consumer": "LLM",
    },
    {
        "field": "identity_reveal",
        "category": "GenreExtensions",
        "decision": "genre_extension",
        "reason": "Needed where identity truth timing drives leverage.",
        "consumer": "LLM",
    },
    {
        "field": "betrayal_divorce_safety",
        "category": "GenreExtensions",
        "decision": "genre_extension",
        "reason": "Needed for 幸得相遇离婚时-style rupture, safety, and evidence timing.",
        "consumer": "LLM",
    },
    {
        "field": "status_reversal_bottom_card",
        "category": "GenreExtensions",
        "decision": "genre_extension",
        "reason": "Needed for CEO/offer/legal/business reversal timing.",
        "consumer": "LLM",
    },
    {
        "field": "medical_or_pregnancy_risk",
        "category": "GenreExtensions",
        "decision": "genre_extension",
        "reason": "Needed when bodily risk changes the priority between rescue and revenge.",
        "consumer": "LLM",
    },
    {
        "field": "producer_review_fields",
        "category": "ProducerReviewFields",
        "decision": "producer_required",
        "reason": "Keeps ASR/keyframe/inference hygiene explicit.",
        "consumer": "producer",
    },
    {
        "field": "branch_timeline",
        "category": "NonP0Fields",
        "decision": "exclude",
        "reason": "Implies continuous alternate plot, which P0 explicitly does not promise.",
        "consumer": "none",
    },
    {
        "field": "global_inventory",
        "category": "NonP0Fields",
        "decision": "exclude",
        "reason": "Only local resource state is needed; global mutation would recreate ArcForge-like continuity.",
        "consumer": "none",
    },
    {
        "field": "full_social_graph",
        "category": "NonP0Fields",
        "decision": "exclude",
        "reason": "Local actors/witnesses are enough for moment-level consequence.",
        "consumer": "none",
    },
    {
        "field": "auto_visual_truth",
        "category": "NonP0Fields",
        "decision": "exclude",
        "reason": "Keyframe refs do not prove object/person claims without human or visual-model review.",
        "consumer": "none",
    },
]


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_candidate_file(path: str) -> dict[str, Any]:
    data = read_json(resolve_path(path))
    return data


def load_review_file(path: str | None) -> dict[str, Any] | None:
    return read_json(resolve_path(path)) if path else None


def mechanism_counts(candidates: list[dict[str, Any]]) -> Counter[str]:
    return Counter(candidate["trigger_type"] for candidate in candidates)


def collect_drama(args: argparse.Namespace, drama_id: str, candidates_path: str, review_path: str | None, windows_path: str | None, buckets_path: str | None) -> dict[str, Any]:
    candidates = load_candidate_file(candidates_path)
    review = load_review_file(review_path)
    windows = read_json(resolve_path(windows_path)) if windows_path else None
    buckets = read_json(resolve_path(buckets_path)) if buckets_path else None
    return {
        "drama_id": drama_id,
        "title": DRAMA_TITLES.get(drama_id, drama_id),
        "candidates_ref": repo_relative(resolve_path(candidates_path)),
        "review_ref": repo_relative(resolve_path(review_path)) if review_path else "",
        "windows_ref": repo_relative(resolve_path(windows_path)) if windows_path else "",
        "buckets_ref": repo_relative(resolve_path(buckets_path)) if buckets_path else "",
        "candidate_count": candidates.get("candidate_count") or len(candidates.get("candidates") or []),
        "window_count": (windows or {}).get("window_count"),
        "bucket_count": (buckets or {}).get("bucket_count"),
        "review_count": (review or {}).get("review_count") or (review or {}).get("reviewed_count", 0),
        "label_counts": (review or {}).get("label_counts") or (review or {}).get("status_counts", {}),
        "mechanism_counts": dict(mechanism_counts(candidates.get("candidates") or [])),
        "reviewed": (review or {}).get("reviewed_candidates") or [],
    }


def field_evidence(drama: dict[str, Any], field: str) -> str:
    reviewed = drama.get("reviewed") or []
    hits = [
        item
        for item in reviewed
        if field in item.get("field_pressure_observed", [])
        or field in " ".join(item.get("field_pressure_observed", []))
        or field in item.get("trigger_type", "")
    ]
    if hits:
        examples = ", ".join(f"`{item['candidate_id']}`" for item in hits[:3])
        return f"{len(hits)} reviewed refs: {examples}"
    mechanisms = drama.get("mechanism_counts") or {}
    if field in {"source_window", "review_state", "companion_surface", "viewer_impulse", "actor_context", "local_constraints", "canon_baseline", "action_space", "judgment_policy", "outcome_response_contract", "score_axes", "visual_result_policy", "producer_review_fields"}:
        return f"all {drama['candidate_count']} candidates require it at runtime/review level"
    rough_map = {
        "resource_scarcity": ["resource_crisis", "survival_tradeoff"],
        "exposure_and_secrecy": ["exposure_risk", "system_rule", "hidden_power_rule", "identity_reveal"],
        "relationship_pressure": ["family_pressure", "relationship_betrayal", "medical_or_pregnancy_risk"],
        "village_or_public_reputation": ["village_pressure", "humiliation_reversal"],
        "evidence_or_trap_logic": ["evidence_or_trap", "status_reversal"],
        "system_or_hidden_power_rule": ["system_rule", "hidden_power_rule"],
        "humiliation_reversal": ["humiliation_reversal", "relationship_betrayal"],
        "survival_tradeoff": ["survival_tradeoff", "resource_crisis"],
        "hidden_power_rule": ["hidden_power_rule"],
        "identity_reveal": ["identity_reveal"],
        "betrayal_divorce_safety": ["relationship_betrayal"],
        "status_reversal_bottom_card": ["status_reversal"],
        "medical_or_pregnancy_risk": ["medical_or_pregnancy_risk"],
    }
    count = sum(mechanisms.get(mech, 0) for mech in rough_map.get(field, []))
    return f"{count} mechanism hits" if count else "-"


def render_matrix(dramas: list[dict[str, Any]]) -> str:
    lines = [
        "# Field Evidence Matrix v0.2",
        "",
        f"> Generated: {date.today().isoformat()}",
        "> Basis: source-based ARS for 荒年 / 云渺 / 幸得相遇离婚时. Migration reviews are deterministic schema-evidence samples, not final pack truth.",
        "",
        "## Source Coverage",
        "",
        "| Drama | Windows | Candidates | Buckets | Reviewed sample | Top mechanisms |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for drama in dramas:
        mechanisms = ", ".join(f"`{name}` {count}" for name, count in Counter(drama["mechanism_counts"]).most_common(5))
        lines.append(
            f"| {drama['title']} (`{drama['drama_id']}`) | {drama.get('window_count') or '-'} | {drama['candidate_count']} | {drama.get('bucket_count') or '-'} | {drama['review_count']} | {mechanisms} |"
        )
    lines.extend(
        [
            "",
            "## Field Decisions",
            "",
            "| Field | Category | Decision | 荒年 evidence | 云渺 evidence | 离婚 evidence | Product consequence |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    drama_by_id = {drama["drama_id"]: drama for drama in dramas}
    for item in FIELD_DECISIONS:
        lines.append(
            "| `{field}` | `{category}` | `{decision}` | {huangnian} | {yunmiao} | {lihun} | {reason} |".format(
                field=item["field"],
                category=item["category"],
                decision=item["decision"],
                huangnian=field_evidence(drama_by_id["huangnian"], item["field"]),
                yunmiao=field_evidence(drama_by_id["yunmiao"], item["field"]),
                lihun=field_evidence(drama_by_id["lihun"], item["field"]),
                reason=item["reason"].replace("|", " "),
            )
        )
    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            "- A field is `CoreEnvelope` only when absence would break every moment's source boundary, action routing, or viewer output.",
            "- Genre-specific pressure from 云渺 or 离婚 becomes `GenreExtensions`, not core, unless the same field is required by unrelated mechanisms.",
            "- `ProducerReviewFields` are required for tool hygiene but are not all consumed by the viewer runtime.",
            "- `NonP0Fields` stay out because they turn Deadman into continuous branch simulation.",
            "",
        ]
    )
    return "\n".join(lines)


def render_pack_doc(dramas: list[dict[str, Any]]) -> str:
    core = [item for item in FIELD_DECISIONS if item["category"] == "CoreEnvelope"]
    optional = [item for item in FIELD_DECISIONS if item["category"] == "OptionalCausalityModules"]
    genre = [item for item in FIELD_DECISIONS if item["category"] == "GenreExtensions"]
    producer = [item for item in FIELD_DECISIONS if item["category"] == "ProducerReviewFields"]
    nonp0 = [item for item in FIELD_DECISIONS if item["category"] == "NonP0Fields"]
    lines = [
        "# Moment Causality Pack v0.2",
        "",
        f"> Product: Deadman / 要是我来  ",
        f"> Generated: {date.today().isoformat()}  ",
        "> Contract: local credible consequence, not continuous alternate timeline.",
        "",
        "## 0. Runtime Boundary",
        "",
        "A `MomentCausalityPack` answers one local viewer question:",
        "",
        "```text",
        "要是我在这一刻这么做，当前局面里可信后果是什么？",
        "```",
        "",
        "It must not promise that later episodes follow this branch. It can briefly explain why the original plot remains watchable.",
        "",
        "## 1. CoreEnvelope",
        "",
        "Required for every promoted Deadman moment:",
        "",
    ]
    for item in core:
        lines.append(f"- `{item['field']}`: {item['reason']} Consumer: `{item['consumer']}`.")
    lines.extend(
        [
            "",
            "Minimal JSON shape:",
            "",
            "```json",
            json.dumps(example_pack_shape(), ensure_ascii=False, indent=2),
            "```",
            "",
            "## 2. OptionalCausalityModules",
            "",
            "Attach only when the reviewed candidate pressures the mechanism:",
            "",
        ]
    )
    for item in optional:
        lines.append(f"- `{item['field']}`: {item['reason']}")
    lines.extend(["", "## 3. GenreExtensions", ""])
    for item in genre:
        lines.append(f"- `{item['field']}`: {item['reason']}")
    lines.extend(["", "## 4. ProducerReviewFields", ""])
    for item in producer:
        lines.append(f"- `{item['field']}`: {item['reason']}")
    lines.extend(["", "## 5. NonP0Fields", ""])
    for item in nonp0:
        lines.append(f"- `{item['field']}`: {item['reason']}")
    lines.extend(
        [
            "",
            "## 6. ARS Miner Output Requirements",
            "",
            "Before a node can be promoted, ARS must emit:",
            "",
            "- timestamped `source_window` with transcript refs and keyframe/contact-sheet refs;",
            "- `trigger_type` plus candidate mechanism bucket;",
            "- scene-specific companion `hook` and 2-3 bounded `default_options`; ",
            "- `canon_baseline` and `original_plot_note` draft;",
            "- field-pressure notes for every optional or genre module it expects;",
            "- review/evidence flags separating ASR text, visual refs, and inference.",
            "",
        ]
    )
    return "\n".join(lines)


def example_pack_shape() -> dict[str, Any]:
    return {
        "pack_id": "drama_ep01_m001",
        "schema_version": "moment_causality_pack.v0.2",
        "source_drama": {
            "drama_id": "string",
            "title": "string",
            "episode_id": "string",
            "source_policy": "local media + ASR/keyframe evidence; reviewed before demo",
        },
        "source_window": {
            "start_ms": 0,
            "end_ms": 20000,
            "interaction_window": {"notice_at_seconds": 0, "start_seconds": 0, "end_seconds": 20},
            "transcript_refs": [],
            "keyframe_refs": [],
            "contact_sheet_ref": "",
        },
        "review_state": {
            "status": "schema_evidence|keep|demo_candidate|reject",
            "evidence_grade": "low|medium|high",
            "evidence_vs_inference": "string",
            "human_review_required": True,
        },
        "companion_surface": {"notice_marker": "!|?", "hook": "string", "friend_tone": "string"},
        "viewer_impulse": "string",
        "actor_context": {"pov_actor": "string", "directly_affected_actors": [], "relationship_context": "string"},
        "local_constraints": {"known_facts": [], "hidden_facts": [], "hard_constraints": [], "risk_notes": []},
        "canon_baseline": {"original_action": "string", "original_rationale": "string", "original_plot_note": "string"},
        "action_space": {"action_type": "string", "default_options": [], "custom_action_policy": {"allowed": True, "scope": "local credible consequence only"}},
        "optional_modules": {},
        "judgment_policy": {"must_consider": [], "must_not_claim": ["later episodes follow this branch", "unsupported facts", "unbounded power"]},
        "outcome_response_contract": {"format": "short local consequence + optional original plot note", "time_horizon": "current scene or immediate aftermath"},
        "visual_result_policy": {"preset_image_slot": "optional", "custom_image_policy": "realtime_or_text_only_fallback", "visual_truth_level": "keyframe_ref|reviewed|generated"},
        "score_axes": {"emotion_heat": 0, "choice_leverage": 0, "causal_clarity": 0, "world_constraint_value": 0, "watch_flow_fit": 0, "visual_result_fit": 0},
        "producer_review_fields": {"reviewer_notes": "", "field_evidence_refs": [], "open_questions": []},
    }


def render_report(dramas: list[dict[str, Any]]) -> str:
    lines = [
        "# Multi-Drama Field Induction Report v0.2",
        "",
        f"> Generated: {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        "This pass upgrades Deadman from a one-drama `荒年` bridge to a source-based three-genre field induction set. The result is not final pack truth for 云渺 or 幸得相遇离婚时; it is schema evidence for the minimum fields a future LLM judgment adapter must consume.",
        "",
        "## Per-Drama Results",
        "",
        "| Drama | Candidates | Reviewed | Label counts | Candidate artifact | Review artifact |",
        "|---|---:|---:|---|---|---|",
    ]
    for drama in dramas:
        labels = ", ".join(f"`{key}` {value}" for key, value in drama.get("label_counts", {}).items()) or "-"
        lines.append(f"| {drama['title']} | {drama['candidate_count']} | {drama['review_count']} | {labels} | `{drama['candidates_ref']}` | `{drama['review_ref'] or '-'}` |")
    lines.extend(
        [
            "",
            "## v0.1 Fields That Survived",
            "",
            "- `source_window`, `review_state`, `companion_surface.hook`, `viewer_impulse`, `actor_context`, `local_constraints`, `canon_baseline`, `action_space`, `judgment_policy`, `outcome_response_contract`, `watch_flow_fit`, `visual_result_policy`, and `producer_review_fields` survive as core.",
            "- `resource_scarcity`, `exposure_and_secrecy`, `relationship_pressure`, `village_or_public_reputation`, `evidence_or_trap_logic`, `system_or_hidden_power_rule`, `humiliation_reversal`, and `survival_tradeoff` survive as optional modules.",
            "",
            "## Renamed Or Split",
            "",
            "- `system_or_hidden_power_rule` now remains a shared optional module, while 云渺-specific pressure is split into `hidden_power_rule` and `identity_reveal` GenreExtensions.",
            "- Divorce/revenge pressure is not folded into generic `relationship_pressure`; it gets `betrayal_divorce_safety`, `status_reversal_bottom_card`, and `medical_or_pregnancy_risk` extensions.",
            "- `visual_result_policy` now explicitly covers preset image slots and custom text-only fallback.",
            "",
            "## Added For 云渺",
            "",
            "- `hidden_power_rule`: power state, rule visibility, cost/cooldown, power cap.",
            "- `identity_reveal`: reveal scope, leverage loss, misrecognition value.",
            "",
            "## Added For 幸得相遇离婚时",
            "",
            "- `betrayal_divorce_safety`: rupture cost, safety status, evidence needed.",
            "- `status_reversal_bottom_card`: institutional leverage, bottom-card timing, future reversal value.",
            "- `medical_or_pregnancy_risk`: rescue priority, evidence preservation, accountability delay.",
            "",
            "## Safe To Feed Backend Immediately",
            "",
            "- CoreEnvelope fields.",
            "- Optional module names and coarse field pressure.",
            "- Reviewed `荒年` demo packs.",
            "- Migration candidates only as schema evidence, not final frontstage moments.",
            "",
            "## Still Requires Human Review",
            "",
            "- Any 云渺 / 离婚 candidate before runtime promotion.",
            "- ASR-derived plot facts, named roles, quantities, injuries, pregnancy status, and visual claims.",
            "- Original plot note wording, because it directly affects whether users accept returning to the main drama.",
            "",
            "## Blockers / Provider Notes",
            "",
            "- No blocking provider failure is encoded in this report if per-drama ASR summaries show successful outputs. Check ignored `tmp/ars_*_analysis/volc_asr/summary.json` for provider-level details.",
            "- Raw provider responses remain under ignored `tmp/` paths.",
            "",
        ]
    )
    return "\n".join(lines)


def schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://oseria.local/deadman/moment_causality_pack.v0.2.schema.json",
        "title": "Deadman Moment Causality Pack v0.2",
        "type": "object",
        "required": [
            "pack_id",
            "schema_version",
            "source_drama",
            "source_window",
            "review_state",
            "companion_surface",
            "viewer_impulse",
            "actor_context",
            "local_constraints",
            "canon_baseline",
            "action_space",
            "judgment_policy",
            "outcome_response_contract",
            "visual_result_policy",
            "score_axes",
            "producer_review_fields",
        ],
        "properties": {
            "pack_id": {"type": "string"},
            "schema_version": {"const": "moment_causality_pack.v0.2"},
            "source_drama": {"type": "object"},
            "source_window": {"type": "object"},
            "review_state": {"type": "object"},
            "companion_surface": {"type": "object"},
            "viewer_impulse": {"type": "string"},
            "actor_context": {"type": "object"},
            "local_constraints": {"type": "object"},
            "canon_baseline": {"type": "object"},
            "action_space": {"type": "object"},
            "optional_modules": {
                "type": "object",
                "properties": {
                    "resource_scarcity": {"type": "object"},
                    "exposure_and_secrecy": {"type": "object"},
                    "relationship_pressure": {"type": "object"},
                    "village_or_public_reputation": {"type": "object"},
                    "evidence_or_trap_logic": {"type": "object"},
                    "system_or_hidden_power_rule": {"type": "object"},
                    "humiliation_reversal": {"type": "object"},
                    "survival_tradeoff": {"type": "object"},
                    "hidden_power_rule": {"type": "object"},
                    "identity_reveal": {"type": "object"},
                    "betrayal_divorce_safety": {"type": "object"},
                    "status_reversal_bottom_card": {"type": "object"},
                    "medical_or_pregnancy_risk": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "judgment_policy": {"type": "object"},
            "outcome_response_contract": {"type": "object"},
            "visual_result_policy": {"type": "object"},
            "score_axes": {"type": "object"},
            "producer_review_fields": {"type": "object"},
        },
        "additionalProperties": True,
        "x-deadman-field-decisions": FIELD_DECISIONS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--huangnian-candidates", required=True)
    parser.add_argument("--huangnian-review")
    parser.add_argument("--huangnian-windows", required=True)
    parser.add_argument("--huangnian-buckets", required=True)
    parser.add_argument("--yunmiao-candidates", required=True)
    parser.add_argument("--yunmiao-review", required=True)
    parser.add_argument("--yunmiao-windows", required=True)
    parser.add_argument("--yunmiao-buckets", required=True)
    parser.add_argument("--lihun-candidates", required=True)
    parser.add_argument("--lihun-review", required=True)
    parser.add_argument("--lihun-windows", required=True)
    parser.add_argument("--lihun-buckets", required=True)
    parser.add_argument("--out-pack-md", default="docs/Moment_Causality_Pack_v0.2.md")
    parser.add_argument("--out-matrix-md", default="docs/Field_Evidence_Matrix_v0.2.md")
    parser.add_argument("--out-report-md", default="docs/MultiDrama_Field_Induction_Report_v0.2.md")
    parser.add_argument("--out-schema", default="data/schemas/moment_causality_pack.v0.2.json")
    args = parser.parse_args()

    dramas = [
        collect_drama(args, "huangnian", args.huangnian_candidates, args.huangnian_review, args.huangnian_windows, args.huangnian_buckets),
        collect_drama(args, "yunmiao", args.yunmiao_candidates, args.yunmiao_review, args.yunmiao_windows, args.yunmiao_buckets),
        collect_drama(args, "lihun", args.lihun_candidates, args.lihun_review, args.lihun_windows, args.lihun_buckets),
    ]
    write_text(resolve_path(args.out_matrix_md), render_matrix(dramas))
    write_text(resolve_path(args.out_pack_md), render_pack_doc(dramas))
    write_text(resolve_path(args.out_report_md), render_report(dramas))
    write_json(resolve_path(args.out_schema), schema())
    print(
        json.dumps(
            {
                "dramas": [
                    {
                        "drama_id": drama["drama_id"],
                        "candidate_count": drama["candidate_count"],
                        "review_count": drama["review_count"],
                    }
                    for drama in dramas
                ],
                "out_pack_md": repo_relative(resolve_path(args.out_pack_md)),
                "out_matrix_md": repo_relative(resolve_path(args.out_matrix_md)),
                "out_report_md": repo_relative(resolve_path(args.out_report_md)),
                "out_schema": repo_relative(resolve_path(args.out_schema)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
