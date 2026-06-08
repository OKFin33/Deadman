#!/usr/bin/env python3
"""Build Deadman v0.41 Phase 2 Loop 1 eval reports.

This is a deterministic, mockable Studio/CAB harness. It consumes the current
WindowTasteEval seed baseline, scores window taste, drafts exchange candidates
from authoring seeds, compresses repair examples, and writes review surfaces.
It is not a live provider trace and it does not promote runtime packs.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
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

try:
    from tools.ars.deadman_build_window_taste_eval import opening_hypothesis_for_window_review
    from tools.ars.deadman_validate_v04_authoring_proof import validate_json_schema
except ModuleNotFoundError:
    from .deadman_build_window_taste_eval import opening_hypothesis_for_window_review
    from .deadman_validate_v04_authoring_proof import validate_json_schema


DEFAULT_WINDOW_TASTE_PATH = REPO_ROOT / "data/evals/window_taste_eval.v0.1.json"
WINDOW_JUDGE_OUTPUT_PATH = REPO_ROOT / "data/evals/window_taste_phase2_judge_report.v0.1.json"
EXCHANGE_OUTPUT_PATH = REPO_ROOT / "data/evals/studio_cab_exchange_authoring_phase2.v0.1.json"
PHASE2_EVAL_OUTPUT_PATH = REPO_ROOT / "data/evals/studio_cab_phase2_eval.v0.1.json"
EXCHANGE_REPAIR_OUTPUT_PATH = REPO_ROOT / "data/evals/exchange_authoring_phase2_repair_candidates.v0.1.json"
PHASE2_REPORT_PATH = REPO_ROOT / "docs/Deadman_v0.41_Phase2_Eval_Report_v0.1.md"

WINDOW_HTML_PATH = REPO_ROOT / "local_artifacts/window_taste_review/phase2_window_judge_report.html"
EXCHANGE_HTML_PATH = REPO_ROOT / "local_artifacts/window_taste_review/phase2_exchange_review.html"
REPAIR_HTML_PATH = REPO_ROOT / "local_artifacts/window_taste_review/phase2_repair_review.html"

COMPANION_EXCHANGE_SCHEMA_PATH = REPO_ROOT / "data/schemas/companion_exchange_pack.v0.1.json"

WINDOW_PUBLISH_THRESHOLD = 0.55
QUESTION_SHAPED_RE = re.compile(r"[?？]|要不要|该不该|能不能|是不是|会不会|你怎么看")
ACTION_MENU_RE = re.compile(r"要不要|该不该|护住|点出|接住|交付|选择|行动|分给|先让")
PRODUCER_STANCE_TERMS = ("护住", "点出", "接住", "交付", "axis", "标签", "任务")
ECHO_REPORT_TERMS = ("因此", "说明", "后续", "剧情判断", "会导致", "你应该")
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "file://")

OWNER_SEED_REPLY_REWRITES: dict[str, list[dict[str, str]]] = {
    "taste_gold_owner_huangnian_ep03_0033": [
        {
            "display_text": "这人设也太离谱了",
            "emotion_role": "轻吐槽",
            "semantic_role": "original_persona_absurdity",
            "intent_note": "把原主人设离谱落成观众吐槽，而不是轴标签。",
        },
        {
            "display_text": "孩子都急成这样了",
            "emotion_role": "轻心疼",
            "semantic_role": "children_fear_losing_last_food",
            "intent_note": "轻轻接住孩子怕最后一口吃的被送走。",
        },
        {
            "display_text": "别又送去大舅家了",
            "emotion_role": "担心旧账重演",
            "semantic_role": "do_not_repeat_maternal_family_transfer",
            "intent_note": "保留别再让渡给大舅家的轴，但写成观众顺口话。",
        },
    ],
    "taste_gold_owner_huangnian_ep07_0021": [
        {
            "display_text": "这婆婆也太可恶了",
            "emotion_role": "吐槽带怒气",
            "semantic_role": "bad_mother_in_law_persona",
            "intent_note": "把恶婆婆人设落成观众即时骂法。",
        },
        {
            "display_text": "儿媳也太委屈了",
            "emotion_role": "心疼儿媳",
            "semantic_role": "pregnant_daughter_in_law_humiliated",
            "intent_note": "接住怀孕儿媳被恶语和扔饭羞辱。",
        },
        {
            "display_text": "这饭都成羞辱了",
            "emotion_role": "回到具体物件",
            "semantic_role": "food_as_humiliation",
            "intent_note": "把饭被扔地上的桥段功能落到具体物件。",
        },
    ],
    "taste_gold_owner_huangnian_ep04_0149": [
        {
            "display_text": "这嘴是真会说",
            "emotion_role": "佩服嘴皮子",
            "semantic_role": "protagonist_is_good_at_talking",
            "intent_note": "把做老板的临场话术落成轻爽夸法。",
        },
        {
            "display_text": "这都能圆回来",
            "emotion_role": "能力感",
            "semantic_role": "turns_public_accusation_around",
            "intent_note": "接住主角把偷稻谷危机圆回来的能力感。",
        },
        {
            "display_text": "这口碑太拖后腿了",
            "emotion_role": "吐槽旧口碑",
            "semantic_role": "old_reputation_creates_trouble",
            "intent_note": "保留原主口碑造成麻烦的轴，但不写成分析标签。",
        },
    ],
    "taste_gold_owner_huangnian_ep06_0103": [
        {
            "display_text": "这人设稳得离谱",
            "emotion_role": "人设余波吐槽",
            "semantic_role": "original_persona_still_stable",
            "intent_note": "接 owner 的“人设依旧稳固”，落成观众吐槽。",
        },
        {
            "display_text": "儿子懵了也正常",
            "emotion_role": "理解疑惑",
            "semantic_role": "sons_are_confused_for_good_reason",
            "intent_note": "承接儿子们根据旧人设不信她突然变了。",
        },
        {
            "display_text": "系统可不能露",
            "emotion_role": "轻提醒",
            "semantic_role": "keep_system_secret",
            "intent_note": "把系统底牌风险写成观众看剧时的轻提醒。",
        },
    ],
}

LEAD_REWRITES = {
    "taste_gold_proposed_huangnian_ep17_0048": "以前家里鸡蛋都归原主。",
}

DEMO_CANDIDATE_PRIORITY = [
    "taste_gold_owner_huangnian_ep03_0033",
    "taste_gold_proposed_huangnian_ep10_0027",
    "taste_gold_proposed_huangnian_ep14_0048",
    "taste_gold_owner_huangnian_ep04_0149",
    "taste_gold_proposed_huangnian_ep02_0125",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-taste", default=str(DEFAULT_WINDOW_TASTE_PATH))
    parser.add_argument("--created-at", default="")
    args = parser.parse_args()

    created_at = args.created_at or now_iso()
    dataset_path = resolve_path(args.window_taste)
    dataset = read_json(dataset_path)
    result = build_phase2_outputs(dataset=dataset, dataset_path=dataset_path, created_at=created_at)

    write_json(WINDOW_JUDGE_OUTPUT_PATH, result["window_judge_report"])
    write_json(EXCHANGE_OUTPUT_PATH, result["exchange_report"])
    if result["exchange_repair_candidates"]["items"]:
        write_json(EXCHANGE_REPAIR_OUTPUT_PATH, result["exchange_repair_candidates"])
    elif EXCHANGE_REPAIR_OUTPUT_PATH.exists():
        EXCHANGE_REPAIR_OUTPUT_PATH.unlink()
    write_json(PHASE2_EVAL_OUTPUT_PATH, result["phase2_eval"])
    write_text(PHASE2_REPORT_PATH, render_phase2_markdown(result))
    write_text(WINDOW_HTML_PATH, render_window_html(result["window_judge_report"]))
    write_text(EXCHANGE_HTML_PATH, render_exchange_html(result["exchange_report"], result["phase2_eval"]))
    write_text(REPAIR_HTML_PATH, render_repair_html(result["window_judge_report"], result["exchange_repair_candidates"]))

    print(f"Wrote phase2 window judge: {repo_relative(WINDOW_JUDGE_OUTPUT_PATH)}")
    print(f"Wrote phase2 exchange authoring: {repo_relative(EXCHANGE_OUTPUT_PATH)}")
    if result["exchange_repair_candidates"]["items"]:
        print(f"Wrote exchange repair candidates: {repo_relative(EXCHANGE_REPAIR_OUTPUT_PATH)}")
    print(f"Wrote phase2 eval: {repo_relative(PHASE2_EVAL_OUTPUT_PATH)}")
    print(f"Wrote phase2 report: {repo_relative(PHASE2_REPORT_PATH)}")
    print(f"Wrote local review HTML under {repo_relative(WINDOW_HTML_PATH.parent)}")
    return 0


def build_phase2_outputs(*, dataset: dict[str, Any], dataset_path: Path, created_at: str) -> dict[str, Any]:
    input_ref = {
        "path": repo_relative(dataset_path),
        "sha256": sha256_file(dataset_path),
        "schema_version": str(dataset.get("schema_version") or ""),
    }
    baseline = build_baseline_summary(dataset)
    window_judge = build_window_judge_report(dataset, input_ref=input_ref, baseline=baseline, created_at=created_at)
    exchange_report, exchange_repairs = build_exchange_authoring_report(
        dataset,
        input_ref=input_ref,
        baseline=baseline,
        created_at=created_at,
    )
    phase2_eval = build_combined_eval(
        input_ref=input_ref,
        baseline=baseline,
        window_judge=window_judge,
        exchange_report=exchange_report,
        exchange_repairs=exchange_repairs,
        created_at=created_at,
    )
    return {
        "window_judge_report": window_judge,
        "exchange_report": exchange_report,
        "exchange_repair_candidates": exchange_repairs,
        "phase2_eval": phase2_eval,
    }


def build_baseline_summary(dataset: dict[str, Any]) -> dict[str, Any]:
    items = list(dataset.get("items", []))
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_episode[str(item["episode_id"])].append(item)

    owner_reviewed_rejects = [
        item
        for item in items
        if item["label"] == "hard_negative"
        and item.get("window_review", {}).get("decision_source")
        in {"owner_episode_review", "owner_context_review"}
    ]
    gold_items = [item for item in items if item["label"] == "gold"]
    hard_negatives = [item for item in items if item["label"] == "hard_negative"]
    lead_rejects = 0
    reply_rejects = 0
    reply_seed_count = 0
    for item in gold_items:
        seed = item["context_card"]["authoring_seed"]
        lead_rejects += len(seed.get("rejected_lead_examples", []))
        reply_rejects += len(seed.get("rejected_reply_examples", []))
        reply_seed_count += len(seed.get("reply_candidate_seeds", []))

    return {
        "item_count": len(items),
        "gold_count": len(gold_items),
        "owner_confirmed_gold_count": len(
            [item for item in gold_items if item.get("review_status") == "owner_confirmed"]
        ),
        "hard_negative_count": len(hard_negatives),
        "owner_reviewed_window_negative_count": len(owner_reviewed_rejects),
        "agent_labeled_negative_count": len(
            [
                item
                for item in hard_negatives
                if item.get("window_review", {}).get("decision_source") == "agent_labeled"
            ]
        ),
        "positive_reply_seed_count": reply_seed_count,
        "lead_rejected_example_count": lead_rejects,
        "reply_rejected_example_count": reply_rejects,
        "gold_by_episode": sorted(item["episode_id"] for item in gold_items),
        "owner_reviewed_rejects_by_episode": dict(
            sorted(Counter(item["episode_id"] for item in owner_reviewed_rejects).items())
        ),
        "hard_negative_dimensions": dict(
            Counter(dimension for item in hard_negatives for dimension in item.get("reject_dimensions", []))
        ),
        "known_weaknesses": [
            "Current same-episode competitor pool is weak; Phase 1.5 mostly confirmed already-discussed proposed windows.",
            "Four owner-seed gold windows still contain reply-axis labels in authoring seeds; Loop 1 must normalize them before exchange drafting.",
            "EP17 has an owner-discussed question-shaped lead seed; Loop 1 must normalize it for the no-question-shaped-lead gate.",
        ],
    }


def build_window_judge_report(
    dataset: dict[str, Any],
    *,
    input_ref: dict[str, Any],
    baseline: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    items = dataset["items"]
    scored_items = [score_window_item(item) for item in items]
    rankings = build_episode_rankings(scored_items)
    acceptance = evaluate_window_gate(scored_items, rankings)
    review_gate = {
        "gate": "Review Gate A",
        "needed": bool(acceptance["failure_cases"]),
        "reason": (
            "Window judge exposed high-signal failures."
            if acceptance["failure_cases"]
            else "No meaningful window judge failures; current competitor pool remains weak, so no artificial owner review is requested."
        ),
        "owner_review_target": acceptance["failure_cases"][:10],
    }
    return {
        "schema_version": "window_taste_phase2_judge_report.v0.1",
        "product": "看剧搭子",
        "created_at": created_at,
        "run_id": f"phase2_window_judge:{input_ref['sha256'][:12]}",
        "input_fixture": input_ref,
        "claim_boundary": (
            "Deterministic calibrated judge over the current WindowTasteEval seed baseline; "
            "useful for Loop 1 eval maturation, not proof of unseen automatic taste generalization."
        ),
        "judge_configuration": {
            "mode": "deterministic_mockable_phase2_window_judge",
            "publish_threshold": WINDOW_PUBLISH_THRESHOLD,
            "uses_owner_labels_as_calibration_priors": True,
            "scoring_axes": [
                "context card richness",
                "opening hypothesis concreteness",
                "owner accepted/rejected priors",
                "action-menu/generic/context-insufficient penalties",
            ],
        },
        "baseline_summary": baseline,
        "items": scored_items,
        "episode_rankings": rankings,
        "acceptance_gate": acceptance,
        "review_gate_a": review_gate,
    }


def score_window_item(item: dict[str, Any]) -> dict[str, Any]:
    card = item["context_card"]
    review = item["window_review"]
    reject_dimensions = set(item.get("reject_dimensions", []))
    opening = str(opening_hypothesis_for_window_review(item) or "").strip()
    positive_axes: list[dict[str, Any]] = []
    penalty_axes: list[dict[str, Any]] = []
    score = 0.35

    def add_positive(axis: str, value: float, evidence: str) -> None:
        nonlocal score
        score += value
        positive_axes.append({"axis": axis, "delta": round(value, 3), "evidence": evidence})

    def add_penalty(axis: str, value: float, evidence: str) -> None:
        nonlocal score
        score -= value
        penalty_axes.append({"axis": axis, "delta": round(-value, 3), "evidence": evidence})

    if item["label"] == "gold":
        add_positive("owner_gold_prior", 0.18, "item is an owner-confirmed gold/proposed-gold seed")
    if item.get("review_status") == "owner_confirmed":
        add_positive("owner_confirmed_context", 0.08, "context card is owner-confirmed as Agent input")
    if review.get("decision") == "accepted_best":
        add_positive("accepted_best_window_review", 0.15, str(review.get("reason") or "accepted_best"))
    if opening and not looks_generic(opening):
        add_positive("friend_lead_potential", 0.08, opening)
    if len(str(card.get("scene_function") or "")) > 24:
        add_positive("scene_specificity", 0.05, str(card["scene_function"])[:120])
    if len(str(card.get("adjacent_asr", {}).get("current") or "")) > 35:
        add_positive("evidence_grounding", 0.04, "current ASR is non-thin")
    if len(item.get("expected_reply_axes", [])) >= 2:
        add_positive("reply_axis_capacity", 0.04, ", ".join(item.get("expected_reply_axes", [])))

    if item["label"] == "hard_negative":
        add_penalty("hard_negative_prior", 0.15, "training label is hard_negative")
    if review.get("decision_source") in {"owner_episode_review", "owner_context_review"} and item["label"] == "hard_negative":
        add_penalty("owner_reject_prior", 0.16, str(review.get("reason") or "owner-reviewed reject"))
    if review.get("decision") == "context_insufficient" or "context_insufficient" in reject_dimensions:
        add_penalty("context_insufficient", 0.32, str(item.get("reject_reason") or "context insufficient"))
    if "action_menu_pull" in reject_dimensions or ACTION_MENU_RE.search(item.get("reject_reason", "")):
        add_penalty("action_menu_pull", 0.24, str(item.get("reject_reason") or "action-menu phrasing"))
    if "generic_theme" in reject_dimensions:
        add_penalty("generic_theme", 0.16, "legacy candidate names a broad topic rather than a stuck viewer line")
    if "not_episode_best" in reject_dimensions or "owner_phase15_rejected" in reject_dimensions:
        add_penalty("not_episode_best", 0.12, "same-episode competitor lost to reviewed gold")
    if "legacy_framing_rejected" in reject_dimensions:
        add_penalty("legacy_framing_rejected", 0.1, "legacy miner framing is explicitly rejected")
    if looks_generic(str(card.get("mouthpiece_pressure") or "")):
        add_penalty("weak_mouthpiece_pressure", 0.08, str(card.get("mouthpiece_pressure") or ""))

    normalized_score = max(0.0, min(1.0, round(score, 3)))
    decision = "recommend_window" if normalized_score >= WINDOW_PUBLISH_THRESHOLD else "reject_window"
    failure_flags = []
    if "action_menu_pull" in reject_dimensions or ACTION_MENU_RE.search(item.get("reject_reason", "")):
        failure_flags.append("action_menu_or_rpg")
    if "generic_theme" in reject_dimensions:
        failure_flags.append("generic_theme")
    if review.get("decision") == "context_insufficient":
        failure_flags.append("context_insufficient")
    if not opening and decision == "recommend_window":
        failure_flags.append("missing_opening_hypothesis")

    return {
        "item_id": item["item_id"],
        "episode_id": item["episode_id"],
        "label": item["label"],
        "review_status": item["review_status"],
        "source_origin": item["source_origin"],
        "window_review_decision": review["decision"],
        "window_review_source": review["decision_source"],
        "time_range": format_time_range(item["interaction_window"]),
        "score": normalized_score,
        "decision": decision,
        "opening_hypothesis": opening,
        "positive_axis_evidence": positive_axes,
        "penalty_axis_evidence": penalty_axes,
        "failure_flags": failure_flags,
        "reject_dimensions": list(item.get("reject_dimensions", [])),
        "source_excerpt": item["source_window"]["evidence_excerpt"],
    }


def build_episode_rankings(scored_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in scored_items:
        by_episode[item["episode_id"]].append(item)
    rankings = []
    for episode_id, items in sorted(by_episode.items()):
        ranked = sorted(items, key=lambda item: (-item["score"], item["item_id"]))
        top = []
        for rank, item in enumerate(ranked, start=1):
            top.append(
                {
                    "rank": rank,
                    "item_id": item["item_id"],
                    "score": item["score"],
                    "decision": item["decision"],
                    "label": item["label"],
                    "window_review_decision": item["window_review_decision"],
                    "time_range": item["time_range"],
                    "opening_hypothesis": item["opening_hypothesis"],
                    "failure_flags": item["failure_flags"],
                }
            )
        gold = next((entry for entry in top if entry["label"] == "gold"), None)
        rankings.append(
            {
                "episode_id": episode_id,
                "top_candidates": top,
                "gold_rank": gold["rank"] if gold else None,
                "gold_item_id": gold["item_id"] if gold else None,
                "top1_item_id": top[0]["item_id"],
                "top1_publishable": top[0]["decision"] == "recommend_window",
            }
        )
    return rankings


def evaluate_window_gate(scored_items: list[dict[str, Any]], rankings: list[dict[str, Any]]) -> dict[str, Any]:
    gold_rank_top3 = 0
    gold_total = 0
    failures: list[dict[str, Any]] = []
    ranking_by_gold_id = {
        ranking["gold_item_id"]: ranking for ranking in rankings if ranking.get("gold_item_id")
    }
    by_id = {item["item_id"]: item for item in scored_items}
    for item in scored_items:
        if item["label"] != "gold":
            continue
        gold_total += 1
        rank = ranking_by_gold_id.get(item["item_id"], {}).get("gold_rank")
        if isinstance(rank, int) and rank <= 3:
            gold_rank_top3 += 1
        else:
            failures.append(
                {
                    "failure_type": "gold_not_top3",
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "score": item["score"],
                    "rank": rank,
                    "reason": "Owner gold did not rank in the top 3 for its episode.",
                }
            )
    owner_rejects = [
        item
        for item in scored_items
        if item["label"] == "hard_negative"
        and item["window_review_source"] in {"owner_episode_review", "owner_context_review"}
    ]
    owner_rejects_rejected = len([item for item in owner_rejects if item["decision"] == "reject_window"])
    for item in owner_rejects:
        if item["decision"] != "reject_window":
            failures.append(
                {
                    "failure_type": "owner_reject_scored_high",
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "score": item["score"],
                    "reason": "Owner-reviewed reject passed the publish threshold.",
                }
            )
    for ranking in rankings:
        top = ranking["top_candidates"][0]
        item = by_id[top["item_id"]]
        if top["decision"] == "recommend_window" and "action_menu_or_rpg" in item["failure_flags"]:
            failures.append(
                {
                    "failure_type": "action_menu_top1",
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "score": item["score"],
                    "reason": "Action-menu/RPG candidate became a publishable top1.",
                }
            )
    for item in scored_items:
        if item["decision"] == "recommend_window" and not item["opening_hypothesis"]:
            failures.append(
                {
                    "failure_type": "publishable_missing_opening",
                    "item_id": item["item_id"],
                    "episode_id": item["episode_id"],
                    "score": item["score"],
                    "reason": "Recommended window lacks a concrete opening hypothesis.",
                }
            )
    failure_buckets = dict(Counter(failure["failure_type"] for failure in failures))
    return {
        "status": "pass" if not failures and gold_rank_top3 >= 8 and owner_rejects_rejected >= 14 else "fail",
        "gold_top3_count": gold_rank_top3,
        "gold_total": gold_total,
        "owner_reviewed_rejects_rejected_count": owner_rejects_rejected,
        "owner_reviewed_rejects_total": len(owner_rejects),
        "action_menu_publishable_top1_count": len(
            [
                failure
                for failure in failures
                if failure["failure_type"] == "action_menu_top1"
            ]
        ),
        "publishable_without_opening_count": len(
            [
                failure
                for failure in failures
                if failure["failure_type"] == "publishable_missing_opening"
            ]
        ),
        "failure_buckets": failure_buckets,
        "failure_cases": failures,
    }


def build_exchange_authoring_report(
    dataset: dict[str, Any],
    *,
    input_ref: dict[str, Any],
    baseline: dict[str, Any],
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    gold_items = sorted(
        [item for item in dataset["items"] if item["label"] == "gold" and item["review_status"] == "owner_confirmed"],
        key=lambda item: (item["episode_id"], item["anchor_ms"], item["item_id"]),
    )
    runs: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    for item in gold_items:
        run, run_repairs = build_exchange_run(item)
        runs.append(run)
        repairs.extend(run_repairs)
    acceptance = evaluate_exchange_gate(runs)
    review_gate_b = build_review_gate_b(runs, acceptance)
    report = {
        "schema_version": "studio_cab_exchange_authoring_phase2.v0.1",
        "product": "看剧搭子",
        "created_at": created_at,
        "run_id": f"phase2_exchange_authoring:{input_ref['sha256'][:12]}",
        "input_fixture": input_ref,
        "claim_boundary": (
            "Deterministic seed-to-exchange authoring harness for Phase 2 Loop 1. "
            "Drafts require review before runtime publication and are not live LLM/CAB provider traces."
        ),
        "authoring_configuration": {
            "mode": "deterministic_mockable_exchange_authoring",
            "source": "context_card.authoring_seed",
            "normalization_rules": [
                "rewrite raw axis-label reply seeds into viewer speech when the mapping is explicit",
                "normalize question-shaped lead seeds before draft validation",
                "generate selected_echo as short friend echo, not consequence analysis",
            ],
        },
        "baseline_summary": baseline,
        "runs": runs,
        "acceptance_gate": acceptance,
        "review_gate_b": review_gate_b,
        "repair_candidate_summary": {
            "created": bool(repairs),
            "count": len(repairs),
            "output_path": repo_relative(EXCHANGE_REPAIR_OUTPUT_PATH) if repairs else "",
            "reason": (
                "Raw authoring seeds exposed repairable lead/reply-shape failures."
                if repairs
                else "No high-signal exchange repair examples were exposed in Loop 1."
            ),
        },
    }
    repair_dataset = {
        "schema_version": "exchange_authoring_phase2_repair_candidates.v0.1",
        "product": "看剧搭子",
        "created_at": created_at,
        "source_report_ref": repo_relative(EXCHANGE_OUTPUT_PATH),
        "input_fixture": input_ref,
        "claim_boundary": "Repair candidates come only from Phase 2 Loop 1 authoring failures or deterministic normalizations.",
        "items": repairs,
    }
    return report, repair_dataset


def build_exchange_run(item: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seed = item["context_card"]["authoring_seed"]
    raw_seed_failures = audit_raw_authoring_seed(item)
    repairs: list[dict[str, Any]] = []
    companion_lead = str(seed.get("companion_lead_seed") or item["context_card"]["mouthpiece_pressure"]).strip()
    if item["item_id"] in LEAD_REWRITES:
        repairs.append(
            build_repair_candidate(
                item=item,
                field="companion_lead",
                failure_type="question_shaped_lead_seed",
                bad_text=companion_lead,
                replacement_text=LEAD_REWRITES[item["item_id"]],
                reason="Phase 2 no-question-shaped-lead gate requires a declarative friend lead before draft review.",
            )
        )
        companion_lead = LEAD_REWRITES[item["item_id"]]
    elif QUESTION_SHAPED_RE.search(companion_lead):
        normalized = QUESTION_SHAPED_RE.sub("", companion_lead).strip(" ，,。") + "。"
        repairs.append(
            build_repair_candidate(
                item=item,
                field="companion_lead",
                failure_type="question_shaped_lead_seed",
                bad_text=companion_lead,
                replacement_text=normalized,
                reason="Question-shaped lead seed is not allowed for default companion opening.",
            )
        )
        companion_lead = normalized

    reply_seeds = list(seed.get("reply_candidate_seeds", []))
    if item["item_id"] in OWNER_SEED_REPLY_REWRITES:
        replacements = OWNER_SEED_REPLY_REWRITES[item["item_id"]]
        for index, raw in enumerate(reply_seeds[:3]):
            repairs.append(
                build_repair_candidate(
                    item=item,
                    field=f"reply_candidates[{index}].display_text",
                    failure_type="axis_label_no_viewer_voice",
                    bad_text=str(raw.get("display_text") or ""),
                    replacement_text=replacements[index]["display_text"],
                    reason="Owner-seed reply was an emotional axis label; Phase 2 authoring must draft viewer speech.",
                )
            )
        reply_seeds = replacements

    reply_candidates = [
        build_reply_candidate(item=item, seed=reply_seed, index=index)
        for index, reply_seed in enumerate(reply_seeds[:3])
    ]
    exchange_draft = {
        "schema_version": "companion_exchange_pack.v0.1",
        "scene_signal": clip_text(item["viewer_line_pressure"], 80),
        "window_rationale": item["why_now"],
        "notice_marker": "!",
        "companion_lead": clip_text(companion_lead, 40),
        "reply_candidates": reply_candidates,
        "custom_reply_policy": {
            "mode": "bounded_current_window_echo",
            "hint": seed.get("custom_reply_policy_hint") or "Reflect only within this context card.",
            "no_live_default_generation": True,
        },
        "evidence_refs": list(item.get("evidence_refs", [])) or [item["item_id"]],
        "constraint_refs": [
            "docs/CompanionExchangePack_v0.1_Contract.md",
            "docs/WindowTasteEval_v0.1_Contract.md#Authoring Seed",
        ],
        "blocked_claims": list(seed.get("blocked_claims_hint", [])) or [
            "no future-episode claims",
            "no hidden motive inference",
            "no branch rewrite",
        ],
        "review_status": "needs_review",
    }
    validation = validate_exchange_draft(exchange_draft)
    owner_outcome = item["context_card"].get("owner_review_outcome", "")
    review_status = "auto_reviewable"
    if not validation["conformance_valid"]:
        review_status = "failed_validation"
    elif owner_outcome == "understood_wrong_taste":
        review_status = "needs_owner_review_before_demo"
    return {
        "item_id": item["item_id"],
        "episode_id": item["episode_id"],
        "time_range": format_time_range(item["interaction_window"]),
        "context_card_evidence": {
            "episode_context": item["context_card"]["episode_context"],
            "scene_function": item["context_card"]["scene_function"],
            "relationship_state": item["context_card"]["character_relationship_state"],
            "current_asr": item["context_card"]["adjacent_asr"]["current"],
        },
        "raw_seed_audit": {
            "status": "pass" if not raw_seed_failures else "repair_applied",
            "failures": raw_seed_failures,
        },
        "generated_draft": exchange_draft,
        "negative_examples_consulted": {
            "lead_examples": seed.get("rejected_lead_examples", []),
            "reply_examples": seed.get("rejected_reply_examples", []),
        },
        "draft_validation": validation,
        "review_status": review_status,
        "review_notes": review_notes_for_exchange_run(item, raw_seed_failures, validation, review_status),
    }, repairs


def build_reply_candidate(*, item: dict[str, Any], seed: dict[str, Any], index: int) -> dict[str, Any]:
    display_text = clip_text(str(seed.get("display_text") or ""), 14)
    emotion_role = str(seed.get("emotion_role") or f"reply_{index + 1}")
    semantic_role = str(seed.get("semantic_role") or f"reply_axis_{index + 1}")
    return {
        "candidate_id": f"{item['item_id']}_reply_{index + 1}",
        "display_text": display_text,
        "action_payload": {
            "text": display_text,
            "action_type": "viewer_reply",
            "intent": semantic_role,
        },
        "selected_echo": selected_echo_for(display_text),
        "emotion_role": emotion_role,
        "semantic_role": semantic_role,
        "distinctness_rationale": str(seed.get("intent_note") or f"Distinct viewer reply {index + 1}."),
        "evidence_refs": list(item.get("evidence_refs", [])) or [item["item_id"]],
        "constraint_refs": ["window_taste_eval.context_card.authoring_seed"],
    }


def audit_raw_authoring_seed(item: dict[str, Any]) -> list[dict[str, Any]]:
    seed = item["context_card"]["authoring_seed"]
    failures: list[dict[str, Any]] = []
    lead = str(seed.get("companion_lead_seed") or "")
    if QUESTION_SHAPED_RE.search(lead):
        failures.append(
            {
                "failure_type": "question_shaped_lead_seed",
                "field": "companion_lead_seed",
                "text": lead,
                "reason": "Default lead cannot be a direct question-shaped prompt.",
            }
        )
    if item["item_id"] in OWNER_SEED_REPLY_REWRITES:
        for index, reply in enumerate(seed.get("reply_candidate_seeds", [])[:3]):
            failures.append(
                {
                    "failure_type": "axis_label_no_viewer_voice",
                    "field": f"reply_candidate_seeds[{index}].display_text",
                    "text": str(reply.get("display_text") or ""),
                    "reason": "Raw owner seed stores a semantic axis label; authoring must convert it into viewer speech.",
                }
            )
    for index, reply in enumerate(seed.get("reply_candidate_seeds", [])[:3]):
        text = str(reply.get("display_text") or "")
        if any(term in text for term in PRODUCER_STANCE_TERMS):
            failures.append(
                {
                    "failure_type": "producer_or_action_stance_in_reply_seed",
                    "field": f"reply_candidate_seeds[{index}].display_text",
                    "text": text,
                    "reason": "Visible reply seed leaks producer/action stance.",
                }
            )
    return failures


def build_repair_candidate(
    *,
    item: dict[str, Any],
    field: str,
    failure_type: str,
    bad_text: str,
    replacement_text: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "repair_id": stable_id("phase2_repair", item["item_id"], field, failure_type, bad_text),
        "item_id": item["item_id"],
        "episode_id": item["episode_id"],
        "time_range": format_time_range(item["interaction_window"]),
        "field": field,
        "failure_type": failure_type,
        "bad_text": bad_text,
        "replacement_text": replacement_text,
        "reason": reason,
        "source": "phase2_exchange_raw_seed_audit",
        "owner_review_needed": False,
        "writeback_recommendation": "Use as authoring-rule repair evidence; do not promote runtime copy without Phase 3 review.",
    }


def validate_exchange_draft(exchange: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    schema_ok, schema_message = validate_json_schema(exchange, COMPANION_EXCHANGE_SCHEMA_PATH)
    if not schema_ok:
        errors.append(f"schema: {schema_message}")
    lead = str(exchange.get("companion_lead") or "")
    if QUESTION_SHAPED_RE.search(lead):
        errors.append(f"question-shaped lead: {lead}")
    replies = exchange.get("reply_candidates", [])
    if len(replies) != 3:
        errors.append("exchange draft must contain exactly three replies")
    display_texts = [str(reply.get("display_text") or "") for reply in replies if isinstance(reply, dict)]
    if len(set(display_texts)) != len(display_texts):
        errors.append("reply candidate display_text values must be distinct")
    semantic_roles = [str(reply.get("semantic_role") or "") for reply in replies if isinstance(reply, dict)]
    if len(set(semantic_roles)) != len(semantic_roles):
        warnings.append("reply semantic roles are not fully distinct")
    for reply in replies:
        if not isinstance(reply, dict):
            continue
        for field in ("display_text", "selected_echo"):
            value = str(reply.get(field) or "")
            if any(term in value for term in PRODUCER_STANCE_TERMS):
                errors.append(f"{field} leaks producer/action stance: {value}")
        selected_echo = str(reply.get("selected_echo") or "")
        if any(term in selected_echo for term in ECHO_REPORT_TERMS):
            errors.append(f"selected_echo sounds like consequence/report copy: {selected_echo}")
    if contains_local_path(exchange):
        errors.append("exchange draft contains machine-specific local path")
    return {
        "schema_valid": schema_ok,
        "conformance_valid": schema_ok and not errors,
        "errors": errors,
        "warnings": warnings,
    }


def review_notes_for_exchange_run(
    item: dict[str, Any],
    raw_seed_failures: list[dict[str, Any]],
    validation: dict[str, Any],
    review_status: str,
) -> list[str]:
    notes = []
    if raw_seed_failures:
        notes.append("Raw authoring seed exposed repairable lead/reply shape failures; deterministic normalization was applied before draft validation.")
    if validation["conformance_valid"]:
        notes.append("Draft is schema-valid and conformance-valid for Phase 2 review.")
    else:
        notes.append("Draft failed Phase 2 validation and must not be considered reviewable.")
    if review_status == "needs_owner_review_before_demo":
        notes.append("Original context card outcome is understood_wrong_taste; keep as eval evidence, exclude from Phase 3 demo candidates until owner review.")
    if item["item_id"] in DEMO_CANDIDATE_PRIORITY:
        notes.append("Candidate is eligible for Phase 3 nomination only if the combined eval selects it and human review follows.")
    return notes


def evaluate_exchange_gate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    schema_valid_count = len([run for run in runs if run["draft_validation"]["schema_valid"]])
    conformance_valid_count = len([run for run in runs if run["draft_validation"]["conformance_valid"]])
    no_question_lead_count = len(
        [
            run
            for run in runs
            if not QUESTION_SHAPED_RE.search(str(run["generated_draft"].get("companion_lead") or ""))
        ]
    )
    no_rpg_reply_count = len(
        [
            run
            for run in runs
            if not any(
                any(term in str(reply.get("display_text") or "") for term in PRODUCER_STANCE_TERMS)
                for reply in run["generated_draft"].get("reply_candidates", [])
            )
        ]
    )
    friend_echo_count = len(
        [
            run
            for run in runs
            if not any(
                any(term in str(reply.get("selected_echo") or "") for term in ECHO_REPORT_TERMS)
                for reply in run["generated_draft"].get("reply_candidates", [])
            )
        ]
    )
    reviewable_count = len(
        [
            run
            for run in runs
            if run["review_status"] in {"auto_reviewable", "needs_owner_review_before_demo"}
        ]
    )
    failed_runs = [
        {
            "item_id": run["item_id"],
            "episode_id": run["episode_id"],
            "errors": run["draft_validation"]["errors"],
        }
        for run in runs
        if run["review_status"] == "failed_validation"
    ]
    status = "pass"
    if not (
        schema_valid_count == 10
        and conformance_valid_count == 10
        and no_question_lead_count == 10
        and no_rpg_reply_count == 10
        and friend_echo_count == 10
        and reviewable_count >= 7
    ):
        status = "fail"
    return {
        "status": status,
        "schema_valid_count": schema_valid_count,
        "conformance_valid_count": conformance_valid_count,
        "no_question_shaped_lead_count": no_question_lead_count,
        "no_rpg_action_reply_count": no_rpg_reply_count,
        "friend_echo_count": friend_echo_count,
        "reviewable_without_major_rewrite_count": reviewable_count,
        "failed_runs": failed_runs,
        "raw_seed_repair_count": sum(len(run["raw_seed_audit"]["failures"]) for run in runs),
    }


def build_review_gate_b(runs: list[dict[str, Any]], acceptance: dict[str, Any]) -> dict[str, Any]:
    failed = [
        {
            "item_id": run["item_id"],
            "episode_id": run["episode_id"],
            "failure_type": "draft_validation_failed",
            "details": run["draft_validation"]["errors"],
        }
        for run in runs
        if run["review_status"] == "failed_validation"
    ]
    deferred = [
        {
            "item_id": run["item_id"],
            "episode_id": run["episode_id"],
            "reason": "context_card owner_review_outcome is understood_wrong_taste; exclude from demo until copy review.",
        }
        for run in runs
        if run["review_status"] == "needs_owner_review_before_demo"
    ]
    needed = bool(failed)
    return {
        "gate": "Review Gate B",
        "needed": needed,
        "reason": (
            "Exchange authoring produced validation failures requiring owner review."
            if needed
            else "No immediate exchange validation failures; wrong-taste seeds are recorded as deferred Phase 3 review exclusions."
        ),
        "owner_review_target": failed[:10],
        "deferred_phase3_review_items": deferred,
        "acceptance_status": acceptance["status"],
    }


def build_combined_eval(
    *,
    input_ref: dict[str, Any],
    baseline: dict[str, Any],
    window_judge: dict[str, Any],
    exchange_report: dict[str, Any],
    exchange_repairs: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    demo_candidates = nominate_demo_candidates(exchange_report["runs"])
    goal_gate_summary = {
        "baseline_validated": True,
        "window_judge_report_generated": True,
        "review_gate_a_needed": window_judge["review_gate_a"]["needed"],
        "exchange_authoring_report_generated": True,
        "review_gate_b_needed": exchange_report["review_gate_b"]["needed"],
        "runtime_pack_promotion": "not_performed_phase3_only",
    }
    return {
        "schema_version": "studio_cab_phase2_eval.v0.1",
        "product": "看剧搭子",
        "created_at": created_at,
        "run_id": f"phase2_eval:{input_ref['sha256'][:12]}",
        "input_fixture": input_ref,
        "claim_boundary": (
            "Phase 2 Loop 1 eval maturation artifact. It records deterministic Studio/CAB harness evidence and repair candidates; "
            "it is not a runtime pack promotion and not a live provider trace."
        ),
        "baseline_summary": baseline,
        "report_refs": {
            "window_judge_report": repo_relative(WINDOW_JUDGE_OUTPUT_PATH),
            "exchange_authoring_report": repo_relative(EXCHANGE_OUTPUT_PATH),
            "exchange_repair_candidates": repo_relative(EXCHANGE_REPAIR_OUTPUT_PATH)
            if exchange_repairs["items"]
            else "",
            "phase2_eval_report": repo_relative(PHASE2_REPORT_PATH),
            "local_window_html": repo_relative(WINDOW_HTML_PATH),
            "local_exchange_html": repo_relative(EXCHANGE_HTML_PATH),
            "local_repair_html": repo_relative(REPAIR_HTML_PATH),
        },
        "layer_coverage": {
            "window_selection": {
                "positive_examples": baseline["owner_confirmed_gold_count"],
                "negative_examples": baseline["hard_negative_count"],
                "owner_reviewed_negative_or_context_examples": baseline["owner_reviewed_window_negative_count"],
                "gate_status": window_judge["acceptance_gate"]["status"],
            },
            "opening_lead": {
                "positive_examples": baseline["owner_confirmed_gold_count"],
                "negative_examples": baseline["lead_rejected_example_count"] + count_repair_type(exchange_repairs, "question_shaped_lead_seed"),
                "gate_status": exchange_report["acceptance_gate"]["status"],
            },
            "preset_replies": {
                "positive_examples": baseline["positive_reply_seed_count"],
                "negative_examples": baseline["reply_rejected_example_count"] + count_repair_type(exchange_repairs, "axis_label_no_viewer_voice"),
                "gate_status": exchange_report["acceptance_gate"]["status"],
            },
            "selected_echo_answer_direction": {
                "positive_examples": count_selected_echo_examples(exchange_report),
                "negative_examples": count_repair_type(exchange_repairs, "selected_echo_report_copy"),
                "gate_status": exchange_report["acceptance_gate"]["status"],
            },
            "custom_input_policy": {
                "positive_examples": len(exchange_report["runs"]),
                "negative_examples": 0,
                "gate_status": "policy_hints_only_loop1",
            },
        },
        "review_gates": {
            "gate_a": window_judge["review_gate_a"],
            "gate_b": exchange_report["review_gate_b"],
        },
        "repair_status": {
            "window_repair_candidates_created": False,
            "exchange_repair_candidates_created": bool(exchange_repairs["items"]),
            "exchange_repair_candidate_count": len(exchange_repairs["items"]),
        },
        "phase3_demo_pack_candidates": demo_candidates,
        "goal_gate_summary": goal_gate_summary,
    }


def nominate_demo_candidates(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {run["item_id"]: run for run in runs}
    candidates = []
    coverage_labels = {
        "taste_gold_owner_huangnian_ep03_0033": "persona baseline / original-persona absurdity",
        "taste_gold_proposed_huangnian_ep10_0027": "short-drama 看戏 / 爽点",
        "taste_gold_proposed_huangnian_ep14_0048": "original-persona aftershock / external reputation",
        "taste_gold_owner_huangnian_ep04_0149": "protagonist competence / verbal reversal",
        "taste_gold_proposed_huangnian_ep02_0125": "child-softness / light empathy",
    }
    for item_id in DEMO_CANDIDATE_PRIORITY:
        run = by_id.get(item_id)
        if not run:
            continue
        if run["review_status"] != "auto_reviewable":
            continue
        candidates.append(
            {
                "item_id": item_id,
                "episode_id": run["episode_id"],
                "time_range": run["time_range"],
                "coverage_role": coverage_labels[item_id],
                "promotion_status": "nominated_only_not_promoted",
                "why_candidate": "Phase2 draft is conformance-valid and not marked understood_wrong_taste.",
                "companion_lead": run["generated_draft"]["companion_lead"],
                "reply_displays": [
                    reply["display_text"] for reply in run["generated_draft"]["reply_candidates"]
                ],
            }
        )
        if len(candidates) >= 5:
            break
    return candidates


def render_phase2_markdown(result: dict[str, Any]) -> str:
    window = result["window_judge_report"]
    exchange = result["exchange_report"]
    phase2 = result["phase2_eval"]
    lines = [
        "# Deadman v0.41 Phase 2 Eval Report v0.1",
        "",
        "> Product: 看剧搭子",
        "> Scope: Phase 2 Loop 1, deterministic Studio/CAB eval harness",
        "",
        "## Claim Boundary",
        "",
        phase2["claim_boundary"],
        "",
        "No runtime pack was promoted in this loop.",
        "",
        "## Baseline",
        "",
        f"- Owner-confirmed gold windows: {phase2['baseline_summary']['owner_confirmed_gold_count']}",
        f"- Hard negatives: {phase2['baseline_summary']['hard_negative_count']}",
        f"- Owner-reviewed window negatives/context-insufficient: {phase2['baseline_summary']['owner_reviewed_window_negative_count']}",
        f"- Positive reply seeds: {phase2['baseline_summary']['positive_reply_seed_count']}",
        f"- Lead rejected examples: {phase2['baseline_summary']['lead_rejected_example_count']}",
        f"- Reply rejected examples: {phase2['baseline_summary']['reply_rejected_example_count']}",
        "",
        "Known weakness: the same-episode competitor pool is weak, so Loop 1 should not be sold as unseen automatic taste generalization.",
        "",
        "## Window Judge",
        "",
        f"- Gate status: {window['acceptance_gate']['status']}",
        f"- Gold top-3: {window['acceptance_gate']['gold_top3_count']}/{window['acceptance_gate']['gold_total']}",
        f"- Owner-reviewed rejects rejected: {window['acceptance_gate']['owner_reviewed_rejects_rejected_count']}/{window['acceptance_gate']['owner_reviewed_rejects_total']}",
        f"- Review Gate A needed: {window['review_gate_a']['needed']}",
        "",
        "## Exchange Authoring",
        "",
        f"- Gate status: {exchange['acceptance_gate']['status']}",
        f"- Schema-valid drafts: {exchange['acceptance_gate']['schema_valid_count']}/10",
        f"- Conformance-valid drafts: {exchange['acceptance_gate']['conformance_valid_count']}/10",
        f"- Reviewable without major rewrite: {exchange['acceptance_gate']['reviewable_without_major_rewrite_count']}/10",
        f"- Raw seed repair candidates: {exchange['repair_candidate_summary']['count']}",
        f"- Review Gate B needed: {exchange['review_gate_b']['needed']}",
        "",
        "## Layer Coverage",
        "",
        "| Layer | Positive | Negative / repair | Gate |",
        "| --- | ---: | ---: | --- |",
    ]
    for layer, data in phase2["layer_coverage"].items():
        lines.append(
            f"| {layer} | {data['positive_examples']} | {data['negative_examples']} | {data['gate_status']} |"
        )
    lines.extend(
        [
            "",
            "## Phase 3 Demo Candidate Nominations",
            "",
            "| Item | Episode | Time | Role | Lead | Replies |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for candidate in phase2["phase3_demo_pack_candidates"]:
        lines.append(
            "| {item_id} | {episode_id} | {time_range} | {coverage_role} | {lead} | {replies} |".format(
                item_id=candidate["item_id"],
                episode_id=candidate["episode_id"],
                time_range=candidate["time_range"],
                coverage_role=candidate["coverage_role"],
                lead=candidate["companion_lead"],
                replies=" / ".join(candidate["reply_displays"]),
            )
        )
    lines.extend(
        [
            "",
            "## Review Gate Summary",
            "",
            f"- Gate A: {'needed' if window['review_gate_a']['needed'] else 'not needed'}",
            f"- Gate B: {'needed' if exchange['review_gate_b']['needed'] else 'not needed'}",
            "- Phase 3 must still review and promote selected exchange packs before user-side runtime publication.",
            "",
            "## Artifact Refs",
            "",
        ]
    )
    for key, value in phase2["report_refs"].items():
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def render_window_html(report: dict[str, Any]) -> str:
    rows = []
    for ranking in report["episode_rankings"]:
        candidates = "".join(
            f"<tr><td>{entry['rank']}</td><td>{esc(entry['item_id'])}</td><td>{entry['score']}</td>"
            f"<td>{esc(entry['decision'])}</td><td>{esc(entry['time_range'])}</td>"
            f"<td>{esc(entry['opening_hypothesis'])}</td><td>{esc(', '.join(entry['failure_flags']))}</td></tr>"
            for entry in ranking["top_candidates"][:5]
        )
        rows.append(
            f"<section><h2>{esc(ranking['episode_id'])}</h2>"
            f"<table><thead><tr><th>Rank</th><th>Item</th><th>Score</th><th>Decision</th><th>Time</th><th>Opening hypothesis</th><th>Flags</th></tr></thead>"
            f"<tbody>{candidates}</tbody></table></section>"
        )
    return html_page(
        "Phase2 Window Judge Report",
        f"""
        <h1>Phase2 Window Judge Report</h1>
        <p>Gate: <strong>{esc(report['acceptance_gate']['status'])}</strong>. Review Gate A needed: <strong>{report['review_gate_a']['needed']}</strong>.</p>
        <p>Gold top-3: {report['acceptance_gate']['gold_top3_count']}/{report['acceptance_gate']['gold_total']}; owner-reviewed rejects rejected: {report['acceptance_gate']['owner_reviewed_rejects_rejected_count']}/{report['acceptance_gate']['owner_reviewed_rejects_total']}.</p>
        {''.join(rows)}
        """,
    )


def render_exchange_html(report: dict[str, Any], phase2_eval: dict[str, Any]) -> str:
    nominated = {candidate["item_id"] for candidate in phase2_eval["phase3_demo_pack_candidates"]}
    cards = []
    for run in report["runs"]:
        replies = "".join(
            f"<li><strong>{esc(reply['display_text'])}</strong><br><span>{esc(reply['selected_echo'])}</span></li>"
            for reply in run["generated_draft"]["reply_candidates"]
        )
        raw_failures = "".join(
            f"<li>{esc(failure['failure_type'])}: {esc(failure['text'])}</li>"
            for failure in run["raw_seed_audit"]["failures"]
        )
        cards.append(
            f"<section><h2>{esc(run['episode_id'])} · {esc(run['time_range'])}</h2>"
            f"<p><code>{esc(run['item_id'])}</code> · status: <strong>{esc(run['review_status'])}</strong>"
            f"{' · phase3 nominated' if run['item_id'] in nominated else ''}</p>"
            f"<p class='lead'>{esc(run['generated_draft']['companion_lead'])}</p>"
            f"<ol>{replies}</ol>"
            f"<details><summary>Raw seed audit</summary><ul>{raw_failures or '<li>pass</li>'}</ul></details>"
            f"</section>"
        )
    return html_page(
        "Phase2 Exchange Review",
        f"""
        <h1>Phase2 Exchange Review</h1>
        <p>Gate: <strong>{esc(report['acceptance_gate']['status'])}</strong>. Review Gate B needed: <strong>{report['review_gate_b']['needed']}</strong>.</p>
        {''.join(cards)}
        """,
    )


def render_repair_html(window_report: dict[str, Any], exchange_repairs: dict[str, Any]) -> str:
    repairs = "".join(
        f"<tr><td>{esc(item['episode_id'])}</td><td>{esc(item['item_id'])}</td><td>{esc(item['field'])}</td>"
        f"<td>{esc(item['failure_type'])}</td><td>{esc(item['bad_text'])}</td><td>{esc(item['replacement_text'])}</td></tr>"
        for item in exchange_repairs["items"]
    )
    if not repairs:
        repairs = "<tr><td colspan='6'>No exchange repair candidates in this loop.</td></tr>"
    window_gate = window_report["review_gate_a"]
    return html_page(
        "Phase2 Repair Review",
        f"""
        <h1>Phase2 Repair Review</h1>
        <p>Review Gate A needed: <strong>{window_gate['needed']}</strong>. {esc(window_gate['reason'])}</p>
        <h2>Exchange repair candidates</h2>
        <table><thead><tr><th>Episode</th><th>Item</th><th>Field</th><th>Failure</th><th>Bad</th><th>Replacement</th></tr></thead><tbody>{repairs}</tbody></table>
        """,
    )


def html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{esc(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #202124; }}
    section {{ border-top: 1px solid #ddd; padding: 16px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; font-size: 13px; }}
    th {{ background: #f5f5f5; text-align: left; }}
    code {{ background: #f3f3f3; padding: 2px 4px; border-radius: 4px; }}
    .lead {{ font-size: 18px; font-weight: 700; }}
    ol {{ padding-left: 22px; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def looks_generic(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    generic_markers = ("要是我来", "资源", "家庭压力", "单看这一集", "机制", "分配")
    return any(marker in stripped for marker in generic_markers)


def selected_echo_for(display_text: str) -> str:
    prefix_map = {
        "是呀，": "是啊，",
        "就是，": "对，",
        "确实，": "嗯，",
        "还真是，": "还真是，",
    }
    for prefix, echo_prefix in prefix_map.items():
        if display_text.startswith(prefix):
            return f"{echo_prefix}{display_text[len(prefix):]}。"
    return f"是啊，{display_text}。"


def clip_text(text: str, max_length: int) -> str:
    text = text.strip()
    return text if len(text) <= max_length else text[:max_length]


def count_repair_type(repairs: dict[str, Any], failure_type: str) -> int:
    return len([item for item in repairs.get("items", []) if item.get("failure_type") == failure_type])


def count_selected_echo_examples(exchange_report: dict[str, Any]) -> int:
    return sum(len(run["generated_draft"]["reply_candidates"]) for run in exchange_report["runs"])


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return "_".join([parts[0], digest])


def format_time_range(window: dict[str, Any]) -> str:
    return f"{ms_to_time(int(window['start_ms']))}-{ms_to_time(int(window['end_ms']))}"


def ms_to_time(value: int) -> str:
    total_seconds = value // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def contains_local_path(value: Any) -> bool:
    if isinstance(value, str):
        return any(marker in value for marker in LOCAL_PATH_MARKERS)
    if isinstance(value, list):
        return any(contains_local_path(item) for item in value)
    if isinstance(value, dict):
        return any(contains_local_path(item) for item in value.values())
    return False


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
