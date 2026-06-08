#!/usr/bin/env python3
"""Validate Deadman v0.41 Studio CAB LangGraph proof reports."""

from __future__ import annotations

import argparse
import json
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
DEFAULT_GRAPH_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_graph_proof.v0.1.json"
SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_graph_proof.v0.1.json"
EXPECTED_NODE_ORDER = [
    "load_studio_guidance_dataset",
    "select_phase2_6_cases",
    "cab_author_displays_node",
    "cab_author_echoes_node",
    "validate_and_compress",
    "write_sanitized_graph_proof",
]

try:
    from tools.ars.deadman_validate_studio_real_provider_proof import (
        DEFAULT_PROOF_PATH as REAL_PROVIDER_PROOF_PATH,
        validate_json_schema,
        validate_studio_real_provider_proof,
    )
except ModuleNotFoundError:
    from .deadman_validate_studio_real_provider_proof import (
        DEFAULT_PROOF_PATH as REAL_PROVIDER_PROOF_PATH,
        validate_json_schema,
        validate_studio_real_provider_proof,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_GRAPH_PROOF_PATH))
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    proof = read_json(proof_path)
    errors = validate_studio_cab_graph_proof(proof=proof, proof_path=proof_path)
    if errors:
        print(f"Deadman Studio CAB graph proof failed: {repo_relative(proof_path)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Deadman Studio CAB graph proof passed: {repo_relative(proof_path)}")
    return 0


def validate_studio_cab_graph_proof(*, proof: dict[str, Any], proof_path: Path) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(proof, SCHEMA_PATH)
    if not schema_ok:
        return [f"schema: {schema_message}"]
    graph_identity = proof["graph_identity"]
    if graph_identity["node_order"] != EXPECTED_NODE_ORDER:
        errors.append("graph_identity.node_order does not match Studio CAB graph contract")
    if graph_identity["core_semantic_node"] != "cab_author_displays_node":
        errors.append("core semantic node must be cab_author_displays_node")
    proof_report = proof["proof_report"]
    if not isinstance(proof_report, dict):
        return [*errors, "proof_report must be an object"]
    inner_errors = validate_studio_real_provider_proof(
        proof=proof_report,
        proof_path=REAL_PROVIDER_PROOF_PATH,
    )
    errors.extend(f"proof_report: {error}" for error in inner_errors)
    if proof["status"] != proof_report.get("status"):
        errors.append("graph proof status must match proof_report status")
    if proof["publication_decision"] != proof_report.get("publication_decision"):
        errors.append("graph proof publication_decision must match proof_report")
    if proof["guidance_dataset_ref"] != proof_report.get("guidance_dataset_ref"):
        errors.append("graph proof guidance_dataset_ref must match proof_report")
    if proof_report.get("planned_case_count") != 8:
        errors.append("graph proof must cover the 8 Phase 2.6 planned cases")
    return errors


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
