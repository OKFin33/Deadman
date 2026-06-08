#!/usr/bin/env python3
"""Generate the owner taste review tray markdown for Studio CAB drafts.

The tray displays each draft together with the judge's verdict and a default
owner_verdict (pre-filled to match the judge). The owner opens the markdown,
scans each draft, changes any owner_verdict they disagree with, optionally adds
a note, and saves. The calibration runner reads the saved markdown.
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
DEFAULT_JUDGE_PATH = REPO_ROOT / "data/evals/studio_cab_taste_judge.v0.1.json"
DEFAULT_TRAY_PATH = REPO_ROOT / "data/review/studio_cab_owner_taste_tray.v0.1.md"

VERDICT_OPTIONS = ("accept", "accept_with_minor_tweak", "reject", "abstain")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_PROOF_PATH))
    parser.add_argument("--judge", default=str(DEFAULT_JUDGE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_TRAY_PATH))
    parser.add_argument("--created-at", default="")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite tray even if it already exists (loses prior owner edits).")
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    judge_path = resolve_path(args.judge)
    output_path = resolve_path(args.output)
    created_at = args.created_at or now_iso()
    if output_path.exists() and not args.force:
        print(f"Tray already exists: {repo_relative(output_path)}. Re-run with --force to overwrite.")
        return 1

    proof = read_json(proof_path)
    judge = read_json(judge_path)
    verdict_by_case = {v["case_id"]: v for v in judge.get("verdicts", [])}
    eligible = [
        case for case in proof.get("case_results", [])
        if case["case_id"] in verdict_by_case
    ]
    tray_markdown = render_tray(
        proof=proof,
        judge=judge,
        proof_path=proof_path,
        judge_path=judge_path,
        eligible_cases=eligible,
        verdict_by_case=verdict_by_case,
        created_at=created_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tray_markdown, encoding="utf-8")
    print(f"Wrote owner taste tray: {repo_relative(output_path)}")
    print(f"Edit owner_verdict per draft, save, then run "
          f"tools/ars/deadman_build_studio_taste_calibration.py.")
    return 0


def render_tray(
    *,
    proof: dict[str, Any],
    judge: dict[str, Any],
    proof_path: Path,
    judge_path: Path,
    eligible_cases: list[dict[str, Any]],
    verdict_by_case: dict[str, dict[str, Any]],
    created_at: str,
) -> str:
    proof_sha = sha256_file(proof_path)
    judge_sha = sha256_file(judge_path)
    lines: list[str] = []
    lines.append("# Studio CAB Owner Taste Review Tray v0.1")
    lines.append("")
    lines.append("> Product: 看剧搭子")
    lines.append(f"> Generated: {created_at}")
    lines.append(f"> Drafts to review: {len(eligible_cases)}")
    lines.append("")
    lines.append("## How to use")
    lines.append("")
    lines.append("1. Read each draft below.")
    lines.append("2. The line `owner_verdict:` is pre-filled with `abstain`. Change it to "
                 "one of " + ", ".join(f"`{v}`" for v in VERDICT_OPTIONS) + " "
                 "if you have a view. Leave as `abstain` if you cannot judge.")
    lines.append("3. Optionally write a short note on `owner_notes:`.")
    lines.append("4. Save this file.")
    lines.append("5. Run "
                 "`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/ars/deadman_build_studio_taste_calibration.py` "
                 "to build the calibration artifact.")
    lines.append("")
    lines.append("Verdict semantics:")
    lines.append("- `accept`: publishable as-is, no rewrite needed.")
    lines.append("- `accept_with_minor_tweak`: publishable after small wording tweaks.")
    lines.append("- `reject`: do not publish; the draft does not survive owner taste.")
    lines.append("- `abstain`: cannot judge, skip for calibration.")
    lines.append("")
    lines.append("## References")
    lines.append("")
    lines.append(f"- Real-provider proof: `{repo_relative(proof_path)}` (sha256: `{proof_sha}`)")
    lines.append(f"- Judge artifact: `{repo_relative(judge_path)}` (sha256: `{judge_sha}`)")
    lines.append("")
    lines.append("---")
    lines.append("")

    for idx, case in enumerate(eligible_cases, start=1):
        verdict = verdict_by_case.get(case["case_id"], {})
        judge_overall = verdict.get("overall_verdict", "not_available")
        default_verdict = "abstain"
        draft = case.get("draft", {})
        replies = draft.get("reply_candidates", [])
        lines.append(f"## Draft {idx} / {len(eligible_cases)}: {case['episode_id']} — {case['item_id']}")
        lines.append("")
        lines.append(f"- **case_id**: `{case['case_id']}`")
        lines.append(f"- **case_type**: `{case['case_type']}`")
        lines.append(f"- **expected_behavior**: `{case.get('expected_behavior', '')}`")
        lines.append("")
        lines.append("### companion_lead")
        lines.append("")
        lines.append(f"> {draft.get('companion_lead', '')}")
        lines.append("")
        lines.append("### reply_candidates")
        lines.append("")
        for r_idx, reply in enumerate(replies, start=1):
            lines.append(f"**{r_idx}. display_text**: {reply.get('display_text', '')}")
            lines.append("")
            lines.append(f"   - emotion_role: `{reply.get('emotion_role', '')}`")
            lines.append(f"   - semantic_role: `{reply.get('semantic_role', '')}`")
            lines.append(f"   - viewer_motivation (who picks this / wants to hear): {reply.get('viewer_motivation', '')}")
            lines.append(f"   - selected_echo: {reply.get('selected_echo', '')}")
            lines.append("")
        deterministic_buckets = case.get("failure_buckets", [])
        lines.append("### deterministic check")
        lines.append("")
        lines.append(f"- failure_buckets: `{deterministic_buckets}`")
        lines.append(f"- conformance: `{case.get('conformance_validation', 'not_available')}`")
        lines.append("")
        lines.append("### judge verdict")
        lines.append("")
        lines.append(f"- lead_taste: `{verdict.get('lead_taste', 'not_available')}`")
        lines.append(f"- reply_voice_taste: `{verdict.get('reply_voice_taste', 'not_available')}`")
        lines.append(f"- reply_axis_diversity: `{verdict.get('reply_axis_diversity', 'not_available')}`")
        lines.append(f"- echo_taste: `{verdict.get('echo_taste', 'not_available')}`")
        lines.append(f"- **overall_verdict**: `{verdict.get('overall_verdict', 'not_available')}`")
        lines.append(f"- judge_rationale: {verdict.get('rationale_summary', '')}")
        lines.append("")
        lines.append("### owner verdict (edit below)")
        lines.append("")
        lines.append(f"Judge said: `{judge_overall}`. Replace `abstain` with one of "
                     "`accept` / `accept_with_minor_tweak` / `reject` if you have a view; "
                     "leave as `abstain` if you cannot judge.")
        lines.append("")
        lines.append("```")
        lines.append(f"owner_verdict: {default_verdict}")
        lines.append("owner_notes: ")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
