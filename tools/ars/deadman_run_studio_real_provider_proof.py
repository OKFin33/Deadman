#!/usr/bin/env python3
"""Run the Deadman v0.41 Phase 2.6 real-provider Studio proof.

This runner consumes the validated Studio Guidance Dataset and writes a
sanitized proof report only. It does not promote runtime packs and does not
store raw provider prompts or responses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from tools.ars.deadman_producer_graph_llm import (
        ArkCandidateJudgeProvider,
        LlmProviderError,
        provider_metadata,
        safe_int,
    )
    from tools.ars.deadman_validate_studio_guidance_dataset import (
        DEFAULT_GUIDANCE_PATH,
        validate_studio_guidance_dataset,
    )
except ModuleNotFoundError:
    from .deadman_producer_graph_llm import (
        ArkCandidateJudgeProvider,
        LlmProviderError,
        provider_metadata,
        safe_int,
    )
    from .deadman_validate_studio_guidance_dataset import (
        DEFAULT_GUIDANCE_PATH,
        validate_studio_guidance_dataset,
    )


DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
REPORT_SCHEMA_PATH = REPO_ROOT / "data/schemas/studio_cab_real_provider_proof.v0.1.json"
SCHEMA_VERSION = "studio_cab_real_provider_proof.v0.1"
PRODUCT = "看剧搭子"

# v0.3 taste spec (do/don't patterns) — the SAME overlay the hero author consumes, now folded into the
# graph's authoring core so the formal pipeline authors with taste (owner 6/10: integrate hero -> graph).
_OVERLAY_V03_PATH = REPO_ROOT / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.3.json"


def _require_overlay(path):
    """Fail-CLOSED (P0-B): the graph authoring core must NOT silently author without the taste spec."""
    if not path.exists():
        raise FileNotFoundError(
            f"v0.3 taste overlay missing at {path} — graph authoring core is fail-closed and will not "
            "author without the taste spec (see docs/context/dataset-rebuild-v03-contract.md).")
    return json.loads(path.read_text(encoding="utf-8"))


_OVERLAY_V03 = _require_overlay(_OVERLAY_V03_PATH)


def _taste_patterns(layer: str):
    """-> (negative_patterns, positive_patterns) for a layer from the finalized v0.3 overlay."""
    neg = [{"pattern": n.get("pattern"), "severity": n.get("severity"),
            "illustrative_examples": n.get("illustrative_examples", [])}
           for n in _OVERLAY_V03.get("named_negatives", []) if n.get("layer") == layer]
    pos = [{"pattern": n.get("pattern"), "when": n.get("when"),
            "illustrative_examples": n.get("illustrative_examples", [])}
           for n in _OVERLAY_V03.get("named_positives", []) if n.get("layer") == layer]
    return neg, pos


def _scene_context_for_case(provider: Any, guidance: dict[str, Any], case: dict[str, Any]):
    """Build the layered scene context for a case via the shared context node (hero core).
    Bridges the guidance case -> (drama, episode, window) so the graph authors with the same
    knowledge-horizon context as the hero flow. Graceful: returns None on any miss."""
    import re
    try:
        item_id = str(case.get("item_id", ""))
        we = find_window_example(guidance, item_id) or {}
        epi = we.get("episode_id") or str(case.get("episode_id", ""))
        if not epi:
            return None
        drama = epi.split("_")[0]
        m = re.match(r"\s*(\d+):(\d+)\s*-\s*(\d+):(\d+)", str(we.get("time_range", "")))
        s, e = ((int(m.group(1)) * 60 + int(m.group(2))) * 1000,
                (int(m.group(3)) * 60 + int(m.group(4))) * 1000) if m else (0, 10000)
        from tools.ars.deadman_author_drama_heroes import build_scene_context
        return build_scene_context(provider, drama, epi, s, e, drama)
    except Exception:
        return None
DECISIVE_PASS_BUCKETS = {
    "expected_rejection_pass",
    "context_boundary_pass",
}
SUCCESS_BUCKETS = DECISIVE_PASS_BUCKETS | {
    "reviewable_without_major_rewrite",
    "repair_regression_pass",
}
SOFT_FAILURE_BUCKETS = {
    "reviewable_with_minor_repair",
    "needs_owner_taste_review",
}
HARD_FAILURE_BUCKETS = {
    "wrong_window",
    "wrong_lead_shape",
    "wrong_reply_shape",
    "wrong_echo_shape",
    "insufficient_context_detected",
    "unsupported_claim",
    "future_branch_claim",
    "rpg_or_action_menu_regression",
    "echo_paraphrases_display_text",
    "echo_formulaic_prefix_repetition",
    "echo_disconnected_from_display_text",
    "echo_too_long",
    "display_text_reused_from_rejected_round",
    "provider_or_schema_failure",
}
ALLOWED_FAILURE_BUCKETS = SUCCESS_BUCKETS | SOFT_FAILURE_BUCKETS | HARD_FAILURE_BUCKETS
# Owner-approved echoes sit at 21-31 chars; the prompt aims <=~30. This is a
# generous deterministic BACKSTOP that only catches egregious blowouts so prompt
# brevity stays the primary control (owner directive: prompt-first, det. backstop).
ECHO_MAX_CHARS_BACKSTOP = 45
QUESTION_MARKERS = ("?", "？", "要不要", "该不该", "你是不是", "是不是想", "你想说")
AFFIRMATION_PREFIXES = ("是啊", "对啊", "可不", "没错", "嗯嗯", "嗯", "对", "确实", "真的")
TEXT_NORMALIZE_STRIP = ",.!?，。！？　、；;:：~～—-"
ACTION_OR_META_MARKERS = (
    "选择",
    "立刻",
    "改写",
    "护住",
    "点出",
    "接住",
    "兜底",
    "方向",
    "语义",
    "情绪轴",
    "吐槽原主吃独食",
)
FUTURE_CLAIM_MARKERS = ("后面会", "之后会", "下一集", "结局", "最终会", "会后悔")


class StudioProofProvider(Protocol):
    name: str
    model: str
    mock_provider: bool

    def complete_case(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Return provider payload plus sanitized provider metadata."""


@dataclass(frozen=True)
class ArkStudioProofProvider:
    inner: ArkCandidateJudgeProvider
    name: str = "ark"
    mock_provider: bool = False

    @property
    def model(self) -> str:
        return self.inner.model

    @classmethod
    def from_env(cls) -> "ArkStudioProofProvider":
        return cls(inner=ArkCandidateJudgeProvider.from_env())

    def complete_case(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response_data = self.inner._call_chat_completions(prompt, schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = self.inner._parse_provider_payload(response_data)
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        return {
            "payload": payload,
            "provider": provider_metadata(self.name, self.model, False, latency_ms, usage),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guidance", default=str(DEFAULT_GUIDANCE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--created-at", default="")
    parser.add_argument("--case-limit", type=int, default=0)
    args = parser.parse_args()

    guidance_path = resolve_path(args.guidance)
    output_path = resolve_path(args.output)
    created_at = args.created_at or now_iso()
    guidance = read_json(guidance_path)
    guidance_errors = validate_studio_guidance_dataset(dataset=guidance, dataset_path=guidance_path)
    if guidance_errors:
        print("Studio guidance dataset is not valid; refusing Phase 2.6 proof.")
        for error in guidance_errors:
            print(f"- {error}")
        return 1

    try:
        provider = ArkStudioProofProvider.from_env()
    except LlmProviderError as exc:
        print(f"Phase 2.6 provider unavailable: {exc}")
        return 2

    report = build_real_provider_proof_report(
        guidance=guidance,
        guidance_path=guidance_path,
        provider=provider,
        created_at=created_at,
        case_limit=args.case_limit,
    )
    write_json(output_path, report)
    print(f"Wrote Studio real-provider proof: {repo_relative(output_path)}")
    return 0


def build_real_provider_proof_report(
    *,
    guidance: dict[str, Any],
    guidance_path: Path,
    provider: StudioProofProvider,
    created_at: str,
    case_limit: int = 0,
    planned_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_cases = list(planned_cases) if planned_cases is not None else list(guidance["real_provider_proof_plan"]["planned_cases"])
    if case_limit > 0:
        selected_cases = selected_cases[:case_limit]
    rejected_display_blacklist = build_rejected_display_text_blacklist(guidance)
    case_results: list[dict[str, Any]] = []
    for case in selected_cases:
        stage_a = run_case_stage_a(provider, guidance, case)
        combined = run_case_stage_b(provider, guidance, stage_a)
        case_results.append(
            case_result_from_combined(combined, case, rejected_display_blacklist)
        )

    return assemble_proof_report(
        selected_cases=selected_cases,
        case_results=case_results,
        guidance=guidance,
        guidance_path=guidance_path,
        provider_name=provider.name,
        provider_model=provider.model,
        provider_mock=bool(provider.mock_provider),
        created_at=created_at,
    )


def case_result_from_combined(
    combined: dict[str, Any],
    case: dict[str, Any],
    rejected_display_blacklist: set[str],
) -> dict[str, Any]:
    """Turn a stage-A+B combined result into a normalized case_result."""
    if not combined.get("ok"):
        return provider_failure_result(
            case,
            combined.get("prompt_hash", ""),
            combined.get("error_label", "ProviderError"),
        )
    return normalize_case_result(
        case=case,
        payload=combined["payload"],
        provider_meta=combined["meta"],
        prompt_hash=combined["prompt_hash"],
        rejected_display_text_blacklist=rejected_display_blacklist,
    )


def assemble_proof_report(
    *,
    selected_cases: list[dict[str, Any]],
    case_results: list[dict[str, Any]],
    guidance: dict[str, Any],
    guidance_path: Path,
    provider_name: str,
    provider_model: str,
    provider_mock: bool,
    created_at: str,
) -> dict[str, Any]:
    failure_buckets = summarize_failure_buckets(case_results)
    repair_candidates = build_repair_candidates(case_results)
    completed_count = sum(1 for result in case_results if result["provider_status"] == "completed")
    status = "completed" if all(set(result["failure_buckets"]) <= SUCCESS_BUCKETS for result in case_results) else "completed_with_failures"
    if not case_results:
        status = "provider_blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "created_at": created_at,
        "status": status,
        "claim_boundary": (
            "Phase 2.6 shadow proof only. Provider drafts are draft_not_owner_reviewed; "
            "no runtime pack promotion occurred."
        ),
        "provider_identity_redacted": {
            "provider": provider_name,
            # Redact a raw ARK endpoint id (ep-...) to the public model-family alias —
            # proof artifacts must never embed the real endpoint id (it lives only in .env).
            "model_alias": (
                "doubao-seed-2.0-lite"
                if (not provider_model or str(provider_model).lower().startswith("ep-"))
                else provider_model
            ),
            "mock_provider": bool(provider_mock),
        },
        "guidance_dataset_ref": {
            "path": repo_relative(guidance_path),
            "sha256": sha256_file(guidance_path),
            "schema_version": guidance["schema_version"],
            "created_at": guidance["created_at"],
        },
        "planned_case_count": len(selected_cases),
        "attempted_case_count": len(case_results),
        "completed_case_count": completed_count,
        "publication_decision": "no_runtime_promotion",
        "case_results": case_results,
        "failure_buckets": failure_buckets,
        "repair_candidates": repair_candidates,
    }


def run_case_stage_a(provider: Any, guidance: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Stage A authoring for one case: window + lead + viewer entries (no echo)."""
    prompt = build_stage_a_prompt(guidance, case)
    scene_context = _scene_context_for_case(provider, guidance, case)  # context node (graceful; None on miss)
    if scene_context:
        prompt["scene_context"] = scene_context
    prompt_hash = sha256_json(prompt)
    try:
        result = provider.complete_case(prompt, stage_a_output_schema())
        payload = result.get("payload") if isinstance(result, dict) else {}
        meta = result.get("provider") if isinstance(result, dict) else {}
        return {
            "case": case,
            "ok": True,
            "payload_a": payload if isinstance(payload, dict) else {},
            "meta": meta if isinstance(meta, dict) else {},
            "prompt_hash": prompt_hash,
            "scene_context": scene_context,  # reused by Stage B so context is built once per case
        }
    except Exception as exc:  # noqa: BLE001 - sanitized error label only
        return {
            "case": case,
            "ok": False,
            "error_label": type(exc).__name__,
            "prompt_hash": prompt_hash,
        }


def run_case_stage_b(provider: Any, guidance: dict[str, Any], stage_a: dict[str, Any]) -> dict[str, Any]:
    """Stage B authoring: one echo per viewer entry, then a combined payload.

    Echoes are generated sequentially so each call sees the echoes already
    written for sibling viewers and can avoid duplicate openings/content.
    """
    case = stage_a["case"]
    scene_context = stage_a.get("scene_context")  # reuse the context built once in Stage A
    if not stage_a.get("ok"):
        return stage_a
    payload_a = stage_a.get("payload_a", {})
    meta_a = stage_a.get("meta", {})
    prompt_hash = stage_a.get("prompt_hash", "")
    window_decision = normalize_window_decision(payload_a.get("window_decision"))
    companion_lead = str(payload_a.get("companion_lead") or "")
    viewer_entries = payload_a.get("reply_candidates")
    viewer_entries = [e for e in viewer_entries if isinstance(e, dict)] if isinstance(viewer_entries, list) else []

    total_usage = _usage_from_meta(meta_a)
    total_latency = safe_int(meta_a.get("latency_ms") if isinstance(meta_a, dict) else 0, default=0)
    combined_replies: list[dict[str, Any]] = []
    prior_echoes: list[str] = []

    if window_decision == "recommend_window":
        entries = viewer_entries[:3]
        display_texts = [str(entry.get("display_text") or "") for entry in entries]
        for idx, entry in enumerate(entries):
            siblings = [text for j, text in enumerate(display_texts) if j != idx]
            echo_prompt = build_stage_b_echo_prompt(
                guidance,
                case,
                companion_lead=companion_lead,
                target_reply=entry,
                sibling_display_texts=siblings,
                prior_echoes=list(prior_echoes),
            )
            if scene_context:
                echo_prompt["scene_context"] = scene_context
            echo = ""
            try:
                echo_result = provider.complete_case(echo_prompt, stage_b_output_schema())
                echo_payload = echo_result.get("payload") if isinstance(echo_result, dict) else {}
                echo_meta = echo_result.get("provider") if isinstance(echo_result, dict) else {}
                if isinstance(echo_payload, dict):
                    echo = str(echo_payload.get("selected_echo") or "")
                _add_usage(total_usage, _usage_from_meta(echo_meta if isinstance(echo_meta, dict) else {}))
                total_latency += safe_int((echo_meta or {}).get("latency_ms") if isinstance(echo_meta, dict) else 0, default=0)
            except Exception:  # noqa: BLE001 - missing echo surfaces as wrong_echo_shape downstream
                echo = ""
            prior_echoes.append(echo)
            combined_replies.append(
                {
                    "display_text": str(entry.get("display_text") or ""),
                    "emotion_role": str(entry.get("emotion_role") or ""),
                    "semantic_role": str(entry.get("semantic_role") or ""),
                    "viewer_motivation": str(entry.get("viewer_motivation") or ""),
                    "selected_echo": echo,
                }
            )

    combined_payload = {
        "case_id": case.get("case_id"),
        "window_decision": window_decision,
        "companion_lead": companion_lead,
        "reply_candidates": combined_replies,
        "failure_buckets": payload_a.get("failure_buckets") if isinstance(payload_a.get("failure_buckets"), list) else [],
        "rationale_summary": payload_a.get("rationale_summary") or "",
        "repair_notes": payload_a.get("repair_notes") if isinstance(payload_a.get("repair_notes"), list) else [],
    }
    combined_meta = {"latency_ms": total_latency, "token_usage": total_usage}
    return {"case": case, "ok": True, "payload": combined_payload, "meta": combined_meta, "prompt_hash": prompt_hash}


def _usage_from_meta(meta: dict[str, Any]) -> dict[str, int]:
    return normalize_token_usage(meta.get("token_usage") if isinstance(meta, dict) else {})


def _add_usage(acc: dict[str, int], add: dict[str, int]) -> None:
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        acc[key] = acc.get(key, 0) + add.get(key, 0)


def stage_a_output_schema() -> dict[str, Any]:
    return {
        "title": "Deadman Studio CAB Stage A Output",
        "type": "object",
        "required": [
            "case_id",
            "window_decision",
            "companion_lead",
            "reply_candidates",
            "failure_buckets",
            "rationale_summary",
            "repair_notes",
        ],
        "properties": {
            "case_id": {"type": "string"},
            "window_decision": {"type": "string"},
            "companion_lead": {"type": "string"},
            "reply_candidates": {"type": "array"},
            "failure_buckets": {"type": "array"},
            "rationale_summary": {"type": "string"},
            "repair_notes": {"type": "array"},
        },
    }


def stage_b_output_schema() -> dict[str, Any]:
    return {
        "title": "Deadman Studio CAB Stage B Echo Output",
        "type": "object",
        "required": ["case_id", "selected_echo", "echo_rationale"],
        "properties": {
            "case_id": {"type": "string"},
            "selected_echo": {"type": "string"},
            "echo_rationale": {"type": "string"},
        },
    }


TWO_LAYER_SEMANTICS = [
    "看剧搭子 has two distinct authoring layers. Do not collapse them.",
    "Layer 1 — display_text: the words the viewer themselves is about to say. The host surfaces what THIS viewer wants to blurt out while watching, grounded in the lead and the current scene. It is the viewer's voice, not a comment ABOUT the scene, not a question, not an instruction to the host. The three display_texts are three different viewer postures/emotional entry points into the same beat.",
    "Layer 2 — selected_echo: the host's reply to the specific viewer who just picked that display_text. It is not a second comment on the scene; it is what that particular viewer wants to hear back after saying their line. Model the viewer behind the display_text first (their posture/motivation), then answer THAT viewer.",
]


def build_stage_a_prompt(guidance: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Stage A: window decision + lead + three viewer-side entries with motivation.

    Stage A authors Layer 1 only (display_text + the modeled viewer behind it).
    It deliberately does NOT author selected_echo; that is Stage B's job so the
    host's reply is generated against one specific viewer at a time.
    """
    item_id = str(case["item_id"])
    window_example = find_window_example(guidance, item_id)
    context_card = find_context_card(guidance, item_id)
    lead_examples = examples_for_item(guidance["splits"]["lead_authoring"].get("examples", []), item_id)
    reply_examples = examples_for_item(guidance["splits"]["reply_authoring"].get("examples", []), item_id)
    rejected_leads = examples_for_item(guidance["splits"]["lead_authoring"].get("rejected_examples", []), item_id)
    rejected_replies = examples_for_item(guidance["splits"]["reply_authoring"].get("rejected_examples", []), item_id)
    return {
        "stage": "stage_a_window_lead_displays",
        "system_prompt": (
            "You are a Deadman Studio/CAB authoring unit for 看剧搭子, working the "
            "first of two layers. Return exactly one strict JSON object. Do not "
            "include prose. Drafts are for human review only. Do not predict future "
            "plot, expose mechanism, or turn replies into RPG actions. Do NOT author "
            "selected_echo in this stage."
        ),
        "task": "studio_cab_real_provider_proof.stage_a",
        "product": PRODUCT,
        "case": case,
        "source_window": window_example,
        "context_card": context_card,
        "lead_examples_for_item": lead_examples,
        "reply_examples_for_item": reply_examples,
        "rejected_lead_examples_for_item": rejected_leads,
        "rejected_reply_examples_for_item": rejected_replies,
        "negative_lead_patterns": _taste_patterns("companion_lead")[0],
        "positive_lead_patterns": _taste_patterns("companion_lead")[1],
        "negative_display_patterns": _taste_patterns("display_text")[0],
        "positive_display_patterns": _taste_patterns("display_text")[1],
        "two_layer_semantics": TWO_LAYER_SEMANTICS,
        "global_rules": [
            "For owner_gold_exchange_authoring: recommend the window and draft one companion_lead plus exactly three viewer-speech reply_candidates.",
            "For owner_reviewed_window_reject: reject the window or mark needs_context; leave companion_lead empty and reply_candidates an empty list. Do not draft a publishable exchange.",
            "For phase2_repair_regression: recommend the window only if appropriate, but avoid the named failure in expected_behavior.",
            "companion_lead is the host opening their mouth: one short friend-style line that surfaces the scene's tension/feeling and makes the viewer want to chime in. Not a question, not a UI prompt.",
            "Each display_text is the viewer's own about-to-say line (Layer 1). Write what the viewer wants to say, not a label or evaluation of the scene. The three display_texts must take three genuinely different viewer postures into the same beat.",
            "For each reply candidate also write viewer_motivation: one short phrase naming the posture/feeling of the viewer who would pick this exact display_text — i.e. why they would say it and what they are hoping to hear back. This is internal modeling, written plainly, and will drive Stage B.",
            "Do not reuse any display_text string that appears in the dataset's owner-reviewed rejected examples. If a prior round failed, re-author the display_text rather than holding it over.",
            "Avoid the v0.3 failure PATTERNS in negative_lead_patterns / negative_display_patterns — each names a failure SITUATION, not a verbatim string (severity hard = never; soft_preference = lean away). AIM FOR positive_lead_patterns / positive_display_patterns when the scene matches a pattern's situation.",
            "If scene_context is present, GROUND in its layered memory (l0_canon + l3_series_spine = story so far + l2_recent_events + prior_window_asr + whats_happening) and respect the KNOWLEDGE HORIZON — never reference or 'reveal' anything later than this window (no 原来如此/真相大白 with no real reveal). Refer to people by role/relationship/pronoun, NOT proper names (ASR mis-recognizes names).",
            "Every provider draft remains draft_not_owner_reviewed until owner review.",
        ],
        "output_contract": {
            "case_id": case["case_id"],
            "window_decision": "recommend_window|reject_window|needs_context|needs_owner_review",
            "companion_lead": "short friend-style lead, empty if rejecting",
            "reply_candidates": [
                {
                    "display_text": "viewer-speech preset (the viewer's own words)",
                    "emotion_role": "short role",
                    "semantic_role": "short role",
                    "viewer_motivation": "short phrase: who picks this and what they want to hear back",
                }
            ],
            "failure_buckets": sorted(HARD_FAILURE_BUCKETS),
            "rationale_summary": "short sanitized reason",
            "repair_notes": ["short notes for human review"],
        },
    }


def build_stage_b_echo_prompt(
    guidance: dict[str, Any],
    case: dict[str, Any],
    *,
    companion_lead: str,
    target_reply: dict[str, Any],
    sibling_display_texts: list[str],
    prior_echoes: list[str],
) -> dict[str, Any]:
    """Stage B: author one selected_echo for one specific viewer.

    The host replies to the single viewer who picked target_reply.display_text,
    grounded in their viewer_motivation, the lead, and the scene. Prior echoes
    are passed so this echo does not duplicate sibling openings or content.
    """
    item_id = str(case["item_id"])
    window_example = find_window_example(guidance, item_id)
    context_card = find_context_card(guidance, item_id)
    runtime_echo_examples = guidance["splits"]["selected_echo_direction"].get("runtime_reviewed_examples", [])[:3]
    rejected_echo_examples = [
        compact_dict(item)
        for item in guidance["splits"]["selected_echo_direction"].get("rejected_examples", [])
        if isinstance(item, dict)
    ]
    return {
        "stage": "stage_b_echo",
        "system_prompt": (
            "You are a Deadman Studio/CAB authoring unit for 看剧搭子, working the "
            "second layer. You reply, as the co-watching host, to ONE specific "
            "viewer who just said the given display_text. Return exactly one strict "
            "JSON object. Do not include prose. Do not predict future plot or expose "
            "mechanism."
        ),
        "task": "studio_cab_real_provider_proof.stage_b",
        "product": PRODUCT,
        "case_id": case["case_id"],
        "source_window": window_example,
        "context_card": context_card,
        "companion_lead": companion_lead,
        "this_viewer": {
            "display_text": str(target_reply.get("display_text") or ""),
            "emotion_role": str(target_reply.get("emotion_role") or ""),
            "semantic_role": str(target_reply.get("semantic_role") or ""),
            "viewer_motivation": str(target_reply.get("viewer_motivation") or ""),
        },
        "other_viewer_display_texts": sibling_display_texts,
        "echoes_already_written_this_case": prior_echoes,
        "two_layer_semantics": TWO_LAYER_SEMANTICS,
        "selected_echo_direction_examples": {
            "runtime_reviewed_style_examples": runtime_echo_examples,
            "owner_reviewed_rejected_echo_examples": rejected_echo_examples,
        },
        "negative_echo_patterns": _taste_patterns("echo")[0],
        "positive_echo_patterns": _taste_patterns("echo")[1],
        "echo_rules": [
            "Write selected_echo as the host replying to THIS viewer (the one who said this_viewer.display_text), not as a second comment on the scene.",
            "selected_echo must do two things: (a) acknowledge the specific point this viewer just made — answer the person, give them the 'yes I caught that' beat their viewer_motivation is hoping for; (b) extend it one notch with a concrete reason, scene detail, or related feeling that this particular viewer would want to hear.",
            "Do not merely paraphrase or restate the display_text (that reads as echo复述). Do not change topic into an independent statement that ignores this viewer (that reads as echo脱节). Owner has rejected both extremes.",
            "Do not open with the same affirmation prefix (是啊 / 对啊 / 嗯 / 对 / 可不 / 没错 / 确实) as any echo in echoes_already_written_this_case. Vary the opening or skip the affirmation when natural.",
            "Keep it short and spoken, like a friend on the couch turning to answer just this one person. Aim for about 30 Chinese characters or fewer (owner-reviewed echoes run ~21-31 chars). One breath, one beat — long echoes overshadow the viewer and create frontend display pressure.",
            "Avoid the v0.3 echo failure PATTERNS in negative_echo_patterns; AIM FOR positive_echo_patterns — catch the viewer then extend one notch the way the matching pattern's situation describes.",
            "If scene_context is present, ground the echo in its layered memory and respect the KNOWLEDGE HORIZON — don't 'reveal' or act surprised by something already established, and use roles/pronouns not proper names.",
        ],
        "output_contract": {
            "case_id": case["case_id"],
            "selected_echo": "short host reply to THIS viewer",
            "echo_rationale": "one short phrase on how it answers this viewer (not the scene)",
        },
    }


def find_window_example(guidance: dict[str, Any], item_id: str) -> dict[str, Any]:
    split = guidance["splits"]["window_selection"]
    for collection in ("gold_examples", "negative_examples"):
        for item in split.get(collection, []):
            if item.get("item_id") == item_id:
                return compact_dict(item)
    return {}


def find_context_card(guidance: dict[str, Any], item_id: str) -> dict[str, Any]:
    split = guidance["splits"]["context_card_requirements"]
    for collection in ("sufficient_examples", "context_insufficient_examples"):
        for item in split.get(collection, []):
            if item.get("item_id") == item_id:
                return compact_dict(item)
    return {}


def examples_for_item(examples: list[Any], item_id: str) -> list[dict[str, Any]]:
    return [compact_dict(item) for item in examples if isinstance(item, dict) and item.get("item_id") == item_id]


def compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    blocked = {"source_ref"}
    return {key: child for key, child in value.items() if key not in blocked}


def build_rejected_display_text_blacklist(guidance: dict[str, Any]) -> set[str]:
    """display_texts owner-rejected AS display_texts (off-taste viewer lines).

    Only reply_authoring.rejected_examples qualify: those are display_text-level
    rejections. selected_echo_direction.rejected_examples are echo-level failures
    whose attached display_text is incidental and must NOT be blacklisted —
    reusing a good display_text is fine; only resurrecting an off-taste viewer
    line is the regression this guards against.
    """
    blacklist: set[str] = set()
    splits = guidance.get("splits", {}) if isinstance(guidance, dict) else {}
    split = splits.get("reply_authoring", {})
    for example in split.get("rejected_examples", []) or []:
        if not isinstance(example, dict):
            continue
        text = example.get("display_text")
        if isinstance(text, str) and text.strip():
            blacklist.add(_normalize_for_echo_check(text))
    return blacklist


def normalize_case_result(
    *,
    case: dict[str, Any],
    payload: dict[str, Any],
    provider_meta: dict[str, Any],
    prompt_hash: str,
    rejected_display_text_blacklist: set[str] | None = None,
) -> dict[str, Any]:
    schema_errors = validate_provider_payload(payload)
    if schema_errors:
        return schema_invalid_result(case, prompt_hash, provider_meta, schema_errors)
    window_decision = normalize_window_decision(payload.get("window_decision"))
    reply_candidates = normalize_reply_candidates(payload.get("reply_candidates"))
    draft = {
        "companion_lead": truncate(str(payload.get("companion_lead") or ""), 160),
        "reply_candidates": reply_candidates,
    }
    buckets = evaluate_case_conformance(
        case=case,
        window_decision=window_decision,
        draft=draft,
        rejected_display_text_blacklist=rejected_display_text_blacklist,
    )
    decisive_pass = any(bucket in DECISIVE_PASS_BUCKETS for bucket in buckets)
    if not decisive_pass:
        provider_buckets = normalize_failure_buckets(payload.get("failure_buckets"))
        for bucket in provider_buckets:
            if bucket not in buckets:
                buckets.append(bucket)
        if any(bucket not in SUCCESS_BUCKETS for bucket in buckets):
            buckets = [bucket for bucket in buckets if bucket not in SUCCESS_BUCKETS]
        if not buckets:
            buckets = ["reviewable_without_major_rewrite"]
    conformance = "pass" if set(buckets) <= SUCCESS_BUCKETS else "fail"
    token_usage = normalize_token_usage(provider_meta.get("token_usage"))
    return {
        "case_id": str(case["case_id"]),
        "case_type": str(case["case_type"]),
        "item_id": str(case["item_id"]),
        "episode_id": str(case["episode_id"]),
        "provenance": str(case["provenance"]),
        "expected_behavior": str(case["expected_behavior"]),
        "provider_status": "completed",
        "provider_status_class": "success",
        "latency_bucket": latency_bucket(safe_int(provider_meta.get("latency_ms"), default=0)),
        "token_usage": token_usage,
        "schema_validation": "pass",
        "conformance_validation": conformance,
        "draft_review_status": "draft_not_owner_reviewed",
        "window_decision": window_decision,
        "failure_buckets": buckets,
        "draft": draft,
        "rationale_summary": truncate(str(payload.get("rationale_summary") or ""), 500),
        "repair_notes": [truncate(str(note), 220) for note in payload.get("repair_notes", []) if isinstance(note, str)][:5],
        "prompt_hash": prompt_hash,
    }


def validate_provider_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if normalize_window_decision(payload.get("window_decision")) == "not_available":
        errors.append("missing or invalid window_decision")
    if "reply_candidates" in payload and not isinstance(payload.get("reply_candidates"), list):
        errors.append("reply_candidates must be a list")
    if "failure_buckets" in payload and not isinstance(payload.get("failure_buckets"), list):
        errors.append("failure_buckets must be a list")
    if "repair_notes" in payload and not isinstance(payload.get("repair_notes"), list):
        errors.append("repair_notes must be a list")
    return errors


def schema_invalid_result(
    case: dict[str, Any],
    prompt_hash: str,
    provider_meta: dict[str, Any],
    schema_errors: list[str],
) -> dict[str, Any]:
    return base_failure_result(
        case=case,
        prompt_hash=prompt_hash,
        provider_status="schema_invalid",
        provider_status_class="schema_error",
        latency=latency_bucket(safe_int(provider_meta.get("latency_ms"), default=0)),
        token_usage=normalize_token_usage(provider_meta.get("token_usage")),
        rationale=f"Provider payload failed schema normalization: {'; '.join(schema_errors)[:300]}",
    )


def provider_failure_result(case: dict[str, Any], prompt_hash: str, error_label: str) -> dict[str, Any]:
    return base_failure_result(
        case=case,
        prompt_hash=prompt_hash,
        provider_status="provider_failed",
        provider_status_class="provider_error",
        latency="not_available",
        token_usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        rationale=truncate(f"Provider failed with sanitized error type {error_label}.", 400),
    )


def base_failure_result(
    *,
    case: dict[str, Any],
    prompt_hash: str,
    provider_status: str,
    provider_status_class: str,
    latency: str,
    token_usage: dict[str, int],
    rationale: str,
) -> dict[str, Any]:
    return {
        "case_id": str(case["case_id"]),
        "case_type": str(case["case_type"]),
        "item_id": str(case["item_id"]),
        "episode_id": str(case["episode_id"]),
        "provenance": str(case["provenance"]),
        "expected_behavior": str(case["expected_behavior"]),
        "provider_status": provider_status,
        "provider_status_class": provider_status_class,
        "latency_bucket": latency,
        "token_usage": token_usage,
        "schema_validation": "fail",
        "conformance_validation": "fail",
        "draft_review_status": "draft_not_owner_reviewed",
        "window_decision": "not_available",
        "failure_buckets": ["provider_or_schema_failure"],
        "draft": {"companion_lead": "", "reply_candidates": []},
        "rationale_summary": rationale,
        "repair_notes": ["Retry provider or inspect sanitized failure bucket before owner taste review."],
        "prompt_hash": prompt_hash,
    }


def evaluate_case_conformance(
    *,
    case: dict[str, Any],
    window_decision: str,
    draft: dict[str, Any],
    rejected_display_text_blacklist: set[str] | None = None,
) -> list[str]:
    buckets: list[str] = []
    case_type = str(case.get("case_type") or "")
    provenance = str(case.get("provenance") or "")
    expected_behavior = str(case.get("expected_behavior") or "")
    lead = str(draft.get("companion_lead") or "")
    replies = draft.get("reply_candidates") if isinstance(draft.get("reply_candidates"), list) else []
    blacklist = rejected_display_text_blacklist or set()
    if case_type == "owner_reviewed_window_reject":
        if window_decision not in {"reject_window", "needs_context"}:
            buckets.append("wrong_window")
        if replies or lead:
            buckets.append("needs_owner_taste_review")
        deduped = dedupe(buckets)
        if deduped:
            return deduped
        if provenance == "owner_context_insufficient" or window_decision == "needs_context":
            return ["context_boundary_pass"]
        return ["expected_rejection_pass"]
    if window_decision != "recommend_window":
        buckets.append("wrong_window" if window_decision != "needs_context" else "insufficient_context_detected")
    if not lead or is_question_shaped(lead):
        buckets.append("wrong_lead_shape")
    if len(replies) != 3:
        buckets.append("wrong_reply_shape")
    for reply in replies:
        text = str(reply.get("display_text") or "")
        echo = str(reply.get("selected_echo") or "")
        if not text or has_action_or_meta_marker(text):
            buckets.append("wrong_reply_shape")
        if not echo:
            buckets.append("wrong_echo_shape")
        if has_future_claim(text) or has_future_claim(echo) or has_future_claim(lead):
            buckets.append("future_branch_claim")
        if has_rpg_marker(text):
            buckets.append("rpg_or_action_menu_regression")
        if echo and text and echo_paraphrases_display_text(echo, text):
            buckets.append("echo_paraphrases_display_text")
        if echo and len(echo) > ECHO_MAX_CHARS_BACKSTOP:
            buckets.append("echo_too_long")
        if text and _normalize_for_echo_check(text) in blacklist:
            buckets.append("display_text_reused_from_rejected_round")
    echo_texts = [str(r.get("selected_echo") or "") for r in replies]
    if len(echo_texts) == 3 and echoes_share_affirmation_prefix(echo_texts):
        buckets.append("echo_formulaic_prefix_repetition")
    if "axis_label_no_viewer_voice" in expected_behavior:
        if any(has_action_or_meta_marker(str(reply.get("display_text") or "")) for reply in replies):
            buckets.append("wrong_reply_shape")
    if "question_shaped_lead_seed" in expected_behavior and is_question_shaped(lead):
        buckets.append("wrong_lead_shape")
    deduped = dedupe(buckets)
    if deduped:
        return deduped
    if case_type == "phase2_repair_regression":
        return ["repair_regression_pass"]
    return ["reviewable_without_major_rewrite"]


def normalize_window_decision(value: Any) -> str:
    decision = str(value or "")
    if decision in {"recommend_window", "reject_window", "needs_context", "needs_owner_review"}:
        return decision
    return "not_available"


def normalize_reply_candidates(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    replies: list[dict[str, str]] = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        replies.append(
            {
                "display_text": truncate(str(item.get("display_text") or ""), 80),
                "emotion_role": truncate(str(item.get("emotion_role") or ""), 80),
                "semantic_role": truncate(str(item.get("semantic_role") or ""), 80),
                "viewer_motivation": truncate(str(item.get("viewer_motivation") or ""), 160),
                "selected_echo": truncate(str(item.get("selected_echo") or ""), 160),
            }
        )
    return replies


def normalize_failure_buckets(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return dedupe(
        [
            str(item)
            for item in value
            if isinstance(item, str)
            and item in HARD_FAILURE_BUCKETS
            and item != "provider_or_schema_failure"
        ]
    )


def normalize_token_usage(value: Any) -> dict[str, int]:
    usage = value if isinstance(value, dict) else {}
    return {
        "input_tokens": safe_int(usage.get("input_tokens"), default=0),
        "output_tokens": safe_int(usage.get("output_tokens"), default=0),
        "total_tokens": safe_int(usage.get("total_tokens"), default=0),
    }


def latency_bucket(latency_ms: int) -> str:
    if latency_ms <= 0:
        return "not_available"
    if latency_ms < 5000:
        return "lt_5s"
    if latency_ms < 15000:
        return "lt_15s"
    if latency_ms < 30000:
        return "lt_30s"
    return "gte_30s"


def summarize_failure_buckets(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_bucket: dict[str, list[str]] = {}
    for result in case_results:
        for bucket in result.get("failure_buckets", []):
            by_bucket.setdefault(str(bucket), []).append(str(result["case_id"]))
    return [
        {"bucket": bucket, "count": len(case_ids), "case_ids": case_ids}
        for bucket, case_ids in sorted(by_bucket.items())
    ]


def build_repair_candidates(case_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    repairs: list[dict[str, str]] = []
    for result in case_results:
        for bucket in result.get("failure_buckets", []):
            if bucket in SUCCESS_BUCKETS:
                continue
            repairs.append(
                {
                    "repair_id": "real_provider_repair_" + hashlib.sha256(
                        f"{result['case_id']}:{bucket}".encode("utf-8")
                    ).hexdigest()[:12],
                    "case_id": str(result["case_id"]),
                    "item_id": str(result["item_id"]),
                    "episode_id": str(result["episode_id"]),
                    "failure_bucket": str(bucket),
                    "field": field_for_failure(str(bucket)),
                    "problem": repair_problem(str(bucket)),
                    "suggested_repair_seed": suggested_repair_seed(str(bucket), result),
                    "provenance": "real_provider_proof",
                }
            )
    return repairs


def field_for_failure(bucket: str) -> str:
    return {
        "wrong_window": "window_decision",
        "wrong_lead_shape": "companion_lead",
        "wrong_reply_shape": "reply_candidates",
        "wrong_echo_shape": "selected_echo",
        "future_branch_claim": "blocked_claims",
        "rpg_or_action_menu_regression": "reply_candidates",
        "insufficient_context_detected": "context_card",
        "provider_or_schema_failure": "provider_payload",
    }.get(bucket, "owner_review")


def repair_problem(bucket: str) -> str:
    return {
        "wrong_window": "Provider selected or rejected a window against the owner boundary.",
        "wrong_lead_shape": "Provider lead is missing, question-shaped, or not a compact friend lead.",
        "wrong_reply_shape": "Provider replies are missing, not viewer speech, or collapse into producer labels.",
        "wrong_echo_shape": "Provider selected_echo is missing or not a short companion response.",
        "future_branch_claim": "Provider output may depend on future plot or unsupported branch claims.",
        "rpg_or_action_menu_regression": "Provider output drifted into action-menu or RPG language.",
        "insufficient_context_detected": "Provider could not safely author from the provided context.",
        "provider_or_schema_failure": "Provider failed or returned a payload that could not be normalized.",
    }.get(bucket, "Provider output needs owner taste review.")


def suggested_repair_seed(bucket: str, result: dict[str, Any]) -> str:
    if bucket == "wrong_window":
        return "Recheck current-window owner decision before drafting visible copy."
    if bucket == "wrong_lead_shape":
        return "Rewrite as one scene-bound friend line, not a question or UI prompt."
    if bucket == "wrong_reply_shape":
        return "Rewrite presets as three short viewer-speech lines, not labels or actions."
    if bucket == "wrong_echo_shape":
        return "Add short selected_echo for each preset, grounded in the current scene."
    return str(result.get("rationale_summary") or "Route to repair review.")


def is_question_shaped(text: str) -> bool:
    return any(marker in text for marker in QUESTION_MARKERS)


def _normalize_for_echo_check(text: str) -> str:
    cleaned = "".join(ch for ch in (text or "") if ch not in TEXT_NORMALIZE_STRIP and not ch.isspace())
    return cleaned


def _strip_affirmation_prefix(text: str) -> str:
    cleaned = text
    while True:
        stripped = False
        for prefix in AFFIRMATION_PREFIXES:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                stripped = True
                break
        if not stripped:
            return cleaned


def echo_paraphrases_display_text(echo: str, display_text: str) -> bool:
    norm_echo = _strip_affirmation_prefix(_normalize_for_echo_check(echo))
    norm_dt = _normalize_for_echo_check(display_text)
    if not norm_echo or not norm_dt:
        return False
    if norm_echo.startswith(norm_dt):
        return True
    if norm_dt in norm_echo and len(norm_dt) / max(len(norm_echo), 1) >= 0.6:
        return True
    return False


def echoes_share_affirmation_prefix(echoes: list[str]) -> bool:
    if len(echoes) < 3:
        return False
    matched_prefixes: list[str] = []
    for echo in echoes:
        cleaned = (echo or "").lstrip()
        matched: str | None = None
        for prefix in AFFIRMATION_PREFIXES:
            if cleaned.startswith(prefix):
                matched = prefix
                break
        if matched is None:
            return False
        matched_prefixes.append(matched)
    return len(set(matched_prefixes)) == 1


def has_action_or_meta_marker(text: str) -> bool:
    return any(marker in text for marker in ACTION_OR_META_MARKERS)


def has_rpg_marker(text: str) -> bool:
    return any(marker in text for marker in ("选择", "立刻", "改写", "行动", "操作"))


def has_future_claim(text: str) -> bool:
    return any(marker in text for marker in FUTURE_CLAIM_MARKERS)


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def truncate(text: str, limit: int) -> str:
    return text[:limit]


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


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
