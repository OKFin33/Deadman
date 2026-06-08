#!/usr/bin/env python3
"""Validate Deadman v0.41 Studio CAB taste calibration artifacts."""

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
DEFAULT_PATH = REPO_ROOT / "data/evals/studio_cab_taste_calibration.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_taste_calibration.v0.1.json"
PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
JUDGE_PATH = REPO_ROOT / "data/evals/studio_cab_taste_judge.v0.1.json"
TRAY_PATH = REPO_ROOT / "data/review/studio_cab_owner_taste_tray.v0.1.md"
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "file://")
FORBIDDEN_TEXT = ("ARK_API_KEY", "Bearer ", "api_key", "local_artifacts/", "tmp/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=str(DEFAULT_PATH))
    args = parser.parse_args()
    artifact_path = resolve_path(args.artifact)
    artifact = read_json(artifact_path)
    errors = validate_studio_taste_calibration(artifact=artifact, artifact_path=artifact_path)
    if errors:
        print(f"Deadman Studio taste calibration failed: {repo_relative(artifact_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman Studio taste calibration passed: {repo_relative(artifact_path)}")
    return 0


def validate_studio_taste_calibration(*, artifact: dict[str, Any], artifact_path: Path) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(artifact, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    if contains_local_path(artifact):
        errors.append("calibration contains machine-specific local path")
    if contains_forbidden_text(artifact):
        errors.append("calibration contains forbidden provider/local trace text")
    proof_ref = artifact["proof_ref"]
    if resolve_path(proof_ref["path"]) != PROOF_PATH:
        errors.append("calibration proof_ref must point to canonical real-provider proof")
    elif PROOF_PATH.exists() and sha256_file(PROOF_PATH) != proof_ref["sha256"]:
        errors.append("calibration proof_ref hash does not match current real-provider proof")
    judge_ref = artifact["judge_ref"]
    if resolve_path(judge_ref["path"]) != JUDGE_PATH:
        errors.append("calibration judge_ref must point to canonical judge artifact")
    elif JUDGE_PATH.exists() and sha256_file(JUDGE_PATH) != judge_ref["sha256"]:
        errors.append("calibration judge_ref hash does not match current judge artifact")
    tray_ref = artifact["tray_ref"]
    if resolve_path(tray_ref["path"]) != TRAY_PATH:
        errors.append("calibration tray_ref must point to canonical tray file")
    elif TRAY_PATH.exists() and sha256_file(TRAY_PATH) != tray_ref["sha256"]:
        errors.append("calibration tray_ref hash does not match current tray file")
    expected_summary = expected_summary_from_entries(artifact["calibration_entries"])
    if artifact["summary"] != expected_summary:
        errors.append("summary does not match calibration_entries roll-up")
    return errors


def expected_summary_from_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(entries)
    owner_reviewed = sum(1 for e in entries if e["owner_verdict"] != "abstain")
    owner_abstained = total - owner_reviewed
    owner_dist = {k: 0 for k in ("accept", "accept_with_minor_tweak", "reject", "abstain")}
    judge_dist = {k: 0 for k in ("accept", "accept_with_minor_tweak", "reject", "not_available")}
    agreement_count = 0
    for entry in entries:
        owner_dist[entry["owner_verdict"]] += 1
        judge_dist[entry["judge_overall_verdict"]] += 1
        if entry["agreement"] == "agree":
            agreement_count += 1
    agreement_rate = round(agreement_count / owner_reviewed, 4) if owner_reviewed else 0.0
    return {
        "total_cases": total,
        "owner_reviewed": owner_reviewed,
        "owner_abstained": owner_abstained,
        "owner_verdict_distribution": owner_dist,
        "judge_verdict_distribution": judge_dist,
        "agreement_count": agreement_count,
        "agreement_rate": agreement_rate,
    }


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
