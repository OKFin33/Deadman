#!/usr/bin/env python3
"""Provider helpers for Deadman Studio producer graph LLM nodes."""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_ARK_TEMPERATURE = 0.0
DEFAULT_ARK_TIMEOUT_SECONDS = 120.0
DEFAULT_CANDIDATE_JUDGE_POOL_MAX = 240
DEFAULT_CANDIDATE_JUDGE_SEMANTIC_POOL_MAX = 120
DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MIN = 3
DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MAX = 60
DEFAULT_CANDIDATE_JUDGE_SHORTLIST_PER_SOURCE = 0.5
DEFAULT_CANDIDATE_JUDGE_SHORTLIST_POOL_RATIO = 0.10


class LlmProviderProtocol(Protocol):
    name: str
    model: str
    mock_provider: bool

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON-compatible object that must validate against schema."""


class LlmProviderError(RuntimeError):
    """Provider error with secrets removed from the message."""


@dataclass(frozen=True)
class MockCandidateJudgeProvider:
    name: str = "mock"
    model: str = "deadman-mock-candidate-judge-v0.1"
    mock_provider: bool = True

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        candidates = prompt.get("candidates") or []
        shortlist_limit = safe_int(prompt.get("shortlist_limit"), default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MIN)
        judgments = [
            self._judge_candidate(candidate)
            for candidate in candidates[:shortlist_limit]
            if isinstance(candidate, dict)
        ]
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "schema_version": "deadman_llm_candidate_judgment.v0.1",
            "task": "llm_candidate_judge",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": {
                "name": self.name,
                "model": self.model,
                "mock_provider": True,
                "latency_ms": latency_ms,
                "token_usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
            },
            "source_candidate_ref": prompt.get("source_candidate_ref", ""),
            "input_candidate_count": len([candidate for candidate in candidates if isinstance(candidate, dict)]),
            "shortlist_policy": prompt.get("selection_policy", {}),
            "judgment_count": len(judgments),
            "decisions_summary": summarize_decisions(judgments),
            "judgments": judgments,
        }

    def _judge_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        rank = safe_int(candidate.get("rank"), default=9999)
        score = safe_float(candidate.get("rank_score"), default=0.0)
        if rank <= 5 or score >= 85:
            decision = "recommend"
            confidence = 0.82
            failure_modes: list[str] = []
            rationale = "High deterministic rank and clear review pressure."
        elif rank <= 25 or score >= 60:
            decision = "keep_for_review"
            confidence = 0.68
            failure_modes = []
            rationale = "Plausible scene pressure, but human review should decide promotion."
        else:
            decision = "reject"
            confidence = 0.61
            failure_modes = ["low_rank_or_weak_scene_pressure"]
            rationale = "Weak deterministic rank for the current P0 promotion pass."

        return {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "decision": decision,
            "confidence": confidence,
            "rationale": rationale,
            "failure_modes": failure_modes,
            "source_refs": candidate.get("source_refs") or {},
        }


@dataclass(frozen=True)
class MockSemanticMinerProvider:
    name: str = "mock"
    model: str = "deadman-mock-semantic-miner-v0.1"
    mock_provider: bool = True

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        candidates = [candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]
        windows = [window for window in prompt.get("windows", []) if isinstance(window, dict)]
        semantic_candidates = [self._enrich_candidate(candidate) for candidate in candidates[:5]]
        if windows:
            discovered = self._discover_from_window(windows[0])
            if discovered["semantic_candidate_id"] not in {
                candidate["semantic_candidate_id"] for candidate in semantic_candidates
            }:
                semantic_candidates.append(discovered)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "schema_version": "deadman_llm_semantic_candidates.v0.1",
            "task": "llm_semantic_miner",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, True, latency_ms, {}),
            "source_refs": prompt.get("source_refs", {}),
            "candidate_count": len(semantic_candidates),
            "candidates": semantic_candidates,
        }

    def _enrich_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(candidate.get("candidate_id") or "")
        return {
            "semantic_candidate_id": f"{candidate_id}_sem",
            "origin": "deterministic_enriched",
            "linked_candidate_id": candidate_id,
            "episode_id": str(candidate.get("episode_id") or "unknown_episode"),
            "window_id": str(candidate.get("window_id") or "unknown_window"),
            "time_range_ms": [
                safe_int(candidate.get("start_ms"), default=0),
                safe_int(candidate.get("end_ms"), default=safe_int(candidate.get("start_ms"), default=0)),
            ],
            "hook": str(candidate.get("hook") or "这个节点适合二审。"),
            "viewer_impulse": str(candidate.get("viewer_impulse") or "要是我来，会想换一种做法。"),
            "intervention_logic": str(candidate.get("why_now") or candidate.get("evidence_excerpt") or "场景出现可行动压力。")[:500],
            "evidence_excerpt": str(candidate.get("evidence_excerpt") or "source evidence unavailable")[:500],
            "uncertainty": "medium",
            "confidence": min(0.9, max(0.35, safe_float(candidate.get("rank_score"), default=50.0) / 100)),
            "field_signals": [str(candidate.get("trigger_type") or "scene_pressure")],
            "suggested_options": [str(option) for option in candidate.get("default_options", []) if isinstance(option, str)][:3],
            "source_refs": candidate.get("source_refs") or {},
            "failure_modes": [],
        }

    def _discover_from_window(self, window: dict[str, Any]) -> dict[str, Any]:
        window_id = str(window.get("window_id") or "unknown_window")
        start_ms = safe_int(window.get("start_ms"), default=0)
        end_ms = safe_int(window.get("end_ms"), default=start_ms)
        excerpt = str(window.get("transcript_text") or "source window evidence unavailable")[:500]
        return {
            "semantic_candidate_id": f"{window_id}_llm001",
            "origin": "llm_discovered",
            "linked_candidate_id": "",
            "episode_id": str(window.get("episode_id") or "unknown_episode"),
            "window_id": window_id,
            "time_range_ms": [start_ms, end_ms],
            "hook": "这里可能有一个被规则漏掉的可互动点。",
            "viewer_impulse": "要是我来，会想在这一刻插手。",
            "intervention_logic": "Mock semantic pass marks one source window for human review only.",
            "evidence_excerpt": excerpt,
            "uncertainty": "high",
            "confidence": 0.42,
            "field_signals": ["llm_discovered_pressure"],
            "suggested_options": ["先按原剧情走", "试着温和介入", "直接改变眼前选择"],
            "source_refs": {"window_id": window_id},
            "failure_modes": ["mock_low_confidence"],
        }


@dataclass(frozen=True)
class MockDramaContextDraftProvider:
    name: str = "mock"
    model: str = "deadman-mock-drama-context-draft-v0.1"
    mock_provider: bool = True

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        reviewed_count = len([item for item in prompt.get("reviewed_candidates", []) if isinstance(item, dict)])
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "schema_version": "deadman_llm_drama_context_draft.v0.1",
            "task": "llm_drama_context_draft",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, True, latency_ms, {}),
            "source_refs": prompt.get("source_refs", {}),
            "context_draft": {
                "premise_draft": f"{prompt.get('drama_title', '')} producer draft from {reviewed_count} reviewed candidates.",
                "genre_contract_draft": "Survival pressure, relationship stakes, and source-bounded intervention remain primary.",
                "protagonist_draft": "Producer review should keep the protagonist as a constrained actor, not an omnipotent solver.",
                "core_constraints_draft": [
                    {
                        "field": "source_bounded_intervention",
                        "value": "Drafts may suggest interaction framing, but runtime truth still comes from reviewed packs.",
                        "confidence": 0.72,
                        "inference_level": "human_review_required",
                        "source_refs": prompt.get("source_refs", {}),
                    }
                ],
                "relationship_drafts": [
                    {
                        "field": "family_pressure",
                        "value": "Food, reputation, and protection choices should remain socially visible.",
                        "confidence": 0.68,
                        "inference_level": "model_inferred",
                        "source_refs": prompt.get("source_refs", {}),
                    }
                ],
                "guardrails": [
                    "Never publish this draft without human review.",
                    "Do not replace tracked context.v0.1.json directly.",
                ],
                "open_questions": ["Which draft claims are source-supported enough for promotion?"],
            },
            "uncertainty_notes": ["Mock draft is schema coverage, not source authority."],
        }


@dataclass(frozen=True)
class MockMomentPackDraftProvider:
    name: str = "mock"
    model: str = "deadman-mock-moment-pack-draft-v0.1"
    mock_provider: bool = True

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        demo_nodes = [item for item in prompt.get("demo_nodes", []) if isinstance(item, dict)]
        drafts = [self._draft_from_demo_node(item) for item in demo_nodes]
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "schema_version": "deadman_llm_moment_pack_drafts.v0.1",
            "task": "llm_moment_pack_draft",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, True, latency_ms, {}),
            "source_refs": prompt.get("source_refs", {}),
            "draft_count": len(drafts),
            "moment_drafts": drafts,
        }

    def _draft_from_demo_node(self, item: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(item.get("candidate_id") or item.get("moment_id") or "unknown_candidate")
        options = item.get("default_options") or item.get("revised_default_options") or []
        return {
            "candidate_id": candidate_id,
            "draft_moment_id": f"{candidate_id}_llm_draft",
            "hook_draft": str(item.get("companion_hook") or item.get("scene_specific_hook") or "这里要不要换个做法？"),
            "viewer_impulse_draft": str(item.get("viewer_impulse") or "要是我来，会想试试另一种选择。"),
            "preset_action_drafts": [str(option) for option in options if isinstance(option, str)][:3]
            or ["稳住局面", "温和介入", "强行改局"],
            "actor_context_draft": str(item.get("why_now_reviewed") or item.get("evidence_notes") or "Draft actor context needs review."),
            "local_constraints_draft": ["source-bounded", "requires human review before promotion"],
            "canon_baseline_draft": {
                "original_action": "Original plot remains the baseline.",
                "original_rationale": str(item.get("original_plot_note_reviewed") or "Source rationale needs review."),
                "audience_tension": str(item.get("viewer_impulse") or "Audience wants to intervene."),
            },
            "judgment_basis_draft": ["source evidence", "relationship pressure", "watch-flow fit"],
            "visual_result_policy_draft": "Visual result is illustrative only and cannot prove source truth.",
            "inference_level": "human_review_required",
            "requires_human_review": True,
            "source_refs": {"candidate_id": candidate_id},
        }


@dataclass(frozen=True)
class ArkCandidateJudgeProvider:
    api_key: str
    model: str
    base_url: str = DEFAULT_ARK_BASE_URL
    temperature: float = DEFAULT_ARK_TEMPERATURE
    timeout_seconds: float = DEFAULT_ARK_TIMEOUT_SECONDS
    name: str = "ark"
    mock_provider: bool = False

    @classmethod
    def from_env(cls) -> "ArkCandidateJudgeProvider":
        api_key = os.environ.get("ARK_API_KEY", "").strip()
        model = (os.environ.get("ARK_MODEL") or os.environ.get("ARK_ENDPOINT_ID") or "").strip()
        if not api_key or not model:
            raise LlmProviderError("ARK_API_KEY and ARK_MODEL or ARK_ENDPOINT_ID are required for ark provider")
        return cls(
            api_key=api_key,
            model=model,
            base_url=os.environ.get("ARK_BASE_URL", DEFAULT_ARK_BASE_URL).strip().rstrip("/"),
            temperature=safe_float(os.environ.get("ARK_TEMPERATURE"), default=DEFAULT_ARK_TEMPERATURE),
            timeout_seconds=safe_float(os.environ.get("ARK_TIMEOUT_SECONDS"), default=DEFAULT_ARK_TIMEOUT_SECONDS),
        )

    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response_data = self._call_chat_completions(prompt, schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        provider_payload = self._parse_provider_payload(response_data)
        judgments = self._normalize_judgments(provider_payload, prompt)
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        return {
            "schema_version": "deadman_llm_candidate_judgment.v0.1",
            "task": "llm_candidate_judge",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": {
                "name": self.name,
                "model": self.model,
                "mock_provider": False,
                "latency_ms": latency_ms,
                "token_usage": {
                    "input_tokens": safe_int((usage or {}).get("prompt_tokens"), default=0),
                    "output_tokens": safe_int((usage or {}).get("completion_tokens"), default=0),
                    "total_tokens": safe_int((usage or {}).get("total_tokens"), default=0),
                },
            },
            "source_candidate_ref": prompt.get("source_candidate_ref", ""),
            "input_candidate_count": len([candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]),
            "shortlist_policy": prompt.get("selection_policy", {}),
            "judgment_count": len(judgments),
            "decisions_summary": summarize_decisions(judgments),
            "judgments": judgments,
        }

    def _chat_payload(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        system_content = str(
            prompt.get("system_prompt")
            or "You produce producer-only JSON drafts for short-drama interaction review. Return exactly one strict JSON object."
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_content,
                },
                {
                    "role": "user",
                    "content": json.dumps(provider_prompt_payload(prompt, schema), ensure_ascii=False),
                },
            ],
            "temperature": self.temperature,
        }
        if env_flag("ARK_ENABLE_JSON_RESPONSE_FORMAT"):
            payload["response_format"] = {"type": "json_object"}
        if env_flag("ARK_DISABLE_THINKING"):
            payload["thinking"] = {"type": "disabled"}
        seed = os.environ.get("ARK_SEED", "").strip()
        if seed:
            payload["seed"] = safe_int(seed, default=0)
        return payload

    def _call_chat_completions(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        payload = self._chat_payload(prompt, schema)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LlmProviderError(self._redact(f"ark request failed: {exc.__class__.__name__}: {exc}")) from exc

        if response.status_code >= 400:
            detail = response.text[:500]
            raise LlmProviderError(self._redact(f"ark request failed with status {response.status_code}: {detail}"))
        try:
            data = response.json()
        except ValueError as exc:
            raise LlmProviderError(f"ark response was not JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LlmProviderError("ark response root was not an object")
        return data

    def _parse_provider_payload(self, response_data: dict[str, Any]) -> dict[str, Any]:
        try:
            message = response_data["choices"][0]["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmProviderError("ark response did not include choices[0].message.content") from exc
        if not isinstance(content, str):
            raise LlmProviderError("ark message content was not a string")
        cleaned = strip_json_fence(content.strip())
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(f"ark message content was not valid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise LlmProviderError("ark message JSON root was not an object")
        return payload

    def _normalize_judgments(self, provider_payload: dict[str, Any], prompt: dict[str, Any]) -> list[dict[str, Any]]:
        raw_judgments = provider_payload.get("judgments")
        if not isinstance(raw_judgments, list):
            raise LlmProviderError("ark message JSON missing judgments array")

        candidates = [candidate for candidate in prompt.get("candidates", []) if isinstance(candidate, dict)]
        candidate_by_id = {str(candidate.get("candidate_id") or ""): candidate for candidate in candidates}
        raw_by_id: dict[str, dict[str, Any]] = {}
        for item in raw_judgments:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "")
            if candidate_id in candidate_by_id and candidate_id not in raw_by_id:
                raw_by_id[candidate_id] = item

        shortlist_limit = safe_int(prompt.get("shortlist_limit"), default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MIN)
        judgments: list[dict[str, Any]] = []
        for candidate_id, raw in list(raw_by_id.items())[:shortlist_limit]:
            candidate = candidate_by_id[candidate_id]
            candidate_id = str(candidate.get("candidate_id") or "")
            decision = str(raw.get("decision") or "keep_for_review")
            if decision not in {"recommend", "keep_for_review", "reject"}:
                decision = "keep_for_review"
            confidence = max(0.0, min(1.0, safe_float(raw.get("confidence"), default=0.5)))
            rationale = str(raw.get("rationale") or "No rationale returned; route to human review.").strip()
            failure_modes_value = raw.get("failure_modes")
            failure_modes = (
                [str(value) for value in failure_modes_value if isinstance(value, str)]
                if isinstance(failure_modes_value, list)
                else []
            )
            judgments.append(
                {
                    "candidate_id": candidate_id,
                    "decision": decision,
                    "confidence": confidence,
                    "rationale": rationale[:800],
                    "failure_modes": failure_modes[:8],
                    "source_refs": candidate.get("source_refs") or {},
                }
            )
        return judgments

    def _redact(self, text: str) -> str:
        if not self.api_key:
            return text
        return text.replace(self.api_key, "[REDACTED_ARK_API_KEY]")


@dataclass(frozen=True)
class ArkSemanticMinerProvider(ArkCandidateJudgeProvider):
    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response_data = self._call_chat_completions(prompt, schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        provider_payload = self._parse_provider_payload(response_data)
        candidates = normalize_semantic_candidates(provider_payload, prompt)
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        return {
            "schema_version": "deadman_llm_semantic_candidates.v0.1",
            "task": "llm_semantic_miner",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, False, latency_ms, usage),
            "source_refs": prompt.get("source_refs", {}),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }


@dataclass(frozen=True)
class ArkDramaContextDraftProvider(ArkCandidateJudgeProvider):
    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response_data = self._call_chat_completions(prompt, schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        provider_payload = self._parse_provider_payload(response_data)
        context_draft = provider_payload.get("context_draft")
        if not isinstance(context_draft, dict):
            raise LlmProviderError("ark message JSON missing context_draft object")
        context_draft = normalize_context_draft(context_draft)
        uncertainty_notes = provider_payload.get("uncertainty_notes")
        if not isinstance(uncertainty_notes, list):
            uncertainty_notes = ["Provider did not return uncertainty_notes; human review required."]
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        return {
            "schema_version": "deadman_llm_drama_context_draft.v0.1",
            "task": "llm_drama_context_draft",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, False, latency_ms, usage),
            "source_refs": prompt.get("source_refs", {}),
            "context_draft": context_draft,
            "uncertainty_notes": [str(note) for note in uncertainty_notes],
        }


@dataclass(frozen=True)
class ArkMomentPackDraftProvider(ArkCandidateJudgeProvider):
    def complete_json(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response_data = self._call_chat_completions(prompt, schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        provider_payload = self._parse_provider_payload(response_data)
        drafts = provider_payload.get("moment_drafts")
        if not isinstance(drafts, list):
            raise LlmProviderError("ark message JSON missing moment_drafts array")
        normalized = normalize_moment_drafts(drafts, prompt)
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        return {
            "schema_version": "deadman_llm_moment_pack_drafts.v0.1",
            "task": "llm_moment_pack_draft",
            "run_id": prompt.get("run_id", ""),
            "drama_id": prompt.get("drama_id", ""),
            "drama_title": prompt.get("drama_title", ""),
            "provider": provider_metadata(self.name, self.model, False, latency_ms, usage),
            "source_refs": prompt.get("source_refs", {}),
            "draft_count": len(normalized),
            "moment_drafts": normalized,
        }


def build_candidate_judge_prompt(
    *,
    run_id: str,
    drama_id: str,
    drama_title: str,
    source_candidate_ref: str,
    candidate_data: dict[str, Any],
    semantic_candidate_data: dict[str, Any] | None = None,
    source_window_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = candidate_data.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    semantic_candidates = []
    if isinstance(semantic_candidate_data, dict):
        semantic_candidates = [
            semantic_candidate_to_judge_candidate(candidate)
            for candidate in semantic_candidate_data.get("candidates", [])
            if isinstance(candidate, dict)
        ]
    source_windows = []
    if isinstance(source_window_data, dict):
        source_windows = [window for window in source_window_data.get("windows", []) if isinstance(window, dict)]
    source_count = count_distinct_sources(source_windows) or count_distinct_sources(candidates, semantic_candidates)
    pool_limit, pool_policy = llm_pool_budget(
        len(candidates),
        exact_env="LLM_CANDIDATE_JUDGE_POOL_LIMIT",
        max_env="LLM_CANDIDATE_JUDGE_POOL_MAX",
        default_max=DEFAULT_CANDIDATE_JUDGE_POOL_MAX,
    )
    semantic_pool_limit, semantic_pool_policy = llm_pool_budget(
        len(semantic_candidates),
        exact_env="LLM_CANDIDATE_JUDGE_SEMANTIC_POOL_LIMIT",
        max_env="LLM_CANDIDATE_JUDGE_SEMANTIC_POOL_MAX",
        default_max=DEFAULT_CANDIDATE_JUDGE_SEMANTIC_POOL_MAX,
    )
    selected_candidates = [
        compact_candidate_for_judge(candidate)
        for candidate in candidates[:pool_limit]
        if isinstance(candidate, dict)
    ] + [
        compact_candidate_for_judge(candidate)
        for candidate in semantic_candidates[:semantic_pool_limit]
        if isinstance(candidate, dict)
    ]
    shortlist_limit, shortlist_policy = candidate_judge_shortlist_budget(
        candidate_count=len(selected_candidates),
        source_count=source_count,
    )
    return {
        "task": "llm_candidate_judge",
        "run_id": run_id,
        "drama_id": drama_id,
        "drama_title": drama_title,
        "source_candidate_ref": source_candidate_ref,
        "system_prompt": (
            "You are the semantic shortlist gate for a short-drama feature called 要是我来. "
            "Deterministic recall is only an evidence pool. Select only the moments where a viewer would feel "
            "emotional fluctuation and want to say something immediately. Return strict JSON only."
        ),
        "instructions": [
            "Select up to shortlist_limit candidates for human review; do not judge every provided candidate.",
            "Prefer moments where the viewer would feel 不吐不快: anger, pity, unfairness, fear of exposure, or urge to reverse a wrong choice.",
            "Reject generic resource/family/system mentions unless the scene creates an immediate emotional pressure and a real local action choice.",
            "Preserve candidate ids and source refs.",
            "Use recommend for the strongest shortlist and keep_for_review for borderline but emotionally sharp moments.",
            "Do not return omitted candidates.",
            "Keep each rationale under 80 Chinese characters or 40 English words.",
        ],
        "selection_policy": {
            "deterministic_total": len(candidates),
            "deterministic_pool_size": pool_limit,
            "deterministic_pool_policy": pool_policy,
            "semantic_total": len(semantic_candidates),
            "semantic_pool_size": semantic_pool_limit,
            "semantic_pool_policy": semantic_pool_policy,
            "source_count": source_count,
            "shortlist_target": shortlist_limit,
            "shortlist_policy": shortlist_policy,
            "semantic_filter": "viewer 不吐不快 / high-emotion intervention pressure",
            "reason": "deterministic recall remains audit evidence; LLM performs semantic shortlist selection before human review",
        },
        "shortlist_limit": shortlist_limit,
        "output_contract": {
            "judgments": [
                {
                    "candidate_id": "string",
                    "decision": "recommend|keep_for_review",
                    "confidence": "number from 0 to 1",
                    "rationale": "why this would make a viewer want to speak up immediately",
                    "failure_modes": ["short_failure_code"],
                }
            ]
        },
        "candidates": selected_candidates,
    }


def build_semantic_miner_prompt(
    *,
    run_id: str,
    drama_id: str,
    drama_title: str,
    source_refs: dict[str, str],
    window_data: dict[str, Any],
    candidate_data: dict[str, Any],
    mechanism_data: dict[str, Any],
    field_minimum_text: str,
) -> dict[str, Any]:
    windows = window_data.get("windows")
    candidates = candidate_data.get("candidates")
    mechanism_buckets = mechanism_data.get("mechanism_buckets")
    return {
        "task": "llm_semantic_miner",
        "run_id": run_id,
        "drama_id": drama_id,
        "drama_title": drama_title,
        "source_refs": source_refs,
        "system_prompt": (
            "You find producer-review interaction moments in short-drama source windows. "
            "Return strict JSON only. Never write or claim runtime promotion."
        ),
        "instructions": [
            "Find semantically strong interaction moments that deterministic recall missed or underexplained.",
            "Use deterministic_enriched when you refine an existing candidate.",
            "Use llm_discovered only when the window evidence supports a new review candidate.",
            "Preserve episode/window/source references and mark uncertainty.",
        ],
        "output_contract": {
            "candidates": [
                {
                    "semantic_candidate_id": "string",
                    "origin": "deterministic_enriched|llm_discovered",
                    "linked_candidate_id": "string or empty",
                    "episode_id": "string",
                    "window_id": "string",
                    "time_range_ms": [0, 0],
                    "hook": "producer review hook",
                    "viewer_impulse": "viewer-facing impulse",
                    "intervention_logic": "why this is an intervention node",
                    "evidence_excerpt": "short source evidence",
                    "uncertainty": "low|medium|high",
                    "confidence": "0..1",
                    "field_signals": ["field codes"],
                    "suggested_options": ["short actions"],
                    "failure_modes": ["risk codes"],
                }
            ]
        },
        "field_minimum_excerpt": field_minimum_text[:4000],
        "mechanism_buckets": mechanism_buckets if isinstance(mechanism_buckets, list) else [],
        "windows": [compact_window(window) for window in (windows if isinstance(windows, list) else [])[:40]],
        "candidates": [
            compact_candidate(candidate) for candidate in (candidates if isinstance(candidates, list) else [])[:30]
        ],
    }


def build_drama_context_draft_prompt(
    *,
    run_id: str,
    drama_id: str,
    drama_title: str,
    source_refs: dict[str, str],
    current_context: dict[str, Any],
    reviewed_demo_nodes: dict[str, Any],
    reviewed_candidates: dict[str, Any],
    semantic_candidates: dict[str, Any] | None,
    candidate_judgment: dict[str, Any] | None,
) -> dict[str, Any]:
    demo_nodes = reviewed_demo_nodes.get("demo_nodes")
    reviewed = reviewed_candidates.get("reviewed_candidates")
    return {
        "task": "llm_drama_context_draft",
        "run_id": run_id,
        "drama_id": drama_id,
        "drama_title": drama_title,
        "source_refs": source_refs,
        "system_prompt": (
            "You draft producer-only drama context notes from reviewed short-drama evidence. "
            "Return strict JSON only. Do not overwrite tracked context packs."
        ),
        "instructions": [
            "Draft context additions for human review only.",
            "Mark source_supported, model_inferred, or human_review_required.",
            "Preserve uncertainty and open questions.",
            "Never claim that a draft is runtime truth.",
        ],
        "output_contract": {
            "context_draft": {
                "premise_draft": "string",
                "genre_contract_draft": "string",
                "protagonist_draft": "string",
                "core_constraints_draft": [
                    {
                        "field": "string",
                        "value": "string",
                        "confidence": "0..1",
                        "inference_level": "source_supported|model_inferred|human_review_required",
                        "source_refs": {},
                    }
                ],
                "relationship_drafts": [],
                "guardrails": ["string"],
                "open_questions": ["string"],
            },
            "uncertainty_notes": ["string"],
        },
        "current_context": compact_mapping(current_context, limit=24),
        "demo_nodes": [compact_demo_node(item) for item in (demo_nodes if isinstance(demo_nodes, list) else [])],
        "reviewed_candidates": [
            compact_reviewed_candidate(item) for item in (reviewed if isinstance(reviewed, list) else [])[:30]
        ],
        "semantic_summary": semantic_summary(semantic_candidates),
        "candidate_judgment_summary": candidate_judgment_summary(candidate_judgment),
    }


def build_moment_pack_draft_prompt(
    *,
    run_id: str,
    drama_id: str,
    drama_title: str,
    source_refs: dict[str, str],
    current_context: dict[str, Any],
    reviewed_demo_nodes: dict[str, Any],
    reviewed_candidates: dict[str, Any],
    drama_context_draft: dict[str, Any] | None,
) -> dict[str, Any]:
    demo_nodes = reviewed_demo_nodes.get("demo_nodes")
    reviewed = reviewed_candidates.get("reviewed_candidates")
    return {
        "task": "llm_moment_pack_draft",
        "run_id": run_id,
        "drama_id": drama_id,
        "drama_title": drama_title,
        "source_refs": source_refs,
        "system_prompt": (
            "You draft producer-only Moment Pack fields for approved short-drama candidates. "
            "Return strict JSON only. Drafts require human review and must not publish directly."
        ),
        "instructions": [
            "Use only reviewed demo nodes or reviewed candidates supplied in the prompt.",
            "Keep hook/options viewer-language, not analysis labels.",
            "Set requires_human_review to true for every draft.",
            "Never claim visual output as source proof.",
        ],
        "output_contract": {
            "moment_drafts": [
                {
                    "candidate_id": "string",
                    "draft_moment_id": "string",
                    "hook_draft": "viewer-facing hook",
                    "viewer_impulse_draft": "viewer impulse",
                    "preset_action_drafts": ["short action"],
                    "actor_context_draft": "string",
                    "local_constraints_draft": ["string"],
                    "canon_baseline_draft": {
                        "original_action": "string",
                        "original_rationale": "string",
                        "audience_tension": "string",
                    },
                    "judgment_basis_draft": ["string"],
                    "visual_result_policy_draft": "string",
                    "inference_level": "source_supported|model_inferred|human_review_required",
                    "requires_human_review": True,
                    "source_refs": {},
                }
            ]
        },
        "current_context": compact_mapping(current_context, limit=16),
        "context_draft_summary": compact_mapping(drama_context_draft or {}, limit=16),
        "demo_nodes": [compact_demo_node(item) for item in (demo_nodes if isinstance(demo_nodes, list) else [])],
        "reviewed_candidates": [
            compact_reviewed_candidate(item) for item in (reviewed if isinstance(reviewed, list) else [])[:30]
        ],
    }


def provider_prompt_payload(prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in prompt.items() if key != "system_prompt"}
    payload["schema_title"] = schema.get("title", "")
    payload["output_format_instructions"] = [
        "Return exactly one JSON object and no prose.",
        "Do not wrap the JSON in Markdown fences.",
        "The JSON object must match the task output_contract and schema title.",
    ]
    return payload


def provider_metadata(name: str, model: str, mock_provider: bool, latency_ms: int, usage: Any) -> dict[str, Any]:
    usage_dict = usage if isinstance(usage, dict) else {}
    return {
        "name": name,
        "model": model,
        "mock_provider": mock_provider,
        "latency_ms": latency_ms,
        "token_usage": {
            "input_tokens": safe_int(usage_dict.get("prompt_tokens"), default=0),
            "output_tokens": safe_int(usage_dict.get("completion_tokens"), default=0),
            "total_tokens": safe_int(usage_dict.get("total_tokens"), default=0),
        },
    }


def semantic_candidate_to_judge_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    time_range = candidate.get("time_range_ms")
    start_ms = time_range[0] if isinstance(time_range, list) and len(time_range) > 0 else None
    end_ms = time_range[1] if isinstance(time_range, list) and len(time_range) > 1 else None
    return {
        "candidate_id": candidate.get("semantic_candidate_id"),
        "episode_id": candidate.get("episode_id"),
        "window_id": candidate.get("window_id"),
        "start_ms": start_ms,
        "end_ms": end_ms,
        "semantic_origin": candidate.get("origin"),
        "linked_candidate_id": candidate.get("linked_candidate_id"),
        "rank": 999,
        "rank_score": safe_float(candidate.get("confidence"), default=0.5) * 100,
        "trigger_type": ",".join(str(value) for value in candidate.get("field_signals", []) if isinstance(value, str)),
        "hook": candidate.get("hook"),
        "evidence_excerpt": candidate.get("evidence_excerpt"),
        "source_refs": candidate.get("source_refs") or {},
    }


def normalize_semantic_candidates(provider_payload: dict[str, Any], prompt: dict[str, Any]) -> list[dict[str, Any]]:
    raw_candidates = provider_payload.get("candidates")
    if not isinstance(raw_candidates, list):
        raise LlmProviderError("ark message JSON missing candidates array")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates):
        if not isinstance(raw, dict):
            continue
        candidate_id = str(raw.get("semantic_candidate_id") or f"llm_semantic_{index + 1:03d}")
        origin = str(raw.get("origin") or "llm_discovered")
        if origin not in {"deterministic_enriched", "llm_discovered"}:
            origin = "llm_discovered"
        time_range = raw.get("time_range_ms")
        if not isinstance(time_range, list) or len(time_range) != 2:
            time_range = [0, 0]
        uncertainty = str(raw.get("uncertainty") or "high")
        if uncertainty not in {"low", "medium", "high"}:
            uncertainty = "high"
        normalized.append(
            {
                "semantic_candidate_id": candidate_id,
                "origin": origin,
                "linked_candidate_id": str(raw.get("linked_candidate_id") or ""),
                "episode_id": str(raw.get("episode_id") or "unknown_episode"),
                "window_id": str(raw.get("window_id") or "unknown_window"),
                "time_range_ms": [safe_int(time_range[0], default=0), safe_int(time_range[1], default=0)],
                "hook": str(raw.get("hook") or "这里适合进入人工复核。")[:200],
                "viewer_impulse": str(raw.get("viewer_impulse") or "要是我来，会想试试另一种选择。")[:200],
                "intervention_logic": str(raw.get("intervention_logic") or "Model marked this as review-worthy.")[:800],
                "evidence_excerpt": str(raw.get("evidence_excerpt") or "source evidence omitted")[:800],
                "uncertainty": uncertainty,
                "confidence": max(0.0, min(1.0, safe_float(raw.get("confidence"), default=0.5))),
                "field_signals": [str(value) for value in raw.get("field_signals", []) if isinstance(value, str)][:12],
                "suggested_options": [str(value) for value in raw.get("suggested_options", []) if isinstance(value, str)][:5],
                "source_refs": raw.get("source_refs") if isinstance(raw.get("source_refs"), dict) else {},
                "failure_modes": [str(value) for value in raw.get("failure_modes", []) if isinstance(value, str)][:8],
            }
        )
    return normalized


def normalize_context_draft(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "premise_draft": str(raw.get("premise_draft") or "Draft premise requires human review."),
        "genre_contract_draft": str(raw.get("genre_contract_draft") or "Draft genre contract requires human review."),
        "protagonist_draft": str(raw.get("protagonist_draft") or "Draft protagonist profile requires human review."),
        "core_constraints_draft": normalize_draft_items(raw.get("core_constraints_draft")),
        "relationship_drafts": normalize_draft_items(raw.get("relationship_drafts")),
        "guardrails": normalize_string_list(raw.get("guardrails")),
        "open_questions": normalize_string_list(raw.get("open_questions")),
    }


def normalize_draft_items(value: Any) -> list[dict[str, Any]]:
    items = value if isinstance(value, list) else []
    normalized: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        inference_level = str(raw.get("inference_level") or "human_review_required")
        if inference_level not in {"source_supported", "model_inferred", "human_review_required"}:
            inference_level = "human_review_required"
        normalized.append(
            {
                "field": str(raw.get("field") or "unknown"),
                "value": str(raw.get("value") or "Draft value requires human review."),
                "confidence": max(0.0, min(1.0, safe_float(raw.get("confidence"), default=0.5))),
                "inference_level": inference_level,
                "source_refs": raw.get("source_refs") if isinstance(raw.get("source_refs"), dict) else {},
            }
        )
    return normalized


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def normalize_moment_drafts(raw_drafts: list[Any], prompt: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_drafts):
        if not isinstance(raw, dict):
            continue
        candidate_id = str(raw.get("candidate_id") or f"unknown_candidate_{index + 1:03d}")
        baseline = raw.get("canon_baseline_draft")
        if not isinstance(baseline, dict):
            baseline = {}
        inference_level = str(raw.get("inference_level") or "human_review_required")
        if inference_level not in {"source_supported", "model_inferred", "human_review_required"}:
            inference_level = "human_review_required"
        normalized.append(
            {
                "candidate_id": candidate_id,
                "draft_moment_id": str(raw.get("draft_moment_id") or f"{candidate_id}_llm_draft"),
                "hook_draft": str(raw.get("hook_draft") or "这里要不要换个做法？")[:200],
                "viewer_impulse_draft": str(raw.get("viewer_impulse_draft") or "要是我来，会想试试另一种选择。")[:200],
                "preset_action_drafts": [
                    str(value) for value in raw.get("preset_action_drafts", []) if isinstance(value, str)
                ][:5]
                or ["稳住局面", "温和介入", "强行改局"],
                "actor_context_draft": str(raw.get("actor_context_draft") or "Draft actor context needs review.")[:800],
                "local_constraints_draft": [
                    str(value) for value in raw.get("local_constraints_draft", []) if isinstance(value, str)
                ][:12],
                "canon_baseline_draft": {
                    "original_action": str(baseline.get("original_action") or "Original plot remains baseline."),
                    "original_rationale": str(baseline.get("original_rationale") or "Source rationale needs review."),
                    "audience_tension": str(baseline.get("audience_tension") or "Audience wants to intervene."),
                },
                "judgment_basis_draft": [
                    str(value) for value in raw.get("judgment_basis_draft", []) if isinstance(value, str)
                ][:12],
                "visual_result_policy_draft": str(
                    raw.get("visual_result_policy_draft")
                    or "Visual result is illustrative only and cannot prove source truth."
                ),
                "inference_level": inference_level,
                "requires_human_review": True,
                "source_refs": raw.get("source_refs") if isinstance(raw.get("source_refs"), dict) else {},
            }
        )
    return normalized


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "episode_id": candidate.get("episode_id"),
        "window_id": candidate.get("window_id"),
        "start_ms": candidate.get("start_ms"),
        "end_ms": candidate.get("end_ms"),
        "rank": candidate.get("rank"),
        "rank_score": candidate.get("rank_score"),
        "trigger_type": candidate.get("trigger_type"),
        "hook": candidate.get("hook"),
        "viewer_impulse": candidate.get("viewer_impulse"),
        "evidence_excerpt": str(candidate.get("evidence_excerpt") or "")[:800],
        "default_options": candidate.get("default_options") or [],
        "source_refs": candidate.get("source_refs") or {},
    }


def compact_candidate_for_judge(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "episode_id": candidate.get("episode_id"),
        "window_id": candidate.get("window_id"),
        "start_ms": candidate.get("start_ms"),
        "end_ms": candidate.get("end_ms"),
        "rank": candidate.get("rank"),
        "rank_score": candidate.get("rank_score"),
        "trigger_type": candidate.get("trigger_type"),
        "hook": candidate.get("hook"),
        "viewer_impulse": candidate.get("viewer_impulse"),
        "evidence_excerpt": str(candidate.get("evidence_excerpt") or "")[:260],
        "source_refs": candidate.get("source_refs") if isinstance(candidate.get("source_refs"), dict) else {},
    }


def compact_window(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "window_id": window.get("window_id"),
        "episode_id": window.get("episode_id"),
        "start_ms": window.get("start_ms"),
        "end_ms": window.get("end_ms"),
        "transcript_text": str(window.get("transcript_text") or "")[:900],
        "source_quality": window.get("source_quality"),
    }


def compact_demo_node(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "moment_id": item.get("moment_id"),
        "candidate_id": item.get("candidate_id"),
        "review_status": item.get("review_status"),
        "trigger_type": item.get("corrected_trigger_type"),
        "hook": item.get("companion_hook") or item.get("scene_specific_hook"),
        "viewer_impulse": item.get("viewer_impulse"),
        "default_options": item.get("default_options") or item.get("revised_default_options") or [],
        "original_plot_note": item.get("original_plot_note_reviewed"),
        "evidence": item.get("evidence") or item.get("source_evidence_excerpt"),
    }


def compact_reviewed_candidate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": item.get("candidate_id"),
        "review_status": item.get("review_status"),
        "episode_id": item.get("episode_id"),
        "window_id": item.get("window_id"),
        "hook": item.get("scene_specific_hook"),
        "default_options": item.get("revised_default_options") or [],
        "why_now": item.get("why_now_reviewed"),
        "evidence_grade": item.get("evidence_grade"),
        "evidence_notes": item.get("evidence_notes"),
        "source_evidence_excerpt": str(item.get("source_evidence_excerpt") or "")[:800],
    }


def compact_mapping(data: dict[str, Any], *, limit: int) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for index, (key, value) in enumerate(data.items()):
        if index >= limit:
            break
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[key] = value
        elif isinstance(value, list):
            compact[key] = value[:8]
        elif isinstance(value, dict):
            compact[key] = compact_mapping(value, limit=8)
    return compact


def semantic_summary(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    return {
        "candidate_count": data.get("candidate_count", len(candidates)),
        "top_candidates": [
            {
                "semantic_candidate_id": item.get("semantic_candidate_id"),
                "origin": item.get("origin"),
                "hook": item.get("hook"),
                "confidence": item.get("confidence"),
            }
            for item in candidates[:10]
            if isinstance(item, dict)
        ],
    }


def candidate_judgment_summary(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    return {
        "judgment_count": data.get("judgment_count", 0),
        "decisions_summary": data.get("decisions_summary", {}),
    }


def summarize_decisions(judgments: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"recommend": 0, "keep_for_review": 0, "reject": 0}
    for judgment in judgments:
        decision = str(judgment.get("decision") or "")
        if decision in summary:
            summary[decision] += 1
    return summary


def llm_pool_budget(item_count: int, *, exact_env: str, max_env: str, default_max: int) -> tuple[int, dict[str, Any]]:
    override = optional_positive_int_env(exact_env)
    if override is not None:
        limit = min(item_count, override)
        return limit, {"mode": "override", "env": exact_env, "requested": override, "applied": limit}
    safety_max = positive_int_env(max_env, default=default_max)
    limit = min(item_count, safety_max)
    return limit, {"mode": "dynamic_all_with_safety_max", "safety_max": safety_max, "applied": limit}


def candidate_judge_shortlist_budget(*, candidate_count: int, source_count: int) -> tuple[int, dict[str, Any]]:
    if candidate_count <= 0:
        return 0, {"mode": "empty_pool", "candidate_count": candidate_count, "source_count": source_count}

    override = optional_positive_int_env("LLM_CANDIDATE_JUDGE_SHORTLIST_LIMIT")
    if override is not None:
        limit = min(candidate_count, override)
        return limit, {
            "mode": "override",
            "env": "LLM_CANDIDATE_JUDGE_SHORTLIST_LIMIT",
            "requested": override,
            "applied": limit,
            "candidate_count": candidate_count,
            "source_count": source_count,
        }

    min_limit = positive_int_env("LLM_CANDIDATE_JUDGE_SHORTLIST_MIN", default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MIN)
    max_limit = positive_int_env("LLM_CANDIDATE_JUDGE_SHORTLIST_MAX", default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_MAX)
    if max_limit < min_limit:
        max_limit = min_limit
    per_source = positive_float_env(
        "LLM_CANDIDATE_JUDGE_SHORTLIST_PER_SOURCE",
        default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_PER_SOURCE,
    )
    pool_ratio = positive_float_env(
        "LLM_CANDIDATE_JUDGE_SHORTLIST_POOL_RATIO",
        default=DEFAULT_CANDIDATE_JUDGE_SHORTLIST_POOL_RATIO,
    )
    source_basis = max(source_count, 1)
    source_budget = math.ceil(source_basis * per_source)
    pool_budget = math.ceil(candidate_count * pool_ratio)
    raw_budget = max(min_limit, source_budget, pool_budget)
    limit = min(candidate_count, max_limit, raw_budget)
    return limit, {
        "mode": "dynamic",
        "candidate_count": candidate_count,
        "source_count": source_count,
        "source_basis": source_basis,
        "min": min_limit,
        "max": max_limit,
        "per_source": per_source,
        "pool_ratio": pool_ratio,
        "source_budget": source_budget,
        "pool_budget": pool_budget,
        "applied": limit,
    }


def count_distinct_sources(*groups: list[dict[str, Any]]) -> int:
    source_ids: set[str] = set()
    for group in groups:
        for item in group:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("episode_id") or "").strip()
            if source_id and source_id not in {"unknown", "unknown_episode"}:
                source_ids.add(source_id)
    return len(source_ids)


def safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def optional_positive_int_env(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    value = safe_int(raw, default=0)
    return value if value > 0 else None


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def positive_int_env(name: str, *, default: int) -> int:
    value = safe_int(os.environ.get(name), default=default)
    return value if value > 0 else default


def positive_float_env(name: str, *, default: float) -> float:
    value = safe_float(os.environ.get(name), default=default)
    return value if value > 0 else default


def strip_json_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
