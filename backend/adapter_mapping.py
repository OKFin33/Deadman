"""Fail-closed mapper from promoted v0.1 moments to adapter-ready v0.3 input."""

from __future__ import annotations

from typing import Any

from .models import JudgmentRequest
from .pack_store import DramaPack


MAPPING_VERSION = "deadman_backend_adapter_mapping.v0.1"
SOURCE_SCHEMA_VERSION = "moment_causality_pack.v0.1"
TARGET_SCHEMA_VERSION = "moment_causality_pack.v0.3.draft"
LOCAL_TIME_HORIZON = "current_scene_or_immediate_aftermath"
BLOCKED_BRANCH_CLAIMS = [
    "future episodes follow this branch",
    "canon was wrong",
    "the branch continues automatically",
]
VISUAL_NEGATIVE_CONSTRAINTS = [
    "do not present generated images as evidence",
    "do not imply later episodes follow this branch",
]


class AdapterMappingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_adapter_input(
    *,
    request_id: str,
    drama_pack: DramaPack,
    moment: dict[str, Any],
    request: JudgmentRequest,
) -> dict[str, Any]:
    """Build the future adapter input without changing deterministic judgment."""

    warnings: list[str] = []
    moment_pack = build_typed_moment_pack(
        drama_pack=drama_pack,
        moment=moment,
        mapping_warnings=warnings,
    )
    action_space = _require_dict(moment.get("action_space"), "action_space")
    candidate = _candidate_for_action(moment, request) if request.action.source == "preset_candidate" else None
    candidate_payload = _dict_or_empty(candidate.get("action_payload")) if candidate is not None else {}
    action_type = _required_string(
        candidate_payload.get("action_type") or action_space.get("action_type"),
        "action_space.action_type",
    )
    action_text = _required_string(
        candidate_payload.get("text") or request.action.text,
        "user_action.text",
    )
    preset_id: str | None = None
    if request.action.source == "preset_candidate":
        preset_id = _required_string(request.action.candidate_id, "action.candidate_id")
    elif request.action.source == "preset":
        if request.action.option_index is None:
            raise AdapterMappingError("adapter_mapping_invalid_action", "Preset adapter input requires action.option_index.")
        preset_id = f"preset_{request.action.option_index}"

    visual_result = "preset_slot" if request.action.source in {"preset", "preset_candidate"} else "plan_only"
    adapter_input: dict[str, Any] = {
        "request_id": request_id,
        "drama_id": drama_pack.drama_id,
        "moment_pack": moment_pack,
        "user_action": {
            "origin": "preset" if request.action.source == "preset_candidate" else request.action.source,
            "source": request.action.source,
            "action_type": action_type,
            "text": action_text,
            "display_text": request.action.text,
            "preset_id": preset_id,
            "candidate_id": request.action.candidate_id,
            "action_payload": candidate_payload if candidate_payload else request.action.action_payload,
            "emotion_role": str(candidate.get("emotion_role") or "") if candidate is not None else "",
            "semantic_role": str(candidate.get("semantic_role") or "") if candidate is not None else "",
        },
        "runtime_policy": {
            "time_horizon": LOCAL_TIME_HORIZON,
            "allow_future_branch_claims": False,
            "allow_visual_as_proof": False,
            "output_language": "zh-CN",
            "hide_producer_only_fields_from_prompt": True,
        },
        "requested_output": {
            "text_result": True,
            "visual_result": visual_result,
        },
        "debug": {
            "mapping_version": MAPPING_VERSION,
            "source_schema_version": SOURCE_SCHEMA_VERSION,
            "mapping_warnings": warnings,
            "score_axes": _dict_or_empty(moment.get("score_axes")),
        },
    }
    validate_adapter_input(adapter_input)
    _assert_score_axes_isolated(adapter_input)
    return adapter_input


def build_typed_moment_pack(
    *,
    drama_pack: DramaPack,
    moment: dict[str, Any],
    mapping_warnings: list[str] | None = None,
) -> dict[str, Any]:
    warnings = mapping_warnings if mapping_warnings is not None else []
    pack_id = _required_string(moment.get("moment_id") or moment.get("pack_id"), "moment_id or pack_id")
    source_drama = _dict_or_empty(moment.get("source_drama"))
    source_window = _require_dict(moment.get("source_window"), "source_window")
    start_ms = _required_int(source_window.get("start_ms"), "source_window.start_ms")
    end_ms = _required_int(source_window.get("end_ms"), "source_window.end_ms")
    if end_ms <= start_ms:
        raise AdapterMappingError("adapter_mapping_invalid", "source_window.end_ms must be greater than start_ms.")

    action_space = _map_action_space(moment)
    response_contract = _map_response_contract(moment)
    actor_local_state = _map_actor_local_state(moment, warnings)
    optional_modules = _dict_or_empty(moment.get("optional_modules"))
    actor_context = _dict_or_empty(moment.get("actor_context"))
    local_constraints = _dict_or_empty(moment.get("local_constraints"))
    canon_baseline = _dict_or_empty(moment.get("canon_baseline"))
    if not (optional_modules or actor_context or local_constraints or canon_baseline):
        raise AdapterMappingError(
            "adapter_mapping_missing_stakes",
            "No module, actor context, canon baseline, or local constraint can ground critical stakes.",
        )

    typed_pack: dict[str, Any] = {
        "pack_id": pack_id,
        "schema_version": TARGET_SCHEMA_VERSION,
        "source_window": {
            "drama_id": str(moment.get("drama_id") or source_drama.get("drama_id") or drama_pack.drama_id),
            "episode_id": _required_string(source_drama.get("episode_id"), "source_drama.episode_id"),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "interaction_window": _dict_or_empty(moment.get("interaction_window")),
            "source_refs": _source_ref_list(source_window),
        },
        "review_and_provenance": _map_review_and_provenance(moment, source_window),
        "companion_entry": _map_companion_entry(moment),
        "action_space": action_space,
        "response_contract": response_contract,
        "visual_result_policy": _map_visual_result_policy(moment),
        "actor_local_state": actor_local_state,
        "critical_stakes_state": _map_critical_stakes_state(moment, drama_pack),
        "local_constraint_state": _map_local_constraint_state(moment, drama_pack),
        "escalation_risk": _map_escalation_risk(moment, drama_pack),
        "canon_baseline": _map_canon_baseline(moment),
        "watch_flow_rationale": _map_watch_flow_rationale(moment),
        "optional_modules": _map_optional_modules(moment),
        "producer_only": {
            "score_axes": _dict_or_empty(moment.get("score_axes")),
            "field_demand_trace": _field_demand_trace(moment),
        },
    }
    validate_typed_moment_pack(typed_pack)
    return typed_pack


def validate_adapter_input(adapter_input: dict[str, Any]) -> None:
    _require_keys(adapter_input, ["request_id", "drama_id", "moment_pack", "user_action", "runtime_policy", "requested_output"])
    validate_typed_moment_pack(_require_dict(adapter_input["moment_pack"], "moment_pack"))
    user_action = _require_dict(adapter_input["user_action"], "user_action")
    _require_keys(user_action, ["origin", "action_type", "text", "preset_id"])
    if user_action["origin"] not in {"preset", "custom"}:
        raise AdapterMappingError("adapter_mapping_invalid", "user_action.origin must be preset or custom.")
    runtime_policy = _require_dict(adapter_input["runtime_policy"], "runtime_policy")
    expected_policy = {
        "time_horizon": LOCAL_TIME_HORIZON,
        "allow_future_branch_claims": False,
        "allow_visual_as_proof": False,
        "output_language": "zh-CN",
        "hide_producer_only_fields_from_prompt": True,
    }
    for key, expected in expected_policy.items():
        if runtime_policy.get(key) != expected:
            raise AdapterMappingError("adapter_mapping_invalid", f"runtime_policy.{key} must be {expected!r}.")
    requested_output = _require_dict(adapter_input["requested_output"], "requested_output")
    if requested_output.get("text_result") is not True:
        raise AdapterMappingError("adapter_mapping_invalid", "requested_output.text_result must be true.")
    if requested_output.get("visual_result") not in {"preset_slot", "plan_only", "none"}:
        raise AdapterMappingError("adapter_mapping_invalid", "requested_output.visual_result has an unsupported value.")


def validate_typed_moment_pack(moment_pack: dict[str, Any]) -> None:
    _require_keys(
        moment_pack,
        [
            "pack_id",
            "schema_version",
            "source_window",
            "review_and_provenance",
            "companion_entry",
            "action_space",
            "response_contract",
            "visual_result_policy",
            "actor_local_state",
            "critical_stakes_state",
            "local_constraint_state",
            "escalation_risk",
            "canon_baseline",
            "watch_flow_rationale",
        ],
    )
    if moment_pack["schema_version"] != TARGET_SCHEMA_VERSION:
        raise AdapterMappingError("adapter_mapping_invalid", "moment_pack.schema_version is not the v0.3 draft contract.")
    _require_keys(_require_dict(moment_pack["source_window"], "source_window"), ["drama_id", "episode_id", "start_ms", "end_ms"])
    _require_keys(
        _require_dict(moment_pack["critical_stakes_state"], "critical_stakes_state"),
        ["stake_type", "stake_owner", "time_pressure", "scarcity_or_risk_level", "irreversibility", "risk_if_action", "risk_if_no_action"],
    )
    _require_keys(
        _require_dict(moment_pack["escalation_risk"], "escalation_risk"),
        ["risk_type", "risk_source", "immediacy", "severity", "mitigation", "who_can_escalate"],
    )
    watch_flow = _require_dict(moment_pack["watch_flow_rationale"], "watch_flow_rationale")
    _require_keys(watch_flow, ["why_original_still_works", "viewer_return_line", "must_not_claim"])
    for claim in BLOCKED_BRANCH_CLAIMS:
        if claim not in watch_flow.get("must_not_claim", []):
            raise AdapterMappingError("adapter_mapping_invalid", f"watch_flow_rationale.must_not_claim must include {claim!r}.")
    response_contract = _require_dict(moment_pack["response_contract"], "response_contract")
    if response_contract.get("time_horizon") != LOCAL_TIME_HORIZON:
        raise AdapterMappingError("adapter_mapping_invalid", "response_contract.time_horizon must stay local.")
    if response_contract.get("allow_future_branch_claims") is not False or response_contract.get("allow_canon_wrong_claims") is not False:
        raise AdapterMappingError("adapter_mapping_invalid", "response_contract must block future-branch and canon-wrong claims.")
    visual_policy = _require_dict(moment_pack["visual_result_policy"], "visual_result_policy")
    _require_keys(visual_policy, ["provider_policy", "visual_prompt_plan", "must_not_be_used_as_proof", "proof_eligibility"])
    if visual_policy.get("provider_policy") != "not_connected":
        raise AdapterMappingError("adapter_mapping_invalid", "visual_result_policy.provider_policy must be not_connected.")
    if visual_policy.get("must_not_be_used_as_proof") is not True or visual_policy.get("proof_eligibility") != "never":
        raise AdapterMappingError("adapter_mapping_invalid", "visual_result_policy must block visual proof.")
    prompt_plan = _require_dict(visual_policy["visual_prompt_plan"], "visual_result_policy.visual_prompt_plan")
    if prompt_plan.get("provider_policy") != "not_connected":
        raise AdapterMappingError("adapter_mapping_invalid", "visual_prompt_plan.provider_policy must be not_connected.")


def _map_review_and_provenance(moment: dict[str, Any], source_window: dict[str, Any]) -> dict[str, Any]:
    producer_review = _dict_or_empty(moment.get("producer_review_fields"))
    return _publish_safe_refs(
        {
            "review_state": _dict_or_empty(moment.get("review_state")),
            "provenance": _dict_or_empty(moment.get("provenance")),
            "source_refs": _dict_or_empty(moment.get("source_refs")),
            "field_evidence_refs": _as_string_list(producer_review.get("field_evidence_refs", [])),
            "transcript_refs": source_window.get("transcript_refs", []),
            "keyframe_refs": source_window.get("keyframe_refs", []),
        }
    )


def _source_ref_list(source_window: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for ref_type, key in (("transcript", "transcript_refs"), ("keyframe", "keyframe_refs")):
        for item in _as_list(source_window.get(key, [])):
            if isinstance(item, dict):
                refs.append({"ref_type": ref_type, **item})
    contact_sheet = source_window.get("contact_sheet_ref")
    if isinstance(contact_sheet, dict):
        refs.append({"ref_type": "contact_sheet", **contact_sheet})
    safe_refs = _publish_safe_refs(refs)
    return [item for item in safe_refs if isinstance(item, dict)]


def _field_demand_trace(moment: dict[str, Any]) -> list[dict[str, str]]:
    producer_review = _dict_or_empty(moment.get("producer_review_fields"))
    return [
        {"field_ref": item}
        for item in _as_string_list(producer_review.get("field_evidence_refs", []))
    ]


def _evidence_ref_list(source_refs: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    reviewed = source_refs.get("reviewed_demo_node")
    if isinstance(reviewed, str) and reviewed:
        refs.append({"ref_type": "reviewed_demo_node", "id": reviewed})
    for ref_type, key in (("transcript", "transcript_snippets"), ("keyframe", "keyframe_refs")):
        for item in _as_list(source_refs.get(key, [])):
            if isinstance(item, dict):
                refs.append({"ref_type": ref_type, **item})
    contact_sheet = source_refs.get("contact_sheet_ref")
    if isinstance(contact_sheet, dict):
        refs.append({"ref_type": "contact_sheet", **contact_sheet})
    safe_refs = _publish_safe_refs(refs)
    return [item for item in safe_refs if isinstance(item, dict)]


def _map_companion_entry(moment: dict[str, Any]) -> dict[str, Any]:
    companion = _dict_or_empty(moment.get("companion_surface"))
    exchange = _dict_or_empty(moment.get("companion_exchange"))
    return {
        "notice_marker": str(companion.get("notice_marker") or ""),
        "hook": str(companion.get("hook") or ""),
        "scene_signal": str(exchange.get("scene_signal") or companion.get("hook") or ""),
        "companion_lead": str(exchange.get("companion_lead") or companion.get("companion_lead") or ""),
        "viewer_impulse": str(companion.get("viewer_impulse") or ""),
        "interaction_window": _dict_or_empty(moment.get("interaction_window")),
    }


def _map_action_space(moment: dict[str, Any]) -> dict[str, Any]:
    source = _require_dict(moment.get("action_space"), "action_space")
    default_options = _as_string_list(source.get("default_options", []))
    if not default_options:
        raise AdapterMappingError("adapter_mapping_invalid", "Preset moment has no action_space.default_options.")
    mouthpiece_candidates = _reply_candidates(moment, source)
    return {
        "action_type": _required_string(source.get("action_type"), "action_space.action_type"),
        "default_options": default_options,
        "mouthpiece_candidates_schema_version": str(source.get("mouthpiece_candidates_schema_version") or ("mouthpiece_candidates.v0.1" if mouthpiece_candidates else "")),
        "mouthpiece_candidates": mouthpiece_candidates,
        "preset_options": _preset_options(default_options, mouthpiece_candidates),
        "custom_action_policy": _dict_or_empty(source.get("custom_action_policy")),
    }


def _preset_options(default_options: list[str], mouthpiece_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for index, text in enumerate(default_options):
        candidate = mouthpiece_candidates[index] if index < len(mouthpiece_candidates) else {}
        options.append(
            {
                "preset_id": str(candidate.get("candidate_id") or f"preset_{index}"),
                "option_index": index,
                "text": str(candidate.get("display_text") or text),
                "action_payload": _dict_or_empty(candidate.get("action_payload")),
            }
        )
    return options


def _candidate_for_action(moment: dict[str, Any], request: JudgmentRequest) -> dict[str, Any] | None:
    candidate_id = str(request.action.candidate_id or "").strip()
    if not candidate_id:
        raise AdapterMappingError("adapter_mapping_invalid_action", "Preset candidate adapter input requires action.candidate_id.")
    source = _require_dict(moment.get("action_space"), "action_space")
    for candidate in _reply_candidates(moment, source):
        if str(candidate.get("candidate_id") or "") == candidate_id:
            display_text = str(candidate.get("display_text") or "").strip()
            if display_text and request.action.text.strip() != display_text:
                raise AdapterMappingError("adapter_mapping_invalid_action", "Preset candidate action.text must match display_text.")
            expected_payload = _dict_or_empty(candidate.get("action_payload"))
            if expected_payload and request.action.action_payload != expected_payload:
                raise AdapterMappingError("adapter_mapping_invalid_action", "Preset candidate action_payload must match the reviewed payload.")
            return candidate
    raise AdapterMappingError("adapter_mapping_invalid_action", f"Preset candidate_id {candidate_id!r} is not in companion_exchange.reply_candidates.")


def _reply_candidates(moment: dict[str, Any], action_space: dict[str, Any]) -> list[dict[str, Any]]:
    exchange = moment.get("companion_exchange")
    if isinstance(exchange, dict) and isinstance(exchange.get("reply_candidates"), list):
        return [item for item in exchange["reply_candidates"] if isinstance(item, dict)]
    return _mouthpiece_candidates(action_space)


def _mouthpiece_candidates(action_space: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = action_space.get("mouthpiece_candidates")
    if not isinstance(candidates, list):
        return []
    safe_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        if isinstance(candidate, dict):
            safe_candidates.append(candidate)
    return safe_candidates


def _map_response_contract(moment: dict[str, Any]) -> dict[str, Any]:
    source = _dict_or_empty(moment.get("outcome_response_contract"))
    time_horizon = _normalize_time_horizon(source.get("time_horizon"))
    if time_horizon != LOCAL_TIME_HORIZON:
        raise AdapterMappingError("adapter_mapping_nonlocal_time_horizon", "Adapter mapping only supports current-scene local outcomes.")
    return {
        "time_horizon": LOCAL_TIME_HORIZON,
        "allow_future_branch_claims": False,
        "allow_canon_wrong_claims": False,
        "source_format": source.get("format"),
        "include_original_plot_note": bool(source.get("include_original_plot_note", True)),
    }


def _map_visual_result_policy(moment: dict[str, Any]) -> dict[str, Any]:
    result_media = _dict_or_empty(moment.get("result_media"))
    preset_slots = [slot for slot in _as_list(result_media.get("preset_options", [])) if isinstance(slot, dict)]
    result_media_mode = "preset_slot" if preset_slots else "text_only"
    fallback = "placeholder_slot" if preset_slots else "text_only"
    if result_media_mode == "preset_slot" and not preset_slots:
        raise AdapterMappingError("adapter_mapping_visual_policy_invalid", "visual_result_policy cannot identify a preset slot.")
    return {
        "result_media_mode": result_media_mode,
        "truth_level": "illustrative_result",
        "proof_eligibility": "never",
        "must_not_be_used_as_proof": True,
        "fallback": fallback,
        "latency_budget_ms": 0,
        "provider_policy": "not_connected",
        "preset_slot_ids": [f"preset_{slot.get('option_index')}" for slot in preset_slots if slot.get("option_index") is not None],
        "visual_prompt_plan": {
            "prompt_source": "preset" if preset_slots else "none",
            "prompt_text": "",
            "negative_constraints": VISUAL_NEGATIVE_CONSTRAINTS,
            "style_policy": "short_drama_result_card" if preset_slots else "none",
            "provider_policy": "not_connected",
        },
    }


def _map_actor_local_state(moment: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    actor = _dict_or_empty(moment.get("actor_context"))
    pov_actor = str(actor.get("pov_actor") or "").strip()
    if not pov_actor:
        pov_actor = "主角"
        warnings.append("actor_context.pov_actor missing; defaulted to 主角.")
    return {
        "pov_actor": pov_actor,
        "directly_affected_actors": _as_string_list(actor.get("directly_affected_actors", [])),
        "relationship_context": str(actor.get("relationship_context") or ""),
        "local_emotional_pressure": str(actor.get("local_emotional_pressure") or ""),
    }


def _map_critical_stakes_state(moment: dict[str, Any], drama_pack: DramaPack) -> dict[str, Any]:
    modules = _dict_or_empty(moment.get("optional_modules"))
    actor = _dict_or_empty(moment.get("actor_context"))
    local = _dict_or_empty(moment.get("local_constraints"))
    canon = _dict_or_empty(moment.get("canon_baseline"))
    if not (modules or actor or local or canon):
        raise AdapterMappingError(
            "adapter_mapping_missing_stakes",
            "critical_stakes_state has no grounded source material.",
        )

    directly_affected = _as_string_list(actor.get("directly_affected_actors", []))
    stake_owner = directly_affected[0] if directly_affected else str(actor.get("pov_actor") or "主角")
    risk_notes = _as_string_list(local.get("risk_notes", []))
    risk_if_action = risk_notes[0] if risk_notes else str(canon.get("original_rationale") or "Action may create local explanation pressure.")
    risk_if_no_action = str(actor.get("local_emotional_pressure") or canon.get("audience_tension") or "Doing nothing preserves the current harm or pressure.")

    if "resource_scarcity" in modules:
        resource = _dict_or_empty(modules["resource_scarcity"])
        return {
            "stake_type": "resource",
            "stake_owner": str(resource.get("distribution_target") or stake_owner),
            "time_pressure": "immediate",
            "scarcity_or_risk_level": _risk_level(resource.get("scarcity_level")),
            "irreversibility": "costly",
            "risk_if_action": risk_if_action,
            "risk_if_no_action": str(resource.get("defer_cost") or risk_if_no_action),
        }
    if "system_or_hidden_power_rule" in modules:
        power = _dict_or_empty(modules["system_or_hidden_power_rule"])
        return {
            "stake_type": "power",
            "stake_owner": str(actor.get("pov_actor") or stake_owner),
            "time_pressure": "immediate",
            "scarcity_or_risk_level": "medium",
            "irreversibility": "unknown",
            "risk_if_action": str(power.get("power_cap") or risk_if_action),
            "risk_if_no_action": risk_if_no_action,
        }
    if "humiliation_reversal" in modules:
        humiliation = _dict_or_empty(modules["humiliation_reversal"])
        return {
            "stake_type": "status",
            "stake_owner": str(humiliation.get("protected_actor") or stake_owner),
            "time_pressure": "immediate",
            "scarcity_or_risk_level": "high",
            "irreversibility": "costly",
            "risk_if_action": str(humiliation.get("escalation_risk") or risk_if_action),
            "risk_if_no_action": str(humiliation.get("harm_state") or risk_if_no_action),
        }
    if "evidence_or_trap_logic" in modules or "village_or_public_reputation" in modules:
        evidence = _dict_or_empty(modules.get("evidence_or_trap_logic"))
        reputation = _dict_or_empty(modules.get("village_or_public_reputation"))
        return {
            "stake_type": "reputation",
            "stake_owner": stake_owner,
            "time_pressure": "immediate",
            "scarcity_or_risk_level": "medium",
            "irreversibility": "costly",
            "risk_if_action": str(reputation.get("escalation_risk") or evidence.get("counterparty_leverage") or risk_if_action),
            "risk_if_no_action": str(evidence.get("claim_account") or risk_if_no_action),
        }
    if "relationship_pressure" in modules:
        relationship = _dict_or_empty(modules["relationship_pressure"])
        return {
            "stake_type": "relationship",
            "stake_owner": stake_owner,
            "time_pressure": "immediate",
            "scarcity_or_risk_level": "medium",
            "irreversibility": "costly",
            "risk_if_action": risk_if_action,
            "risk_if_no_action": str(relationship.get("prior_trust_damage") or risk_if_no_action),
        }
    if "exposure_and_secrecy" in modules:
        exposure = _dict_or_empty(modules["exposure_and_secrecy"])
        return {
            "stake_type": "power",
            "stake_owner": str(actor.get("pov_actor") or stake_owner),
            "time_pressure": "immediate",
            "scarcity_or_risk_level": _risk_level(exposure.get("suspicion_risk")),
            "irreversibility": "unknown",
            "risk_if_action": str(exposure.get("source_explanation") or risk_if_action),
            "risk_if_no_action": risk_if_no_action,
        }
    return {
        "stake_type": "other",
        "stake_owner": stake_owner,
        "time_pressure": "unknown",
        "scarcity_or_risk_level": "unknown",
        "irreversibility": "unknown",
        "risk_if_action": risk_if_action,
        "risk_if_no_action": risk_if_no_action,
    }


def _map_local_constraint_state(moment: dict[str, Any], drama_pack: DramaPack) -> dict[str, Any]:
    local = _dict_or_empty(moment.get("local_constraints"))
    context = drama_pack.context
    return {
        "known_facts": _as_string_list(local.get("known_facts", [])),
        "unknown_or_hidden_facts": _as_string_list(local.get("unknown_or_hidden_facts", [])),
        "hard_constraints": _as_string_list(local.get("hard_constraints", [])),
        "risk_notes": _as_string_list(local.get("risk_notes", [])),
        "core_constraints": [
            {
                "id": str(item.get("id") or ""),
                "constraint": str(item.get("constraint") or ""),
                "confidence": str(item.get("confidence") or ""),
            }
            for item in _as_list(context.get("core_constraints", []))
            if isinstance(item, dict)
        ],
        "judgment_guardrails": _dict_or_empty(context.get("judgment_guardrails")),
    }


def _map_escalation_risk(moment: dict[str, Any], drama_pack: DramaPack) -> dict[str, Any]:
    modules = _dict_or_empty(moment.get("optional_modules"))
    actor = _dict_or_empty(moment.get("actor_context"))
    local = _dict_or_empty(moment.get("local_constraints"))
    affected = _as_string_list(actor.get("directly_affected_actors", []))
    risk_notes = _as_string_list(local.get("risk_notes", []))
    risk_source = risk_notes[0] if risk_notes else "local scene pressure"
    who_can_escalate = affected[1:] or affected or [str(actor.get("pov_actor") or "主角")]
    risk_type = "other"
    severity = "medium"
    mitigation = "Keep the result local and explainable within current scene evidence."

    if "exposure_and_secrecy" in modules or "system_or_hidden_power_rule" in modules:
        exposure = _dict_or_empty(modules.get("exposure_and_secrecy"))
        power = _dict_or_empty(modules.get("system_or_hidden_power_rule"))
        risk_type = "capability_exposure"
        risk_source = str(exposure.get("witness_scope") or power.get("rule_visibility") or risk_source)
        severity = _severity(exposure.get("suspicion_risk"), default="high" if exposure else "medium")
        mitigation = str(exposure.get("concealment_strategy") or power.get("world_explanation") or mitigation)
    elif "village_or_public_reputation" in modules:
        reputation = _dict_or_empty(modules["village_or_public_reputation"])
        risk_type = "social"
        risk_source = str(reputation.get("witnesses") or risk_source)
        severity = "high"
        mitigation = str(reputation.get("reputation_delta") or mitigation)
    elif "humiliation_reversal" in modules:
        humiliation = _dict_or_empty(modules["humiliation_reversal"])
        risk_type = "relationship"
        risk_source = str(humiliation.get("harm_state") or risk_source)
        severity = "medium"
        mitigation = str(humiliation.get("dignity_repair") or mitigation)
    elif "resource_scarcity" in modules:
        resource = _dict_or_empty(modules["resource_scarcity"])
        risk_type = "resource"
        risk_source = str(resource.get("resource_type") or risk_source)
        severity = _severity(resource.get("scarcity_level"), default="medium")
        mitigation = str(resource.get("defer_cost") or mitigation)
    elif "evidence_or_trap_logic" in modules:
        evidence = _dict_or_empty(modules["evidence_or_trap_logic"])
        risk_type = "social"
        risk_source = str(evidence.get("claim_account") or risk_source)
        severity = "medium"
        mitigation = str(evidence.get("counter_claim_shape") or mitigation)
    elif drama_pack.context.get("core_constraints"):
        risk_type = "watch_flow"
        risk_source = "drama context guardrails"
        mitigation = "Do not claim later episodes follow the branch."

    return {
        "risk_type": risk_type,
        "risk_source": risk_source,
        "immediacy": "immediate",
        "severity": severity,
        "mitigation": mitigation,
        "who_can_escalate": who_can_escalate,
    }


def _map_canon_baseline(moment: dict[str, Any]) -> dict[str, Any]:
    canon = _dict_or_empty(moment.get("canon_baseline"))
    return {
        "original_action": str(canon.get("original_action") or ""),
        "original_rationale": str(canon.get("original_rationale") or ""),
        "audience_tension": str(canon.get("audience_tension") or ""),
        "original_plot_note": str(canon.get("original_plot_note") or moment.get("original_plot_note") or ""),
    }


def _map_watch_flow_rationale(moment: dict[str, Any]) -> dict[str, Any]:
    canon = _dict_or_empty(moment.get("canon_baseline"))
    policy = _dict_or_empty(moment.get("judgment_policy"))
    blocked_claims = list(BLOCKED_BRANCH_CLAIMS)
    for claim in _as_string_list(policy.get("must_not_claim", [])):
        if "later episodes" in claim or "branch" in claim or "canon" in claim:
            continue
    why_original = str(canon.get("original_plot_note") or canon.get("original_rationale") or "")
    if not why_original:
        raise AdapterMappingError("adapter_mapping_missing_watch_flow", "watch_flow_rationale cannot explain why original plot still works.")
    return {
        "why_original_still_works": why_original,
        "viewer_return_line": "这个结果只解释当前场景或紧接着的一小段后果，原剧后续仍按原剧情观看。",
        "must_not_claim": blocked_claims,
        "source_must_not_claim": _as_string_list(policy.get("must_not_claim", [])),
    }


def _map_optional_modules(moment: dict[str, Any]) -> dict[str, Any]:
    modules = _dict_or_empty(moment.get("optional_modules"))
    actor = _dict_or_empty(moment.get("actor_context"))
    source_refs = _dict_or_empty(moment.get("source_refs"))
    mapped: dict[str, Any] = {}
    if "relationship_pressure" in modules:
        rel = _dict_or_empty(modules["relationship_pressure"])
        role = str(rel.get("relationship_role") or actor.get("relationship_context") or "")
        mapped["relationship_state"] = {
            "relationship_type": _relationship_type(role),
            "trust_level": "low" if rel.get("prior_trust_damage") else "unknown",
            "dependency": "resource" if "resource" in role.lower() else "emotional",
            "protection_priority": str(rel.get("care_priority") or rel.get("trust_delta_policy") or ""),
        }
    if "system_or_hidden_power_rule" in modules or "exposure_and_secrecy" in modules:
        power = _dict_or_empty(modules.get("system_or_hidden_power_rule"))
        exposure = _dict_or_empty(modules.get("exposure_and_secrecy"))
        mapped["capability_rules"] = {
            "capability_type": "system" if power else "other",
            "hard_limit": str(power.get("power_cap") or "no unlimited power or public system explanation"),
            "activation_cost": str(power.get("cost_or_cooldown") or "unknown"),
            "visibility_cost": str(exposure.get("source_explanation") or power.get("rule_visibility") or "visibility creates local suspicion"),
            "known_to_actor": True,
            "known_to_others": False,
            "failure_mode_if_overused": str(power.get("power_cap") or exposure.get("suspicion_risk") or "watch-flow break"),
        }
    if "exposure_and_secrecy" in modules:
        exposure = _dict_or_empty(modules["exposure_and_secrecy"])
        mapped["information_asymmetry"] = {
            "hidden_fact": str(exposure.get("visible_advantage") or exposure.get("source_explanation") or "hidden resource source"),
            "who_knows": [str(actor.get("pov_actor") or "主角")],
            "who_does_not_know": [str(exposure.get("witness_scope") or "local witnesses")],
            "who_would_learn": [str(exposure.get("witness_scope") or "local witnesses")],
            "reveal_timing": "avoid",
            "leverage_change": "mixed",
            "cost_of_reveal": str(exposure.get("suspicion_risk") or exposure.get("source_explanation") or "local suspicion"),
        }
    if "evidence_or_trap_logic" in modules:
        evidence = _dict_or_empty(modules["evidence_or_trap_logic"])
        mapped["proof_state"] = {
            "proof_type": "witness",
            "available_now": True,
            "threshold": _proof_threshold(evidence.get("proof_threshold")),
            "holder": str(actor.get("pov_actor") or "主角"),
            "risk_if_claimed_without_proof": str(evidence.get("counterparty_leverage") or "public accusation can backfire"),
            "evidence_refs": _evidence_ref_list(source_refs),
        }
        mapped.setdefault(
            "information_asymmetry",
            {
                "hidden_fact": str(evidence.get("claim_account") or "claim needs proof"),
                "who_knows": [str(actor.get("pov_actor") or "主角")],
                "who_does_not_know": ["local witnesses"],
                "who_would_learn": ["local witnesses"],
                "reveal_timing": "now",
                "leverage_change": "mixed",
                "cost_of_reveal": str(evidence.get("counterparty_leverage") or "unsupported claim can backfire"),
            },
        )
    if "village_or_public_reputation" in modules or "humiliation_reversal" in modules:
        reputation = _dict_or_empty(modules.get("village_or_public_reputation"))
        humiliation = _dict_or_empty(modules.get("humiliation_reversal"))
        mapped["audience_reputation_state"] = {
            "audience_scope": _audience_scope(reputation.get("witnesses") or humiliation.get("harm_state")),
            "audience_alignment": "hostile" if reputation else "mixed",
            "status_at_stake": str(reputation.get("public_claim") or humiliation.get("harm_state") or "local dignity"),
            "humiliation_vector": str(humiliation.get("harm_state") or reputation.get("public_claim") or ""),
            "likely_reaction": str(reputation.get("reputation_delta") or humiliation.get("dignity_repair") or "local reaction changes only"),
        }
    return mapped


def _normalize_time_horizon(value: object) -> str:
    text = str(value or "").strip().replace("_", " ").lower()
    if text in {"current scene or immediate aftermath", "current scene", LOCAL_TIME_HORIZON.replace("_", " ")}:
        return LOCAL_TIME_HORIZON
    return text


def _risk_level(value: object) -> str:
    text = str(value or "").lower()
    if "high" in text or "高" in text:
        return "high"
    if "medium" in text or "中" in text:
        return "medium"
    if "low" in text or "低" in text:
        return "low"
    return "unknown"


def _severity(value: object, *, default: str) -> str:
    risk = _risk_level(value)
    if risk == "unknown":
        return default
    return risk


def _relationship_type(value: object) -> str:
    text = str(value or "").lower()
    if "daughter" in text or "mother" in text or "child" in text or "family" in text:
        return "family"
    if "village" in text:
        return "village"
    return "unknown"


def _audience_scope(value: object) -> str:
    text = str(value or "").lower()
    if "village" in text or "村" in text:
        return "village"
    if "public" in text or "围观" in text:
        return "public"
    if "family" in text or "家" in text:
        return "family"
    return "unknown"


def _proof_threshold(value: object) -> str:
    text = str(value or "").lower()
    if "legal" in text or "high" in text:
        return "high"
    if "medium" in text:
        return "medium"
    if "low" in text or "local" in text:
        return "low"
    return "unknown"


def _assert_score_axes_isolated(value: Any) -> None:
    allowed_paths = {
        ("moment_pack", "producer_only", "score_axes"),
        ("debug", "score_axes"),
    }
    leaks: list[str] = []

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                next_path = (*path, str(key))
                if key == "score_axes" and next_path not in allowed_paths:
                    leaks.append(".".join(next_path))
                walk(child, next_path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, (*path, str(index)))

    walk(value, ())
    if leaks:
        raise AdapterMappingError("adapter_mapping_score_axes_leak", f"score_axes leaked into viewer-facing fields: {', '.join(leaks)}")


def _publish_safe_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _publish_safe_refs(child)
            for key, child in value.items()
            if not _contains_tmp(child)
        }
    if isinstance(value, list):
        return [_publish_safe_refs(item) for item in value if not _contains_tmp(item)]
    return value


def _contains_tmp(value: Any) -> bool:
    if isinstance(value, str):
        return "tmp/" in value or value.startswith("tmp")
    if isinstance(value, dict):
        return any(_contains_tmp(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_tmp(item) for item in value)
    return False


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterMappingError("adapter_mapping_invalid", f"{field_name} must be an object.")
    return value


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value)]


def _required_string(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AdapterMappingError("adapter_mapping_invalid", f"{field_name} is required.")
    return text


def _required_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise AdapterMappingError("adapter_mapping_invalid", f"{field_name} is required.")
    return value


def _require_keys(value: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise AdapterMappingError("adapter_mapping_invalid", f"Missing required keys: {', '.join(missing)}.")
