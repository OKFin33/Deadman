#!/usr/bin/env python3
"""Validate the Deadman v0.41 Studio Guidance Dataset."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_GUIDANCE_PATH = REPO_ROOT / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_guidance_dataset.v0.1.json"
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "file://")
FORBIDDEN_SOURCE_PATH_FRAGMENTS = (
    ".agent/",
    ".env",
    "local_artifacts/",
    "node_modules/",
    "provider_trace",
    "tmp/",
)
EXPECTED_SOURCE_PATHS = {
    "data/evals/window_taste_eval.v0.1.json",
    "data/evals/window_taste_phase2_judge_report.v0.1.json",
    "data/evals/studio_cab_exchange_authoring_phase2.v0.1.json",
    "data/evals/studio_cab_phase2_eval.v0.1.json",
    "data/evals/exchange_authoring_phase2_repair_candidates.v0.1.json",
    "data/dramas/huangnian/moments.v0.1.json",
}
EXPECTED_SPLITS = {
    "window_selection",
    "context_card_requirements",
    "lead_authoring",
    "reply_authoring",
    "selected_echo_direction",
    "custom_input_policy",
    "release_gate_rules",
}
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
    parser.add_argument("--dataset", default=str(DEFAULT_GUIDANCE_PATH))
    args = parser.parse_args()

    dataset_path = resolve_path(args.dataset)
    dataset = read_json(dataset_path)
    errors = validate_studio_guidance_dataset(dataset=dataset, dataset_path=dataset_path)
    if errors:
        print(f"Deadman Studio Guidance Dataset failed: {repo_relative(dataset_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman Studio Guidance Dataset passed: {repo_relative(dataset_path)}")
    return 0


def validate_studio_guidance_dataset(*, dataset: dict[str, Any], dataset_path: Path) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(dataset, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    if contains_local_path(dataset):
        errors.append("dataset contains machine-specific local path")

    errors.extend(validate_sources(dataset))
    errors.extend(validate_counts(dataset))
    errors.extend(validate_provenance(dataset))
    errors.extend(validate_provider_proof_plan(dataset))
    errors.extend(validate_contract_refs(dataset))
    if dataset_path == DEFAULT_GUIDANCE_PATH and dataset.get("created_at") != "2026-06-07T00:00:00Z":
        errors.append("tracked guidance dataset should use deterministic created_at 2026-06-07T00:00:00Z")
    return errors


def validate_sources(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_paths = {source["path"] for source in dataset["source_artifacts"]}
    missing = sorted(EXPECTED_SOURCE_PATHS - seen_paths)
    extra = sorted(seen_paths - EXPECTED_SOURCE_PATHS)
    if missing:
        errors.append(f"missing source artifacts: {missing}")
    if extra:
        errors.append(f"unexpected source artifacts: {extra}")
    for source in dataset["source_artifacts"]:
        path = str(source["path"])
        if any(fragment in path for fragment in FORBIDDEN_SOURCE_PATH_FRAGMENTS):
            errors.append(f"source artifact path is not public-safe: {path}")
        local_path = resolve_path(path)
        if not local_path.exists():
            errors.append(f"source artifact missing: {path}")
            continue
        actual_hash = sha256_file(local_path)
        if actual_hash != source["sha256"]:
            errors.append(f"source artifact hash mismatch: {path}")
    return errors


def validate_counts(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = dataset["summary"]
    splits = dataset["splits"]
    if set(splits) != EXPECTED_SPLITS:
        errors.append(f"splits mismatch: {sorted(splits)}")

    window_split = splits["window_selection"]
    lead_split = splits["lead_authoring"]
    reply_split = splits["reply_authoring"]
    echo_split = splits["selected_echo_direction"]
    proof_plan = dataset["real_provider_proof_plan"]

    expected_counts = {
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
        "runtime_reviewed_selected_echo_examples": len(echo_split["runtime_reviewed_examples"]),
        "owner_reviewed_selected_echo_examples": len(echo_split.get("owner_reviewed_examples", [])),
        "draft_selected_echo_examples": len(echo_split["draft_examples"]),
        "real_provider_proof_cases_planned": len(proof_plan["planned_cases"]),
    }
    for key, expected in expected_counts.items():
        if summary[key] != expected:
            errors.append(f"summary.{key}={summary[key]} does not match actual {expected}")

    if summary["window_gold_examples"] != 10:
        errors.append("guidance dataset must carry exactly 10 window gold examples for Phase 2.5")
    if summary["window_negative_examples"] != 50:
        errors.append("guidance dataset must carry exactly 50 window negative examples for Phase 2.5")
    if summary["owner_reviewed_window_negative_or_context_examples"] < 17:
        errors.append("guidance dataset needs at least 17 owner-reviewed reject/context examples")
    if summary["real_provider_proof_cases_planned"] != 8:
        errors.append("real-provider proof plan must contain 8 planned cases")
    if summary["runtime_reviewed_selected_echo_examples"] < 15:
        errors.append("selected echo split needs the 15 reviewed runtime examples")
    if summary["draft_selected_echo_examples"] != 30:
        errors.append("selected echo split should carry all 30 Phase2 draft examples as direction-only")
    return errors


def validate_provenance(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance_policy = dataset["provenance_policy"]
    if set(provenance_policy["allowed_values"]) != ALLOWED_PROVENANCE:
        errors.append("provenance_policy.allowed_values does not match validator allowlist")
    for path, value in iter_nodes(dataset):
        if isinstance(value, dict) and "provenance" in value:
            provenance = value["provenance"]
            if provenance not in ALLOWED_PROVENANCE:
                errors.append(f"{path}.provenance has unsupported value {provenance!r}")
            review_status = value.get("review_status")
            if provenance in {"draft_not_owner_reviewed", "phase2_repair"} and review_status == "owner_reviewed_positive":
                errors.append(f"{path} lets {provenance} masquerade as owner-reviewed positive")
            if provenance == "runtime_reviewed" and review_status != "reviewed":
                errors.append(f"{path} runtime_reviewed example must carry review_status=reviewed")
            if provenance == "phase2_repair" and review_status != "phase2_repair_auto_applied":
                if "repair_examples" not in path and "planned_cases" not in path:
                    errors.append(f"{path} phase2_repair field example must carry phase2_repair_auto_applied")

    echo_split = dataset["splits"]["selected_echo_direction"]
    for index, example in enumerate(echo_split["draft_examples"]):
        if example["provenance"] != "draft_not_owner_reviewed":
            errors.append(f"selected_echo_direction.draft_examples[{index}] provenance must stay draft_not_owner_reviewed")
        if example["review_status"] != "draft_not_owner_reviewed":
            errors.append(f"selected_echo_direction.draft_examples[{index}] review_status must stay draft_not_owner_reviewed")
    for index, example in enumerate(echo_split["runtime_reviewed_examples"]):
        if example["provenance"] != "runtime_reviewed" or example["review_status"] != "reviewed":
            errors.append(f"selected_echo_direction.runtime_reviewed_examples[{index}] must stay runtime reviewed")
    return errors


def validate_provider_proof_plan(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    plan = dataset["real_provider_proof_plan"]
    if plan["status"] != "prepared_not_run":
        errors.append("real-provider proof plan status must remain prepared_not_run")
    if plan["provider_invocation"] != "not_started":
        errors.append("real-provider proof plan must not show a provider invocation")
    if "ARK_API_KEY" not in plan["requires_env"]:
        errors.append("real-provider proof plan must require ARK_API_KEY")
    case_types = [case["case_type"] for case in plan["planned_cases"]]
    if case_types.count("owner_gold_exchange_authoring") != 3:
        errors.append("real-provider proof plan must include 3 owner gold cases")
    if case_types.count("owner_reviewed_window_reject") != 3:
        errors.append("real-provider proof plan must include 3 owner-reviewed reject/context cases")
    if case_types.count("phase2_repair_regression") != 2:
        errors.append("real-provider proof plan must include 2 phase2 repair regression cases")
    repair_cases = [case for case in plan["planned_cases"] if case["case_type"] == "phase2_repair_regression"]
    repair_failures = {
        str(case["expected_behavior"]).replace("avoid ", "", 1)
        for case in repair_cases
        if str(case.get("expected_behavior", "")).startswith("avoid ")
    }
    if len(repair_failures) < len(repair_cases):
        errors.append("real-provider proof repair cases should cover distinct failure types")
    if "question_shaped_lead_seed" not in repair_failures:
        errors.append("real-provider proof repair cases must include question_shaped_lead_seed")
    return errors


def validate_contract_refs(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ref in dataset["contracts"]:
        path = resolve_path(ref)
        if not path.exists():
            errors.append(f"contract ref missing: {ref}")
    return errors


def iter_nodes(value: Any, path: str = "<root>"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_nodes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_nodes(child, f"{path}[{index}]")


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
