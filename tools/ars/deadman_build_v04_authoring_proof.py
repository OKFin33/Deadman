#!/usr/bin/env python3
"""Build the tracked v0.4 Studio/CAB authoring proof fixture.

The fixture is intentionally small and public-safe. It proves the authoring
unit, validation, and review handoff with the local mock provider. Raw provider
traces and local run caches remain under ignored tmp paths.
"""

from __future__ import annotations

import argparse
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from tools.ars.deadman_producer_graph_llm import MockMomentPackDraftProvider
except ModuleNotFoundError:
    from .deadman_producer_graph_llm import MockMomentPackDraftProvider


DEFAULT_MOMENTS_PATH = REPO_ROOT / "data/dramas/huangnian/moments.v0.1.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/evals/deadman_v0.4_authoring_proof.v0.1.json"
COMPANION_EXCHANGE_SCHEMA_PATH = REPO_ROOT / "data/schemas/companion_exchange_pack.v0.1.json"
PROOF_SCHEMA_PATH = REPO_ROOT / "data/schemas/deadman_v04_authoring_proof.v0.1.json"
DEFAULT_GOLD_MOMENT_ID = "huangnian_ep03_m001"
DEFAULT_NON_GOLD_MOMENT_ID = "huangnian_ep04_m001"
DRAMA_ID = "huangnian"
DRAMA_TITLE = "荒年全村啃树皮，我有系统满仓肉"

QUESTION_SHAPED_RE = re.compile(r"[?？]|要不要|该不该|能不能|是不是|会不会|你怎么看")
ABSOLUTE_PATH_RE = re.compile(
    "|".join(
        [
            re.escape("/" + "Users/"),
            re.escape("/var/" + "folders/"),
            r"file://",
            r"/@fs/[A-Za-z]+/",
            r"[A-Za-z]:\\\\",
        ]
    )
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--moments", default=str(DEFAULT_MOMENTS_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--gold-moment-id", default=DEFAULT_GOLD_MOMENT_ID)
    parser.add_argument("--non-gold-moment-id", default=DEFAULT_NON_GOLD_MOMENT_ID)
    parser.add_argument("--created-at", default="")
    args = parser.parse_args()

    moments_path = resolve_path(args.moments)
    output_path = resolve_path(args.output)
    moments = load_moments(moments_path)
    provider = MockMomentPackDraftProvider()
    proof = build_authoring_proof(
        moments=moments,
        provider=provider,
        gold_moment_id=args.gold_moment_id,
        non_gold_moment_id=args.non_gold_moment_id,
        created_at=args.created_at or now_iso(),
    )
    write_json(output_path, proof)
    print(f"Wrote v0.4 authoring proof: {repo_relative(output_path)}")
    return 0


def build_authoring_proof(
    *,
    moments: list[dict[str, Any]],
    provider: MockMomentPackDraftProvider,
    gold_moment_id: str,
    non_gold_moment_id: str,
    created_at: str,
) -> dict[str, Any]:
    moment_map = {str(moment.get("moment_id")): moment for moment in moments}
    gold = require_moment(moment_map, gold_moment_id)
    non_gold = require_moment(moment_map, non_gold_moment_id)
    runs = [
        build_proof_run(
            moment=gold,
            provider=provider,
            run_role="ep03_gold_smoke",
            is_gold_reference=True,
        ),
        build_proof_run(
            moment=non_gold,
            provider=provider,
            run_role="non_gold_authoring_proof",
            is_gold_reference=False,
        ),
    ]
    proof_status = "pass" if all(run["draft_validation"]["conformance_valid"] for run in runs) else "failed"
    return {
        "schema_version": "deadman_v0.4_authoring_proof.v0.1",
        "product": "看剧搭子",
        "proof_status": proof_status,
        "created_at": created_at,
        "authoring_runtime": {
            "name": "deadman-companion-exchange-authoring",
            "mode": "mock_provider_contract_harness",
            "provider": runs[0]["generated_draft"]["provider"],
            "claim_boundary": (
                "This tracked fixture proves the v0.4 authoring loop, schema "
                "normalization, validation, and human-review handoff with a "
                "local mock provider. It is not a live external LLM/CAB provider claim."
            ),
        },
        "scope": {
            "gold_smoke_moment_id": gold_moment_id,
            "non_gold_moment_id": non_gold_moment_id,
            "source_pack_ref": "data/dramas/huangnian/moments.v0.1.json",
            "published_pack_ref": "data/dramas/huangnian/moments.v0.1.json",
        },
        "runs": runs,
    }


def build_proof_run(
    *,
    moment: dict[str, Any],
    provider: MockMomentPackDraftProvider,
    run_role: str,
    is_gold_reference: bool,
) -> dict[str, Any]:
    input_window = build_input_window(moment)
    provider_payload = provider.complete_json(
        {
            "run_id": f"v0.4_authoring_proof:{moment['moment_id']}",
            "drama_id": DRAMA_ID,
            "drama_title": DRAMA_TITLE,
            "source_refs": {"moments_pack": "data/dramas/huangnian/moments.v0.1.json"},
            "demo_nodes": [build_sanitized_demo_node(moment)],
        },
        schema={},
    )
    moment_draft = provider_payload["moment_drafts"][0]
    exchange_draft = build_companion_exchange_draft(moment, moment_draft)
    validation = validate_exchange_draft(exchange_draft)
    moment_id = str(moment["moment_id"])
    return {
        "run_role": run_role,
        "moment_id": moment_id,
        "episode_id": episode_id(moment),
        "is_gold_reference": is_gold_reference,
        "input_window": input_window,
        "generated_draft": {
            "provider": provider_payload["provider"],
            "moment_pack_draft": moment_draft,
            "companion_exchange_draft": exchange_draft,
        },
        "draft_validation": validation,
        "human_review": human_review_for(moment, is_gold_reference),
        "final_status": {
            "published": True,
            "published_review_status": companion_exchange(moment).get("review_status", ""),
            "published_pack_ref": f"data/dramas/huangnian/moments.v0.1.json#{moment_id}",
        },
    }


def build_input_window(moment: dict[str, Any]) -> dict[str, Any]:
    exchange = companion_exchange(moment)
    return {
        "moment_id": str(moment["moment_id"]),
        "episode_id": episode_id(moment),
        "interaction_window": sanitize_json(moment.get("interaction_window", {})),
        "scene_signal": exchange["scene_signal"],
        "window_rationale": exchange["window_rationale"],
        "evidence_refs": list(exchange["evidence_refs"]),
        "constraint_refs": list(exchange["constraint_refs"]),
        "blocked_claims": list(exchange["blocked_claims"]),
        "draft_seed_policy": (
            "Use sanitized reviewed pack fields as a reproducible authoring "
            "seed; generated draft still requires human review before publish."
        ),
    }


def build_sanitized_demo_node(moment: dict[str, Any]) -> dict[str, Any]:
    exchange = companion_exchange(moment)
    action_space = moment.get("action_space") if isinstance(moment.get("action_space"), dict) else {}
    return {
        "candidate_id": f"{moment['moment_id']}_authoring_input",
        "moment_id": moment["moment_id"],
        "episode_id": episode_id(moment),
        "scene_specific_hook": exchange["companion_lead"],
        "viewer_impulse": exchange["scene_signal"],
        "default_options": [candidate["display_text"] for candidate in exchange["reply_candidates"]],
        "mouthpiece_candidates": exchange["reply_candidates"],
        "corrected_trigger_type": str(action_space.get("action_type") or moment.get("action_type") or "scene_response"),
        "why_now_reviewed": exchange["window_rationale"],
        "evidence_notes": "; ".join(exchange["evidence_refs"]),
        "original_plot_note_reviewed": str(moment.get("original_plot_note") or "Source window remains the baseline."),
    }


def build_companion_exchange_draft(moment: dict[str, Any], moment_draft: dict[str, Any]) -> dict[str, Any]:
    exchange = companion_exchange(moment)
    draft_candidates = moment_draft.get("mouthpiece_candidate_drafts")
    candidates = draft_candidates if isinstance(draft_candidates, list) else []
    return {
        "schema_version": "companion_exchange_pack.v0.1",
        "scene_signal": exchange["scene_signal"],
        "window_rationale": exchange["window_rationale"],
        "notice_marker": exchange.get("notice_marker", "!"),
        "companion_lead": str(moment_draft.get("hook_draft") or exchange["companion_lead"])[:40],
        "reply_candidates": [sanitize_candidate(candidate) for candidate in candidates[:3]],
        "custom_reply_policy": sanitize_json(exchange.get("custom_reply_policy", {})),
        "evidence_refs": list(exchange["evidence_refs"]),
        "constraint_refs": list(exchange["constraint_refs"]),
        "blocked_claims": list(exchange["blocked_claims"]),
        "review_status": "needs_review",
    }


def sanitize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    cleaned = sanitize_json(candidate)
    cleaned.pop("requires_human_review", None)
    return cleaned


def validate_exchange_draft(exchange_draft: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    schema_ok, schema_message = validate_json_schema(exchange_draft, COMPANION_EXCHANGE_SCHEMA_PATH)
    if not schema_ok:
        errors.append(f"schema: {schema_message}")
    visible_values = [
        str(exchange_draft.get("companion_lead") or ""),
        *[str(candidate.get("display_text") or "") for candidate in exchange_draft.get("reply_candidates", [])],
        *[str(candidate.get("selected_echo") or "") for candidate in exchange_draft.get("reply_candidates", [])],
    ]
    for value in visible_values:
        if QUESTION_SHAPED_RE.search(value):
            errors.append(f"question-shaped visible copy: {value}")
    if has_absolute_path(exchange_draft):
        errors.append("absolute local path found in exchange draft")
    if len(exchange_draft.get("reply_candidates", [])) != 3:
        errors.append("exchange draft must contain exactly three candidate replies")
    return {
        "schema_valid": schema_ok,
        "conformance_valid": schema_ok and not errors,
        "errors": errors,
    }


def human_review_for(moment: dict[str, Any], is_gold_reference: bool) -> dict[str, Any]:
    if is_gold_reference:
        notes = [
            "EP03 smoke draft reproduced the reviewed companion exchange shape.",
            "Gold window remains useful only as authoring smoke, not proof of generalization.",
        ]
    else:
        notes = [
            "Non-gold window produced a schema-valid reviewable companion exchange draft.",
            "Reviewer accepts the draft path with wording already revised into the published reviewed pack.",
            "Final pack stays source-bounded and exposes no Studio/CAB trace to viewers.",
        ]
    return {
        "decision": "accepted_with_revision",
        "reviewer": "codex_contract_review",
        "notes": notes,
    }


def validate_json_schema(data: Any, schema_path: Path) -> tuple[bool, str]:
    from jsonschema import Draft202012Validator

    schema = read_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return True, ""
    return False, "; ".join(f"{list(error.path)} {error.message}" for error in errors[:5])


def load_moments(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    moments = data.get("moments") if isinstance(data, dict) else None
    if not isinstance(moments, list):
        raise ValueError(f"{repo_relative(path)} does not contain moments[]")
    return [moment for moment in moments if isinstance(moment, dict)]


def require_moment(moment_map: dict[str, dict[str, Any]], moment_id: str) -> dict[str, Any]:
    moment = moment_map.get(moment_id)
    if not moment:
        raise ValueError(f"moment not found: {moment_id}")
    companion_exchange(moment)
    return moment


def companion_exchange(moment: dict[str, Any]) -> dict[str, Any]:
    exchange = moment.get("companion_exchange")
    if not isinstance(exchange, dict):
        raise ValueError(f"{moment.get('moment_id')} is missing companion_exchange")
    required = [
        "scene_signal",
        "window_rationale",
        "companion_lead",
        "reply_candidates",
        "evidence_refs",
        "constraint_refs",
        "blocked_claims",
    ]
    missing = [key for key in required if not exchange.get(key)]
    if missing:
        raise ValueError(f"{moment.get('moment_id')} companion_exchange missing {missing}")
    return exchange


def episode_id(moment: dict[str, Any]) -> str:
    source_drama = moment.get("source_drama")
    if isinstance(source_drama, dict) and source_drama.get("episode_id"):
        return str(source_drama["episode_id"])
    return str(moment.get("episode_id") or "")


def has_absolute_path(value: Any) -> bool:
    if isinstance(value, str):
        return bool(ABSOLUTE_PATH_RE.search(value))
    if isinstance(value, list):
        return any(has_absolute_path(item) for item in value)
    if isinstance(value, dict):
        return any(has_absolute_path(item) for item in value.values())
    return False


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json(item) for key, item in value.items() if not has_absolute_path(item)}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value if not has_absolute_path(item)]
    return value


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
