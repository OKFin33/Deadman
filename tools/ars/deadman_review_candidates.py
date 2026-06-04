#!/usr/bin/env python3
"""Create a deterministic schema-evidence review sample from ARS candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)


FIELD_PRESSURE: dict[str, dict[str, Any]] = {
    "resource_crisis": {
        "fields": ["resource_scarcity", "distribution_target", "scarcity_level"],
        "missing": "Without resource fields, the judgment cannot price who eats now and who pays later.",
        "bucket": "OptionalCausalityModules",
    },
    "exposure_risk": {
        "fields": ["exposure_and_secrecy", "source_explanation", "witness_scope"],
        "missing": "Without exposure fields, hidden advantages become unconditional power.",
        "bucket": "OptionalCausalityModules",
    },
    "family_pressure": {
        "fields": ["relationship_pressure", "care_priority", "trust_delta_policy"],
        "missing": "Without relationship pressure, the result becomes generic plot commentary.",
        "bucket": "OptionalCausalityModules",
    },
    "village_pressure": {
        "fields": ["village_or_public_reputation", "witnesses", "exchange_dependency"],
        "missing": "Without witness/public fields, confrontation has no social cost.",
        "bucket": "OptionalCausalityModules",
    },
    "humiliation_reversal": {
        "fields": ["humiliation_reversal", "retaliation_scale", "escalation_risk"],
        "missing": "Without retaliation scale,爽感 cannot be balanced against cost.",
        "bucket": "OptionalCausalityModules",
    },
    "evidence_or_trap": {
        "fields": ["evidence_or_trap_logic", "evidence_refs", "proof_threshold"],
        "missing": "Without proof fields,反打 lacks credibility.",
        "bucket": "OptionalCausalityModules",
    },
    "system_rule": {
        "fields": ["system_or_hidden_power_rule", "rule_visibility", "power_cap"],
        "missing": "Without rule fields, system actions become unbounded cheats.",
        "bucket": "OptionalCausalityModules",
    },
    "survival_tradeoff": {
        "fields": ["survival_tradeoff", "minimum_safe_action", "long_term_risk"],
        "missing": "Without tradeoff fields, survival choices collapse into unconditional rescue.",
        "bucket": "OptionalCausalityModules",
    },
    "nonsense_or_overpowered_break": {
        "fields": ["power_cap", "softened_output_policy", "watch_flow_fit"],
        "missing": "Without guardrails, custom input can break watch flow.",
        "bucket": "ProducerReviewFields",
    },
    "hidden_power_rule": {
        "fields": ["hidden_power_rule", "power_state", "cost_or_cooldown", "power_cap"],
        "missing": "Without hidden-power constraints, cultivation scenes lose credibility.",
        "bucket": "GenreExtensions",
    },
    "identity_reveal": {
        "fields": ["identity_reveal", "reveal_scope", "leverage_loss"],
        "missing": "Without identity state,摊牌 timing cannot be judged.",
        "bucket": "GenreExtensions",
    },
    "relationship_betrayal": {
        "fields": ["betrayal_divorce_safety", "rupture_cost", "evidence_needed"],
        "missing": "Without betrayal and safety fields, divorce/revenge nodes become pure venting.",
        "bucket": "GenreExtensions",
    },
    "status_reversal": {
        "fields": ["status_reversal_bottom_card", "institutional_leverage", "future_reversal_value"],
        "missing": "Without bottom-card fields,打脸 timing cannot be balanced.",
        "bucket": "GenreExtensions",
    },
    "medical_or_pregnancy_risk": {
        "fields": ["medical_or_pregnancy_risk", "rescue_priority", "accountability_delay"],
        "missing": "Without bodily-risk fields,救人/算账 order is arbitrary.",
        "bucket": "GenreExtensions",
    },
}


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def select_candidates(candidates: list[dict[str, Any]], *, top_n: int, min_total: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = list(candidates[:top_n])
    seen = {item["candidate_id"] for item in selected}
    mechanisms = {item["trigger_type"] for item in selected}
    for item in candidates[top_n:]:
        if len(selected) >= min_total and item["trigger_type"] in mechanisms:
            continue
        if item["candidate_id"] in seen:
            continue
        selected.append(item)
        seen.add(item["candidate_id"])
        mechanisms.add(item["trigger_type"])
        if len(selected) >= min_total and len(mechanisms) >= 6:
            break
    return selected


def review_label(candidate: dict[str, Any], index: int) -> str:
    if index <= 3 and candidate["rank_score"] >= 68:
        return "demo_candidate"
    if candidate["rank_score"] >= 63:
        return "keep"
    if candidate["rank_score"] >= 54:
        return "schema_evidence"
    return "reject"


def evidence_basis(candidate: dict[str, Any]) -> list[str]:
    refs = candidate.get("source_refs") or {}
    basis: list[str] = []
    if refs.get("transcript_refs"):
        basis.append("transcript-based")
    if refs.get("keyframe_refs"):
        basis.append("visual-reference-based")
    if candidate.get("evidence_excerpt"):
        basis.append("inferred-from-window-text")
    return basis or ["low-evidence"]


def review_candidate(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    mechanism = candidate["trigger_type"]
    pressure = FIELD_PRESSURE.get(
        mechanism,
        {
            "fields": ["local_constraints"],
            "missing": "Needs reviewer judgment before promotion.",
            "bucket": "ProducerReviewFields",
        },
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "rank": candidate.get("rank"),
        "rank_score": candidate.get("rank_score"),
        "episode_id": candidate.get("episode_id"),
        "time_ms": {"start": candidate.get("start_ms"), "end": candidate.get("end_ms")},
        "trigger_type": mechanism,
        "label": review_label(candidate, index),
        "hook": candidate.get("hook"),
        "evidence_excerpt": candidate.get("evidence_excerpt"),
        "field_pressure_observed": pressure["fields"],
        "missing_if_v0_1_only": pressure["missing"],
        "evidence_basis": evidence_basis(candidate),
        "field_bucket_influence": pressure["bucket"],
        "influence_scope": "core_candidate" if mechanism in {"exposure_risk", "family_pressure", "evidence_or_trap"} else pressure["bucket"],
        "human_review_required_before_demo": True,
        "reviewer_note": "Deterministic schema-evidence review sample; not final pack truth.",
    }


def write_markdown(path: Path, drama_id: str, drama_title: str, reviewed: list[dict[str, Any]]) -> None:
    lines = [
        f"# {drama_title} Candidate Review Sample v0.2",
        "",
        "> Deterministic schema-evidence sample. Labels guide field induction only; human review is still required before runtime promotion.",
        "",
        "| # | Candidate | Label | Mechanism | Score | Field pressure | Evidence |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for index, item in enumerate(reviewed, start=1):
        fields = ", ".join(f"`{field}`" for field in item["field_pressure_observed"])
        evidence = str(item.get("evidence_excerpt") or "").replace("|", " ")
        lines.append(
            f"| {index} | `{item['candidate_id']}` | `{item['label']}` | `{item['trigger_type']}` | {item['rank_score']:.2f} | {fields} | {evidence} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-id", required=True)
    parser.add_argument("--drama-title", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--min-total", type=int, default=16)
    args = parser.parse_args()

    source = read_json(resolve_path(args.candidates))
    selected = select_candidates(source["candidates"], top_n=args.top_n, min_total=args.min_total)
    reviewed = [review_candidate(candidate, index) for index, candidate in enumerate(selected, start=1)]
    output = {
        "version": "v0.2",
        "drama_id": args.drama_id,
        "drama_title": args.drama_title,
        "source_candidates_ref": repo_relative(resolve_path(args.candidates)),
        "review_method": "deterministic_schema_evidence_sample",
        "review_count": len(reviewed),
        "label_counts": dict(Counter(item["label"] for item in reviewed)),
        "reviewed_candidates": reviewed,
    }
    out_json = resolve_path(args.out_json)
    write_json(out_json, output)
    write_markdown(resolve_path(args.out_md), args.drama_id, args.drama_title, reviewed)
    print(
        json.dumps(
            {
                "drama_id": args.drama_id,
                "review_count": len(reviewed),
                "label_counts": output["label_counts"],
                "out_json": repo_relative(out_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
