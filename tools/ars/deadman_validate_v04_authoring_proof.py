#!/usr/bin/env python3
"""Validate the tracked Deadman v0.4 Studio authoring proof fixture."""

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
    from tools.ars.deadman_build_v04_authoring_proof import (
        COMPANION_EXCHANGE_SCHEMA_PATH,
        DEFAULT_GOLD_MOMENT_ID,
        DEFAULT_NON_GOLD_MOMENT_ID,
        DEFAULT_OUTPUT_PATH,
        PROOF_SCHEMA_PATH,
        has_absolute_path,
        read_json,
        repo_relative,
        resolve_path,
        validate_json_schema,
    )
except ModuleNotFoundError:
    from .deadman_build_v04_authoring_proof import (
        COMPANION_EXCHANGE_SCHEMA_PATH,
        DEFAULT_GOLD_MOMENT_ID,
        DEFAULT_NON_GOLD_MOMENT_ID,
        DEFAULT_OUTPUT_PATH,
        PROOF_SCHEMA_PATH,
        has_absolute_path,
        read_json,
        repo_relative,
        resolve_path,
        validate_json_schema,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    proof = read_json(proof_path)
    errors = validate_authoring_proof(proof)
    if errors:
        print(f"Deadman v0.4 authoring proof failed: {repo_relative(proof_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman v0.4 authoring proof passed: {repo_relative(proof_path)}")
    return 0


def validate_authoring_proof(proof: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(proof, PROOF_SCHEMA_PATH)
    if not schema_ok:
        errors.append(f"proof schema: {schema_message}")
        return errors
    if proof.get("proof_status") != "pass":
        errors.append("proof_status must be pass")
    if has_absolute_path(proof):
        errors.append("proof contains absolute local path")
    runtime = proof.get("authoring_runtime", {})
    provider = runtime.get("provider", {}) if isinstance(runtime, dict) else {}
    if provider.get("mock_provider") is not True:
        errors.append("tracked proof must declare mock_provider=true unless a separate non-mock proof is added")
    claim_boundary = str(runtime.get("claim_boundary") or "")
    if "not a live external LLM/CAB provider claim" not in claim_boundary:
        errors.append("mock proof must include explicit non-live-provider claim boundary")

    runs = proof.get("runs", [])
    roles = {run.get("run_role") for run in runs if isinstance(run, dict)}
    if "ep03_gold_smoke" not in roles:
        errors.append("missing EP03 gold smoke run")
    if "non_gold_authoring_proof" not in roles:
        errors.append("missing non-gold authoring proof run")

    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"runs[{index}] must be an object")
            continue
        errors.extend(validate_run(run, index))
    return errors


def validate_run(run: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    role = run.get("run_role")
    moment_id = run.get("moment_id")
    if role == "ep03_gold_smoke":
        if moment_id != DEFAULT_GOLD_MOMENT_ID or run.get("is_gold_reference") is not True:
            errors.append(f"runs[{index}] EP03 smoke must use {DEFAULT_GOLD_MOMENT_ID} as gold reference")
    if role == "non_gold_authoring_proof":
        if moment_id == DEFAULT_GOLD_MOMENT_ID or run.get("is_gold_reference") is not False:
            errors.append(f"runs[{index}] non-gold proof must not use the EP03 gold moment")
        if moment_id != DEFAULT_NON_GOLD_MOMENT_ID:
            errors.append(f"runs[{index}] expected non-gold proof moment {DEFAULT_NON_GOLD_MOMENT_ID}")
    generated = run.get("generated_draft", {}) if isinstance(run.get("generated_draft"), dict) else {}
    exchange = generated.get("companion_exchange_draft")
    if not isinstance(exchange, dict):
        errors.append(f"runs[{index}] generated_draft.companion_exchange_draft missing")
    else:
        schema_ok, schema_message = validate_json_schema(exchange, COMPANION_EXCHANGE_SCHEMA_PATH)
        if not schema_ok:
            errors.append(f"runs[{index}] exchange schema: {schema_message}")
        if exchange.get("review_status") != "needs_review":
            errors.append(f"runs[{index}] exchange draft must be needs_review")
        if len(exchange.get("reply_candidates", [])) != 3:
            errors.append(f"runs[{index}] exchange draft must contain exactly three replies")
    validation = run.get("draft_validation", {}) if isinstance(run.get("draft_validation"), dict) else {}
    if validation.get("schema_valid") is not True or validation.get("conformance_valid") is not True:
        errors.append(f"runs[{index}] draft validation must pass")
    review = run.get("human_review", {}) if isinstance(run.get("human_review"), dict) else {}
    if review.get("decision") not in {"accepted", "accepted_with_revision"}:
        errors.append(f"runs[{index}] human review must accept or accept_with_revision")
    final_status = run.get("final_status", {}) if isinstance(run.get("final_status"), dict) else {}
    if final_status.get("published") is not True or final_status.get("published_review_status") != "reviewed":
        errors.append(f"runs[{index}] final published status must point to reviewed pack")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
