#!/usr/bin/env python3
"""Build Deadman Drama Context Pack data from reviewed ARS artifacts.

This is a production-side bridge from reviewed local evidence into runtime data.
It does not call providers, read secrets, or ingest automatic candidates.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)

DRAMA_CONFIG: dict[str, dict[str, Any]] = {
    "huangnian": {
        "title": "荒年全村啃树皮，我有系统满仓肉",
        "episode_scope": "first_20_episodes",
        "protagonist_name": "程弯弯",
        "summary_source_label": "allowed_drama_summary",
        "expected_moment_ids": [
            "huangnian_ep12_m001",
            "huangnian_ep07_m001",
            "huangnian_ep03_m001",
            "huangnian_ep04_m001",
            "huangnian_ep06_m001",
        ],
    }
}

TRIGGER_TO_ACTION_TYPE = {
    "resource_visibility": "resource",
    "humiliation_reversal": "humiliation",
    "system_rule": "system_rule",
    "evidence_or_trap": "evidence",
    "exposure_risk": "exposure",
}

MOMENT_ACTOR_CONTEXT = {
    "huangnian_ep12_m001": {
        "pov_actor": "程弯弯",
        "directly_affected_actors": ["四蛋", "程弯弯一家"],
        "relationship_context": "四蛋把兔子当作家庭贡献，食物分配会影响孩子对程弯弯的信任。",
        "local_emotional_pressure": "孩子一年没吃过肉，却默认自己可能没有份。",
    },
    "huangnian_ep07_m001": {
        "pov_actor": "程弯弯",
        "directly_affected_actors": ["儿媳", "程弯弯家人", "施压的家中长辈"],
        "relationship_context": "家庭内部的羞辱和桌规压力会影响儿媳被保护的感受。",
        "local_emotional_pressure": "观众会想立刻阻止羞辱，但过激反击可能扩大内部冲突。",
    },
    "huangnian_ep03_m001": {
        "pov_actor": "程弯弯",
        "directly_affected_actors": ["程弯弯", "程弯弯家人"],
        "relationship_context": "系统能力第一次进入生存决策，既能救急，也会带来解释成本。",
        "local_emotional_pressure": "观众会想马上用系统变现，但不能让公开面板破坏世界约束。",
    },
    "huangnian_ep04_m001": {
        "pov_actor": "程弯弯",
        "directly_affected_actors": ["程弯弯", "村中围观者", "诬陷方"],
        "relationship_context": "村庄见证人会放大名声变化，证据不足时反打可能被倒打一耙。",
        "local_emotional_pressure": "被当众诬陷时，观众会想立刻摊牌反击。",
    },
    "huangnian_ep06_m001": {
        "pov_actor": "程弯弯",
        "directly_affected_actors": ["程弯弯", "程弯弯家人"],
        "relationship_context": "白米等高价值资源能解决眼前饥饿，也会触发来源追问。",
        "local_emotional_pressure": "资源已经露出，观众会想说破真相来止住怀疑。",
    },
}

MOMENT_OPTIONAL_MODULES = {
    "huangnian_ep12_m001": {
        "resource_scarcity": {
            "resource_type": "兔肉/兔子",
            "quantity_or_visibility": "source window shows a rabbit/meal decision, exact quantity not normalized",
            "scarcity_level": "high",
            "distribution_target": "child/family meal",
            "defer_cost": "delaying food preserves options but weakens immediate trust repair",
        },
        "relationship_pressure": {
            "relationship_role": "mother-child trust repair",
            "prior_trust_damage": "family trust is not fully repaired at this stage",
            "care_priority": "make the child's contribution and share legible",
            "trust_delta_policy": "local trust can improve, but cannot become unconditional instantly",
            "repair_pace": "gradual",
        },
    },
    "huangnian_ep07_m001": {
        "humiliation_reversal": {
            "harm_state": "daughter-in-law is being humiliated by household rules",
            "retaliation_scale": "local de-escalating protection is safer than uncontrolled violence",
            "protected_actor": "daughter-in-law",
            "escalation_risk": "public or violent reversal can create new family backlash",
            "dignity_repair": "stop the immediate humiliation and make protection visible",
        },
        "relationship_pressure": {
            "relationship_role": "mother-in-law / daughter-in-law protection",
            "prior_trust_damage": "family members need actions, not only promises",
            "care_priority": "protect the harmed family member first",
            "trust_delta_policy": "one intervention can earn a local trust delta only",
            "repair_pace": "scene-local",
        },
    },
    "huangnian_ep03_m001": {
        "system_or_hidden_power_rule": {
            "power_or_system_action": "first visible use of system sale/exchange logic",
            "rule_visibility": "private to protagonist; do not expose as public UI",
            "cost_or_cooldown": "not established in reviewed evidence",
            "world_explanation": "use small, ordinary explanations when resources enter the scene",
            "power_cap": "no unlimited money/resource escalation",
        },
        "exposure_and_secrecy": {
            "visible_advantage": "system can convert ordinary goods into survival resources",
            "source_explanation": "must remain locally plausible",
            "witness_scope": "keep hidden from public witnesses",
            "suspicion_risk": "medium",
            "concealment_strategy": "small-scale trial before public benefit",
        },
    },
    "huangnian_ep04_m001": {
        "evidence_or_trap_logic": {
            "evidence_refs": "source window refs and reviewed notes only; keyframes are object/time refs, not motive proof",
            "claim_account": "程弯弯 is accused in a village/public setting",
            "counter_claim_shape": "respond with concrete evidence or witness order instead of pure argument",
            "counterparty_leverage": "public accusation can turn crowd sentiment",
            "proof_threshold": "enough for local reputation shift, not a legal judgment",
        },
        "village_or_public_reputation": {
            "witnesses": "village/public onlookers",
            "public_claim": "theft/false accusation pressure",
            "reputation_delta": "can improve if evidence is legible",
            "exchange_dependency": "village reputation affects later survival exchange",
            "escalation_risk": "crowd conflict can harden if the counterclaim is unsupported",
        },
    },
    "huangnian_ep06_m001": {
        "exposure_and_secrecy": {
            "visible_advantage": "white rice/resource visibility",
            "source_explanation": "do not publicly explain system or hidden storage",
            "witness_scope": "family-level witnesses in reviewed demo node",
            "suspicion_risk": "high",
            "concealment_strategy": "partial explanation and smaller release of resource",
        },
        "resource_scarcity": {
            "resource_type": "白米/food resource",
            "quantity_or_visibility": "visible enough to trigger source questions",
            "scarcity_level": "high",
            "distribution_target": "family survival",
            "defer_cost": "hiding too much may leave immediate hunger unresolved",
        },
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def load_reviewed_demo_nodes(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    nodes = data.get("demo_nodes")
    if not isinstance(nodes, list):
        raise ValueError(f"{path} does not contain a demo_nodes list")
    return nodes


def load_reviewed_candidate_map(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    candidates = data.get("reviewed_candidates", [])
    if not isinstance(candidates, list):
        raise ValueError(f"{path} does not contain a reviewed_candidates list")
    return {candidate.get("candidate_id"): candidate for candidate in candidates if candidate.get("candidate_id")}


def find_summary_row(summary_text: str, title: str) -> str:
    for line in summary_text.splitlines():
        if title in line and line.strip().startswith("|"):
            return line.strip()
    raise ValueError(f"Could not find summary table row for {title}")


def split_markdown_row(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip("|").split("|")]


def parse_huangnian_summary(summary_text: str, title: str) -> dict[str, str]:
    row = find_summary_row(summary_text, title)
    cells = split_markdown_row(row)
    if len(cells) < 4:
        raise ValueError(f"Unexpected summary row shape: {row}")
    return {
        "title": cells[0],
        "source_summary": cells[1],
        "genre_hook": cells[2],
        "product_fit": cells[3],
        "raw_row": row,
    }


def hydrate_transcript_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hydrated = []
    asr_cache: dict[str, Any] = {}
    for ref in refs:
        next_ref = dict(ref)
        path = next_ref.get("path")
        utterance_index = next_ref.get("utterance_index")
        if path and "text" not in next_ref:
            asr_path = resolve_path(path)
            if asr_path.exists():
                if path not in asr_cache:
                    asr_cache[path] = read_json(asr_path)
                utterances = asr_cache[path].get("utterances", [])
                if isinstance(utterance_index, int) and 0 <= utterance_index < len(utterances):
                    utterance = utterances[utterance_index]
                    next_ref["text"] = utterance.get("text", "")
                    next_ref.setdefault("start_ms", utterance.get("start_time"))
                    next_ref.setdefault("end_ms", utterance.get("end_time"))
        hydrated.append(next_ref)
    return hydrated


def normalized_source_window(node: dict[str, Any]) -> dict[str, Any]:
    source_window = dict(node.get("source_window") or {})
    transcript_refs = source_window.get("transcript_refs") or []
    if not isinstance(transcript_refs, list):
        transcript_refs = []
    source_window["transcript_refs"] = hydrate_transcript_refs(transcript_refs)
    source_window.setdefault("keyframe_refs", [])
    source_window.setdefault("contact_sheet_ref", "")
    return source_window


def episode_id_for_node(node: dict[str, Any]) -> str:
    match = re.match(r"(huangnian_ep\d+)_", node.get("candidate_id", ""))
    if match:
        return match.group(1)
    for ref in (node.get("source_window") or {}).get("transcript_refs", []):
        match = re.search(r"(huangnian_ep\d+)", ref.get("path", ""))
        if match:
            return match.group(1)
    return "huangnian_unknown_episode"


def evidence_id(prefix: str, index: int) -> str:
    return f"DCP-EV-{prefix}-{index:03d}"


def build_evidence_entries(
    drama_id: str,
    summary: dict[str, str],
    summaries_path: Path,
    demo_nodes_path: Path,
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = [
        {
            "id": evidence_id("SUMMARY", 1),
            "type": "summary_derived_claim",
            "source": repo_relative(summaries_path),
            "claim": "Premise, broad genre hook, and product-fit framing for 荒年.",
            "evidence": summary["source_summary"],
            "confidence": "medium",
            "notes": "Public/allowed summary is broad drama-level evidence only; it is not timestamp-level proof.",
            "supports": ["premise", "genre_contract", "protagonist.role"],
        }
    ]
    for index, node in enumerate(nodes, start=1):
        moment_id = node["moment_id"]
        grade = (node.get("evidence") or {}).get("grade", "medium")
        entries.append(
            {
                "id": evidence_id("NODE", index),
                "type": "reviewed_node_derived_claim",
                "source": f"{repo_relative(demo_nodes_path)}#{moment_id}",
                "claim": f"Reviewed demo moment {moment_id} supports local runtime constraints for {node.get('corrected_trigger_type')}.",
                "evidence": (node.get("evidence") or {}).get("notes", ""),
                "confidence": grade,
                "notes": node.get("evidence_vs_inference", ""),
                "supports": ["core_constraints", "relationship_map", "judgment_guardrails"],
            }
        )
        source_window = normalized_source_window(node)
        entries.append(
            {
                "id": evidence_id("ASR", index),
                "type": "asr_keyframe_supported_claim",
                "source": f"{repo_relative(demo_nodes_path)}#{moment_id}.source_window",
                "claim": f"ASR/keyframe refs support objects, utterances, and timing for {moment_id}.",
                "evidence": (node.get("evidence") or {}).get("excerpt", ""),
                "confidence": grade,
                "notes": "ASR supports dialogue; keyframes/contact sheets are time/object references and do not prove psychological motivation.",
                "supports": [f"moments.{moment_id}.source_window"],
                "source_refs": {
                    "transcript_ref_count": len(source_window.get("transcript_refs", [])),
                    "keyframe_refs": source_window.get("keyframe_refs", []),
                    "contact_sheet_ref": source_window.get("contact_sheet_ref", ""),
                },
            }
        )
    entries.append(
        {
            "id": evidence_id("INFERENCE", 1),
            "type": "inference_only_product_constraint",
            "source": "Deadman docs + reviewed bridge policy",
            "claim": "P0 outcomes stay local and must not rewrite later episodes or pretend to simulate the full world.",
            "evidence": "Moment Causality Pack v0.1 and goal contract define the local consequence boundary.",
            "confidence": "high",
            "notes": "This is a product/runtime constraint, not source-canon evidence.",
            "supports": ["judgment_guardrails", "runtime_priority", "tone_policy"],
        }
    )
    return entries


def build_context_pack(
    drama_id: str,
    summary: dict[str, str],
    evidence_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    config = DRAMA_CONFIG[drama_id]
    return {
        "schema_version": "drama_context_pack.v0.1",
        "drama_id": drama_id,
        "title": config["title"],
        "source_scope": {
            "episode_scope": config["episode_scope"],
            "basis": [
                "allowed_drama_summary",
                "reviewed_demo_nodes",
                "asr_snippets",
                "keyframe_contact_sheet_refs",
            ],
            "evidence_status": "reviewed_bridge_artifact",
        },
        "premise": summary["source_summary"],
        "genre_contract": [
            {
                "claim": "Famine-survival and farming/household recovery are the main pressure system.",
                "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 1), evidence_id("NODE", 5)],
                "confidence": "high",
            },
            {
                "claim": "System/hidden-resource advantage can solve local crises but should stay partially concealed.",
                "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 3), evidence_id("NODE", 5)],
                "confidence": "medium",
            },
            {
                "claim": "Family trust repair and public village reputation are drama engines, not background color.",
                "evidence_ids": [evidence_id("NODE", 1), evidence_id("NODE", 2), evidence_id("NODE", 4)],
                "confidence": "medium",
            },
            {
                "claim": "P0 interaction answers local credible consequences, then lets the viewer keep watching.",
                "evidence_ids": [evidence_id("INFERENCE", 1)],
                "confidence": "high",
            },
        ],
        "protagonist": {
            "name": config["protagonist_name"],
            "role": "modern entrepreneur transmigrated into an ancient-famine widow raising four children",
            "capabilities": [
                {
                    "claim": "survival planning, household/resource decision-making, and gradual trust repair",
                    "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 1), evidence_id("NODE", 2)],
                    "confidence": "medium",
                },
                {
                    "claim": "access to a survival system / hidden resource advantage",
                    "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 3), evidence_id("NODE", 5)],
                    "confidence": "medium",
                },
            ],
            "limits": [
                {
                    "claim": "cannot publicly over-explain the system or create unlimited resources without suspicion",
                    "evidence_ids": [evidence_id("NODE", 3), evidence_id("NODE", 5), evidence_id("INFERENCE", 1)],
                    "confidence": "high",
                },
                {
                    "claim": "family and village trust changes must be gradual and scene-local in P0",
                    "evidence_ids": [evidence_id("NODE", 1), evidence_id("NODE", 4), evidence_id("INFERENCE", 1)],
                    "confidence": "medium",
                },
            ],
        },
        "core_constraints": [
            {
                "id": "famine_resource_scarcity",
                "constraint": "Food and resource scarcity must remain real pressure even when the protagonist has advantages.",
                "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 1), evidence_id("ASR", 1), evidence_id("NODE", 5)],
                "source_basis": "summary + reviewed nodes + ASR snippets",
                "confidence": "high",
            },
            {
                "id": "resource_exposure_risk",
                "constraint": "Visible food, white rice, money, or system benefits create suspicion,争抢, or explanation pressure.",
                "evidence_ids": [evidence_id("NODE", 3), evidence_id("NODE", 5), evidence_id("ASR", 5)],
                "source_basis": "reviewed nodes + ASR snippets",
                "confidence": "high",
            },
            {
                "id": "hidden_system_rule",
                "constraint": "System/hidden-resource ability can guide decisions but should not be publicly over-explained.",
                "evidence_ids": [evidence_id("SUMMARY", 1), evidence_id("NODE", 3), evidence_id("INFERENCE", 1)],
                "source_basis": "summary + reviewed node + product inference",
                "confidence": "medium",
            },
            {
                "id": "gradual_family_trust",
                "constraint": "Children/family trust repair must be earned through visible care; one choice cannot erase all prior damage.",
                "evidence_ids": [evidence_id("NODE", 1), evidence_id("NODE", 2), evidence_id("ASR", 1)],
                "source_basis": "reviewed nodes + ASR snippets",
                "confidence": "medium",
            },
            {
                "id": "village_public_pressure",
                "constraint": "Village/public witnesses can amplify reputation, conflict, and later exchange pressure.",
                "evidence_ids": [evidence_id("NODE", 4), evidence_id("ASR", 4)],
                "source_basis": "reviewed node + ASR/keyframe refs",
                "confidence": "medium",
            },
            {
                "id": "local_watch_flow",
                "constraint": "P0 outcomes stay within current scene or immediate aftermath and do not rewrite later episodes.",
                "evidence_ids": [evidence_id("INFERENCE", 1)],
                "source_basis": "inference-only product/runtime constraint",
                "confidence": "high",
            },
        ],
        "relationship_map": [
            {
                "actor": "程弯弯",
                "relation": "protagonist and decision POV",
                "evidence_ids": [evidence_id("SUMMARY", 1)],
                "confidence": "medium",
            },
            {
                "actor": "四蛋",
                "relation": "child/family member; rabbit scene makes trust and distribution visible",
                "evidence_ids": [evidence_id("NODE", 1), evidence_id("ASR", 1)],
                "confidence": "high",
            },
            {
                "actor": "儿媳/家人",
                "relation": "family members whose trust and dignity can be protected or damaged scene-locally",
                "evidence_ids": [evidence_id("NODE", 2)],
                "confidence": "medium",
            },
            {
                "actor": "村庄围观者/外部亲邻",
                "relation": "public pressure surface; witnesses can turn resource or accusation choices into reputation changes",
                "evidence_ids": [evidence_id("NODE", 4), evidence_id("NODE", 5)],
                "confidence": "medium",
            },
        ],
        "tone_policy": {
            "companion_stance": "sharp but protective short-drama companion: names the viewer impulse, then checks it against famine, secrecy, family, and watch-flow constraints",
            "preferred": [
                "short local consequence",
                "plain-language reason the original plot remains watchable",
                "specific references to evidenced object/person/witness/pressure",
                "controlled爽感 without unlimited power escalation",
            ],
            "avoid": [
                "claiming later episodes truly branch",
                "explaining hidden system rules to public characters without evidence",
                "turning every choice into revenge or violence",
                "treating keyframes as proof of motivation",
            ],
        },
        "judgment_guardrails": {
            "must_consider": [
                "local moment pack facts outrank global context",
                "food/resource scarcity and exposure risk",
                "whether witnesses are family-only or public village pressure",
                "whether the action keeps original viewing flow credible",
                "whether trust/reputation changes are gradual enough for a short-drama scene",
            ],
            "must_not_claim": [
                "later episodes actually follow the branch",
                "the public knows the system exists unless the moment pack says so",
                "keyframes prove internal motivation",
                "the protagonist has unlimited resources or consequence-free power",
            ],
            "custom_action_handling": "Accept free-form actions only as local credible consequences; soften or reject actions that require unsupported canon facts, unlimited system use, or continuous alternate-episode simulation.",
        },
        "runtime_priority": [
            "moment_pack_local_facts",
            "drama_context_pack_global_constraints",
            "llm_common_sense",
        ],
        "evidence_map": evidence_entries,
        "confidence": {
            "overall": "medium",
            "notes": "Strong enough for the 5 reviewed P0 demo moments. It is a lightweight Drama Context Pack, not an ArcForge world simulation pack or full source-canon database.",
        },
        "open_questions": [
            {
                "question": "Which source should become canonical for episode-level facts beyond the 5 reviewed demo moments?",
                "impact": "Needed before expanding beyond P0 reviewed nodes.",
            },
            {
                "question": "What are the exact system cost/cooldown/resource limits in later episodes?",
                "impact": "Needed before stronger hidden-power judgments.",
            },
            {
                "question": "Which names/relationships beyond 四蛋 and family roles should be normalized into a reusable cast index?",
                "impact": "Needed before backend pack ingestion or multi-moment continuity.",
            },
        ],
    }


def score_axes_for_node(node: dict[str, Any]) -> dict[str, int]:
    trigger = node.get("corrected_trigger_type", "")
    base = {
        "emotion_heat": 78,
        "choice_leverage": 74,
        "causal_clarity": 72,
        "world_constraint_value": 76,
        "watch_flow_fit": 82,
        "visual_result_fit": 55,
    }
    if trigger in {"resource_visibility", "humiliation_reversal", "exposure_risk"}:
        base["emotion_heat"] = 85
    if trigger in {"system_rule", "evidence_or_trap", "exposure_risk"}:
        base["choice_leverage"] = 84
    if trigger in {"system_rule", "resource_visibility", "exposure_risk"}:
        base["world_constraint_value"] = 88
    if (node.get("evidence") or {}).get("grade") == "high":
        base["causal_clarity"] += 6
        base["visual_result_fit"] += 8
    return base


def known_facts_for_node(node: dict[str, Any]) -> list[str]:
    source_window = normalized_source_window(node)
    facts = []
    for ref in source_window.get("transcript_refs", [])[:4]:
        text = ref.get("text")
        if text:
            facts.append(f"ASR: {text}")
    evidence_notes = (node.get("evidence") or {}).get("notes")
    if evidence_notes:
        facts.append(f"reviewed evidence note: {evidence_notes}")
    return facts


def convert_moment_pack(
    drama_id: str,
    node: dict[str, Any],
    reviewed_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    moment_id = node["moment_id"]
    source_window = normalized_source_window(node)
    evidence = node.get("evidence") or {}
    trigger = node.get("corrected_trigger_type", "other")
    action_type = TRIGGER_TO_ACTION_TYPE.get(trigger, "other")
    return {
        "pack_id": moment_id,
        "moment_id": moment_id,
        "schema_version": "moment_causality_pack.v0.1",
        "drama_id": drama_id,
        "drama_context_ref": "context.v0.1.json",
        "source_drama": {
            "title": DRAMA_CONFIG[drama_id]["title"],
            "episode_id": episode_id_for_node(node),
            "source_policy": "reviewed demo node + local ASR/keyframe refs; no v0.2 automatic candidate ingestion",
        },
        "source_window": source_window,
        "provenance": {
            "candidate_id": node.get("candidate_id"),
            "reviewed_candidate_ref": reviewed_candidate.get("candidate_id") if reviewed_candidate else None,
            "candidate_id_stability": "provenance_only_not_runtime_identity",
            "source_artifact": "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
        },
        "review_state": {
            "status": "demo_candidate",
            "reviewed_at": "2026-05-24",
            "evidence_grade": evidence.get("grade", "medium"),
            "evidence_notes": evidence.get("notes", ""),
            "evidence_vs_inference": node.get("evidence_vs_inference", ""),
        },
        "companion_surface": {
            "notice_marker": "?" if trigger in {"system_rule", "evidence_or_trap"} else "!",
            "hook": node.get("companion_hook", ""),
            "viewer_impulse": node.get("viewer_impulse", ""),
            "scene_specificity_check": "must name an object, relation, witness, rule, or decision pressure from the source window",
        },
        "actor_context": MOMENT_ACTOR_CONTEXT.get(
            moment_id,
            {
                "pov_actor": "程弯弯",
                "directly_affected_actors": [],
                "relationship_context": "",
                "local_emotional_pressure": "",
            },
        ),
        "local_constraints": {
            "known_facts": known_facts_for_node(node),
            "unknown_or_hidden_facts": [
                "later-episode branch outcome",
                "full motive state beyond reviewed notes",
                "system limits not present in the source window",
            ],
            "hard_constraints": [
                "answer only current scene or immediate aftermath",
                "do not claim continuous branch rewrite",
                "do not expose system or hidden resource details unless local pack evidence allows it",
                "do not treat keyframe refs as psychological proof",
            ],
            "risk_notes": [
                "resource exposure can create suspicion or争抢",
                "family/village trust deltas should stay gradual",
            ],
        },
        "canon_baseline": {
            "original_action": (node.get("canon_baseline_reviewed") or {}).get("original_action", ""),
            "original_rationale": (node.get("canon_baseline_reviewed") or {}).get("original_rationale", ""),
            "audience_tension": (node.get("canon_baseline_reviewed") or {}).get("audience_tension", ""),
            "original_plot_note": node.get("original_plot_note_reviewed", ""),
        },
        "action_space": {
            "action_type": action_type,
            "default_options": node.get("default_options", []),
            "custom_action_policy": node.get(
                "custom_action_policy",
                {
                    "allowed": True,
                    "scope": "local credible consequence only",
                    "reject_or_soften": [
                        "continuous branch rewrite",
                        "unbounded system/power escalation",
                        "claims not grounded in source window",
                    ],
                },
            ),
        },
        "judgment_policy": {
            "must_consider": [
                "source_window evidence",
                "drama_context_ref global constraints",
                "scene-local watch_flow_fit",
                "resource/secrecy/family/public pressure where applicable",
            ],
            "must_not_claim": [
                "later episodes actually follow this branch",
                "facts not present in source evidence",
                "unbounded system or power escalation",
            ],
        },
        "outcome_response_contract": {
            "format": "short local consequence + why original plot still remains watchable",
            "time_horizon": "current scene or immediate aftermath",
            "include_original_plot_note": True,
        },
        "visual_result_policy": {
            "allowed": "result card or still prompt only when object/person is evidenced",
            "keyframe_ref_quality": "medium" if source_window.get("keyframe_refs") else "none",
            "visual_evidence": evidence.get("grade", "medium") if source_window.get("keyframe_refs") else "low",
        },
        "score_axes": score_axes_for_node(node),
        "optional_modules": MOMENT_OPTIONAL_MODULES.get(moment_id, {}),
        "required_pack_fields": node.get("required_pack_fields", []),
        "original_plot_note": node.get("original_plot_note_reviewed", ""),
        "evidence": {
            "grade": evidence.get("grade", "medium"),
            "notes": evidence.get("notes", ""),
            "excerpt": evidence.get("excerpt", ""),
        },
        "source_refs": {
            "reviewed_demo_node": "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
            "reviewed_candidates": "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json",
            "transcript_paths": sorted(
                {
                    ref.get("path")
                    for ref in source_window.get("transcript_refs", [])
                    if ref.get("path")
                }
            ),
            "keyframe_refs": source_window.get("keyframe_refs", []),
            "contact_sheet_ref": source_window.get("contact_sheet_ref", ""),
        },
        "producer_review_fields": {
            "reviewer_notes": (reviewed_candidate or {}).get("why_now_reviewed", ""),
            "field_evidence_refs": node.get("required_pack_fields", []),
            "open_questions": [],
            "do_not_promote_reasons": [],
        },
    }


def build_moment_collection(
    drama_id: str,
    nodes: list[dict[str, Any]],
    candidate_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected = DRAMA_CONFIG[drama_id]["expected_moment_ids"]
    node_by_id = {node.get("moment_id"): node for node in nodes}
    missing = [moment_id for moment_id in expected if moment_id not in node_by_id]
    if missing:
        raise ValueError(f"Missing expected reviewed demo moments: {', '.join(missing)}")
    packs = [
        convert_moment_pack(drama_id, node_by_id[moment_id], candidate_map.get(node_by_id[moment_id].get("candidate_id")))
        for moment_id in expected
    ]
    return {
        "schema_version": "moment_causality_pack.v0.1",
        "collection_schema_version": "moment_causality_pack_collection.v0.1",
        "drama_id": drama_id,
        "title": DRAMA_CONFIG[drama_id]["title"],
        "drama_context_ref": "context.v0.1.json",
        "source_policy": "reviewed demo nodes only; candidate_id is provenance, moment_id is runtime identity",
        "moment_count": len(packs),
        "moments": packs,
    }


def build_manifest(
    drama_id: str,
    context_pack: dict[str, Any],
    moment_collection: dict[str, Any],
    out_dir: Path,
    promote_dir: Path | None,
) -> dict[str, Any]:
    promoted_ids = [moment["moment_id"] for moment in moment_collection["moments"]]
    return {
        "schema_version": "deadman_drama_runtime_manifest.v0.1",
        "drama_id": drama_id,
        "title": DRAMA_CONFIG[drama_id]["title"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pack_type": "lightweight_drama_context_pack_not_arcforge_world_simulation",
        "context_pack": {
            "path": "context.v0.1.json",
            "schema_version": context_pack["schema_version"],
            "confidence": context_pack["confidence"],
        },
        "moment_packs": {
            "path": "moments.v0.1.json",
            "schema_version": "moment_causality_pack.v0.1",
            "count": len(promoted_ids),
            "moment_ids": promoted_ids,
        },
        "runtime_priority": context_pack["runtime_priority"],
        "source_artifacts": {
            "reviewed_demo_nodes": "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
            "reviewed_candidates": "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json",
            "allowed_summary": "docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md",
        },
        "generated_artifacts": {
            "draft_context": repo_relative(out_dir / f"{drama_id}_drama_context.draft.v0.1.json"),
            "evidence_map": repo_relative(out_dir / f"{drama_id}_drama_context.evidence.v0.1.md"),
            "run_report": repo_relative(out_dir / f"{drama_id}_drama_context.run_report.v0.1.md"),
        },
        "promoted_dir": repo_relative(promote_dir) if promote_dir else None,
        "ingestion_status": {
            "backend_judgment_api": "not_implemented_in_this_goal",
            "frontend_ingestion": "not_implemented_in_this_goal",
        },
    }


def build_evidence_markdown(
    drama_id: str,
    context_pack: dict[str, Any],
    nodes: list[dict[str, Any]],
    summary: dict[str, str],
) -> str:
    lines = [
        f"# {DRAMA_CONFIG[drama_id]['title']} Drama Context Evidence Map v0.1",
        "",
        "> Scope: first 20 episodes bridge artifact for Deadman P0. This is a lightweight Drama Context Pack evidence map, not an ArcForge world simulation pack.",
        "",
        "## Summary-Derived Claims",
        "",
        "| Claim | Source | Confidence | Caution |",
        "|---|---|---|---|",
        f"| Premise / broad genre / protagonist setup | `docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md` row: {summary['title']} | medium | Summary is drama-level orientation, not timestamp-level evidence. |",
        "",
        "## Reviewed-Node-Derived Claims",
        "",
        "| Moment | Trigger | Claim | Confidence | Evidence Status |",
        "|---|---|---|---|---|",
    ]
    for node in nodes:
        evidence = node.get("evidence") or {}
        lines.append(
            f"| `{node['moment_id']}` | `{node.get('corrected_trigger_type', '')}` | {node.get('companion_hook', '')} | {evidence.get('grade', 'medium')} | reviewed demo node; hook/options are product inference constrained by source evidence |"
        )
    lines.extend(
        [
            "",
            "## ASR / Keyframe Supported Claims",
            "",
            "| Moment | ASR Supports | Keyframe / Contact Sheet Supports | Caution |",
            "|---|---|---|---|",
        ]
    )
    for node in nodes:
        source_window = normalized_source_window(node)
        asr_excerpt = (node.get("evidence") or {}).get("excerpt", "")
        if len(asr_excerpt) > 90:
            asr_excerpt = asr_excerpt[:87] + "..."
        lines.append(
            f"| `{node['moment_id']}` | {asr_excerpt} | {len(source_window.get('keyframe_refs', []))} keyframe refs; contact sheet `{source_window.get('contact_sheet_ref', '')}` | Keyframes/contact sheets are object/time refs only, not motivation proof. |"
        )
    lines.extend(
        [
            "",
            "## Inference-Only Product Constraints",
            "",
            "- P0 outcome horizon stays at current scene or immediate aftermath.",
            "- Moment Causality Pack local facts outrank Drama Context Pack global constraints.",
            "- `candidate_id` is provenance only; runtime identity is stable `moment_id + source_window`.",
            "- Do not claim later episodes truly branch from the user action.",
            "- Do not turn system/hidden-resource advantage into public, unlimited, consequence-free power.",
            "",
            "## Open Questions",
            "",
        ]
    )
    for question in context_pack["open_questions"]:
        lines.append(f"- {question['question']} Impact: {question['impact']}")
    lines.extend(
        [
            "",
            "## Evidence Entries",
            "",
            "```json",
            json.dumps(context_pack["evidence_map"], ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_run_report(
    drama_id: str,
    out_dir: Path,
    promote_dir: Path | None,
    nodes: list[dict[str, Any]],
    promoted: bool,
) -> str:
    moment_ids = [node["moment_id"] for node in nodes]
    lines = [
        f"# {DRAMA_CONFIG[drama_id]['title']} Drama Context Build Report v0.1",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Drama ID: `{drama_id}`",
        f"- Reviewed demo nodes read: {len(nodes)}",
        f"- Promoted: `{str(promoted).lower()}`",
        f"- Moment IDs: {', '.join(f'`{moment_id}`' for moment_id in moment_ids)}",
        "",
        "## Outputs",
        "",
        f"- Draft context: `{repo_relative(out_dir / f'{drama_id}_drama_context.draft.v0.1.json')}`",
        f"- Evidence map: `{repo_relative(out_dir / f'{drama_id}_drama_context.evidence.v0.1.md')}`",
        f"- Run report: `{repo_relative(out_dir / f'{drama_id}_drama_context.run_report.v0.1.md')}`",
    ]
    if promote_dir:
        lines.extend(
            [
                f"- Promoted context: `{repo_relative(promote_dir / 'context.v0.1.json')}`",
                f"- Promoted moments: `{repo_relative(promote_dir / 'moments.v0.1.json')}`",
                f"- Promoted manifest: `{repo_relative(promote_dir / 'manifest.v0.1.json')}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No provider calls.",
            "- No backend judgment API implemented.",
            "- No frontend ingestion implemented.",
            "- No raw MP4/MOV dependency added to runtime data.",
            "- This is a lightweight Drama Context Pack, not an ArcForge world simulation pack.",
            "",
        ]
    )
    return "\n".join(lines)


def assert_no_media_dependencies(data: Any) -> None:
    text = json.dumps(data, ensure_ascii=False)
    forbidden = [".mp4", ".mov", ".MP4", ".MOV"]
    found = [suffix for suffix in forbidden if suffix in text]
    if found:
        raise ValueError(f"Promoted runtime data contains raw media dependency suffixes: {found}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drama-id", required=True, choices=sorted(DRAMA_CONFIG))
    parser.add_argument("--reviewed-demo-nodes", required=True)
    parser.add_argument("--reviewed-candidates", required=True)
    parser.add_argument("--summaries", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--promote-dir")
    parser.add_argument("--promote", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    drama_id = args.drama_id
    config = DRAMA_CONFIG[drama_id]
    reviewed_demo_nodes_path = resolve_path(args.reviewed_demo_nodes)
    reviewed_candidates_path = resolve_path(args.reviewed_candidates)
    summaries_path = resolve_path(args.summaries)
    out_dir = resolve_path(args.out_dir)
    promote_dir = resolve_path(args.promote_dir) if args.promote_dir else None

    nodes = load_reviewed_demo_nodes(reviewed_demo_nodes_path)
    candidate_map = load_reviewed_candidate_map(reviewed_candidates_path)
    summary_text = summaries_path.read_text(encoding="utf-8")
    summary = parse_huangnian_summary(summary_text, config["title"])

    expected = config["expected_moment_ids"]
    nodes = [node for node in nodes if node.get("moment_id") in expected]
    if len(nodes) != len(expected):
        found = sorted(node.get("moment_id", "") for node in nodes)
        raise ValueError(f"Expected {len(expected)} reviewed demo nodes, found {len(nodes)}: {found}")
    nodes = sorted(nodes, key=lambda node: expected.index(node["moment_id"]))

    evidence_entries = build_evidence_entries(drama_id, summary, summaries_path, reviewed_demo_nodes_path, nodes)
    context_pack = build_context_pack(drama_id, summary, evidence_entries)
    moment_collection = build_moment_collection(drama_id, nodes, candidate_map)

    draft_path = out_dir / f"{drama_id}_drama_context.draft.v0.1.json"
    evidence_path = out_dir / f"{drama_id}_drama_context.evidence.v0.1.md"
    run_report_path = out_dir / f"{drama_id}_drama_context.run_report.v0.1.md"

    write_json(draft_path, context_pack)
    write_text(evidence_path, build_evidence_markdown(drama_id, context_pack, nodes, summary))
    write_text(run_report_path, build_run_report(drama_id, out_dir, promote_dir, nodes, args.promote))

    if args.promote:
        if not promote_dir:
            raise ValueError("--promote requires --promote-dir")
        manifest = build_manifest(drama_id, context_pack, moment_collection, out_dir, promote_dir)
        assert_no_media_dependencies(context_pack)
        assert_no_media_dependencies(moment_collection)
        assert_no_media_dependencies(manifest)
        write_json(promote_dir / "context.v0.1.json", context_pack)
        write_json(promote_dir / "moments.v0.1.json", moment_collection)
        write_json(promote_dir / "manifest.v0.1.json", manifest)

    print(f"Wrote {repo_relative(draft_path)}")
    print(f"Wrote {repo_relative(evidence_path)}")
    print(f"Wrote {repo_relative(run_report_path)}")
    if args.promote and promote_dir:
        print(f"Promoted runtime data to {repo_relative(promote_dir)}")


if __name__ == "__main__":
    main()
