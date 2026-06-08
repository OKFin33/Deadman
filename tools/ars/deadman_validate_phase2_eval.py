#!/usr/bin/env python3
"""Validate Deadman v0.41 Phase 2 Loop 1 eval artifacts."""

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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from tools.ars.deadman_build_phase2_eval import (
        EXCHANGE_OUTPUT_PATH,
        EXCHANGE_REPAIR_OUTPUT_PATH,
        PHASE2_EVAL_OUTPUT_PATH,
        PHASE2_REPORT_PATH,
        WINDOW_JUDGE_OUTPUT_PATH,
        contains_local_path,
        read_json,
        repo_relative,
        resolve_path,
    )
    from tools.ars.deadman_validate_v04_authoring_proof import validate_json_schema
except ModuleNotFoundError:
    from .deadman_build_phase2_eval import (
        EXCHANGE_OUTPUT_PATH,
        EXCHANGE_REPAIR_OUTPUT_PATH,
        PHASE2_EVAL_OUTPUT_PATH,
        PHASE2_REPORT_PATH,
        WINDOW_JUDGE_OUTPUT_PATH,
        contains_local_path,
        read_json,
        repo_relative,
        resolve_path,
    )
    from .deadman_validate_v04_authoring_proof import validate_json_schema


WINDOW_SCHEMA_PATH = REPO_ROOT / "data/schemas/window_taste_phase2_judge_report.v0.1.json"
EXCHANGE_SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_exchange_authoring_phase2.v0.1.json"
PHASE2_SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_phase2_eval.v0.1.json"
EXCHANGE_REPAIR_SCHEMA_PATH = REPO_ROOT / "data/schemas/exchange_authoring_phase2_repair_candidates.v0.1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-report", default=str(WINDOW_JUDGE_OUTPUT_PATH))
    parser.add_argument("--exchange-report", default=str(EXCHANGE_OUTPUT_PATH))
    parser.add_argument("--phase2-eval", default=str(PHASE2_EVAL_OUTPUT_PATH))
    parser.add_argument("--exchange-repairs", default=str(EXCHANGE_REPAIR_OUTPUT_PATH))
    args = parser.parse_args()

    window_path = resolve_path(args.window_report)
    exchange_path = resolve_path(args.exchange_report)
    phase2_path = resolve_path(args.phase2_eval)
    repair_path = resolve_path(args.exchange_repairs)
    errors = validate_phase2_artifacts(
        window_report=read_json(window_path),
        exchange_report=read_json(exchange_path),
        phase2_eval=read_json(phase2_path),
        exchange_repairs=read_json(repair_path) if repair_path.exists() else None,
    )
    if errors:
        print("Deadman v0.41 Phase 2 eval failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman v0.41 Phase 2 eval passed: {repo_relative(phase2_path)}")
    return 0


def validate_phase2_artifacts(
    *,
    window_report: dict[str, Any],
    exchange_report: dict[str, Any],
    phase2_eval: dict[str, Any],
    exchange_repairs: dict[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_schema("window judge report", window_report, WINDOW_SCHEMA_PATH))
    errors.extend(validate_schema("exchange authoring report", exchange_report, EXCHANGE_SCHEMA_PATH))
    errors.extend(validate_schema("phase2 eval", phase2_eval, PHASE2_SCHEMA_PATH))
    if exchange_repairs is not None:
        errors.extend(validate_schema("exchange repair candidates", exchange_repairs, EXCHANGE_REPAIR_SCHEMA_PATH))
    if errors:
        return errors

    if contains_local_path(window_report) or contains_local_path(exchange_report) or contains_local_path(phase2_eval):
        errors.append("phase2 artifacts contain machine-specific local path")
    if exchange_repairs is not None and contains_local_path(exchange_repairs):
        errors.append("exchange repair candidates contain machine-specific local path")

    window_gate = window_report["acceptance_gate"]
    if window_gate["gold_top3_count"] < 8:
        errors.append("window judge gate needs at least 8/10 owner gold in top3")
    if window_gate["owner_reviewed_rejects_rejected_count"] < 14:
        errors.append("window judge gate needs at least 14/17 owner-reviewed rejects rejected")
    if window_gate["action_menu_publishable_top1_count"] != 0:
        errors.append("window judge has publishable action-menu/RPG top1")
    if window_gate["publishable_without_opening_count"] != 0:
        errors.append("window judge has publishable item without opening hypothesis")
    if len(window_report["review_gate_a"]["owner_review_target"]) > 10:
        errors.append("Review Gate A exceeds 10 compressed items")

    exchange_gate = exchange_report["acceptance_gate"]
    if exchange_gate["schema_valid_count"] != 10:
        errors.append("exchange gate requires 10/10 schema-valid drafts")
    if exchange_gate["conformance_valid_count"] != 10:
        errors.append("exchange gate requires 10/10 conformance-valid drafts")
    if exchange_gate["no_question_shaped_lead_count"] != 10:
        errors.append("exchange gate requires 10/10 no question-shaped leads")
    if exchange_gate["no_rpg_action_reply_count"] != 10:
        errors.append("exchange gate requires 10/10 no RPG/action preset wording")
    if exchange_gate["friend_echo_count"] != 10:
        errors.append("exchange gate requires 10/10 friend-style selected echoes")
    if exchange_gate["reviewable_without_major_rewrite_count"] < 7:
        errors.append("exchange gate requires at least 7/10 reviewable drafts")
    if len(exchange_report["review_gate_b"]["owner_review_target"]) > 10:
        errors.append("Review Gate B exceeds 10 compressed items")

    demo_candidates = phase2_eval["phase3_demo_pack_candidates"]
    if not 3 <= len(demo_candidates) <= 5:
        errors.append("phase2 eval must nominate 3-5 phase3 demo candidates")
    if any(candidate.get("promotion_status") != "nominated_only_not_promoted" for candidate in demo_candidates):
        errors.append("phase2 eval must not promote runtime packs")
    if phase2_eval["goal_gate_summary"]["runtime_pack_promotion"] != "not_performed_phase3_only":
        errors.append("goal summary must state runtime promotion was not performed")

    refs = phase2_eval["report_refs"]
    if refs.get("exchange_repair_candidates") and exchange_repairs is None:
        errors.append("phase2 eval references exchange repair candidates but file is missing")
    if exchange_repairs is not None:
        repair_count = len(exchange_repairs.get("items", []))
        if phase2_eval["repair_status"]["exchange_repair_candidate_count"] != repair_count:
            errors.append("phase2 eval repair count does not match repair dataset")

    if not PHASE2_REPORT_PATH.exists():
        errors.append(f"missing phase2 markdown report: {repo_relative(PHASE2_REPORT_PATH)}")
    return errors


def validate_schema(name: str, data: dict[str, Any], schema_path: Path) -> list[str]:
    schema_ok, schema_message = validate_json_schema(data, schema_path)
    if schema_ok:
        return []
    return [f"{name} schema: {schema_message}"]


if __name__ == "__main__":
    raise SystemExit(main())
