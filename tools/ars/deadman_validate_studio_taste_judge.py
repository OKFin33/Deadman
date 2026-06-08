#!/usr/bin/env python3
"""Validate Deadman v0.41 Studio CAB taste judge reports."""

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
DEFAULT_JUDGE_PATH = REPO_ROOT / "data/evals/studio_cab_taste_judge.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_taste_judge.v0.1.json"
DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
LOCAL_PATH_MARKERS = ("/Users/", "/@fs/", "/var/" + "folders/", "file://")
FORBIDDEN_TEXT = ("ARK_API_KEY", "Bearer ", "api_key", "local_artifacts/", "tmp/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", default=str(DEFAULT_JUDGE_PATH))
    args = parser.parse_args()
    judge_path = resolve_path(args.judge)
    judge = read_json(judge_path)
    errors = validate_studio_taste_judge(judge=judge, judge_path=judge_path)
    if errors:
        print(f"Deadman Studio taste judge report failed: {repo_relative(judge_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman Studio taste judge report passed: {repo_relative(judge_path)}")
    return 0


def validate_studio_taste_judge(*, judge: dict[str, Any], judge_path: Path) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(judge, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    if contains_local_path(judge):
        errors.append("judge report contains machine-specific local path")
    if contains_forbidden_text(judge):
        errors.append("judge report contains forbidden provider/local trace text")
    proof_ref = judge["proof_ref"]
    if resolve_path(proof_ref["path"]) != DEFAULT_PROOF_PATH:
        errors.append("judge proof_ref must point to canonical real-provider proof")
    elif DEFAULT_PROOF_PATH.exists() and sha256_file(DEFAULT_PROOF_PATH) != proof_ref["sha256"]:
        errors.append("judge proof_ref hash does not match current real-provider proof")
    if judge["attempted_case_count"] != len(judge["verdicts"]):
        errors.append("attempted_case_count does not match verdicts length")
    completed = sum(1 for v in judge["verdicts"] if v["provider_status"] == "completed")
    if judge["completed_case_count"] != completed:
        errors.append("completed_case_count does not match completed verdicts")
    summary = judge["verdict_summary"]
    expected = {
        "accept": sum(1 for v in judge["verdicts"] if v["overall_verdict"] == "accept"),
        "accept_with_minor_tweak": sum(1 for v in judge["verdicts"] if v["overall_verdict"] == "accept_with_minor_tweak"),
        "reject": sum(1 for v in judge["verdicts"] if v["overall_verdict"] == "reject"),
        "provider_failed_or_invalid": sum(1 for v in judge["verdicts"] if v["overall_verdict"] == "not_available"),
    }
    if summary != expected:
        errors.append("verdict_summary does not match verdict roll-up")
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
