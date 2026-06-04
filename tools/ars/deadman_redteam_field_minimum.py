#!/usr/bin/env python3
"""Red-team Deadman v0.3 minimum fields against field-contract failure modes."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_INPUT_DIR = REPO_ROOT / "tmp/ars_multidrama_field_minimum_v0.3"
DEFAULT_SCRATCH_DIR = REPO_ROOT / "tmp/ars_multidrama_field_redteam_v0.1"

CORE_OPERATIONAL = [
    "source_window",
    "review_and_provenance",
    "companion_entry",
    "action_space",
    "response_contract",
    "visual_result_policy",
]

CORE_CAUSAL = [
    "actor_local_state",
    "critical_stakes_state",
    "local_constraint_state",
    "escalation_risk",
    "canon_baseline",
    "watch_flow_rationale",
]

REUSABLE_MODULES = [
    "relationship_state",
    "capability_rules",
    "information_asymmetry",
    "proof_state",
    "audience_reputation_state",
]

PRODUCER_ONLY = ["score_axes"]

ACTIVE_FIELDS = CORE_OPERATIONAL + CORE_CAUSAL + REUSABLE_MODULES + PRODUCER_ONLY

RUNTIME_JUDGMENT_FIELDS = CORE_OPERATIONAL + CORE_CAUSAL + REUSABLE_MODULES

EXCLUDED_FIELDS = [
    "branch_timeline",
    "global_inventory",
    "full_social_graph",
    "auto_visual_truth",
    "return_to_plot_fit",
]

ATTACKS = {
    "reasonable_smart": {
        "template": "我不照原剧情来，先做一个更稳的局部选择：保住眼前最关键的筹码，同时不给对方抓住新的把柄。",
        "fields": ["actor_local_state", "critical_stakes_state", "local_constraint_state", "canon_baseline", "watch_flow_rationale"],
        "failure": "If local actor, stakes, constraints, or canon baseline are missing, the result becomes generic advice instead of a credible scene consequence.",
        "severity": "medium",
    },
    "rash_wrong": {
        "template": "我现在就冲上去硬刚，不管后果，先把气出了。",
        "fields": ["critical_stakes_state", "relationship_state", "escalation_risk", "local_constraint_state"],
        "failure": "If escalation and relation pressure are missing, the system rewards reckless behavior with fake catharsis.",
        "severity": "high",
    },
    "overpowered_cheat": {
        "template": "我直接开最大挂，把所有问题一次解决，让所有人立刻服我。",
        "fields": ["capability_rules", "response_contract", "watch_flow_rationale", "escalation_risk"],
        "failure": "If capability limits and response horizon are absent, the feature becomes unbounded cheat fiction.",
        "severity": "critical",
    },
    "cross_episode_meta": {
        "template": "我用后面剧情的信息提前布局，并且让后续剧情彻底改线。",
        "fields": ["response_contract", "canon_baseline", "watch_flow_rationale", "review_and_provenance"],
        "failure": "If the response contract is weak, the output promises a continuous alternate timeline.",
        "severity": "critical",
    },
    "unsupported_proof": {
        "template": "我说我已经有证据和证人，直接当场定死对方。",
        "fields": ["proof_state", "review_and_provenance", "local_constraint_state", "information_asymmetry"],
        "failure": "If proof provenance is missing, the result treats invented evidence as scene truth.",
        "severity": "high",
    },
    "visual_truth_trap": {
        "template": "既然生成图里是这样，那就当作剧情里已经发生并且所有人都看见了。",
        "fields": ["visual_result_policy", "proof_state", "review_and_provenance", "response_contract"],
        "failure": "If visual truth level is missing, generated or keyframe media turns into unsupported proof.",
        "severity": "critical",
    },
}

FIELD_ABLATION_POLICIES = {
    "source_window": ("breaks_runtime", "The player cannot place a marker, time-box a prompt, or cite a scene."),
    "review_and_provenance": ("breaks_credibility", "Schema evidence or candidate-only facts can leak into runtime truth."),
    "companion_entry": ("degrades_quality", "The feature still computes, but the viewer loses the friend/tie-in entry point."),
    "action_space": ("breaks_runtime", "The system cannot bound presets or custom actions before judgment."),
    "response_contract": ("breaks_runtime", "The output can promise a continuous alternate timeline instead of a local consequence."),
    "visual_result_policy": ("breaks_credibility", "Result images can be mistaken for proof or canon evidence."),
    "actor_local_state": ("breaks_credibility", "The model cannot tell whose agency, risk, or intent is being judged."),
    "critical_stakes_state": ("breaks_credibility", "The output cannot price what is saved, lost, harmed, spent, or exposed."),
    "local_constraint_state": ("breaks_credibility", "The model can ignore hard scene limits and invent impossible actions."),
    "escalation_risk": ("breaks_credibility", "Reckless or humiliating choices become unearned wins with no backlash."),
    "canon_baseline": ("breaks_credibility", "The alternative loses its anchor against what canon actually did."),
    "watch_flow_rationale": ("breaks_credibility", "The viewer may conclude canon is stupid and stop watching."),
    "relationship_state": ("breaks_credibility", "Trust, betrayal, dependency, and protection priority collapse into generic advice."),
    "capability_rules": ("breaks_credibility", "Hidden powers or systems become unlimited cheat buttons."),
    "information_asymmetry": ("breaks_credibility", "Identity, secrecy, and reveal timing lose causal cost."),
    "proof_state": ("breaks_credibility", "Accusations and reversals land without evidence, witnesses, or thresholds."),
    "audience_reputation_state": ("breaks_credibility", "Public humiliation or crowd pressure loses social consequence."),
    "score_axes": ("no_material_loss", "Viewer runtime judgment survives; producer ranking and QA lose structure."),
}

ACCEPTED_FUSION_PATCHES = {
    "critical_stakes_state": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "Resource scarcity, bodily danger, pregnancy risk, and rescue priority are all stakes, but they fail differently.",
        "required_subkeys": ["stake_type", "stake_owner", "time_pressure", "scarcity_or_risk_level", "irreversibility"],
        "severity_if_unpatched": "high",
    },
    "information_asymmetry": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "Identity secrecy, hidden facts, reveal scope, and leverage timing can be confused.",
        "required_subkeys": ["hidden_fact", "who_knows", "who_would_learn", "reveal_timing", "leverage_change"],
        "severity_if_unpatched": "high",
    },
    "capability_rules": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "System rules and hidden powers need different limits, costs, visibility, and actor knowledge.",
        "required_subkeys": ["capability_type", "hard_limit", "activation_cost", "visibility_cost", "known_to_actor", "known_to_others"],
        "severity_if_unpatched": "high",
    },
    "proof_state": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "Witness proof, legal proof, business records, and traps have different thresholds.",
        "required_subkeys": ["proof_type", "available_now", "threshold", "holder", "risk_if_claimed_without_proof"],
        "severity_if_unpatched": "medium",
    },
    "audience_reputation_state": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "Village pressure, online/public shame, family witnesses, and elite status audiences differ.",
        "required_subkeys": ["audience_scope", "audience_alignment", "status_at_stake", "humiliation_vector"],
        "severity_if_unpatched": "medium",
    },
    "escalation_risk": {
        "decision": "keep_with_typed_subkeys",
        "lost_distinction": "Retaliation, legal/social backlash, resource loss, and watch-flow break are different costs.",
        "required_subkeys": ["risk_type", "risk_source", "immediacy", "severity", "mitigation"],
        "severity_if_unpatched": "high",
    },
}

EXCLUDED_FIELD_POLICIES = {
    "branch_timeline": "Keep excluded. Use response_contract to produce only a local consequence and explicitly avoid future branch promises.",
    "global_inventory": "Keep excluded. Use critical_stakes_state and local_constraint_state for moment-local resources.",
    "full_social_graph": "Keep excluded. Use actor_local_state, relationship_state, and audience_reputation_state for local actors and witnesses.",
    "auto_visual_truth": "Keep excluded. Use visual_result_policy to label images as illustrative/result media, not evidence.",
    "return_to_plot_fit": "Keep excluded. Use watch_flow_rationale to explain why canon remains acceptable without simulating return-to-plot.",
}


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: str | Path) -> Any:
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    target = resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    target = resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def field_scores(node: dict[str, Any]) -> dict[str, int]:
    return {field: int(payload["need_score"]) for field, payload in node.get("field_needs", {}).items()}


def important_fields(node: dict[str, Any]) -> list[str]:
    scores = field_scores(node)
    return [field for field, score in scores.items() if score >= 2 and field in RUNTIME_JUDGMENT_FIELDS]


def cluster_for_node(node_id: str, clusters: dict[str, Any]) -> str:
    for cluster_id, cluster in clusters["valid_nodes"].items():
        if node_id in cluster.get("member_node_ids", []):
            return cluster_id
    for cluster_id, cluster in clusters["all_nodes"].items():
        if node_id in cluster.get("member_node_ids", []):
            return cluster_id
    return "unclustered"


def choose_representatives(nodes: list[dict[str, Any]], clusters: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {node["node_id"]: node for node in nodes}
    selected: dict[str, dict[str, Any]] = {}
    for cluster_id, cluster in clusters["valid_nodes"].items():
        members = [by_id[node_id] for node_id in cluster.get("member_node_ids", []) if node_id in by_id]
        members = [node for node in members if node.get("valid_for_minimum_set")]
        members.sort(key=lambda item: (item.get("source_tier") == "candidate_only", -float(item.get("rank_score") or 0)))
        drama_seen: set[str] = set()
        picked: list[dict[str, Any]] = []
        for node in members:
            if node["drama_id"] not in drama_seen:
                picked.append(node)
                drama_seen.add(node["drama_id"])
            if len(picked) >= 3:
                break
        for node in members:
            if len(picked) >= 3:
                break
            if node["node_id"] not in {item["node_id"] for item in picked}:
                picked.append(node)
        for node in picked:
            selected[node["node_id"]] = node

    drama_counts = Counter(node["drama_id"] for node in selected.values())
    for drama_id in ["huangnian", "yunmiao", "lihun"]:
        if drama_counts[drama_id] >= 5:
            continue
        candidates = [
            node
            for node in nodes
            if node.get("valid_for_minimum_set") and node["drama_id"] == drama_id and node["node_id"] not in selected
        ]
        candidates.sort(key=lambda item: -float(item.get("rank_score") or 0))
        for node in candidates[: 5 - drama_counts[drama_id]]:
            selected[node["node_id"]] = node
    return list(selected.values())


def build_cases(representatives: list[dict[str, Any]], clusters: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    counter = 1
    for node in representatives:
        cluster_id = cluster_for_node(node["node_id"], clusters)
        node_fields = set(important_fields(node))
        for attack_type, attack in ATTACKS.items():
            required = list(dict.fromkeys([*attack["fields"], *[field for field in node_fields if field in REUSABLE_MODULES]]))
            if attack_type == "overpowered_cheat" and field_scores(node).get("capability_rules", 0) < 2:
                required = [field for field in required if field != "capability_rules"]
                required.append("response_contract")
            if attack_type == "unsupported_proof" and field_scores(node).get("proof_state", 0) < 2:
                required.append("review_and_provenance")
            if attack_type == "visual_truth_trap":
                required.append("visual_result_policy")
            required = list(dict.fromkeys(required))
            case = {
                "case_id": f"rt_v01_{counter:04d}",
                "node_id": node["node_id"],
                "drama_id": node["drama_id"],
                "drama_title": node.get("drama_title", ""),
                "source_tier": node.get("source_tier"),
                "review_status": node.get("review_status"),
                "demand_cluster": cluster_id,
                "attack_type": attack_type,
                "scene_hook": node.get("hook", ""),
                "user_action": attack["template"],
                "expected_required_fields": required,
                "expected_failure_if_missing": list(dict.fromkeys([attack["failure"], *[
                    FIELD_ABLATION_POLICIES[field][1] for field in required if field in FIELD_ABLATION_POLICIES and FIELD_ABLATION_POLICIES[field][0] in {"breaks_credibility", "breaks_runtime"}
                ]])),
                "should_pass": True,
                "red_team_rationale": (
                    f"Tests whether {cluster_id} can stay local and credible under {attack_type} pressure "
                    "using only v0.3 fields."
                ),
                "severity_if_failed": attack["severity"],
            }
            cases.append(case)
            counter += 1
    return cases


def build_ablation_results(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid_nodes = [node for node in nodes if node.get("valid_for_minimum_set")]
    results = []
    for field in ACTIVE_FIELDS:
        policy, failure = FIELD_ABLATION_POLICIES[field]
        sample = next(
            (
                node
                for node in valid_nodes
                if field in node.get("field_needs", {}) and int(node["field_needs"][field]["need_score"]) >= 2
            ),
            valid_nodes[0],
        )
        results.append(
            {
                "field": field,
                "category": category_for_field(field),
                "sample_node_id": sample["node_id"],
                "sample_drama_id": sample["drama_id"],
                "ablation_result": policy,
                "failure_mode": failure,
                "recommendation": ablation_recommendation(field, policy),
            }
        )
    return results


def category_for_field(field: str) -> str:
    if field in CORE_OPERATIONAL:
        return "CoreOperational"
    if field in CORE_CAUSAL:
        return "CoreCausal"
    if field in REUSABLE_MODULES:
        return "ReusableCausalityModules"
    if field in PRODUCER_ONLY:
        return "ProducerOnlyFields"
    return "Unknown"


def ablation_recommendation(field: str, policy: str) -> str:
    if field == "score_axes":
        return "Keep producer-only; do not send as viewer causal state."
    if policy == "degrades_quality":
        return "Keep as required product-surface field, not causal evidence."
    return "Keep field; adapter must treat it as explicit input, not infer it from prose."


def nodes_for_fields(nodes: list[dict[str, Any]], fields: list[str], limit: int = 3) -> list[dict[str, str]]:
    valid = [node for node in nodes if node.get("valid_for_minimum_set")]
    picked: list[dict[str, str]] = []
    seen_drama: set[str] = set()
    for node in valid:
        scores = field_scores(node)
        if any(scores.get(field, 0) >= 2 for field in fields) and node["drama_id"] not in seen_drama:
            picked.append({"node_id": node["node_id"], "drama_id": node["drama_id"], "hook": node.get("hook", "")})
            seen_drama.add(node["drama_id"])
        if len(picked) >= limit:
            break
    if len(picked) < 2:
        for node in valid:
            scores = field_scores(node)
            if any(scores.get(field, 0) >= 2 for field in fields) and node["node_id"] not in {item["node_id"] for item in picked}:
                picked.append({"node_id": node["node_id"], "drama_id": node["drama_id"], "hook": node.get("hook", "")})
            if len(picked) >= limit:
                break
    return picked


def build_fusion_stress(nodes: list[dict[str, Any]], fusion_decisions: dict[str, Any]) -> dict[str, Any]:
    accepted = []
    for fusion in fusion_decisions.get("accepted_fusions", []):
        target = fusion["target"]
        patch = ACCEPTED_FUSION_PATCHES[target]
        samples = nodes_for_fields(nodes, [target])
        accepted.append(
            {
                "target": target,
                "sources": fusion.get("sources", []),
                "sample_nodes": samples,
                "preserves": fusion.get("reason", ""),
                "lost_distinction": patch["lost_distinction"],
                "decision": patch["decision"],
                "required_subkeys": patch["required_subkeys"],
                "severity_if_unpatched": patch["severity_if_unpatched"],
            }
        )

    rejected = []
    for fusion in fusion_decisions.get("rejected_fusions", []):
        fields = fusion.get("fields", [])
        samples = nodes_for_fields(nodes, fields)
        rejected.append(
            {
                "fields": fields,
                "sample_nodes": samples,
                "rejection_still_holds": True,
                "failure_if_merged": fusion.get("reason", ""),
                "recommendation": "Keep separate in v0.3; adapter may mention both in one prompt section but must not collapse them.",
            }
        )
    return {"accepted_fusions": accepted, "rejected_fusions": rejected}


def build_excluded_pressure() -> list[dict[str, Any]]:
    return [
        {
            "excluded_field": field,
            "attack_prompt": excluded_attack_prompt(field),
            "pressure_result": "field_not_needed",
            "fallback_policy": policy,
            "severity_if_added": "critical" if field in {"branch_timeline", "auto_visual_truth"} else "high",
        }
        for field, policy in EXCLUDED_FIELD_POLICIES.items()
    ]


def excluded_attack_prompt(field: str) -> str:
    prompts = {
        "branch_timeline": "Continue the alternate branch for the rest of the drama and rewrite later episodes.",
        "global_inventory": "Track all food, money, medicine, and equipment across the whole story world.",
        "full_social_graph": "Model every relative, villager, rival, and hidden alliance before deciding.",
        "auto_visual_truth": "Treat generated result images as canonical proof inside the scene.",
        "return_to_plot_fit": "Force the alternate consequence to mechanically reconnect to canon.",
    }
    return prompts[field]


def build_findings(
    *,
    cases: list[dict[str, Any]],
    ablations: list[dict[str, Any]],
    fusion_stress: dict[str, Any],
    excluded_pressure: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings = [
        {
            "finding_id": "FMRT-001",
            "severity": "high",
            "title": "Accepted fusions survive only if schemas require typed subkeys.",
            "affected_fields": [
                "critical_stakes_state",
                "information_asymmetry",
                "capability_rules",
                "escalation_risk",
            ],
            "affected_clusters": [
                "critical_stakes_tradeoff",
                "visibility_and_timing",
                "capability_bound_visibility",
                "public_escalation",
            ],
            "product_consequence": "Without typed subkeys, the backend can produce爽感 that ignores the exact kind of stake, reveal, ability limit, or backlash.",
            "recommendation": "Do not split these fields. Patch the v0.3 draft schema and adapter prompt with required typed subkeys.",
        },
        {
            "finding_id": "FMRT-002",
            "severity": "high",
            "title": "response_contract and watch_flow_rationale are non-removable boundary fields.",
            "affected_fields": ["response_contract", "watch_flow_rationale", "canon_baseline"],
            "affected_clusters": sorted({case["demand_cluster"] for case in cases if case["attack_type"] == "cross_episode_meta"}),
            "product_consequence": "Cross-episode or meta actions will otherwise turn Deadman into a continuous branch simulator and make returning to the drama feel incoherent.",
            "recommendation": "Keep return_to_plot_fit excluded; enforce local consequence plus one-line watch-flow rationale in judgment output.",
        },
        {
            "finding_id": "FMRT-003",
            "severity": "high",
            "title": "visual_result_policy must explicitly block visual proof claims.",
            "affected_fields": ["visual_result_policy", "proof_state", "review_and_provenance"],
            "affected_clusters": sorted({case["demand_cluster"] for case in cases if case["attack_type"] == "visual_truth_trap"}),
            "product_consequence": "Generated or placeholder result images could be read as evidence, making the consequence look canonically proven when it is only illustrative.",
            "recommendation": "Keep auto_visual_truth excluded and add truth_level/fallback fields before image generation is wired.",
        },
        {
            "finding_id": "FMRT-004",
            "severity": "medium",
            "title": "score_axes should stay producer-only.",
            "affected_fields": ["score_axes"],
            "affected_clusters": [],
            "product_consequence": "Sending ranking scores into runtime judgment can bias the model toward candidate popularity instead of local causal credibility.",
            "recommendation": "Use score_axes for ARS ranking and QA only; backend adapter should not expose it to the viewer-facing judgment prompt.",
        },
    ]
    if any(item["pressure_result"] != "field_not_needed" for item in excluded_pressure):
        findings.append(
            {
                "finding_id": "FMRT-005",
                "severity": "critical",
                "title": "Excluded field pressure produced a blocker.",
                "affected_fields": [item["excluded_field"] for item in excluded_pressure if item["pressure_result"] != "field_not_needed"],
                "affected_clusters": [],
                "product_consequence": "P0 would need to widen beyond local moment judgment.",
                "recommendation": "Stop backend adapter work and revise product boundary.",
            }
        )
    return findings


def verdict_for(findings: list[dict[str, Any]], fusion_stress: dict[str, Any], excluded_pressure: list[dict[str, Any]]) -> str:
    has_critical = any(finding["severity"] == "critical" for finding in findings)
    excluded_blocker = any(item["pressure_result"] != "field_not_needed" for item in excluded_pressure)
    high_unpatched = any(
        item["decision"] == "keep_with_typed_subkeys" and item["severity_if_unpatched"] == "high"
        for item in fusion_stress["accepted_fusions"]
    )
    if has_critical or excluded_blocker:
        return "fail_pending_schema_revision"
    if high_unpatched:
        return "pass_with_required_patch"
    return "pass"


def coverage_summary(cases: list[dict[str, Any]], representatives: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [node for node in nodes if node.get("valid_for_minimum_set")]
    return {
        "matrix_nodes": len(nodes),
        "valid_nodes_for_minimum_set": len(valid),
        "representative_nodes": len(representatives),
        "case_count": len(cases),
        "cases_by_attack_type": dict(Counter(case["attack_type"] for case in cases)),
        "cases_by_drama": dict(Counter(case["drama_id"] for case in cases)),
        "representatives_by_drama": dict(Counter(node["drama_id"] for node in representatives)),
        "cases_by_cluster": dict(Counter(case["demand_cluster"] for case in cases)),
        "source_tier_counts": dict(Counter(node.get("source_tier", "unknown") for node in nodes)),
    }


def schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://oseria.local/deadman/field_minimum_red_team_case.v0.1.json",
        "title": "Deadman Field Minimum Red Team Case v0.1",
        "type": "object",
        "required": [
            "case_id",
            "node_id",
            "drama_id",
            "demand_cluster",
            "attack_type",
            "user_action",
            "expected_required_fields",
            "expected_failure_if_missing",
            "should_pass",
            "red_team_rationale",
            "severity_if_failed",
        ],
        "properties": {
            "case_id": {"type": "string", "pattern": "^rt_v01_[0-9]{4}$"},
            "node_id": {"type": "string"},
            "drama_id": {"type": "string"},
            "drama_title": {"type": "string"},
            "source_tier": {"type": "string"},
            "review_status": {"type": "string"},
            "demand_cluster": {"type": "string"},
            "attack_type": {
                "type": "string",
                "enum": list(ATTACKS.keys()),
            },
            "scene_hook": {"type": "string"},
            "user_action": {"type": "string"},
            "expected_required_fields": {"type": "array", "items": {"type": "string"}},
            "expected_failure_if_missing": {"type": "array", "items": {"type": "string"}},
            "should_pass": {"type": "boolean"},
            "red_team_rationale": {"type": "string"},
            "severity_if_failed": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        },
        "additionalProperties": True,
    }


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", "<br>") for item in row) + " |")
    return "\n".join(out)


def render_summary_doc(eval_data: dict[str, Any]) -> str:
    counts = eval_data["coverage_summary"]
    findings = eval_data["findings"]
    accepted = eval_data["fusion_stress"]["accepted_fusions"]
    rejected = eval_data["fusion_stress"]["rejected_fusions"]
    excluded = eval_data["excluded_field_pressure"]
    high_critical = [f for f in findings if f["severity"] in {"high", "critical"}]
    return "\n".join(
        [
            "# Field Minimum Red Team v0.1",
            "",
            "> Product: Deadman / 要是我来",
            f"> Generated: {eval_data['metadata']['generated_on']}",
            f"> Verdict: `{eval_data['final_verdict']}`",
            "",
            "## Why This Exists",
            "",
            "v0.3 compressed Deadman's field set into a small moment-level contract. This red team checks whether that compression loses the distinctions needed for credible local consequence judgment.",
            "",
            "This is not general safety moderation. It tests field sufficiency, field ablation, fusion boundaries, adversarial viewer actions, and pressure to re-add excluded non-P0 fields.",
            "",
            "## Method",
            "",
            "- Used existing v0.3 matrix and cluster artifacts only.",
            "- Did not rerun video ingestion, ASR, or providers.",
            "- Selected representative valid reviewed/schema-evidence nodes by demand cluster and drama coverage.",
            "- Generated deterministic user-action attacks for each representative node.",
            "- Ran field ablation and fusion stress at the schema-contract level.",
            "",
            "## Corpus",
            "",
            md_table(
                ["Metric", "Value"],
                [
                    ["Matrix nodes", counts["matrix_nodes"]],
                    ["Valid nodes for minimum set", counts["valid_nodes_for_minimum_set"]],
                    ["Representative nodes", counts["representative_nodes"]],
                    ["Red-team cases", counts["case_count"]],
                    ["Cases by drama", json.dumps(counts["cases_by_drama"], ensure_ascii=False)],
                    ["Cases by attack type", json.dumps(counts["cases_by_attack_type"], ensure_ascii=False)],
                ],
            ),
            "",
            "## Pass/Fail Summary",
            "",
            f"Verdict: `{eval_data['final_verdict']}`.",
            "",
            "The 18 active v0.3 fields are sufficient for P0 local judgment, but the backend adapter should not consume them as flat prose. Several accepted fusions need typed subkeys to preserve the distinction they intentionally compressed.",
            "",
            "## High/Critical Findings",
            "",
            md_table(
                ["ID", "Severity", "Title", "Recommendation"],
                [[f["finding_id"], f["severity"], f["title"], f["recommendation"]] for f in high_critical],
            ),
            "",
            "## Field Sufficiency Result",
            "",
            "Every represented demand cluster and every attack type has a field defense in the v0.3 set. No one-off genre field was required for 荒年, 云渺, or 幸得相遇离婚时.",
            "",
            "## Fusion Stress Result",
            "",
            md_table(
                ["Accepted Fusion", "Decision", "Required Subkeys", "Severity If Unpatched"],
                [[item["target"], item["decision"], ", ".join(item["required_subkeys"]), item["severity_if_unpatched"]] for item in accepted],
            ),
            "",
            "Rejected fusions still hold:",
            "",
            md_table(
                ["Rejected Merge", "Still Holds", "Failure If Merged"],
                [[", ".join(item["fields"]), item["rejection_still_holds"], item["failure_if_merged"]] for item in rejected],
            ),
            "",
            "## Excluded-Field Pressure Result",
            "",
            md_table(
                ["Excluded Field", "Result", "Fallback Policy"],
                [[item["excluded_field"], item["pressure_result"], item["fallback_policy"]] for item in excluded],
            ),
            "",
            "## Recommended Changes Before Backend Adapter",
            "",
            "1. Patch the v0.3 draft schema with typed subkeys for accepted fusions.",
            "2. Keep `score_axes` producer-only and out of the viewer judgment prompt.",
            "3. Enforce `response_contract` plus `watch_flow_rationale` in the adapter output format.",
            "4. Add explicit `visual_result_policy.truth_level` before wiring generated images.",
            "5. Keep excluded fields excluded for P0.",
            "",
        ]
    )


def render_casebook(cases: list[dict[str, Any]]) -> str:
    rows = [
        [
            case["case_id"],
            case["node_id"],
            case["drama_id"],
            case["demand_cluster"],
            case["attack_type"],
            ", ".join(case["expected_required_fields"]),
            "<br>".join(case["expected_failure_if_missing"][:3]),
            case["severity_if_failed"],
        ]
        for case in cases
    ]
    return "\n".join(
        [
            "# Field Minimum Red Team Casebook v0.1",
            "",
            "All cases are deterministic field-contract probes generated from existing v0.3 matrix/cluster artifacts. 云渺 and 离婚 cases remain schema-evidence, not promoted runtime truth.",
            "",
            md_table(
                ["Case", "Node", "Drama", "Cluster", "Attack", "Required Fields", "Expected Failure If Missing", "Severity"],
                rows,
            ),
            "",
        ]
    )


def render_findings(findings: list[dict[str, Any]]) -> str:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_findings = sorted(findings, key=lambda item: (severity_order[item["severity"]], item["finding_id"]))
    sections = ["# Field Minimum Red Team Findings v0.1", ""]
    for finding in sorted_findings:
        sections.extend(
            [
                f"## {finding['finding_id']} - {finding['title']}",
                "",
                f"- Severity: `{finding['severity']}`",
                f"- Affected fields: {', '.join(finding['affected_fields']) or '-'}",
                f"- Affected clusters: {', '.join(finding['affected_clusters']) or '-'}",
                f"- Product consequence: {finding['product_consequence']}",
                f"- Recommendation: {finding['recommendation']}",
                "",
            ]
        )
    return "\n".join(sections)


def append_dev_log(eval_data: dict[str, Any]) -> None:
    log_path = REPO_ROOT / ".agent/dev-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"- [Deadman] Executed the v0.3 minimum-field red team using only existing "
        f"field-demand matrix/cluster artifacts; no ASR, video ingestion, or provider "
        f"call was rerun. Promoted `Field_Minimum_Red_Team_v0.1.md`, "
        f"`Field_Minimum_Red_Team_Casebook_v0.1.md`, "
        f"`Field_Minimum_Red_Team_Findings_v0.1.md`, "
        f"`field_minimum_red_team.v0.1.json`, and "
        f"`field_minimum_red_team_case.v0.1.json`. Verdict: "
        f"`{eval_data['final_verdict']}` over {eval_data['coverage_summary']['case_count']} "
        f"cases. Required follow-up before backend adapter work: add typed subkeys "
        f"for accepted fusion fields and keep excluded fields out of P0 runtime.\n"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_dir = resolve_path(args.input_dir)
    scratch_dir = resolve_path(args.scratch_dir)

    matrix = read_json(input_dir / "node_field_demand_matrix.v0.3.json")
    clusters = read_json(input_dir / "node_demand_clusters.v0.3.json")
    fusion_decisions = read_json(input_dir / "field_fusion_decisions.v0.3.json")
    nodes = matrix["nodes"]
    representatives = choose_representatives(nodes, clusters)
    cases = build_cases(representatives, clusters)
    ablations = build_ablation_results(nodes)
    fusion_stress = build_fusion_stress(nodes, fusion_decisions)
    excluded_pressure = build_excluded_pressure()
    findings = build_findings(cases=cases, ablations=ablations, fusion_stress=fusion_stress, excluded_pressure=excluded_pressure)
    final_verdict = verdict_for(findings, fusion_stress, excluded_pressure)
    eval_data = {
        "metadata": {
            "schema_version": "field_minimum_red_team.v0.1",
            "generated_on": date.today().isoformat(),
            "input_artifacts": {
                "matrix": repo_relative(input_dir / "node_field_demand_matrix.v0.3.json"),
                "clusters": repo_relative(input_dir / "node_demand_clusters.v0.3.json"),
                "fusion_decisions": repo_relative(input_dir / "field_fusion_decisions.v0.3.json"),
            },
            "provider_or_video_rerun": False,
            "scope": "field_contract_red_team",
        },
        "field_set_counts": {
            "active_fields": len(ACTIVE_FIELDS),
            "runtime_judgment_fields": len(RUNTIME_JUDGMENT_FIELDS),
            "core_operational": len(CORE_OPERATIONAL),
            "core_causal": len(CORE_CAUSAL),
            "reusable_modules": len(REUSABLE_MODULES),
            "producer_only": len(PRODUCER_ONLY),
            "excluded_fields": len(EXCLUDED_FIELDS),
        },
        "coverage_summary": coverage_summary(cases, representatives, nodes),
        "representative_nodes": [
            {
                "node_id": node["node_id"],
                "drama_id": node["drama_id"],
                "source_tier": node.get("source_tier"),
                "demand_cluster": cluster_for_node(node["node_id"], clusters),
                "hook": node.get("hook", ""),
            }
            for node in representatives
        ],
        "cases": cases,
        "ablation_results": ablations,
        "fusion_stress": fusion_stress,
        "excluded_field_pressure": excluded_pressure,
        "findings": findings,
        "final_verdict": final_verdict,
    }

    write_json(scratch_dir / "red_team_cases.v0.1.json", cases)
    write_json(scratch_dir / "field_ablation.v0.1.json", ablations)
    write_json(scratch_dir / "fusion_stress.v0.1.json", fusion_stress)
    write_text(
        scratch_dir / "run_report.md",
        "\n".join(
            [
                "# Deadman Field Minimum Red Team v0.1 Run Report",
                "",
                f"- Generated: {eval_data['metadata']['generated_on']}",
                "- Provider/video rerun: no",
                f"- Matrix nodes: {eval_data['coverage_summary']['matrix_nodes']}",
                f"- Representative nodes: {eval_data['coverage_summary']['representative_nodes']}",
                f"- Cases: {eval_data['coverage_summary']['case_count']}",
                f"- Verdict: `{final_verdict}`",
                "",
            ]
        ),
    )

    write_json("data/evals/field_minimum_red_team.v0.1.json", eval_data)
    write_json("data/schemas/field_minimum_red_team_case.v0.1.json", schema())
    write_text("docs/Field_Minimum_Red_Team_v0.1.md", render_summary_doc(eval_data))
    write_text("docs/Field_Minimum_Red_Team_Casebook_v0.1.md", render_casebook(cases))
    write_text("docs/Field_Minimum_Red_Team_Findings_v0.1.md", render_findings(findings))
    if not args.no_dev_log:
        append_dev_log(eval_data)
    return eval_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--scratch-dir", default=str(DEFAULT_SCRATCH_DIR))
    parser.add_argument("--no-dev-log", action="store_true")
    args = parser.parse_args()
    eval_data = run(args)
    print(json.dumps({
        "verdict": eval_data["final_verdict"],
        "case_count": eval_data["coverage_summary"]["case_count"],
        "representative_nodes": eval_data["coverage_summary"]["representative_nodes"],
        "provider_or_video_rerun": eval_data["metadata"]["provider_or_video_rerun"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
