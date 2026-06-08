#!/usr/bin/env python3
"""Validate the Deadman v0.41 window-taste eval fixture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_EVAL_PATH = REPO_ROOT / "data/evals/window_taste_eval.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/window_taste_eval.v0.1.json"
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "OSeria-Alter/tmp/")
PRODUCER_STANCE_LEAK_TERMS = ("护住", "点出", "接住", "交付")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval", default=str(DEFAULT_EVAL_PATH))
    args = parser.parse_args()

    eval_path = resolve_path(args.eval)
    dataset = read_json(eval_path)
    errors = validate_window_taste_eval(dataset)
    if errors:
        print(f"Deadman window taste eval failed: {repo_relative(eval_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman window taste eval passed: {repo_relative(eval_path)}")
    return 0


def validate_window_taste_eval(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(dataset, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    if contains_local_path(dataset):
        errors.append("dataset contains machine-specific local path")

    targets = dataset["targets"]
    items = dataset["items"]
    gold_items = [item for item in items if item["label"] == "gold"]
    owner_gold = [item for item in gold_items if item["review_status"] == "owner_confirmed"]
    hard_negatives = [item for item in items if item["label"] == "hard_negative"]

    if len(owner_gold) < targets["owner_confirmed_gold_min"]:
        errors.append(
            f"owner_confirmed gold count {len(owner_gold)} < {targets['owner_confirmed_gold_min']}"
        )
    if len(gold_items) < targets["gold_candidate_min"]:
        errors.append(f"gold candidate count {len(gold_items)} < {targets['gold_candidate_min']}")
    if len(hard_negatives) < targets["hard_negative_min"]:
        errors.append(f"hard-negative count {len(hard_negatives)} < {targets['hard_negative_min']}")

    best_by_episode: dict[str, str] = {}
    for item in gold_items:
        if item["nomination_role"] != "episode_best_candidate":
            errors.append(f"{item['item_id']} gold must be an episode_best_candidate")
        previous = best_by_episode.get(item["episode_id"])
        if previous:
            errors.append(
                f"gold episode best duplicates {item['episode_id']}: {previous}, {item['item_id']}"
            )
        best_by_episode[item["episode_id"]] = item["item_id"]
        if len(item["expected_reply_axes"]) < 2:
            errors.append(f"{item['item_id']} gold needs at least two reply axes")
        if item["reject_dimensions"] or item["reject_reason"]:
            errors.append(f"{item['item_id']} gold must not carry reject fields")

    required_owner_anchors = {
        "taste_gold_owner_huangnian_ep03_0033": ("huangnian_ep03", 33000),
        "taste_gold_owner_huangnian_ep07_0021": ("huangnian_ep07", 21000),
        "taste_gold_owner_huangnian_ep04_0149": ("huangnian_ep04", 109000),
        "taste_gold_owner_huangnian_ep06_0103": ("huangnian_ep06", 63000),
    }
    by_id = {item["item_id"]: item for item in items}
    for item_id, (episode_id, anchor_ms) in required_owner_anchors.items():
        item = by_id.get(item_id)
        if not item:
            errors.append(f"missing owner gold {item_id}")
            continue
        if item["label"] != "gold" or item["review_status"] != "owner_confirmed":
            errors.append(f"{item_id} must be owner-confirmed gold")
        if item["episode_id"] != episode_id or item["anchor_ms"] != anchor_ms:
            errors.append(f"{item_id} must anchor {episode_id} at {anchor_ms}ms")

    ep12_skip = by_id.get("taste_negative_huangnian_ep12_skip_context")
    if not ep12_skip:
        errors.append("missing EP12 skip hard-negative")
    elif ep12_skip["label"] != "hard_negative" or "context_insufficient" not in ep12_skip["reject_dimensions"]:
        errors.append("EP12 skip must be a context_insufficient hard-negative")

    for item in items:
        window = item["interaction_window"]
        if window["duration_ms"] != 10000 or window["end_ms"] - window["start_ms"] != 10000:
            errors.append(f"{item['item_id']} interaction window must be exactly 10 seconds")
        if window["start_ms"] != item["anchor_ms"]:
            errors.append(f"{item['item_id']} interaction window must start at anchor_ms")
        source = item["source_window"]
        if source["end_ms"] < source["start_ms"]:
            errors.append(f"{item['item_id']} source window end before start")
        if item["label"] == "hard_negative":
            if not item["reject_dimensions"]:
                errors.append(f"{item['item_id']} hard-negative needs reject_dimensions")
            if not item["reject_reason"]:
                errors.append(f"{item['item_id']} hard-negative needs reject_reason")
        errors.extend(validate_window_review(item))
        errors.extend(validate_context_card(item))
    return errors


def validate_window_review(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    item_id = str(item.get("item_id") or "<unknown>")
    review = item.get("window_review")
    if not isinstance(review, dict):
        return [f"{item_id} missing window_review"]
    decision = review.get("decision")
    source = review.get("decision_source")
    rank = review.get("episode_rank")
    if not str(review.get("reason") or "").strip():
        errors.append(f"{item_id} window_review.reason is empty")
    if not str(review.get("owner_review_prompt") or "").strip():
        errors.append(f"{item_id} window_review.owner_review_prompt is empty")
    if item.get("label") == "gold" and item.get("source_origin") == "owner_seed":
        if decision != "accepted_best" or source != "owner_seed" or rank != "best":
            errors.append(f"{item_id} owner-seed gold must be accepted_best/source owner_seed/rank best")
        if review.get("needs_video_review") is not False:
            errors.append(f"{item_id} owner-seed gold should not need extra video review")
    if item.get("label") == "gold" and item.get("source_origin") == "agent_proposed":
        if item.get("review_status") == "owner_confirmed":
            if decision != "accepted_best" or source != "owner_episode_review" or rank != "best":
                errors.append(
                    f"{item_id} owner-reviewed agent-proposed gold must be accepted_best/source owner_episode_review/rank best"
                )
            if review.get("needs_video_review") is not False:
                errors.append(f"{item_id} owner-reviewed agent-proposed gold should not need extra video review")
        elif item.get("review_status") == "proposed_for_owner_review":
            if source != "unreviewed" or decision != "unreviewed" or rank != "unranked":
                errors.append(f"{item_id} pending agent-proposed gold must remain explicit-window-review pending")
    if item.get("label") == "hard_negative":
        if decision in {"accepted_best", "accepted_possible"}:
            errors.append(f"{item_id} hard-negative cannot carry accepted window decision")
        if item.get("evaluation_focus") == "framing_quality" and decision != "rejected_framing":
            errors.append(f"{item_id} framing-quality negative must carry rejected_framing")
        if item.get("evaluation_focus") == "window_selection" and "context_insufficient" not in item.get("reject_dimensions", []):
            if decision != "rejected_window":
                errors.append(f"{item_id} window-selection negative must carry rejected_window")
    if "context_insufficient" in item.get("reject_dimensions", []):
        if decision != "context_insufficient":
            errors.append(f"{item_id} context-insufficient item must carry context_insufficient window decision")
    return errors


def validate_context_card(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    card = item.get("context_card")
    if not isinstance(card, dict):
        return [f"{item.get('item_id')} missing context_card"]
    item_id = str(item.get("item_id") or "<unknown>")
    adjacent = card.get("adjacent_asr", {}) if isinstance(card.get("adjacent_asr"), dict) else {}
    if len(str(card.get("episode_context") or "")) < 20:
        errors.append(f"{item_id} context_card.episode_context is too thin")
    if len(str(card.get("scene_function") or "")) < 12:
        errors.append(f"{item_id} context_card.scene_function is too thin")
    if len(str(card.get("character_relationship_state") or "")) < 12:
        errors.append(f"{item_id} context_card.character_relationship_state is too thin")
    if len(str(adjacent.get("current") or "")) < 20:
        errors.append(f"{item_id} context_card.adjacent_asr.current is too thin")
    readiness = card.get("agent_input_readiness")
    if item.get("label") == "gold" and item.get("review_status") == "owner_confirmed":
        if readiness != "owner_confirmed":
            errors.append(f"{item_id} owner-confirmed gold must have owner_confirmed context readiness")
    if item.get("label") == "gold" and item.get("review_status") == "proposed_for_owner_review":
        if readiness != "needs_owner_review":
            errors.append(f"{item_id} proposed gold must have needs_owner_review context readiness")
    if item.get("label") == "hard_negative":
        allowed = {"negative_training_only", "context_insufficient"}
        if readiness not in allowed:
            errors.append(f"{item_id} hard-negative readiness must be one of {sorted(allowed)}")
    if "context_insufficient" in item.get("reject_dimensions", []):
        if readiness != "context_insufficient":
            errors.append(f"{item_id} context_insufficient item must have context_insufficient readiness")
    errors.extend(validate_authoring_seed(item, card))
    return errors


def validate_authoring_seed(item: dict[str, Any], card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    item_id = str(item.get("item_id") or "<unknown>")
    seed = card.get("authoring_seed")
    if not isinstance(seed, dict):
        return [f"{item_id} missing context_card.authoring_seed"]
    applicability = seed.get("applicability")
    replies = seed.get("reply_candidate_seeds")
    rejected_leads = seed.get("rejected_lead_examples")
    rejected_replies = seed.get("rejected_reply_examples")
    if not isinstance(replies, list):
        return [f"{item_id} authoring_seed.reply_candidate_seeds must be a list"]
    if not isinstance(rejected_leads, list):
        return [f"{item_id} authoring_seed.rejected_lead_examples must be a list"]
    if not isinstance(rejected_replies, list):
        return [f"{item_id} authoring_seed.rejected_reply_examples must be a list"]
    if item.get("label") == "gold":
        if applicability != "authoring_reference":
            errors.append(f"{item_id} gold must carry authoring_reference seed")
        if not str(seed.get("companion_lead_seed") or "").strip():
            errors.append(f"{item_id} gold authoring seed needs companion_lead_seed")
        for key in (
            "lead_style_policy",
            "reply_set_policy",
            "viewer_stance_policy",
            "response_tone_policy",
            "preset_echo_policy",
        ):
            if not str(seed.get(key) or "").strip():
                errors.append(f"{item_id} gold authoring seed missing {key}")
        if len(replies) < 2:
            errors.append(f"{item_id} gold authoring seed needs at least two reply seeds")
        if card.get("owner_review_outcome") == "understood_wrong_taste" and not (rejected_leads or rejected_replies):
            errors.append(f"{item_id} wrong-taste gold needs rejected lead or reply examples")
        rejected_lead_texts: set[str] = set()
        for index, rejected in enumerate(rejected_leads):
            if not isinstance(rejected, dict):
                errors.append(f"{item_id} rejected lead example {index} must be object")
                continue
            for key in ("display_text", "negative_type", "reject_reason", "correction_hint"):
                if not str(rejected.get(key) or "").strip():
                    errors.append(f"{item_id} rejected lead example {index} missing {key}")
            rejected_lead_texts.add(str(rejected.get("display_text") or ""))
        companion_lead_seed = str(seed.get("companion_lead_seed") or "")
        if companion_lead_seed in rejected_lead_texts:
            errors.append(f"{item_id} companion lead repeats rejected lead example {companion_lead_seed!r}")
        rejected_texts: set[str] = set()
        for index, rejected in enumerate(rejected_replies):
            if not isinstance(rejected, dict):
                errors.append(f"{item_id} rejected reply example {index} must be object")
                continue
            for key in ("display_text", "negative_type", "reject_reason", "correction_hint"):
                if not str(rejected.get(key) or "").strip():
                    errors.append(f"{item_id} rejected reply example {index} missing {key}")
            rejected_texts.add(str(rejected.get("display_text") or ""))
        for index, reply in enumerate(replies):
            if not isinstance(reply, dict):
                errors.append(f"{item_id} reply seed {index} must be object")
                continue
            for key in ("display_text", "emotion_role", "semantic_role", "intent_note"):
                if not str(reply.get(key) or "").strip():
                    errors.append(f"{item_id} reply seed {index} missing {key}")
            display_text = str(reply.get("display_text") or "")
            if display_text in rejected_texts:
                errors.append(f"{item_id} reply seed {index} repeats rejected reply example {display_text!r}")
            for term in PRODUCER_STANCE_LEAK_TERMS:
                if term in display_text:
                    errors.append(f"{item_id} reply seed {index} leaks producer/action stance term {term!r}")
    if item.get("label") == "hard_negative":
        if applicability not in {"negative_boundary", "not_ready"}:
            errors.append(f"{item_id} hard-negative authoring seed must not be authoring_reference")
    return errors


def validate_json_schema(data: dict[str, Any], schema_path: Path) -> tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:
        return False, f"jsonschema missing: {exc}"
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return True, "ok"
    first = errors[0]
    path = ".".join(str(part) for part in first.absolute_path) or "<root>"
    return False, f"{path}: {first.message}"


def contains_local_path(value: Any) -> bool:
    if isinstance(value, str):
        return any(marker in value for marker in LOCAL_PATH_MARKERS)
    if isinstance(value, list):
        return any(contains_local_path(item) for item in value)
    if isinstance(value, dict):
        return any(contains_local_path(item) for item in value.values())
    return False


def read_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
