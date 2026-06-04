#!/usr/bin/env python3
"""Induce Deadman v0.3 minimum field set from a discrete field-demand matrix."""

from __future__ import annotations

import argparse
import itertools
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
DEFAULT_WORK_DIR = REPO_ROOT / "tmp/ars_multidrama_field_minimum_v0.3"

OPERATIONAL_FIELDS = [
    "source_window",
    "review_and_provenance",
    "companion_entry",
    "action_space",
    "response_contract",
    "visual_result_policy",
]

PRODUCER_ONLY_FIELDS = [
    "score_axes",
]

CORE_CAUSAL_FIELDS = [
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

VARIABLE_ANALYSIS_FIELDS = [
    "relationship_state",
    "critical_stakes_state",
    "capability_rules",
    "information_asymmetry",
    "proof_state",
    "audience_reputation_state",
    "escalation_risk",
    "watch_flow_rationale",
]

EXCLUDED_FIELDS = [
    "branch_timeline",
    "global_inventory",
    "full_social_graph",
    "auto_visual_truth",
    "return_to_plot_fit",
]

FIELD_DESCRIPTIONS = {
    "source_window": "Episode, timestamp, interaction window, and source refs required to locate the moment.",
    "review_and_provenance": "Review status and evidence/inference boundary so producer evidence does not become runtime truth.",
    "companion_entry": "Notice marker, hook, and friend-tone entry copy for the on-screen companion.",
    "action_space": "Preset options plus custom-action policy, bounded to local credible consequence.",
    "response_contract": "Short local consequence format and time horizon; no continuous branch promise.",
    "visual_result_policy": "Preset/custom result-media policy and visual truth level.",
    "score_axes": "Producer ranking/evaluation axes; useful for ARS and QA, not viewer runtime state.",
    "actor_local_state": "POV actor, affected actors, roles, local intent, and immediate condition.",
    "critical_stakes_state": "What can be lost, saved, spent, exposed, injured, or worsened by the action.",
    "local_constraint_state": "Hard scene facts: timing, available tools, known/hidden facts, and non-negotiable limits.",
    "escalation_risk": "Backlash, retaliation, social/legal cost, or watch-flow break risk created by the action.",
    "canon_baseline": "Original action, original rationale, and immediate plot baseline.",
    "watch_flow_rationale": "Why the original drama remains acceptable and the viewer can continue watching.",
    "relationship_state": "Trust, dependency, betrayal, family/romantic pressure, and protection priority.",
    "capability_rules": "System/hidden-power ability limits, costs, cooldowns, visibility, and overpowered guardrails.",
    "information_asymmetry": "Identity, secrecy, hidden facts, reveal timing, and leverage loss/gain.",
    "proof_state": "Evidence, witnesses, records, legal/business proof, and proof threshold.",
    "audience_reputation_state": "Public witnesses, village/social reputation, humiliation, and crowd effect.",
}

OLD_TO_NEW_MAPPING = {
    "actor_context": "actor_local_state",
    "affected_actors": "actor_local_state",
    "relationship_pressure": "relationship_state",
    "betrayal_divorce_safety": "relationship_state + critical_stakes_state + proof_state",
    "resource_scarcity": "critical_stakes_state",
    "survival_tradeoff": "critical_stakes_state + escalation_risk",
    "medical_or_pregnancy_risk": "critical_stakes_state",
    "local_constraints": "local_constraint_state",
    "system_or_hidden_power_rule": "capability_rules",
    "hidden_power_rule": "capability_rules",
    "identity_reveal": "information_asymmetry",
    "exposure_and_secrecy": "information_asymmetry",
    "evidence_or_trap_logic": "proof_state",
    "village_or_public_reputation": "audience_reputation_state",
    "humiliation_reversal": "escalation_risk + audience_reputation_state",
    "status_reversal_bottom_card": "information_asymmetry + proof_state + audience_reputation_state",
    "canon_baseline": "canon_baseline",
    "original_plot_note": "watch_flow_rationale",
    "producer_review_fields": "review_and_provenance",
    "score_axes": "score_axes",
    "visual_result_policy": "visual_result_policy",
}

ACCEPTED_FUSIONS = [
    {
        "target": "critical_stakes_state",
        "sources": ["resource_scarcity", "survival_tradeoff", "medical_or_pregnancy_risk", "bodily_safety", "rescue_priority"],
        "reason": "All answer the same judgment question: what material or bodily stake changes if the viewer acts now?",
    },
    {
        "target": "information_asymmetry",
        "sources": ["identity_reveal", "exposure_and_secrecy", "hidden_facts", "reveal_scope"],
        "reason": "Identity, secrecy, and exposure all price the timing of revealing information.",
    },
    {
        "target": "capability_rules",
        "sources": ["system_or_hidden_power_rule", "hidden_power_rule", "power_cap", "cost_or_cooldown"],
        "reason": "System and hidden-power beats both need bounded capability rules to avoid cheat outcomes.",
    },
    {
        "target": "proof_state",
        "sources": ["evidence_or_trap_logic", "legal_proof", "business_proof", "witness_proof", "evidence_needed"],
        "reason": "These fields all decide whether a counter-move is provable rather than reckless accusation.",
    },
    {
        "target": "audience_reputation_state",
        "sources": ["village_or_public_reputation", "witness_scope", "public_effect", "humiliation_context"],
        "reason": "Public witnesses and reputation pressure are the same social-visibility computation at moment scale.",
    },
    {
        "target": "escalation_risk",
        "sources": ["humiliation_reversal", "retaliation_scale", "backlash_risk", "watch_flow_break_risk"],
        "reason": "爽点 needs a visible cost/backlash channel; retaliation fields are best treated as risk, not a separate genre module.",
    },
]

REJECTED_FUSIONS = [
    {
        "fields": ["canon_baseline", "watch_flow_rationale"],
        "reason": "Baseline states what happened in canon; watch-flow rationale explains why returning to canon remains acceptable. Merging hides a product-critical distinction.",
    },
    {
        "fields": ["source_window", "review_and_provenance"],
        "reason": "Time location is runtime routing; review provenance is producer trust hygiene. They fail differently.",
    },
    {
        "fields": ["companion_entry", "actor_local_state"],
        "reason": "Companion copy is surface UX; actor state is causal input. Merging would pollute judgment prompts with UI text.",
    },
    {
        "fields": ["visual_result_policy", "proof_state"],
        "reason": "A generated/keyframe visual is not proof. This boundary prevents auto-visual truth claims.",
    },
    {
        "fields": ["relationship_state", "audience_reputation_state"],
        "reason": "Private trust pressure and public reputation can co-occur but drive different consequences.",
    },
    {
        "fields": ["capability_rules", "information_asymmetry"],
        "reason": "Hidden power often implies secrecy, but ability limits and reveal timing are separate computations.",
    },
    {
        "fields": ["score_axes", "field_needs"],
        "reason": "Score axes evaluate candidates; field needs are causal/context requirements for judgment.",
    },
]


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scores(node: dict[str, Any]) -> dict[str, int]:
    return {field: int(value["need_score"]) for field, value in node["field_needs"].items()}


def validate_matrix(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for node in matrix["nodes"]:
        for field, need in node["field_needs"].items():
            score = int(need["need_score"])
            if score in {2, 3} and not str(need.get("why_needed") or "").strip():
                errors.append(f"{node['node_id']} field {field} score {score} lacks why_needed")
    return errors


def cluster_name_for(node: dict[str, Any]) -> str:
    s = scores(node)
    if s["capability_rules"] >= 3 and s["information_asymmetry"] >= 2:
        return "capability_bound_visibility"
    if s["critical_stakes_state"] >= 3 and s["proof_state"] >= 2:
        return "critical_stakes_with_proof"
    if s["critical_stakes_state"] >= 3:
        return "critical_stakes_tradeoff"
    if s["information_asymmetry"] >= 3 and s["proof_state"] <= 1:
        return "visibility_and_timing"
    if s["proof_state"] >= 3:
        return "proof_before_reversal"
    if s["relationship_state"] >= 3:
        return "relationship_rupture"
    if s["audience_reputation_state"] >= 3 or s["escalation_risk"] >= 3:
        return "public_escalation"
    return "local_action_routing"


CLUSTER_PRODUCT_IMPLICATION = {
    "capability_bound_visibility": "Prevents hidden-power scenes from becoming unbounded cheats; the model must price both power limits and secrecy.",
    "critical_stakes_with_proof": "For rescue/safety moments, credible爽感 requires both immediate stakes and evidence/accountability timing.",
    "critical_stakes_tradeoff": "For survival/resource moments, the core question is what is saved now and what cost appears immediately after.",
    "visibility_and_timing": "Identity or secrecy moments depend on when information is revealed, not just whether the viewer can win.",
    "proof_before_reversal": "Reversal scenes need proof state; otherwise the output becomes empty revenge copy.",
    "relationship_rupture": "Relationship scenes require trust/dependency state or the result collapses into generic breakup advice.",
    "public_escalation": "Public humiliation scenes need audience and backlash fields to keep爽感 credible.",
    "local_action_routing": "These nodes mostly validate the universal moment envelope rather than adding a new causal module.",
}


def build_node_clusters(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        grouped[cluster_name_for(node)].append(node)

    clusters: dict[str, Any] = {}
    for name, items in sorted(grouped.items()):
        field_totals: Counter[str] = Counter()
        required_totals: Counter[str] = Counter()
        for node in items:
            for field, score in scores(node).items():
                if field not in VARIABLE_ANALYSIS_FIELDS:
                    continue
                if score >= 2:
                    field_totals[field] += 1
                if score == 3:
                    required_totals[field] += 1
        clusters[name] = {
            "cluster_id": name,
            "member_count": len(items),
            "member_node_ids": [item["node_id"] for item in items],
            "source_tier_counts": dict(Counter(item["source_tier"] for item in items)),
            "drama_distribution": dict(Counter(item["drama_id"] for item in items)),
            "trigger_distribution": dict(Counter(item["trigger_type"] for item in items)),
            "top_important_fields": [field for field, _ in field_totals.most_common(8)],
            "top_required_fields": [field for field, _ in required_totals.most_common(8)],
            "representative_examples": [
                {
                    "node_id": item["node_id"],
                    "drama_id": item["drama_id"],
                    "trigger_type": item["trigger_type"],
                    "hook": item.get("hook", ""),
                }
                for item in items[:4]
            ],
            "product_implication": CLUSTER_PRODUCT_IMPLICATION.get(name, "Local consequence judgment needs the shared moment envelope."),
        }
    return clusters


def field_statistics(nodes: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for field in fields:
        score_counts = Counter(scores(node)[field] for node in nodes)
        required_nodes = [node["node_id"] for node in nodes if scores(node)[field] == 3]
        important_nodes = [node["node_id"] for node in nodes if scores(node)[field] >= 2]
        stats[field] = {
            "score_counts": {str(key): score_counts.get(key, 0) for key in range(4)},
            "important_or_required_count": len(important_nodes),
            "required_count": len(required_nodes),
            "required_drama_distribution": dict(Counter(node["drama_id"] for node in nodes if scores(node)[field] == 3)),
            "sample_required_nodes": required_nodes[:8],
        }
    return stats


def pair_co_necessity(nodes: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for left, right in itertools.combinations(fields, 2):
        both_important = [node for node in nodes if scores(node)[left] >= 2 and scores(node)[right] >= 2]
        both_required = [node for node in nodes if scores(node)[left] == 3 and scores(node)[right] == 3]
        if not both_important:
            continue
        pairs.append(
            {
                "fields": [left, right],
                "both_important_count": len(both_important),
                "both_required_count": len(both_required),
                "drama_distribution": dict(Counter(node["drama_id"] for node in both_important)),
                "sample_nodes": [node["node_id"] for node in both_important[:8]],
            }
        )
    return sorted(pairs, key=lambda item: (item["both_required_count"], item["both_important_count"]), reverse=True)


def field_clusters(field_stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_surface_and_routing": {
            "fields": ["source_window", "companion_entry", "action_space", "response_contract", "visual_result_policy"],
            "reason": "These fields locate, invite, route, and present the interaction.",
        },
        "producer_trust_and_selection": {
            "fields": ["review_and_provenance", "score_axes"],
            "reason": "These fields keep ARS/review evidence auditable and help pick/promote moments.",
        },
        "base_local_causality": {
            "fields": ["actor_local_state", "critical_stakes_state", "local_constraint_state", "escalation_risk", "canon_baseline", "watch_flow_rationale"],
            "reason": "These are the minimum fields needed to answer local credible consequence without branching the story.",
        },
        "information_power_and_proof": {
            "fields": ["information_asymmetry", "capability_rules", "proof_state"],
            "reason": "These often co-occur in reversal scenes but remain separable computations.",
        },
        "social_pressure_modules": {
            "fields": ["relationship_state", "audience_reputation_state"],
            "reason": "Private relation pressure and public reputation pressure are reusable modules, not universal core.",
        },
    }


def minimum_set(corpus_counts: dict[str, Any], field_stats_data: dict[str, Any]) -> dict[str, Any]:
    categories = {
        "CoreOperational": OPERATIONAL_FIELDS,
        "CoreCausal": CORE_CAUSAL_FIELDS,
        "ReusableCausalityModules": REUSABLE_MODULES,
        "GenreOrStyleExtensions": [],
        "ProducerOnlyFields": PRODUCER_ONLY_FIELDS,
        "ExcludedFields": EXCLUDED_FIELDS,
    }
    return {
        "schema_version": "moment_field_minimum_set.v0.3",
        "generated": str(date.today()),
        "product_boundary": "Deadman judges one local `要是我来` consequence and preserves watch flow; it does not simulate a continuing alternate timeline.",
        "source_corpus": corpus_counts,
        "taxonomy": categories,
        "fields": {
            field: {
                "category": category,
                "description": FIELD_DESCRIPTIONS.get(field, ""),
                "demand_evidence": field_stats_data.get(field, {}),
            }
            for category, fields in categories.items()
            for field in fields
            if field not in EXCLUDED_FIELDS
        },
        "excluded_fields": {
            field: {
                "reason": {
                    "branch_timeline": "Would imply the story truly follows the alternate branch.",
                    "global_inventory": "Moment-level consequence only needs local resource/stake state.",
                    "full_social_graph": "Local actors and witnesses are enough for P0.",
                    "auto_visual_truth": "Generated/keyframe visuals are not evidence by themselves.",
                    "return_to_plot_fit": "Use `watch_flow_rationale`; the product is not forcing return-to-plot simulation.",
                }[field]
            }
            for field in EXCLUDED_FIELDS
        },
        "old_to_new_mapping": OLD_TO_NEW_MAPPING,
        "accepted_fusions": ACCEPTED_FUSIONS,
        "rejected_fusions": REJECTED_FUSIONS,
    }


def pack_schema() -> dict[str, Any]:
    module_fields = {field: {"type": "object", "additionalProperties": True} for field in REUSABLE_MODULES}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://oseria.local/schemas/deadman/moment_causality_pack.v0.3.draft.json",
        "title": "Deadman Moment Causality Pack v0.3 Draft",
        "type": "object",
        "required": [
            "pack_id",
            "schema_version",
            "source_window",
            "review_and_provenance",
            "companion_entry",
            "action_space",
            "response_contract",
            "actor_local_state",
            "critical_stakes_state",
            "local_constraint_state",
            "escalation_risk",
            "canon_baseline",
            "watch_flow_rationale",
        ],
        "properties": {
            "pack_id": {"type": "string"},
            "schema_version": {"const": "moment_causality_pack.v0.3.draft"},
            "source_window": {
                "type": "object",
                "required": ["drama_id", "episode_id", "start_ms", "end_ms"],
                "properties": {
                    "drama_id": {"type": "string"},
                    "episode_id": {"type": "string"},
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 0},
                    "interaction_window": {"type": "object", "additionalProperties": True},
                    "source_refs": {"type": "array", "items": {"type": "object"}},
                },
                "additionalProperties": True,
            },
            "review_and_provenance": {"type": "object", "additionalProperties": True},
            "companion_entry": {"type": "object", "additionalProperties": True},
            "action_space": {"type": "object", "additionalProperties": True},
            "response_contract": {"type": "object", "additionalProperties": True},
            "visual_result_policy": {"type": "object", "additionalProperties": True},
            "actor_local_state": {"type": "object", "additionalProperties": True},
            "critical_stakes_state": {"type": "object", "additionalProperties": True},
            "local_constraint_state": {"type": "object", "additionalProperties": True},
            "escalation_risk": {"type": "object", "additionalProperties": True},
            "canon_baseline": {"type": "object", "additionalProperties": True},
            "watch_flow_rationale": {"type": "object", "additionalProperties": True},
            "optional_modules": {
                "type": "object",
                "properties": module_fields,
                "additionalProperties": False,
            },
            "producer_only": {
                "type": "object",
                "properties": {
                    "score_axes": {"type": "object", "additionalProperties": True},
                    "field_demand_trace": {"type": "array", "items": {"type": "object"}},
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": False,
    }


def corpus_counts(matrix: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    by_drama: dict[str, Any] = {}
    for drama_id, summary in matrix["corpus_summary"].items():
        drama_nodes = [node for node in nodes if node["drama_id"] == drama_id]
        by_drama[drama_id] = {
            "title": summary["title"],
            "source_candidates": summary["candidate_count"],
            "review_input_count": summary["review_input_count"],
            "candidate_only_added": summary["candidate_only_added"],
            "matrix_node_count": len(drama_nodes),
            "valid_for_minimum_set": sum(1 for node in drama_nodes if node["valid_for_minimum_set"]),
            "source_tier_counts": dict(Counter(node["source_tier"] for node in drama_nodes)),
            "trigger_counts": dict(Counter(node["trigger_type"] for node in drama_nodes)),
        }
    return {
        "total_matrix_nodes": len(nodes),
        "valid_for_minimum_set": sum(1 for node in nodes if node["valid_for_minimum_set"]),
        "source_tier_counts": dict(Counter(node["source_tier"] for node in nodes)),
        "by_drama": by_drama,
    }


def markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in row) + " |")
    return "\n".join(lines)


def render_minimum_doc(minset: dict[str, Any], clusters: dict[str, Any]) -> str:
    category_rows: list[list[Any]] = []
    for category, fields in minset["taxonomy"].items():
        category_rows.append([category, ", ".join(f"`{field}`" for field in fields) or "-"])
    field_rows = [
        [field, meta["category"], meta["description"]]
        for field, meta in minset["fields"].items()
    ]
    mapping_rows = [[old, new] for old, new in OLD_TO_NEW_MAPPING.items()]
    excluded_rows = [[field, meta["reason"]] for field, meta in minset["excluded_fields"].items()]
    challenged_rows = [
        [
            "companion_entry",
            "CoreOperational",
            "No causal score 3 by design; it remains core because without a companion hook the viewer never enters the feature.",
        ],
        [
            "visual_result_policy",
            "CoreOperational",
            "No causal score 3; it remains core for P0 because result media needs truth-level/fallback rules even when causal judgment is text-first.",
        ],
        [
            "score_axes",
            "ProducerOnlyFields",
            "No runtime score 3; it is explicitly demoted from core and kept only for ARS ranking, QA, and later evaluation.",
        ],
    ]
    coverage_rows = [
        [
            cluster_id,
            cluster["member_count"],
            ", ".join(f"{key}:{value}" for key, value in cluster["drama_distribution"].items()),
            ", ".join(f"`{field}`" for field in cluster["top_required_fields"][:5]),
        ]
        for cluster_id, cluster in clusters.items()
    ]
    return "\n".join(
        [
            "# Moment Field Minimum Set v0.3",
            "",
            "> Product: Deadman / 要是我来",
            f"> Generated: {minset['generated']}",
            "",
            "## Product Boundary",
            "",
            minset["product_boundary"],
            "",
            "The field set is intentionally moment-level. It supports local consequence judgment, not ArcForge-style continuous world simulation.",
            "",
            "## Final Field Taxonomy",
            "",
            markdown_table(category_rows, ["Category", "Fields"]),
            "",
            "## Minimal Field Table",
            "",
            markdown_table(field_rows, ["Field", "Category", "Purpose"]),
            "",
            "## v0.2 To v0.3 Mapping",
            "",
            markdown_table(mapping_rows, ["v0.2 Field", "v0.3 Field"]),
            "",
            "## Accepted Field Fusions",
            "",
            markdown_table([[item["target"], ", ".join(item["sources"]), item["reason"]] for item in ACCEPTED_FUSIONS], ["Target", "Sources", "Reason"]),
            "",
            "## Rejected Field Fusions",
            "",
            markdown_table([[", ".join(item["fields"]), item["reason"]] for item in REJECTED_FUSIONS], ["Rejected Merge", "Reason"]),
            "",
            "## Excluded Fields",
            "",
            markdown_table(excluded_rows, ["Field", "Why Excluded"]),
            "",
            "## Fields Challenged Before Inclusion",
            "",
            "Fields with no score-3 demand were challenged before entering the final taxonomy.",
            "",
            markdown_table(challenged_rows, ["Field", "Final Category", "Decision"]),
            "",
            "## Coverage By Demand Cluster",
            "",
            markdown_table(coverage_rows, ["Cluster", "Nodes", "Drama Distribution", "Top Required Fields"]),
            "",
            "## Cross-Genre Examples",
            "",
            "- 荒年 resource/survival nodes map to `critical_stakes_state`, `local_constraint_state`, and `escalation_risk`; food/resource specifics no longer become standalone core fields.",
            "- 云渺 identity/hidden-power nodes map to `information_asymmetry` plus optional `capability_rules`; cultivation surface terms stay outside core.",
            "- 离婚 pregnancy/evidence/status nodes map to `critical_stakes_state`, `proof_state`, `relationship_state`, and `audience_reputation_state`; divorce-specific labels are not required by the runtime core.",
            "",
        ]
    )


def render_cluster_doc(corpus: dict[str, Any], clusters: dict[str, Any], field_cluster_data: dict[str, Any], pair_data: list[dict[str, Any]]) -> str:
    corpus_rows = [
        [
            drama_id,
            info["source_candidates"],
            info["review_input_count"],
            info["candidate_only_added"],
            info["valid_for_minimum_set"],
        ]
        for drama_id, info in corpus["by_drama"].items()
    ]
    cluster_rows = [
        [
            cluster_id,
            cluster["member_count"],
            ", ".join(f"{key}:{value}" for key, value in cluster["drama_distribution"].items()),
            ", ".join(f"`{field}`" for field in cluster["top_required_fields"][:6]),
            cluster["product_implication"],
        ]
        for cluster_id, cluster in clusters.items()
    ]
    field_cluster_rows = [
        [cluster_id, ", ".join(f"`{field}`" for field in item["fields"]), item["reason"]]
        for cluster_id, item in field_cluster_data.items()
    ]
    variable_pairs = [
        item
        for item in pair_data
        if item["fields"][0] in VARIABLE_ANALYSIS_FIELDS and item["fields"][1] in VARIABLE_ANALYSIS_FIELDS
    ]
    pair_rows = [
        [", ".join(f"`{field}`" for field in item["fields"]), item["both_important_count"], item["both_required_count"]]
        for item in variable_pairs[:16]
    ]
    return "\n".join(
        [
            "# Field Demand Cluster Report v0.3",
            "",
            "> Method: discrete `0-3` field-demand matrix. No embedding vectors were used.",
            "",
            "## Corpus Counts",
            "",
            markdown_table(corpus_rows, ["Drama", "Candidates", "Reviewed/Input", "Candidate-Only Added", "Valid For Minimum Set"]),
            "",
            f"- Total matrix nodes: {corpus['total_matrix_nodes']}",
            f"- Valid reviewed/schema-evidence nodes: {corpus['valid_for_minimum_set']}",
            f"- Source tier counts: {corpus['source_tier_counts']}",
            "",
            "## Node Demand Clusters",
            "",
            markdown_table(cluster_rows, ["Cluster", "Nodes", "Drama Distribution", "Top Required Fields", "Product Implication"]),
            "",
            "## Field Co-Necessity Clusters",
            "",
            markdown_table(field_cluster_rows, ["Field Cluster", "Fields", "Reason"]),
            "",
            "## Highest Variable Field Co-Occurrences",
            "",
            markdown_table(pair_rows, ["Field Pair", "Both Score >= 2", "Both Score = 3"]),
            "",
            "## Accepted Merge Candidates",
            "",
            markdown_table([[item["target"], ", ".join(item["sources"]), item["reason"]] for item in ACCEPTED_FUSIONS], ["Target", "Sources", "Reason"]),
            "",
            "## Rejected Merge Candidates",
            "",
            markdown_table([[", ".join(item["fields"]), item["reason"]] for item in REJECTED_FUSIONS], ["Rejected Merge", "Reason"]),
            "",
            "## Coverage And Gaps",
            "",
            "- All valid reviewed/schema-evidence nodes are representable without adding one-off fields.",
            "- Candidate-only nodes are used only as missing-mechanism probes and do not promote fields to core.",
            "- `relationship_state`, `capability_rules`, `information_asymmetry`, `proof_state`, and `audience_reputation_state` remain reusable modules because they are cross-genre but not universal.",
            "- Human review is still required before promoting 云渺 or 离婚 nodes into runtime packs.",
            "",
            "## Why No Embedding Vector",
            "",
            "The target is a minimum computable contract, not semantic retrieval. Embeddings would cluster by topic and wording; the discrete matrix clusters by what the judgment actually needs.",
            "",
        ]
    )


def render_pack_doc() -> str:
    shape = {
        "pack_id": "drama_ep01_m001",
        "schema_version": "moment_causality_pack.v0.3.draft",
        "source_window": {},
        "review_and_provenance": {},
        "companion_entry": {},
        "action_space": {},
        "response_contract": {},
        "visual_result_policy": {},
        "actor_local_state": {},
        "critical_stakes_state": {},
        "local_constraint_state": {},
        "escalation_risk": {},
        "canon_baseline": {},
        "watch_flow_rationale": {},
        "optional_modules": {
            "relationship_state": {},
            "capability_rules": {},
            "information_asymmetry": {},
            "proof_state": {},
            "audience_reputation_state": {},
        },
        "producer_only": {"score_axes": {}, "field_demand_trace": []},
    }
    return "\n".join(
        [
            "# Moment Causality Pack v0.3 Draft",
            "",
            "> Draft contract generated from Moment Field Minimum Set v0.3.",
            "",
            "## Minimal JSON Shape",
            "",
            "```json",
            json.dumps(shape, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Required Fields",
            "",
            "- Core operational: `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy`.",
            "- Core causal: `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale`.",
            "- Producer-only: `score_axes` may travel with packs for review/ranking, but frontend should ignore it.",
            "",
            "## Optional Module Shape",
            "",
            "`optional_modules` may include `relationship_state`, `capability_rules`, `information_asymmetry`, `proof_state`, and `audience_reputation_state`. A module is attached only when field demand score is `2` or `3` for the node.",
            "",
            "## Backend Judgment Consumption",
            "",
            "The backend should build the LLM/deterministic judgment prompt from core causal fields first, then attach only relevant optional modules. It should use `response_contract` and `watch_flow_rationale` to avoid promising future episodes follow the branch.",
            "",
            "## Producer ARS Extraction",
            "",
            "ARS should extract the core fields for every candidate and record module demand scores. Candidate-only evidence can reveal missing demand types, but cannot promote a module to core without reviewed/schema evidence.",
            "",
            "## Frontend Consumption",
            "",
            "The player needs `source_window`, `companion_entry`, `action_space`, `response_contract`, and `visual_result_policy`. It should ignore `producer_only` and should not display raw evidence/provenance unless a producer review UI is active.",
            "",
        ]
    )


def run_report(corpus: dict[str, Any], clusters: dict[str, Any], minset: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Deadman Moment Field Minimum Set v0.3 Run Report",
            "",
            "## Inputs",
            "",
            "- Existing three-drama ARS/review artifacts only.",
            "- No ASR, video ingestion, or provider rerun.",
            "",
            "## Counts",
            "",
            f"- Total matrix nodes: {corpus['total_matrix_nodes']}",
            f"- Valid reviewed/schema-evidence nodes: {corpus['valid_for_minimum_set']}",
            f"- Source tiers: {corpus['source_tier_counts']}",
            "",
            "## Node Demand Clusters",
            "",
            *[f"- `{name}`: {cluster['member_count']} nodes; top required fields {cluster['top_required_fields'][:5]}" for name, cluster in clusters.items()],
            "",
            "## Minimum Set",
            "",
            *[f"- `{category}`: {', '.join(fields) or '-'}" for category, fields in minset["taxonomy"].items()],
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--matrix", default=str(DEFAULT_WORK_DIR / "node_field_demand_matrix.v0.3.json"))
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    args = parser.parse_args()

    matrix = read_json(args.matrix)
    errors = validate_matrix(matrix)
    if errors:
        raise SystemExit("\n".join(errors))

    work_dir = resolve_path(args.work_dir)
    nodes = matrix["nodes"]
    valid_nodes = [node for node in nodes if node["valid_for_minimum_set"]]
    fields = matrix["candidate_field_vocabulary"]
    corpus = corpus_counts(matrix, nodes)
    clusters = build_node_clusters(nodes)
    valid_clusters = build_node_clusters(valid_nodes)
    stats = field_statistics(valid_nodes, fields)
    pairs = pair_co_necessity(valid_nodes, fields)
    field_cluster_data = field_clusters(stats)
    minset = minimum_set(corpus, stats)

    write_json(work_dir / "node_demand_clusters.v0.3.json", {"all_nodes": clusters, "valid_nodes": valid_clusters})
    write_json(work_dir / "field_co_necessity.v0.3.json", {"field_statistics": stats, "pair_co_necessity": pairs, "field_clusters": field_cluster_data})
    write_json(work_dir / "field_fusion_decisions.v0.3.json", {"accepted_fusions": ACCEPTED_FUSIONS, "rejected_fusions": REJECTED_FUSIONS})
    write_text(work_dir / "run_report.md", run_report(corpus, clusters, minset))

    write_json(REPO_ROOT / "data/schemas/moment_field_minimum_set.v0.3.json", minset)
    write_json(REPO_ROOT / "data/schemas/moment_causality_pack.v0.3.draft.json", pack_schema())
    write_text(REPO_ROOT / "docs/Moment_Field_Minimum_Set_v0.3.md", render_minimum_doc(minset, clusters))
    write_text(REPO_ROOT / "docs/Field_Demand_Cluster_Report_v0.3.md", render_cluster_doc(corpus, clusters, field_cluster_data, pairs))
    write_text(REPO_ROOT / "docs/Moment_Causality_Pack_v0.3_Draft.md", render_pack_doc())

    print(
        json.dumps(
            {
                "work_dir": repo_relative(work_dir),
                "matrix_nodes": corpus["total_matrix_nodes"],
                "valid_nodes": corpus["valid_for_minimum_set"],
                "node_clusters": list(clusters.keys()),
                "core_operational": OPERATIONAL_FIELDS,
                "core_causal": CORE_CAUSAL_FIELDS,
                "reusable_modules": REUSABLE_MODULES,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
