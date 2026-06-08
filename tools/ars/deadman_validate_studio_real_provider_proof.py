#!/usr/bin/env python3
"""Validate Deadman v0.41 Phase 2.6 real-provider Studio proof reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_real_provider_proof.v0.1.json"
GUIDANCE_PATH = REPO_ROOT / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "file://")
FORBIDDEN_TEXT = ("ARK_API_KEY", "Bearer ", "api_key", "provider_trace", "local_artifacts/", "tmp/")
SUCCESS_BUCKETS = {
    "reviewable_without_major_rewrite",
    "expected_rejection_pass",
    "context_boundary_pass",
    "repair_regression_pass",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_PROOF_PATH))
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    proof = read_json(proof_path)
    errors = validate_studio_real_provider_proof(proof=proof, proof_path=proof_path)
    if errors:
        print(f"Deadman Studio real-provider proof failed: {repo_relative(proof_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman Studio real-provider proof passed: {repo_relative(proof_path)}")
    fresh, message = proof_freshness(proof)
    print(f"  freshness: {'current' if fresh else 'STALE'} — {message}")
    return 0


def proof_freshness(proof: dict[str, Any]) -> tuple[bool, str]:
    """Report whether the proof's recorded dataset hash matches the live dataset.

    This is freshness, not validity: in the dataset-centric loop a proof legitimately
    lags the dataset by one owner reflow. STALE here means "re-run authoring to
    re-sync", not "invalid".
    """
    ref = proof.get("guidance_dataset_ref", {})
    recorded = ref.get("sha256", "")
    if not GUIDANCE_PATH.exists():
        return True, "current dataset not found; cannot compare"
    current = sha256_file(GUIDANCE_PATH)
    if recorded == current:
        return True, "proof ran against the live guidance dataset"
    return False, "dataset has advanced since this proof (owner reflow); re-run authoring to re-sync"


def validate_studio_real_provider_proof(*, proof: dict[str, Any], proof_path: Path) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(proof, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    if contains_local_path(proof):
        errors.append("proof contains machine-specific local path")
    if contains_forbidden_text(proof):
        errors.append("proof contains forbidden provider/local trace text")
    if proof["publication_decision"] != "no_runtime_promotion":
        errors.append("proof must not promote runtime packs")
    if proof["provider_identity_redacted"].get("mock_provider") is not False:
        errors.append("Phase 2.6 proof must be a real provider run, not mock")

    guidance_ref = proof["guidance_dataset_ref"]
    if resolve_path(guidance_ref["path"]) != GUIDANCE_PATH:
        errors.append("proof guidance_dataset_ref must point to canonical guidance dataset")
    # guidance_dataset_ref.sha256 is PROVENANCE: the hash of the dataset this proof
    # actually consumed. It is intentionally NOT required to equal the current
    # dataset hash. In the dataset-centric loop, authoring runs against state S and
    # owner reflow then advances the dataset to S+1, so the latest proof always
    # lags the live dataset by one reflow. Equality-with-current is a FRESHNESS
    # property (see proof_is_current / freshness reporting), not a validity error.
    # The schema still enforces the hash is a well-formed sha256.

    case_results = proof["case_results"]
    if proof["attempted_case_count"] != len(case_results):
        errors.append("attempted_case_count does not match case_results")
    completed = sum(1 for case in case_results if case["provider_status"] == "completed")
    if proof["completed_case_count"] != completed:
        errors.append("completed_case_count does not match completed case_results")
    if proof_path == DEFAULT_PROOF_PATH and proof["planned_case_count"] != 8:
        errors.append("tracked Phase 2.6 proof must cover the 8 planned cases")

    case_ids = {case["case_id"] for case in case_results}
    if len(case_ids) != len(case_results):
        errors.append("case_results contain duplicate case_id")
    repair_pairs = {
        (repair["case_id"], repair["failure_bucket"])
        for repair in proof["repair_candidates"]
    }
    for index, case in enumerate(case_results):
        if case["draft_review_status"] != "draft_not_owner_reviewed":
            errors.append(f"case_results[{index}] draft_review_status must remain draft_not_owner_reviewed")
        if case["provider_status"] == "completed" and case["schema_validation"] != "pass":
            errors.append(f"case_results[{index}] completed provider result must pass schema_validation")
        non_success = [bucket for bucket in case["failure_buckets"] if bucket not in SUCCESS_BUCKETS]
        if non_success and any(bucket in SUCCESS_BUCKETS for bucket in case["failure_buckets"]):
            errors.append(f"case_results[{index}] mixes success and failure buckets")
        for bucket in non_success:
            if (case["case_id"], bucket) not in repair_pairs:
                errors.append(f"{case['case_id']} failure bucket {bucket} lacks repair_candidate")
    errors.extend(validate_failure_bucket_summary(proof))
    return errors


def validate_failure_bucket_summary(proof: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected: dict[str, list[str]] = {}
    for case in proof["case_results"]:
        for bucket in case["failure_buckets"]:
            expected.setdefault(bucket, []).append(case["case_id"])
    actual = {item["bucket"]: item for item in proof["failure_buckets"]}
    if set(actual) != set(expected):
        errors.append("failure_buckets summary keys do not match case_results")
        return errors
    for bucket, case_ids in expected.items():
        item = actual[bucket]
        if item["count"] != len(case_ids):
            errors.append(f"failure bucket {bucket} count mismatch")
        if item["case_ids"] != case_ids:
            errors.append(f"failure bucket {bucket} case_ids mismatch")
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


def contains_forbidden_text(value: Any) -> bool:
    if isinstance(value, str):
        return any(marker in value for marker in FORBIDDEN_TEXT)
    if isinstance(value, list):
        return any(contains_forbidden_text(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_text(item) for item in value.values())
    return False


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
