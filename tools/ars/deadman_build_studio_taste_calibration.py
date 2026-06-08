#!/usr/bin/env python3
"""Build the Studio CAB taste calibration artifact.

Reads the owner taste tray markdown (after owner edits), pairs each owner
verdict with the judge verdict for the same case, computes overall agreement,
and writes a sanitized calibration artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
DEFAULT_JUDGE_PATH = REPO_ROOT / "data/evals/studio_cab_taste_judge.v0.1.json"
DEFAULT_TRAY_PATH = REPO_ROOT / "data/review/studio_cab_owner_taste_tray.v0.1.md"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/evals/studio_cab_taste_calibration.v0.1.json"
SCHEMA_VERSION = "studio_cab_taste_calibration.v0.1"
PRODUCT = "看剧搭子"

OWNER_VERDICT_VALUES = {"accept", "accept_with_minor_tweak", "reject", "abstain"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_PROOF_PATH))
    parser.add_argument("--judge", default=str(DEFAULT_JUDGE_PATH))
    parser.add_argument("--tray", default=str(DEFAULT_TRAY_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--created-at", default="")
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    judge_path = resolve_path(args.judge)
    tray_path = resolve_path(args.tray)
    output_path = resolve_path(args.output)
    created_at = args.created_at or now_iso()
    proof = read_json(proof_path)
    judge = read_json(judge_path)
    tray_text = tray_path.read_text(encoding="utf-8")
    owner_verdicts = parse_tray(tray_text)
    artifact = build_calibration_artifact(
        proof=proof,
        judge=judge,
        proof_path=proof_path,
        judge_path=judge_path,
        tray_path=tray_path,
        owner_verdicts=owner_verdicts,
        created_at=created_at,
    )
    write_json(output_path, artifact)
    print(f"Wrote Studio CAB taste calibration: {repo_relative(output_path)}")
    print(
        f"summary: agreement_rate={artifact['summary']['agreement_rate']:.2f} "
        f"({artifact['summary']['agreement_count']}/{artifact['summary']['owner_reviewed']} "
        f"owner-reviewed)"
    )
    return 0


_CASE_ID_RE = re.compile(r"\*\*case_id\*\*:\s*`([^`]+)`")
_OWNER_VERDICT_RE = re.compile(r"^owner_verdict:\s*(\S.*?)\s*$", re.MULTILINE)
_OWNER_NOTES_RE = re.compile(r"^owner_notes:\s*(.*?)\s*$", re.MULTILINE)
_DRAFT_SECTION_SPLIT = re.compile(r"^## Draft\s+\d+\s*/\s*\d+", re.MULTILINE)


def parse_tray(text: str) -> dict[str, dict[str, str]]:
    sections = _DRAFT_SECTION_SPLIT.split(text)[1:]  # drop preamble
    result: dict[str, dict[str, str]] = {}
    for section in sections:
        case_id_match = _CASE_ID_RE.search(section)
        if not case_id_match:
            continue
        case_id = case_id_match.group(1).strip()
        verdict_match = _OWNER_VERDICT_RE.search(section)
        notes_match = _OWNER_NOTES_RE.search(section)
        verdict = (verdict_match.group(1).strip() if verdict_match else "abstain")
        verdict = verdict if verdict in OWNER_VERDICT_VALUES else "abstain"
        notes = (notes_match.group(1).strip() if notes_match else "")
        result[case_id] = {"verdict": verdict, "notes": notes}
    return result


def build_calibration_artifact(
    *,
    proof: dict[str, Any],
    judge: dict[str, Any],
    proof_path: Path,
    judge_path: Path,
    tray_path: Path,
    owner_verdicts: dict[str, dict[str, str]],
    created_at: str,
) -> dict[str, Any]:
    judge_by_case = {v["case_id"]: v for v in judge.get("verdicts", [])}
    case_by_case = {c["case_id"]: c for c in proof.get("case_results", [])}

    entries: list[dict[str, Any]] = []
    for case_id, judge_v in judge_by_case.items():
        case = case_by_case.get(case_id, {})
        owner = owner_verdicts.get(case_id, {"verdict": "abstain", "notes": ""})
        owner_verdict = owner["verdict"]
        owner_notes = owner["notes"]
        judge_overall = judge_v.get("overall_verdict", "not_available")
        agreement = compute_agreement(owner_verdict, judge_overall)
        entries.append({
            "case_id": case_id,
            "case_type": case.get("case_type", judge_v.get("case_type", "")),
            "item_id": case.get("item_id", judge_v.get("item_id", "")),
            "episode_id": case.get("episode_id", judge_v.get("episode_id", "")),
            "owner_verdict": owner_verdict,
            "owner_notes": owner_notes,
            "judge_overall_verdict": judge_overall,
            "judge_dimensions": {
                "lead_taste": judge_v.get("lead_taste", "not_available"),
                "reply_voice_taste": judge_v.get("reply_voice_taste", "not_available"),
                "reply_axis_diversity": judge_v.get("reply_axis_diversity", "not_available"),
                "echo_taste": judge_v.get("echo_taste", "not_available"),
            },
            "judge_rationale_summary": judge_v.get("rationale_summary", ""),
            "agreement": agreement,
        })

    summary = build_summary(entries)
    owner_reviewed = summary["owner_reviewed"]
    if owner_reviewed == 0:
        status = "awaiting_owner_review"
    elif owner_reviewed == summary["total_cases"]:
        status = "completed"
    else:
        status = "partial_owner_review"

    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "created_at": created_at,
        "status": status,
        "claim_boundary": (
            "Owner taste verdicts cross-calibrated against judge verdicts (judge "
            "provider recorded in the judge artifact; may be same-model Doubao/Ark "
            "or cross-model Qwen). Calibration is advisory only and does not "
            "promote drafts into runtime packs. Sample size is small; agreement "
            "rate is a directional signal, not a statistical claim."
        ),
        "proof_ref": {
            "path": repo_relative(proof_path),
            "sha256": sha256_file(proof_path),
            "schema_version": proof["schema_version"],
        },
        "judge_ref": {
            "path": repo_relative(judge_path),
            "sha256": sha256_file(judge_path),
            "schema_version": judge["schema_version"],
        },
        "tray_ref": {
            "path": repo_relative(tray_path),
            "sha256": sha256_file(tray_path),
        },
        "calibration_entries": entries,
        "summary": summary,
    }


def compute_agreement(owner: str, judge: str) -> str:
    if owner == "abstain":
        return "abstain"
    if judge == "not_available":
        return "judge_unavailable"
    return "agree" if owner == judge else "disagree"


def build_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
