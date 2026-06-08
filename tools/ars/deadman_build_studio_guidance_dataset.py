#!/usr/bin/env python3
"""Build the Deadman v0.41 Studio Guidance Dataset.

This is a pre-real-provider artifact. It distills WindowTasteEval, Phase 2
reports, repair candidates, and reviewed runtime selected echoes into one
public-safe guidance dataset for Studio/CAB authoring. It does not call any
provider and does not promote runtime packs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_WINDOW_TASTE_PATH = REPO_ROOT / "data/evals/window_taste_eval.v0.1.json"
DEFAULT_WINDOW_JUDGE_PATH = REPO_ROOT / "data/evals/window_taste_phase2_judge_report.v0.1.json"
DEFAULT_EXCHANGE_REPORT_PATH = REPO_ROOT / "data/evals/studio_cab_exchange_authoring_phase2.v0.1.json"
DEFAULT_PHASE2_EVAL_PATH = REPO_ROOT / "data/evals/studio_cab_phase2_eval.v0.1.json"
DEFAULT_EXCHANGE_REPAIRS_PATH = REPO_ROOT / "data/evals/exchange_authoring_phase2_repair_candidates.v0.1.json"
DEFAULT_RUNTIME_MOMENTS_PATH = REPO_ROOT / "data/dramas/huangnian/moments.v0.1.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"

GUIDANCE_CONTRACT_REF = "docs/Studio_Guidance_Dataset_v0.1_Contract.md"
DATASET_CONTRACT_REF = "docs/Deadman_v0.41_Dataset_Development_Contract.md"
PHASE2_CONTRACT_REF = "docs/Deadman_v0.41_Phase2_Studio_CAB_Execution_Contract.md"
REAL_PROVIDER_PROOF_CONTRACT_REF = "docs/Studio_Real_Provider_Proof_v0.1_Contract.md"

ALLOWED_PROVENANCE = {
    "owner_confirmed",
    "owner_reviewed_reject",
    "owner_context_insufficient",
    "agent_labeled_negative",
    "phase2_repair",
    "runtime_reviewed",
    "draft_not_owner_reviewed",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--created-at", default="")
    args = parser.parse_args()

    created_at = args.created_at or now_iso()
    output_path = resolve_path(args.output)
    dataset = build_guidance_dataset(created_at=created_at)
    write_json(output_path, dataset)
    print(f"Wrote Studio Guidance Dataset: {repo_relative(output_path)}")
    return 0


def build_guidance_dataset(*, created_at: str) -> dict[str, Any]:
    window_taste = read_json(DEFAULT_WINDOW_TASTE_PATH)
    window_judge = read_json(DEFAULT_WINDOW_JUDGE_PATH)
    exchange_report = read_json(DEFAULT_EXCHANGE_REPORT_PATH)
    phase2_eval = read_json(DEFAULT_PHASE2_EVAL_PATH)
    exchange_repairs = read_json(DEFAULT_EXCHANGE_REPAIRS_PATH)
    runtime_moments = read_json(DEFAULT_RUNTIME_MOMENTS_PATH)

    items = list(window_taste["items"])
    by_id = {item["item_id"]: item for item in items}
    runs = list(exchange_report["runs"])
    runs_by_item = {run["item_id"]: run for run in runs}
    repair_items = list(exchange_repairs["items"])
    runtime_exchange_examples = runtime_selected_echo_examples(runtime_moments)

    source_artifacts = source_artifact_refs(
        [
            DEFAULT_WINDOW_TASTE_PATH,
            DEFAULT_WINDOW_JUDGE_PATH,
            DEFAULT_EXCHANGE_REPORT_PATH,
            DEFAULT_PHASE2_EVAL_PATH,
            DEFAULT_EXCHANGE_REPAIRS_PATH,
            DEFAULT_RUNTIME_MOMENTS_PATH,
        ]
    )
    window_split = build_window_selection_split(items, window_judge)
    context_split = build_context_card_split(items)
    lead_split = build_lead_authoring_split(items, runs_by_item, repair_items)
    reply_split = build_reply_authoring_split(items, runs_by_item, repair_items)
    selected_echo_split = build_selected_echo_split(runs, runtime_exchange_examples)
    custom_policy_split = build_custom_input_policy_split(runs)
    release_gate_rules = build_release_gate_rules()
    proof_plan = build_real_provider_proof_plan(phase2_eval, window_split, repair_items)

    summary = {
        "window_gold_examples": len(window_split["gold_examples"]),
        "window_negative_examples": len(window_split["negative_examples"]),
        "owner_reviewed_window_negative_or_context_examples": len(
            [
                item
                for item in window_split["negative_examples"]
                if item["provenance"] in {"owner_reviewed_reject", "owner_context_insufficient"}
            ]
        ),
        "lead_examples": len(lead_split["examples"]),
        "lead_rejected_examples": len(lead_split["rejected_examples"]),
        "lead_repair_examples": len(lead_split["repair_examples"]),
        "reply_examples": len(reply_split["examples"]),
        "reply_rejected_examples": len(reply_split["rejected_examples"]),
        "reply_repair_examples": len(reply_split["repair_examples"]),
        "runtime_reviewed_selected_echo_examples": len(selected_echo_split["runtime_reviewed_examples"]),
        "owner_reviewed_selected_echo_examples": len(selected_echo_split.get("owner_reviewed_examples", [])),
        "draft_selected_echo_examples": len(selected_echo_split["draft_examples"]),
        "real_provider_proof_cases_planned": len(proof_plan["planned_cases"]),
    }

    return {
        "schema_version": "studio_cab_guidance_dataset.v0.1",
        "product": "看剧搭子",
        "created_at": created_at,
        "status": "pre_real_provider_proof_ready",
        "claim_boundary": (
            "Canonical Studio/CAB guidance dataset distilled before real-provider proof. "
            "It is not a runtime pack, not a provider trace, and not demo promotion."
        ),
        "source_artifacts": source_artifacts,
        "contracts": [
            GUIDANCE_CONTRACT_REF,
            REAL_PROVIDER_PROOF_CONTRACT_REF,
            DATASET_CONTRACT_REF,
            PHASE2_CONTRACT_REF,
            "docs/WindowTasteEval_v0.1_Contract.md",
            "docs/CompanionExchangePack_v0.1_Contract.md",
        ],
        "agent_native_definition": {
            "runtime_contract": "Defines reviewed fields and publication gates for runtime-safe packs.",
            "evaluation_benchmark": "Defines gold preservation, hard-negative rejection, and authoring conformance checks.",
            "knowledge_boundary": "Defines evidence refs, blocked claims, and source-window limits.",
            "authoring_proof_substrate": "Provides examples, rejects, and repair cases for Studio/CAB draft generation.",
            "product_taste_guardrail": "Prevents drift into RPG menus, generic chat, producer analysis, or live default improvisation.",
        },
        "provenance_policy": {
            "allowed_values": sorted(ALLOWED_PROVENANCE),
            "owner_truth_values": [
                "owner_confirmed",
                "owner_reviewed_reject",
                "owner_context_insufficient",
                "runtime_reviewed",
            ],
            "non_owner_truth_values": [
                "agent_labeled_negative",
                "phase2_repair",
                "draft_not_owner_reviewed",
            ],
            "rule": "Field-level provenance must not be collapsed; provider drafts and Phase2 drafts cannot masquerade as reviewed runtime copy.",
        },
        "summary": summary,
        "splits": {
            "window_selection": window_split,
            "context_card_requirements": context_split,
            "lead_authoring": lead_split,
            "reply_authoring": reply_split,
            "selected_echo_direction": selected_echo_split,
            "custom_input_policy": custom_policy_split,
            "release_gate_rules": release_gate_rules,
        },
        "real_provider_proof_plan": proof_plan,
    }


def build_window_selection_split(items: list[dict[str, Any]], window_judge: dict[str, Any]) -> dict[str, Any]:
    scored_by_id = {item["item_id"]: item for item in window_judge["items"]}
    gold_examples = []
    negative_examples = []
    for item in items:
        scored = scored_by_id.get(item["item_id"], {})
        base = {
            "item_id": item["item_id"],
            "episode_id": item["episode_id"],
            "time_range": format_window(item["interaction_window"]),
            "source_origin": item["source_origin"],
            "window_review_decision": item["window_review"]["decision"],
            "window_review_source": item["window_review"]["decision_source"],
            "context_summary": {
                "episode_context": item["context_card"]["episode_context"],
                "scene_function": item["context_card"]["scene_function"],
                "relationship_state": item["context_card"]["character_relationship_state"],
                "mouthpiece_pressure": item["context_card"]["mouthpiece_pressure"],
                "dependency_note": item["context_card"]["dependency_note"],
            },
            "evidence_refs": list(item.get("evidence_refs", [])),
            "judge_score": scored.get("score"),
            "judge_decision": scored.get("decision"),
            "source_ref": f"{repo_relative(DEFAULT_WINDOW_TASTE_PATH)}#{item['item_id']}",
        }
        if item["label"] == "gold":
            gold_examples.append(
                base
                | {
                    "provenance": "owner_confirmed",
                    "why_good": item["why_now"],
                    "positive_axes": item.get("expected_reply_axes", []),
                    "opening_hypothesis": scored.get("opening_hypothesis") or item["context_card"]["mouthpiece_pressure"],
                }
            )
        else:
            negative_examples.append(
                base
                | {
                    "provenance": negative_provenance(item),
                    "why_bad": item.get("reject_reason", ""),
                    "penalty_axes": list(item.get("reject_dimensions", [])),
                    "training_weight": "owner_truth"
                    if negative_provenance(item) in {"owner_reviewed_reject", "owner_context_insufficient"}
                    else "negative_pressure",
                }
            )
    return {
        "task": "Decide whether Deadman should interrupt at this exact 10-second window.",
        "gold_examples": gold_examples,
        "negative_examples": negative_examples,
        "gate_snapshot": window_judge["acceptance_gate"],
    }


def build_context_card_split(items: list[dict[str, Any]]) -> dict[str, Any]:
    sufficient = []
    insufficient = []
    for item in items:
        card = item["context_card"]
        entry = {
            "item_id": item["item_id"],
            "episode_id": item["episode_id"],
            "provenance": "owner_confirmed" if item["label"] == "gold" else negative_provenance(item),
            "agent_input_readiness": card["agent_input_readiness"],
            "owner_review_outcome": card["owner_review_outcome"],
            "episode_context": card["episode_context"],
            "scene_function": card["scene_function"],
            "relationship_state": card["character_relationship_state"],
            "adjacent_asr": card["adjacent_asr"],
            "dependency_note": card["dependency_note"],
            "source_ref": f"{repo_relative(DEFAULT_WINDOW_TASTE_PATH)}#{item['item_id']}.context_card",
        }
        if card["agent_input_readiness"] == "context_insufficient":
            insufficient.append(entry)
        elif item["label"] == "gold":
            sufficient.append(entry)
    return {
        "task": "Ensure Studio/CAB has enough local story state before authoring.",
        "requirements": [
            "episode_context",
            "scene_function",
            "character_relationship_state",
            "adjacent_asr.current",
            "mouthpiece_pressure",
            "dependency_note",
        ],
        "speaker_cue_rule": "If ASR has no reliable diarization and role identity matters, add manual speaker cue in relationship_state or dependency_note.",
        "sufficient_examples": sufficient,
        "context_insufficient_examples": insufficient,
    }


def build_lead_authoring_split(
    items: list[dict[str, Any]],
    runs_by_item: dict[str, dict[str, Any]],
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    examples = []
    rejected = []
    repair_examples = [repair for repair in repairs if "lead" in repair["field"]]
    for item in items:
        if item["label"] != "gold":
            continue
        seed = item["context_card"]["authoring_seed"]
        run = runs_by_item.get(item["item_id"], {})
        draft = run.get("generated_draft", {}) if isinstance(run, dict) else {}
        examples.append(
            {
                "item_id": item["item_id"],
                "episode_id": item["episode_id"],
                "provenance": lead_reply_provenance(item, run),
                "review_status": field_review_status(item, run),
                "lead_text": draft.get("companion_lead") or seed.get("companion_lead_seed") or "",
                "seed_lead_text": seed.get("companion_lead_seed") or "",
                "scene_signal": item["viewer_line_pressure"],
                "policy": seed.get("lead_style_policy", ""),
                "source_ref": f"{repo_relative(DEFAULT_EXCHANGE_REPORT_PATH)}#{item['item_id']}.generated_draft.companion_lead",
            }
        )
        for index, rejected_item in enumerate(seed.get("rejected_lead_examples", [])):
            rejected.append(
                {
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "provenance": "owner_reviewed_reject",
                    "example_index": index,
                    "display_text": rejected_item["display_text"],
                    "negative_type": rejected_item["negative_type"],
                    "reject_reason": rejected_item["reject_reason"],
                    "correction_hint": rejected_item["correction_hint"],
                    "source_ref": f"{repo_relative(DEFAULT_WINDOW_TASTE_PATH)}#{item['item_id']}.authoring_seed.rejected_lead_examples[{index}]",
                }
            )
    return {
        "task": "Draft one compact scene-bound friend lead.",
        "rules": [
            "not_questionnaire",
            "not_ui_label",
            "not_direct_user_prompt",
            "not_producer_explanation",
            "scene_specific_but_open",
        ],
        "examples": examples,
        "rejected_examples": rejected,
        "repair_examples": repair_examples,
    }


def build_reply_authoring_split(
    items: list[dict[str, Any]],
    runs_by_item: dict[str, dict[str, Any]],
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    examples = []
    rejected = []
    repair_examples = [repair for repair in repairs if "reply_candidates" in repair["field"]]
    for item in items:
        if item["label"] != "gold":
            continue
        seed = item["context_card"]["authoring_seed"]
        run = runs_by_item.get(item["item_id"], {})
        draft = run.get("generated_draft", {}) if isinstance(run, dict) else {}
        for index, reply in enumerate(draft.get("reply_candidates", [])):
            examples.append(
                {
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "provenance": lead_reply_provenance(item, run),
                    "review_status": field_review_status(item, run),
                    "candidate_index": index,
                    "display_text": reply["display_text"],
                    "emotion_role": reply["emotion_role"],
                    "semantic_role": reply["semantic_role"],
                    "distinctness_rationale": reply["distinctness_rationale"],
                    "source_ref": f"{repo_relative(DEFAULT_EXCHANGE_REPORT_PATH)}#{item['item_id']}.generated_draft.reply_candidates[{index}]",
                }
            )
        for index, rejected_item in enumerate(seed.get("rejected_reply_examples", [])):
            rejected.append(
                {
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "provenance": "owner_reviewed_reject",
                    "example_index": index,
                    "display_text": rejected_item["display_text"],
                    "negative_type": rejected_item["negative_type"],
                    "reject_reason": rejected_item["reject_reason"],
                    "correction_hint": rejected_item["correction_hint"],
                    "source_ref": f"{repo_relative(DEFAULT_WINDOW_TASTE_PATH)}#{item['item_id']}.authoring_seed.rejected_reply_examples[{index}]",
                }
            )
    return {
        "task": "Draft exactly three distinct viewer-speech replies.",
        "rules": [
            "viewer_speech_not_axis_label",
            "not_rpg_action",
            "not_branch_choice",
            "not_producer_meta",
            "three_distinct_emotional_axes",
        ],
        "examples": examples,
        "rejected_examples": rejected,
        "repair_examples": repair_examples,
    }


def build_selected_echo_split(
    runs: list[dict[str, Any]],
    runtime_examples: list[dict[str, Any]],
) -> dict[str, Any]:
    draft_examples = []
    for run in runs:
        for index, reply in enumerate(run["generated_draft"]["reply_candidates"]):
            draft_examples.append(
                {
                    "item_id": run["item_id"],
                    "episode_id": run["episode_id"],
                    "provenance": "draft_not_owner_reviewed",
                    "review_status": "draft_not_owner_reviewed",
                    "candidate_index": index,
                    "display_text": reply["display_text"],
                    "selected_echo": reply["selected_echo"],
                    "source_ref": f"{repo_relative(DEFAULT_EXCHANGE_REPORT_PATH)}#{run['item_id']}.generated_draft.reply_candidates[{index}].selected_echo",
                }
            )
    return {
        "task": "Echo a selected preset as a short companion response, not a consequence report.",
        "rules": [
            "runtime_reviewed_examples_can_guide_product",
            "phase2_drafts_are_direction_only",
            "no_future_plot_claim",
            "no_explanation_report",
            "keep_friend_style_short",
        ],
        "runtime_reviewed_examples": runtime_examples,
        "owner_reviewed_examples": [],
        "draft_examples": draft_examples,
    }


def build_custom_input_policy_split(runs: list[dict[str, Any]]) -> dict[str, Any]:
    policy_examples = []
    for run in runs:
        policy = run["generated_draft"]["custom_reply_policy"]
        policy_examples.append(
            {
                "item_id": run["item_id"],
                "episode_id": run["episode_id"],
                "provenance": "draft_not_owner_reviewed",
                "policy_mode": policy.get("mode", ""),
                "hint": policy.get("hint", ""),
                "no_live_default_generation": bool(policy.get("no_live_default_generation")),
                "source_ref": f"{repo_relative(DEFAULT_EXCHANGE_REPORT_PATH)}#{run['item_id']}.generated_draft.custom_reply_policy",
            }
        )
    return {
        "task": "Bound custom input replies to current-window evidence and blocked claims.",
        "status": "policy_hints_only_loop1",
        "allowed_future_labels": [
            "safe_grounded_echo",
            "soften_unsupported_escalation",
            "reject_or_fallback",
            "future_branch_claim",
            "unbounded_revenge",
            "hidden_motive_inference",
            "low_signal_input",
        ],
        "policy_examples": policy_examples,
    }


def build_release_gate_rules() -> dict[str, Any]:
    return {
        "task": "Provide CI-facing product shape and publication gates.",
        "rules": [
            {
                "gate_id": "schema_validity",
                "must_pass": "publishable packs and tracked guidance/eval artifacts validate against schema",
            },
            {
                "gate_id": "publication_safety",
                "must_pass": "no raw media, provider trace, secret, hidden reasoning, or producer-local path in tracked artifacts",
            },
            {
                "gate_id": "product_shape",
                "must_pass": "default lead is not question-shaped; presets are viewer speech, not action menu or branch choice",
            },
            {
                "gate_id": "evidence_boundary",
                "must_pass": "no future-episode claim, hidden-motive inference, or source-window unsupported fact",
            },
            {
                "gate_id": "provenance_integrity",
                "must_pass": "agent-labeled negatives and provider drafts cannot masquerade as owner-reviewed labels",
            },
            {
                "gate_id": "runtime_boundary",
                "must_pass": "Studio guidance and provider proof do not promote runtime packs",
            },
        ],
    }


def build_real_provider_proof_plan(
    phase2_eval: dict[str, Any],
    window_split: dict[str, Any],
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_candidates = phase2_eval.get("phase3_demo_pack_candidates", [])[:3]
    owner_negatives = [
        item
        for item in window_split["negative_examples"]
        if item["provenance"] in {"owner_reviewed_reject", "owner_context_insufficient"}
    ][:3]
    repair_cases = select_repair_proof_cases(repairs, limit=2)
    planned_cases = []
    for candidate in gold_candidates:
        planned_cases.append(
            {
                "case_id": f"real_provider_gold:{candidate['item_id']}",
                "case_type": "owner_gold_exchange_authoring",
                "item_id": candidate["item_id"],
                "episode_id": candidate["episode_id"],
                "expected_behavior": "recommend window and draft complete CompanionExchangePack",
                "provenance": "owner_confirmed",
            }
        )
    for negative in owner_negatives:
        planned_cases.append(
            {
                "case_id": f"real_provider_negative:{negative['item_id']}",
                "case_type": "owner_reviewed_window_reject",
                "item_id": negative["item_id"],
                "episode_id": negative["episode_id"],
                "expected_behavior": "reject window or surface failure bucket",
                "provenance": negative["provenance"],
            }
        )
    for repair in repair_cases:
        planned_cases.append(
            {
                "case_id": f"real_provider_repair:{repair['repair_id']}",
                "case_type": "phase2_repair_regression",
                "item_id": repair["item_id"],
                "episode_id": repair["episode_id"],
                "expected_behavior": f"avoid {repair['failure_type']}",
                "provenance": "phase2_repair",
            }
        )
    return {
        "status": "prepared_not_run",
        "provider_invocation": "not_started",
        "requires_env": ["ARK_API_KEY", "ARK_MODEL or ARK_ENDPOINT_ID"],
        "tracked_output_when_run": "data/evals/studio_cab_real_provider_proof.v0.1.json",
        "raw_trace_policy": "raw prompt/response stay under ignored tmp/ or local_artifacts/ only",
        "sample_policy": "3 owner gold + 3 owner-reviewed rejects/context boundaries + 2 Phase2 repair cases",
        "planned_cases": planned_cases,
    }


def select_repair_proof_cases(repairs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_failure_types: set[str] = set()
    seen_item_ids: set[str] = set()
    for repair in repairs:
        failure_type = str(repair.get("failure_type") or "")
        item_id = str(repair.get("item_id") or "")
        if failure_type in seen_failure_types:
            continue
        selected.append(repair)
        seen_failure_types.add(failure_type)
        seen_item_ids.add(item_id)
        if len(selected) >= limit:
            return selected
    for repair in repairs:
        item_id = str(repair.get("item_id") or "")
        if item_id in seen_item_ids:
            continue
        selected.append(repair)
        seen_item_ids.add(item_id)
        if len(selected) >= limit:
            return selected
    return selected[:limit]


def runtime_selected_echo_examples(runtime_moments: dict[str, Any]) -> list[dict[str, Any]]:
    examples = []
    for moment in runtime_moments.get("moments", []):
        exchange = moment.get("companion_exchange")
        if not isinstance(exchange, dict) or exchange.get("review_status") != "reviewed":
            continue
        episode_id = episode_id_for_moment(moment)
        for index, reply in enumerate(exchange.get("reply_candidates", [])):
            examples.append(
                {
                    "moment_id": moment.get("moment_id", ""),
                    "episode_id": episode_id,
                    "provenance": "runtime_reviewed",
                    "review_status": "reviewed",
                    "candidate_index": index,
                    "companion_lead": exchange.get("companion_lead", ""),
                    "display_text": reply.get("display_text", ""),
                    "selected_echo": reply.get("selected_echo", ""),
                    "source_ref": f"{repo_relative(DEFAULT_RUNTIME_MOMENTS_PATH)}#{moment.get('moment_id', '')}.companion_exchange.reply_candidates[{index}]",
                    "compatibility_note": "Runtime reviewed source; v0.41 Studio guidance still applies stricter viewer-speech and no-RPG rules to new drafts.",
                }
            )
    return examples


def source_artifact_refs(paths: list[Path]) -> list[dict[str, str]]:
    refs = []
    for path in paths:
        data = read_json(path)
        refs.append(
            {
                "path": repo_relative(path),
                "sha256": sha256_file(path),
                "schema_version": str(data.get("schema_version") or data.get("collection_schema_version") or ""),
            }
        )
    return refs


def negative_provenance(item: dict[str, Any]) -> str:
    source = item["window_review"]["decision_source"]
    if source == "owner_episode_review":
        return "owner_reviewed_reject"
    if source == "owner_context_review":
        return "owner_context_insufficient"
    return "agent_labeled_negative"


def lead_reply_provenance(item: dict[str, Any], run: dict[str, Any] | None) -> str:
    if has_phase2_seed_repairs(run):
        return "phase2_repair"
    if item["context_card"].get("owner_review_outcome") in {"understood_gold", "understood_gold_with_revision"}:
        return "owner_confirmed"
    if run and run.get("review_status") in {"auto_reviewable", "needs_owner_review_before_demo"}:
        return "draft_not_owner_reviewed"
    return "draft_not_owner_reviewed"


def field_review_status(item: dict[str, Any], run: dict[str, Any] | None) -> str:
    if has_phase2_seed_repairs(run):
        return "phase2_repair_auto_applied"
    outcome = item["context_card"].get("owner_review_outcome")
    if outcome in {"understood_gold", "understood_gold_with_revision"}:
        return "owner_reviewed_positive"
    if run and run.get("review_status") == "needs_owner_review_before_demo":
        return "needs_owner_review_before_demo"
    return "draft_not_owner_reviewed"


def has_phase2_seed_repairs(run: dict[str, Any] | None) -> bool:
    if not run:
        return False
    audit = run.get("raw_seed_audit")
    if not isinstance(audit, dict):
        return False
    return bool(audit.get("failures"))


def episode_id_for_moment(moment: dict[str, Any]) -> str:
    source_drama = moment.get("source_drama")
    if isinstance(source_drama, dict) and source_drama.get("episode_id"):
        return str(source_drama["episode_id"])
    return str(moment.get("episode_id") or "")


def format_window(window: dict[str, Any]) -> str:
    return f"{ms_to_time(int(window['start_ms']))}-{ms_to_time(int(window['end_ms']))}"


def ms_to_time(value: int) -> str:
    total_seconds = value // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
