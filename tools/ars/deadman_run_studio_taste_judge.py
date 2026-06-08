#!/usr/bin/env python3
"""Run the Deadman v0.41 Studio CAB taste judge over real-provider proof drafts.

The judge is a critic-only role for the existing Phase 2.6/2.7 drafts. It does
not author copy. It does not promote drafts to runtime packs. It scores four
taste dimensions plus one overall verdict per draft and writes a sanitized
report. Owner taste tray + calibration artifact consume this output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
except ModuleNotFoundError:
    from .deadman_producer_graph_llm import (
        ArkCandidateJudgeProvider,
        LlmProviderError,
        provider_metadata,
        safe_int,
    )

DEFAULT_PROOF_PATH = REPO_ROOT / "data/evals/studio_cab_real_provider_proof.v0.1.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/evals/studio_cab_taste_judge.v0.1.json"
SCHEMA_VERSION = "studio_cab_taste_judge.v0.1"
PRODUCT = "看剧搭子"

TASTE_LEVELS = {"excellent", "acceptable", "needs_repair"}
OVERALL_VERDICTS = {"accept", "accept_with_minor_tweak", "reject"}
ELIGIBLE_CASE_TYPES = {"owner_gold_exchange_authoring", "phase2_repair_regression"}
ALLOWED_JUDGE_PROVIDERS = {"ark", "bailian"}
DEFAULT_BAILIAN_MODEL = "qwen3.6-plus"


@dataclass(frozen=True)
class BailianTasteJudgeProvider:
    """Cross-model taste judge backed by the Bailian CLI (Qwen)."""

    name: str = "bailian"
    model: str = DEFAULT_BAILIAN_MODEL
    mock_provider: bool = False
    bl_path: str = field(default_factory=lambda: shutil.which("bl") or "bl")
    timeout_seconds: float = 90.0

    @classmethod
    def from_env(cls) -> "BailianTasteJudgeProvider":
        bl_path = shutil.which("bl")
        if bl_path is None:
            raise RuntimeError(
                "bailian CLI 'bl' not found on PATH; cross-model judge requires bl text chat."
            )
        model = os.environ.get("BAILIAN_JUDGE_MODEL", DEFAULT_BAILIAN_MODEL).strip() or DEFAULT_BAILIAN_MODEL
        return cls(bl_path=bl_path, model=model)

    def call(self, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], int, dict[str, int]]:
        messages = json.dumps(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            ensure_ascii=False,
        )
        cmd = [
            self.bl_path,
            "text",
            "chat",
            "--model",
            self.model,
            "--messages-file",
            "-",
            "--output",
            "json",
            "--quiet",
        ]
        started = time.perf_counter()
        result = subprocess.run(
            cmd,
            input=messages,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        if result.returncode != 0:
            raise RuntimeError(
                f"bl text chat exited with code {result.returncode}; stderr length={len(result.stderr or '')}"
            )
        stdout = (result.stdout or "").strip()
        payload = self._extract_payload(stdout)
        usage = self._extract_usage(stdout)
        return payload, latency_ms, usage

    def _extract_payload(self, stdout: str) -> dict[str, Any]:
        if not stdout:
            raise RuntimeError("bl text chat returned empty stdout")
        # With --quiet --output json, bl emits the assistant content directly.
        # Fall back to parsing the full chat.completion envelope if metadata is present.
        try:
            decoded = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"bl text chat returned non-JSON content (len={len(stdout)}): {exc}")
        if isinstance(decoded, dict) and "choices" in decoded:
            choices = decoded.get("choices") or []
            if not choices or not isinstance(choices[0], dict):
                raise RuntimeError("bl text chat response missing assistant choice")
            content = choices[0].get("message", {}).get("content") or ""
            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"assistant content was not strict JSON: {exc}")
        if not isinstance(decoded, dict):
            raise RuntimeError("bl text chat assistant content was not a JSON object")
        return decoded

    def _extract_usage(self, stdout: str) -> dict[str, int]:
        try:
            decoded = json.loads(stdout)
        except json.JSONDecodeError:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        if not isinstance(decoded, dict):
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        usage = decoded.get("usage", {}) if isinstance(decoded.get("usage"), dict) else {}
        return {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", default=str(DEFAULT_PROOF_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--created-at", default="")
    parser.add_argument(
        "--provider",
        choices=sorted(ALLOWED_JUDGE_PROVIDERS),
        default="bailian",
        help="Which model family to use as the taste judge. 'bailian' runs Qwen via bl text chat (cross-model). 'ark' reuses the authoring provider (same-model self-grading).",
    )
    args = parser.parse_args()

    proof_path = resolve_path(args.proof)
    output_path = resolve_path(args.output)
    created_at = args.created_at or now_iso()
    proof = read_json(proof_path)

    if args.provider == "ark":
        try:
            provider: Any = ArkCandidateJudgeProvider.from_env()
        except LlmProviderError as exc:
            print(f"Taste judge provider unavailable: {exc}")
            return 2
    else:
        try:
            provider = BailianTasteJudgeProvider.from_env()
        except RuntimeError as exc:
            print(f"Taste judge provider unavailable: {exc}")
            return 2

    report = build_taste_judge_report(
        proof=proof,
        proof_path=proof_path,
        provider=provider,
        created_at=created_at,
    )
    write_json(output_path, report)
    print(f"Wrote Studio CAB taste judge report: {repo_relative(output_path)}")
    return 0


def build_taste_judge_report(
    *,
    proof: dict[str, Any],
    proof_path: Path,
    provider: Any,
    created_at: str,
) -> dict[str, Any]:
    eligible = [
        case for case in proof.get("case_results", [])
        if case.get("case_type") in ELIGIBLE_CASE_TYPES
        and case.get("provider_status") == "completed"
        and case.get("draft", {}).get("companion_lead")
        and case.get("draft", {}).get("reply_candidates")
    ]
    verdicts: list[dict[str, Any]] = []
    for case in eligible:
        prompt = build_judge_prompt(case)
        prompt_hash = sha256_json(prompt)
        try:
            payload, meta = call_judge_provider(provider, prompt)
            verdicts.append(normalize_verdict(case, payload, meta, prompt_hash))
        except Exception as exc:
            verdicts.append(provider_failure_verdict(case, prompt_hash, exc))

    summary = {
        "accept": sum(1 for v in verdicts if v["overall_verdict"] == "accept"),
        "accept_with_minor_tweak": sum(1 for v in verdicts if v["overall_verdict"] == "accept_with_minor_tweak"),
        "reject": sum(1 for v in verdicts if v["overall_verdict"] == "reject"),
        "provider_failed_or_invalid": sum(
            1 for v in verdicts if v["overall_verdict"] == "not_available"
        ),
    }
    completed = sum(1 for v in verdicts if v["provider_status"] == "completed")
    status = "completed" if completed == len(verdicts) and verdicts else (
        "provider_blocked" if not verdicts else "completed_with_failures"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "created_at": created_at,
        "status": status,
        "claim_boundary": (
            "Critic-only taste judge. Provider is recorded in "
            "provider_identity_redacted; verdicts are advisory and never promote "
            "drafts to runtime packs."
        ),
        "provider_identity_redacted": {
            "provider": getattr(provider, "name", "ark"),
            "model_alias": provider.model,
            "mock_provider": False,
            "role": "taste_judge",
        },
        "proof_ref": {
            "path": repo_relative(proof_path),
            "sha256": sha256_file(proof_path),
            "schema_version": proof["schema_version"],
        },
        "planned_case_count": len(eligible),
        "attempted_case_count": len(verdicts),
        "completed_case_count": completed,
        "verdicts": verdicts,
        "verdict_summary": summary,
    }


def build_judge_prompt(case: dict[str, Any]) -> dict[str, Any]:
    draft = case.get("draft", {})
    replies = draft.get("reply_candidates", [])
    return {
        "system_prompt": (
            "You are a Deadman 看剧搭子 taste critic. You only score the provided "
            "draft. Do not author replacement copy. Return one strict JSON object "
            "matching the output_contract. No prose, no extra fields."
        ),
        "task": "studio_cab_taste_judge",
        "product": PRODUCT,
        "two_layer_semantics": [
            "display_text is the viewer's own about-to-say line (Layer 1) — what the viewer wants to blurt out, not a comment about the scene.",
            "selected_echo is the host replying to the specific viewer who picked that display_text (Layer 2). viewer_motivation states who that viewer is and what they want to hear back. Judge echo against that motivation, not just against the scene.",
        ],
        "instructions": [
            "Score four dimensions and one overall verdict for this draft.",
            "lead_taste: is companion_lead a short friend-style line a viewer would actually say? Avoid: question shape, UI prompt, axis label, plot prediction.",
            "reply_voice_taste: do all three reply display_texts sound like actual viewer reactions, not action menus, not abstract semantic_role labels?",
            "reply_axis_diversity: do the three replies cover genuinely distinct emotional/semantic angles, or do they repeat the same angle?",
            "echo_taste: for each reply, does selected_echo answer the viewer described by viewer_motivation — acknowledging that viewer's point AND extending it one notch for them — rather than (a) paraphrasing the display_text, (b) drifting into an independent statement that ignores the viewer, or (c) using a formulaic shared opening across the three echoes?",
            "overall_verdict: accept if all four are acceptable+; accept_with_minor_tweak if the draft is publishable after small wording tweaks; reject if a dimension is needs_repair AND that breaks the whole exchange.",
            "Stay grounded to the source window. Do not invent new facts. Do not predict future plot.",
        ],
        "case": {
            "case_id": case["case_id"],
            "case_type": case["case_type"],
            "item_id": case["item_id"],
            "episode_id": case["episode_id"],
            "expected_behavior": case.get("expected_behavior", ""),
        },
        "draft": {
            "companion_lead": draft.get("companion_lead", ""),
            "reply_candidates": [
                {
                    "display_text": r.get("display_text", ""),
                    "emotion_role": r.get("emotion_role", ""),
                    "semantic_role": r.get("semantic_role", ""),
                    "viewer_motivation": r.get("viewer_motivation", ""),
                    "selected_echo": r.get("selected_echo", ""),
                }
                for r in replies
            ],
        },
        "authoring_rationale_for_context": case.get("rationale_summary", ""),
        "output_contract": {
            "case_id": case["case_id"],
            "lead_taste": ["excellent", "acceptable", "needs_repair"],
            "reply_voice_taste": ["excellent", "acceptable", "needs_repair"],
            "reply_axis_diversity": ["excellent", "acceptable", "needs_repair"],
            "echo_taste": ["excellent", "acceptable", "needs_repair"],
            "overall_verdict": ["accept", "accept_with_minor_tweak", "reject"],
            "rationale_summary": "1-2 short sentences, no markdown",
        },
    }


def call_judge_provider(provider: Any, prompt: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = {
        "title": "Studio CAB Taste Judge Output",
        "type": "object",
        "required": [
            "case_id",
            "lead_taste",
            "reply_voice_taste",
            "reply_axis_diversity",
            "echo_taste",
            "overall_verdict",
            "rationale_summary",
        ],
        "properties": {
            "case_id": {"type": "string"},
            "lead_taste": {"type": "string"},
            "reply_voice_taste": {"type": "string"},
            "reply_axis_diversity": {"type": "string"},
            "echo_taste": {"type": "string"},
            "overall_verdict": {"type": "string"},
            "rationale_summary": {"type": "string"},
        },
    }
    if isinstance(provider, BailianTasteJudgeProvider):
        system_prompt = prompt.get("system_prompt", "") or ""
        user_payload = {key: value for key, value in prompt.items() if key != "system_prompt"}
        user_prompt = json.dumps(user_payload, ensure_ascii=False)
        payload, latency_ms, usage = provider.call(system_prompt, user_prompt)
        meta = {
            "name": getattr(provider, "name", "bailian"),
            "model": getattr(provider, "model", DEFAULT_BAILIAN_MODEL),
            "mock_provider": False,
            "latency_ms": latency_ms,
            "token_usage": usage,
        }
        return payload, meta
    started = time.perf_counter()
    response = provider._call_chat_completions(prompt, schema)
    latency_ms = int((time.perf_counter() - started) * 1000)
    payload = provider._parse_provider_payload(response)
    usage = response.get("usage") if isinstance(response, dict) else {}
    meta = provider_metadata(provider.name, provider.model, False, latency_ms, usage)
    return payload, meta


def normalize_verdict(
    case: dict[str, Any],
    payload: dict[str, Any],
    meta: dict[str, Any],
    prompt_hash: str,
) -> dict[str, Any]:
    lead_taste = normalize_taste(payload.get("lead_taste"))
    reply_voice = normalize_taste(payload.get("reply_voice_taste"))
    reply_axis = normalize_taste(payload.get("reply_axis_diversity"))
    echo_taste = normalize_taste(payload.get("echo_taste"))
    overall = normalize_overall(payload.get("overall_verdict"))
    schema_ok = all(
        v != "not_available"
        for v in (lead_taste, reply_voice, reply_axis, echo_taste, overall)
    )
    return {
        "case_id": str(case["case_id"]),
        "case_type": str(case["case_type"]),
        "item_id": str(case["item_id"]),
        "episode_id": str(case["episode_id"]),
        "provider_status": "completed",
        "provider_status_class": "success",
        "latency_bucket": latency_bucket(safe_int(meta.get("latency_ms"), default=0)),
        "token_usage": normalize_token_usage(meta.get("token_usage")),
        "schema_validation": "pass" if schema_ok else "fail",
        "lead_taste": lead_taste,
        "reply_voice_taste": reply_voice,
        "reply_axis_diversity": reply_axis,
        "echo_taste": echo_taste,
        "overall_verdict": overall,
        "rationale_summary": truncate(str(payload.get("rationale_summary") or ""), 500),
        "prompt_hash": prompt_hash,
    }


def provider_failure_verdict(case: dict[str, Any], prompt_hash: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": str(case["case_id"]),
        "case_type": str(case["case_type"]),
        "item_id": str(case["item_id"]),
        "episode_id": str(case["episode_id"]),
        "provider_status": "provider_failed",
        "provider_status_class": "provider_error",
        "latency_bucket": "not_available",
        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "schema_validation": "fail",
        "lead_taste": "not_available",
        "reply_voice_taste": "not_available",
        "reply_axis_diversity": "not_available",
        "echo_taste": "not_available",
        "overall_verdict": "not_available",
        "rationale_summary": truncate(
            f"Taste judge provider failed with sanitized error type {exc.__class__.__name__}.",
            400,
        ),
        "prompt_hash": prompt_hash,
    }


def normalize_taste(value: Any) -> str:
    s = str(value or "").strip()
    return s if s in TASTE_LEVELS else "not_available"


def normalize_overall(value: Any) -> str:
    s = str(value or "").strip()
    return s if s in OVERALL_VERDICTS else "not_available"


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


def truncate(text: str, limit: int) -> str:
    return text[:limit]


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


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
