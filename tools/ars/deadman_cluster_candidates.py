#!/usr/bin/env python3
"""Bucket Deadman ARS candidates by mechanism and write field hypotheses."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
ANALYSIS_DIR = REPO_ROOT / "tmp/ars_huangnian_analysis"
DEFAULT_CANDIDATE_DIR = ANALYSIS_DIR / "candidates"

CLUSTER_DESCRIPTIONS = {
    "resource_crisis": "Resource visibility under famine scarcity.",
    "exposure_risk": "Whether useful resources can be shown without exposing their impossible source.",
    "family_pressure": "Family trust repair, child protection, and household authority.",
    "village_pressure": "Public reputation and village-level survival/social pressure.",
    "humiliation_reversal": "Viewer desire to reverse bullying or humiliation immediately.",
    "evidence_or_trap": "Using evidence, accounts, property, or witnesses to make a reversal stick.",
    "system_rule": "System ability usage under genre/world constraints.",
    "survival_tradeoff": "Immediate survival versus long-term risk under scarcity.",
    "nonsense_or_overpowered_break": "Tempting overpowered moves that may break watch flow or world credibility.",
    "hidden_power_rule": "Hidden power usage under genre/world constraints.",
    "identity_reveal": "Whether true identity should be revealed now or held for later leverage.",
    "relationship_betrayal": "Betrayal, divorce, humiliation, and relationship rupture pressure.",
    "status_reversal": "Using status, evidence, wealth, or institutional leverage as a reversal card.",
    "medical_or_pregnancy_risk": "Immediate bodily/pregnancy risk versus accountability timing.",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def group_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["trigger_type"]].append(candidate)

    clusters: dict[str, Any] = {}
    for mechanism, items in sorted(grouped.items()):
        sorted_items = sorted(items, key=lambda item: item["rank_score"], reverse=True)
        clusters[mechanism] = {
            "label": mechanism,
            "description": CLUSTER_DESCRIPTIONS.get(mechanism, "Candidate judgment mechanism."),
            "candidate_count": len(items),
            "avg_rank_score": round(sum(item["rank_score"] for item in items) / len(items), 2),
            "top_candidate_ids": [item["candidate_id"] for item in sorted_items[:5]],
            "source_episode_ids": sorted({item["episode_id"] for item in items}),
            "shared_judgment_question": shared_question(mechanism),
            "pack_field_pressure": field_pressure(mechanism),
        }
    return clusters


def shared_question(mechanism: str) -> str:
    return {
        "resource_crisis": "Should the player spend or reveal scarce food now, and what local cost follows?",
        "exposure_risk": "How much advantage can the player show before others begin to question the source?",
        "family_pressure": "Which household member should be protected first, and how does trust change?",
        "village_pressure": "Can public confrontation improve survival, or does it damage reputation and exchange channels?",
        "humiliation_reversal": "Is immediate retaliation worth the escalation risk?",
        "evidence_or_trap": "What evidence or account makes the counter-move credible instead of reckless?",
        "system_rule": "What system use is allowed without breaking genre/world constraints?",
        "survival_tradeoff": "Which short-term survival need justifies longer-term exposure or relationship cost?",
        "nonsense_or_overpowered_break": "Which tempting power move should be softened so the viewer can return to the original drama?",
        "hidden_power_rule": "How much hidden power can be used now without collapsing the genre constraints?",
        "identity_reveal": "Should identity truth be revealed now, and what leverage is gained or lost?",
        "relationship_betrayal": "Is immediate rupture safer and more satisfying than delayed evidence-backed reversal?",
        "status_reversal": "Which bottom card should be played now, and what future reversal value is spent?",
        "medical_or_pregnancy_risk": "Should the action prioritize rescue, evidence, or revenge in the immediate scene?",
    }.get(mechanism, "What local causal judgment should this moment ask the viewer to make?")


def field_pressure(mechanism: str) -> list[str]:
    common = ["source_window", "hook", "viewer_impulse", "canon_baseline", "constraints", "action_space", "score_axes"]
    extra = {
        "resource_crisis": ["resource_state", "scarcity_level", "distribution_target"],
        "exposure_risk": ["visibility_scope", "source_explanation", "suspicion_risk"],
        "family_pressure": ["family_roles", "trust_delta", "care_priority"],
        "village_pressure": ["witnesses", "reputation_delta", "exchange_dependency"],
        "humiliation_reversal": ["harm_state", "retaliation_scale", "escalation_risk"],
        "evidence_or_trap": ["evidence_refs", "claim_account", "counterparty_leverage"],
        "system_rule": ["system_action", "rule_cost", "world_explanation"],
        "survival_tradeoff": ["survival_need", "defer_cost", "long_term_risk"],
        "nonsense_or_overpowered_break": ["power_cap", "watch_flow_fit", "softened_output_policy"],
        "hidden_power_rule": ["power_state", "rule_visibility", "cost_or_cooldown", "power_cap"],
        "identity_reveal": ["identity_state", "reveal_scope", "leverage_loss", "misrecognition_value"],
        "relationship_betrayal": ["betrayal_state", "safety_status", "evidence_needed", "rupture_cost"],
        "status_reversal": ["bottom_card", "institutional_leverage", "future_reversal_value", "public_effect"],
        "medical_or_pregnancy_risk": ["bodily_risk", "rescue_priority", "evidence_preservation", "accountability_delay"],
    }
    return common + extra.get(mechanism, [])


def write_cluster_md(path: Path, clusters: dict[str, Any], candidates_by_id: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# Deadman Mechanism Buckets v0.2",
        "",
        "> Grouped by preassigned judgment mechanism labels. This is mechanism-bucket aggregation, not emergent semantic clustering. Semi-automatic evidence; human review required.",
        "",
    ]
    for label, cluster in clusters.items():
        lines.extend(
            [
                f"## `{label}`",
                "",
                f"- Description: {cluster['description']}",
                f"- Candidate count: {cluster['candidate_count']}",
                f"- Average rank score: {cluster['avg_rank_score']}",
                f"- Shared judgment question: {cluster['shared_judgment_question']}",
                f"- Source episodes: {', '.join(cluster['source_episode_ids'])}",
                f"- Field pressure: {', '.join(cluster['pack_field_pressure'])}",
                "",
                "| Top ID | Rank | Time | Hook | Evidence |",
                "|---|---:|---|---|---|",
            ]
        )
        for candidate_id in cluster["top_candidate_ids"]:
            candidate = candidates_by_id[candidate_id]
            time = f"{candidate['episode_id']} {candidate['start_ms']//1000:02d}s-{candidate['end_ms']//1000:02d}s"
            lines.append(
                f"| `{candidate_id}` | {candidate['rank']} | {time} | {candidate['hook']} | {candidate['evidence_excerpt'].replace('|', ' ')} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_field_hypotheses(path: Path, clusters: dict[str, Any]) -> None:
    labels = ", ".join(f"`{label}`" for label in clusters)
    lines = [
        "# Moment Causality Pack v0.2 Field Hypotheses",
        "",
        "> Derived from a Deadman ARS v0.2 mechanism-bucket pass. This is schema evidence, not a frozen production schema.",
        "",
        f"Observed mechanism buckets: {labels}.",
        "",
        "## CoreEnvelope",
        "",
        "Fields that appeared necessary across most candidates:",
        "",
        "- `source_window`: episode id, start/end ms, transcript refs, keyframe refs, contact sheet ref.",
        "- `scene_signal`: one-line source-window signal for companion authoring.",
        "- `viewer_impulse`: the audience line or feeling the interaction is trying to catch.",
        "- `canon_baseline`: original action, original rationale, and audience tension.",
        "- `actor_context`: who is directly affected and what relationship pressure exists.",
        "- `constraints`: famine scarcity, system secrecy, family trust, village reputation, evidence state.",
        "- `action_space`: 2-3 bounded player choices plus optional custom action.",
        "- `score_axes`: emotion_heat, choice_leverage, causal_clarity, world_constraint_value, watch_flow_fit, visual_result_fit.",
        "- `output_policy`: answer local credible consequences, not continuous alternate plot.",
        "- `review_state`: ASR quality, visual evidence quality, and human-review requirement.",
        "",
        "## OptionalCausalityModules",
        "",
        "- `resource`: resource type, quantity/visibility, distribution target, scarcity pressure.",
        "- `exposure`: source explanation, witnesses, suspicion risk, concealment strategy.",
        "- `relationship_pressure`: family role, prior trust damage, care/protection priority.",
        "- `evidence_trap`: object/account/witness references, accusation and counter-claim shape.",
        "- `genre_system_rule`: system action, cost, rule visibility, overpowered-break guardrail.",
        "- `social_reputation`: village/public setting, reputation delta, exchange dependency.",
        "",
        "## Fields To Keep Out Of P0",
        "",
        "- `branch_timeline` or any promise that later episodes truly follow the new branch.",
        "- Long-horizon relationship simulation beyond a compact local consequence.",
        "- Global inventory mutation unless it is needed for the current Moment Pack.",
        "- Full social graph updates; P0 can use local witnesses and relationship labels only.",
        "- `return_to_plot_fit`; the lighter P0 field is `watch_flow_fit`.",
        "",
        "## Fields Requiring Human Review",
        "",
        "- Any source fact promoted from ASR text.",
        "- Any claim about who originally chose what when transcript text is partial or noisy.",
        "- System/resource quantities such as rice, money, meat, eggs, rabbits, or compensation.",
        "- Visual result prompts when keyframes do not clearly show the object or person.",
        "- `original_plot_note`, because it explains why the original drama remains reasonable.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def provider_status() -> dict[str, Any]:
    summary_path = provider_status.analysis_dir / "volc_asr/summary.json"
    if not summary_path.exists():
        return {"status": "missing", "summary_path": repo_relative(summary_path)}
    summary = read_json(summary_path)
    success = [item for item in summary if item.get("provider_status_code") == "20000000"]
    return {
        "status": "available",
        "summary_path": repo_relative(summary_path),
        "success_count": len(success),
        "total_count": len(summary),
        "failed": [item for item in summary if item.get("provider_status_code") != "20000000"],
    }


def write_run_report(path: Path, windows: dict[str, Any], candidates: list[dict[str, Any]], clusters: dict[str, Any]) -> None:
    status = provider_status()
    top = candidates[:8]
    plausible = [item for item in candidates if item["rank_score"] >= 70]
    with_refs = [
        item
        for item in candidates
        if item["source_refs"].get("transcript_refs") and item["source_refs"].get("keyframe_refs")
    ]
    lines = [
        f"# Deadman ARS {write_run_report.drama_id} v0.2 Run Report",
        "",
        "## Commands Run",
        "",
        "```bash",
        "# See the generated per-drama command log or MultiDrama induction report for the exact command.",
        "```",
        "",
        "## Provider Status",
        "",
        f"- Doubao Speech flash ASR: {status.get('status')}",
        f"- Successful episodes: {status.get('success_count', 0)} / {status.get('total_count', 0)}",
        f"- Raw/normalized provider artifacts stayed under `{status.get('summary_path', 'tmp/ars_huangnian_analysis/volc_asr')}` and sibling ignored tmp paths.",
        "",
        "## Output Counts",
        "",
        f"- Windows: {windows.get('window_count')}",
        f"- Candidates: {len(candidates)}",
        f"- Mechanism buckets: {len(clusters)}",
        f"- Candidates ranked as plausible demo nodes (`rank_score >= 70`): {len(plausible)}",
        f"- Candidates with transcript + keyframe refs: {len(with_refs)}",
        "",
        "## Top Recommended Demo Nodes",
        "",
        "| Rank | Candidate | Mechanism | Score | Hook | Evidence |",
        "|---:|---|---|---:|---|---|",
    ]
    for item in top:
        evidence = item["evidence_excerpt"].replace("|", " ")
        lines.append(f"| {item['rank']} | `{item['candidate_id']}` | `{item['trigger_type']}` | {item['rank_score']:.2f} | {item['hook']} | {evidence} |")
    lines.extend(
        [
            "",
            "## Missing Data",
            "",
            "- No manual scene notes were provided for this run.",
            "- No OCR/subtitle extraction was available; only ASR text and sampled keyframes/contact sheets were used.",
            "- Contact sheets are linked as visual references but not machine-interpreted in this deterministic pass.",
            "",
            "## Reliability Issues",
            "",
            "- ASR is useful for timing and dialogue hints, but every promoted source fact still needs human review.",
            "- Candidate hooks are deterministic scene-conditioned drafts over transcript keywords, not final product copy.",
            "- Keyframe refs prove there is visual material near the timestamp; they do not by themselves prove the described object is visible.",
            "- This pass asks for local credible consequences only. It does not promise that later episodes branch.",
            "- `watch_flow_fit` is scored, and `return_to_plot_fit` is intentionally not used.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    parser.add_argument("--windows", help="Input windows JSON path.")
    parser.add_argument("--candidates", help="Input candidate JSON path.")
    parser.add_argument("--out-json", help="Exact mechanism-bucket JSON output path.")
    parser.add_argument("--out-md", help="Exact mechanism-bucket Markdown output path.")
    parser.add_argument("--field-md", help="Exact field-hypothesis Markdown output path.")
    parser.add_argument("--run-report", help="Exact run-report Markdown output path.")
    parser.add_argument("--analysis-dir", default=str(ANALYSIS_DIR))
    parser.add_argument("--drama-id", default="huangnian")
    parser.add_argument("--drama-title", default="荒年全村啃树皮，我有系统满仓肉")
    parser.add_argument("--version", default="v0.2")
    args = parser.parse_args()

    candidate_dir = resolve_path(args.candidate_dir)
    windows_path = resolve_path(args.windows) if args.windows else candidate_dir / f"{args.drama_id}_windows.{args.version}.json"
    candidates_path = resolve_path(args.candidates) if args.candidates else candidate_dir / f"{args.drama_id}_candidates.{args.version}.json"
    out_json = resolve_path(args.out_json) if args.out_json else candidate_dir / f"{args.drama_id}_mechanism_buckets.{args.version}.json"
    out_md = resolve_path(args.out_md) if args.out_md else candidate_dir / f"{args.drama_id}_mechanism_buckets.{args.version}.md"
    field_md = resolve_path(args.field_md) if args.field_md else candidate_dir / f"{args.drama_id}_field_hypotheses.{args.version}.md"
    run_report = resolve_path(args.run_report) if args.run_report else out_json.parent / "run_report.md"
    provider_status.analysis_dir = resolve_path(args.analysis_dir)  # type: ignore[attr-defined]
    write_run_report.drama_id = args.drama_id  # type: ignore[attr-defined]
    windows = read_json(windows_path)
    candidate_data = read_json(candidates_path)
    candidates = candidate_data["candidates"]
    clusters = group_candidates(candidates)
    candidates_by_id = {candidate["candidate_id"]: candidate for candidate in candidates}

    output = {
        "version": args.version,
        "drama_id": args.drama_id,
        "source_drama": args.drama_title,
        "aggregation_type": "mechanism_buckets",
        "cluster_claim": "not_emergent_clustering",
        "bucket_count": len(clusters),
        "mechanism_buckets": clusters,
    }
    write_json(out_json, output)
    write_cluster_md(out_md, clusters, candidates_by_id)
    write_field_hypotheses(field_md, clusters)
    write_run_report(run_report, windows, candidates, clusters)
    print(
        json.dumps(
            {
                "bucket_count": len(clusters),
                "out_json": repo_relative(out_json),
                "out_md": repo_relative(out_md),
                "field_md": repo_relative(field_md),
                "run_report": repo_relative(run_report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
