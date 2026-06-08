#!/usr/bin/env python3
"""Reflow owner field-level taste verdicts back into the Studio Guidance Dataset.

This closes the dataset-centric loop: owner-approved fields become positive
examples (display_text + viewer_motivation, lead, and echo triples), owner-
rejected fields become rejected_examples with a named negative_type. The dataset
is the durable artifact that grows each round; prompts and code are scaffolding.

Dry-run by default: prints the proposed delta and writes nothing. Pass --apply to
merge into the dataset, recompute summary counts, and re-validate. Re-applying the
same verdict file is idempotent (dedup by normalized text per item).
"""

from __future__ import annotations

import argparse
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

DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
DEFAULT_VERDICTS_PATH = REPO_ROOT / "data/review/studio_cab_field_verdicts.v0.1.json"
DEFAULT_DATASET_PATH = REPO_ROOT / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"

GENERIC_LEAD_POLICY = (
    "Owner-reviewed positive lead. Keep it one well-timed friend comment tied to "
    "the exact source-window situation; invite the viewer's own line without a "
    "question, UI instruction, or plot analysis."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_PROOF_PATH))
    parser.add_argument("--verdicts", default=str(DEFAULT_VERDICTS_PATH))
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--apply", action="store_true", help="Write the merged dataset (default: dry-run).")
    parser.add_argument("--created-at", default="")
    args = parser.parse_args()

    proof = read_json(resolve_path(args.proof))
    verdicts = read_json(resolve_path(args.verdicts))
    dataset_path = resolve_path(args.dataset)
    dataset = read_json(dataset_path)
    created_at = args.created_at or now_iso()

    drafts_by_case = {c["case_id"]: c for c in proof.get("case_results", [])}
    delta = build_delta(
        verdicts=verdicts,
        drafts_by_case=drafts_by_case,
        verdict_ref=repo_relative(resolve_path(args.verdicts)),
        created_at=created_at,
    )
    print_delta(delta)

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to merge into the dataset.")
        return 0

    merged, applied = merge_delta(dataset, delta)
    recompute_summary(merged)
    errors = validate_dataset(merged, dataset_path)
    if errors:
        print("\nRefusing to write: merged dataset fails validation:")
        for error in errors[:10]:
            print(f"- {error}")
        return 1
    write_json(dataset_path, merged)
    print(f"\nApplied reflow to {repo_relative(dataset_path)}:")
    for bucket, counts in applied.items():
        print(f"  {bucket}: +{counts['added']} added, {counts['enriched']} enriched")
    return 0


def build_delta(
    *,
    verdicts: dict[str, Any],
    drafts_by_case: dict[str, Any],
    verdict_ref: str,
    created_at: str,
) -> dict[str, list[dict[str, Any]]]:
    delta: dict[str, list[dict[str, Any]]] = {
        "lead_examples": [],
        "lead_rejected_examples": [],
        "reply_examples": [],
        "reply_rejected_examples": [],
        "owner_reviewed_echo_examples": [],
        "echo_rejected_examples": [],
    }
    for case_id, case_verdict in (verdicts.get("cases") or {}).items():
        case = drafts_by_case.get(case_id)
        if not case:
            continue
        item_id = str(case.get("item_id") or "")
        episode_id = str(case.get("episode_id") or "")
        draft = case.get("draft", {})
        lead = str(draft.get("companion_lead") or "")
        replies = draft.get("reply_candidates") or []

        lead_v = case_verdict.get("lead", {})
        if lead_v.get("verdict") == "accept" and lead:
            delta["lead_examples"].append({
                "item_id": item_id,
                "episode_id": episode_id,
                "provenance": "owner_confirmed",
                "review_status": "owner_reviewed_positive",
                "lead_text": lead,
                "scene_signal": lead,
                "policy": GENERIC_LEAD_POLICY,
                "source_ref": f"{verdict_ref}#{case_id}.lead_verdict=accept",
            })
        elif lead_v.get("verdict") == "reject" and lead:
            delta["lead_rejected_examples"].append({
                "item_id": item_id,
                "episode_id": episode_id,
                "provenance": "owner_reviewed_reject",
                "review_status": "owner_reviewed_reject",
                "lead_text": lead,
                "negative_type": str(lead_v.get("negative_type") or "owner_taste_reject"),
                "reject_reason": str(lead_v.get("note") or ""),
                "correction_hint": str(lead_v.get("correction_hint") or ""),
                "source_ref": f"{verdict_ref}#{case_id}.lead_verdict=reject",
            })

        for idx, reply_v in enumerate(case_verdict.get("replies") or []):
            if idx >= len(replies):
                break
            reply = replies[idx]
            display_text = str(reply.get("display_text") or "")
            emotion_role = str(reply.get("emotion_role") or "")
            semantic_role = str(reply.get("semantic_role") or "")
            motivation = str(reply.get("viewer_motivation") or "")
            echo = str(reply.get("selected_echo") or "")

            dt_verdict = reply_v.get("display_text_verdict")
            if dt_verdict == "accept" and display_text:
                delta["reply_examples"].append({
                    "item_id": item_id,
                    "episode_id": episode_id,
                    "provenance": "owner_confirmed",
                    "review_status": "owner_reviewed_positive",
                    "candidate_index": idx,
                    "display_text": display_text,
                    "emotion_role": emotion_role,
                    "semantic_role": semantic_role,
                    "viewer_motivation": motivation,
                    "distinctness_rationale": str(reply_v.get("display_text_note") or "Owner-reviewed positive viewer line."),
                    "source_ref": f"{verdict_ref}#{case_id}.replies[{idx}].display_text_verdict=accept",
                })
            elif dt_verdict == "reject" and display_text:
                delta["reply_rejected_examples"].append({
                    "item_id": item_id,
                    "episode_id": episode_id,
                    "provenance": "owner_reviewed_reject",
                    "review_status": "owner_reviewed_reject",
                    "example_index": idx,
                    "display_text": display_text,
                    "emotion_role": emotion_role,
                    "semantic_role": semantic_role,
                    "negative_type": str(reply_v.get("display_text_negative_type") or "owner_taste_reject"),
                    "reject_reason": str(reply_v.get("display_text_note") or ""),
                    "correction_hint": str(reply_v.get("display_text_correction_hint") or ""),
                    "source_ref": f"{verdict_ref}#{case_id}.replies[{idx}].display_text_verdict=reject",
                })

            echo_verdict = reply_v.get("echo_verdict")
            if echo_verdict == "accept" and echo:
                delta["owner_reviewed_echo_examples"].append({
                    "item_id": item_id,
                    "episode_id": episode_id,
                    "provenance": "owner_confirmed",
                    "review_status": "owner_reviewed_positive",
                    "candidate_index": idx,
                    "companion_lead": lead,
                    "display_text": display_text,
                    "viewer_motivation": motivation,
                    "selected_echo": echo,
                    "source_ref": f"{verdict_ref}#{case_id}.replies[{idx}].echo_verdict=accept",
                })
            elif echo_verdict == "reject" and echo:
                delta["echo_rejected_examples"].append({
                    "item_id": item_id,
                    "episode_id": episode_id,
                    "provenance": "owner_reviewed_reject",
                    "review_status": "owner_reviewed_reject",
                    "example_index": idx,
                    "display_text": display_text,
                    "selected_echo": echo,
                    "viewer_motivation": motivation,
                    "negative_type": str(reply_v.get("echo_negative_type") or "owner_taste_reject"),
                    "reject_reason": str(reply_v.get("echo_note") or ""),
                    "correction_hint": str(reply_v.get("echo_correction_hint") or ""),
                    "source_ref": f"{verdict_ref}#{case_id}.replies[{idx}].echo_verdict=reject",
                })
    return delta


def merge_delta(dataset: dict[str, Any], delta: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, int]]:
    splits = dataset["splits"]
    lead = splits["lead_authoring"]
    reply = splits["reply_authoring"]
    echo = splits["selected_echo_direction"]
    echo.setdefault("owner_reviewed_examples", [])

    applied = {
        "lead_examples": _merge_positive(lead["examples"], lead["rejected_examples"], delta["lead_examples"], key=_lead_key),
        "lead_rejected_examples": _merge_negative(lead["rejected_examples"], lead["examples"], delta["lead_rejected_examples"], key=_lead_key),
        "reply_examples": _merge_positive(reply["examples"], reply["rejected_examples"], delta["reply_examples"], key=_reply_key),
        "reply_rejected_examples": _merge_negative(reply["rejected_examples"], reply["examples"], delta["reply_rejected_examples"], key=_reply_key),
        "owner_reviewed_echo_examples": _merge_positive(echo["owner_reviewed_examples"], echo["rejected_examples"], delta["owner_reviewed_echo_examples"], key=_echo_key),
        "echo_rejected_examples": _merge_negative(echo["rejected_examples"], echo["owner_reviewed_examples"], delta["echo_rejected_examples"], key=_echo_key),
    }
    return dataset, applied


def _merge_positive(target: list, opposite: list, incoming: list, *, key) -> dict[str, int]:
    """Add incoming positives; on key match, ENRICH the existing entry.

    Enrichment is the L3 seed: a display_text/echo that was already gold (e.g. a
    Phase 2.5 seed) but lacked viewer_motivation gets the owner-confirmed
    motivation attached, and its provenance is upgraded to owner_confirmed. This
    is why re-confirming an existing line is not a no-op.
    """
    by_key = {key(item): item for item in target}
    added = 0
    enriched = 0
    for item in incoming:
        k = key(item)
        # newer owner-accept overrides a prior reject of the same text
        opposite[:] = [o for o in opposite if key(o) != k]
        if k in by_key:
            existing = by_key[k]
            changed = False
            motivation = item.get("viewer_motivation")
            if motivation and existing.get("viewer_motivation") != motivation:
                existing["viewer_motivation"] = motivation
                changed = True
            if existing.get("provenance") != "owner_confirmed":
                existing["provenance"] = "owner_confirmed"
                existing["review_status"] = "owner_reviewed_positive"
                changed = True
            if changed:
                enriched += 1
            continue
        target.append(item)
        by_key[k] = item
        added += 1
    return {"added": added, "enriched": enriched}


def _merge_negative(target: list, opposite: list, incoming: list, *, key) -> dict[str, int]:
    existing = {key(item) for item in target}
    added = 0
    for item in incoming:
        k = key(item)
        opposite[:] = [o for o in opposite if key(o) != k]
        if k in existing:
            continue
        target.append(item)
        existing.add(k)
        added += 1
    return {"added": added, "enriched": 0}


def _norm(text: str) -> str:
    strip = ",.!?，。！？　、；;:：~～—- \t\n"
    return "".join(ch for ch in (text or "") if ch not in strip)


def _lead_key(item: dict[str, Any]) -> str:
    text = item.get("lead_text") or item.get("display_text") or ""
    return f"{item.get('item_id','')}::{_norm(text)}"


def _reply_key(item: dict[str, Any]) -> str:
    return f"{item.get('item_id','')}::{_norm(item.get('display_text',''))}"


def _echo_key(item: dict[str, Any]) -> str:
    return f"{item.get('item_id','')}::{_norm(item.get('display_text',''))}::{_norm(item.get('selected_echo',''))}"


def recompute_summary(dataset: dict[str, Any]) -> None:
    s = dataset["splits"]
    summary = dataset["summary"]
    window = s["window_selection"]
    summary["window_gold_examples"] = len(window["gold_examples"])
    summary["window_negative_examples"] = len(window["negative_examples"])
    summary["owner_reviewed_window_negative_or_context_examples"] = len(
        [i for i in window["negative_examples"] if i.get("provenance") in {"owner_reviewed_reject", "owner_context_insufficient"}]
    )
    summary["lead_examples"] = len(s["lead_authoring"]["examples"])
    summary["lead_rejected_examples"] = len(s["lead_authoring"]["rejected_examples"])
    summary["lead_repair_examples"] = len(s["lead_authoring"]["repair_examples"])
    summary["reply_examples"] = len(s["reply_authoring"]["examples"])
    summary["reply_rejected_examples"] = len(s["reply_authoring"]["rejected_examples"])
    summary["reply_repair_examples"] = len(s["reply_authoring"]["repair_examples"])
    summary["runtime_reviewed_selected_echo_examples"] = len(s["selected_echo_direction"]["runtime_reviewed_examples"])
    summary["owner_reviewed_selected_echo_examples"] = len(s["selected_echo_direction"].get("owner_reviewed_examples", []))
    summary["draft_selected_echo_examples"] = len(s["selected_echo_direction"]["draft_examples"])
    summary["real_provider_proof_cases_planned"] = len(dataset["real_provider_proof_plan"]["planned_cases"])


def validate_dataset(dataset: dict[str, Any], dataset_path: Path) -> list[str]:
    try:
        from tools.ars.deadman_validate_studio_guidance_dataset import validate_studio_guidance_dataset
    except ModuleNotFoundError:
        from .deadman_validate_studio_guidance_dataset import validate_studio_guidance_dataset
    return validate_studio_guidance_dataset(dataset=dataset, dataset_path=dataset_path)


def print_delta(delta: dict[str, list[dict[str, Any]]]) -> None:
    print("=== Reflow proposal (dataset delta) ===")
    labels = {
        "lead_examples": "+ lead gold (owner_confirmed)",
        "reply_examples": "+ display_text gold (owner_confirmed, with viewer_motivation)",
        "owner_reviewed_echo_examples": "+ echo gold (owner_confirmed, with viewer_motivation)",
        "lead_rejected_examples": "- lead rejected",
        "reply_rejected_examples": "- display_text rejected",
        "echo_rejected_examples": "- echo rejected",
    }
    for key in ["lead_examples", "reply_examples", "owner_reviewed_echo_examples",
                "lead_rejected_examples", "reply_rejected_examples", "echo_rejected_examples"]:
        items = delta[key]
        print(f"\n{labels[key]} ({len(items)}):")
        for item in items:
            text = item.get("lead_text") or item.get("display_text") or ""
            extra = ""
            if "selected_echo" in item:
                extra = f" | echo: {item['selected_echo'][:40]}"
            if item.get("provenance") == "owner_reviewed_reject":
                extra += f" | negative_type: {item.get('negative_type','')}"
            if "viewer_motivation" in item and item.get("provenance") == "owner_confirmed":
                extra += f" | motiv: {item['viewer_motivation'][:24]}"
            print(f"  [{item.get('item_id','')}] {text[:36]}{extra}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
