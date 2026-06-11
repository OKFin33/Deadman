#!/usr/bin/env python3
"""Drama-generic promote node: accepted companion_exchange drafts -> moments.v0.1.json.

This is contract step 8 (`agentic-production-graph-contract.md`) — the net-new
promote node. It is deliberately NOT `build_drama_context`:

  - `build_drama_context` emits legacy `companion_surface.hook` (0 companion_exchange)
    and is huangnian-pinned via DRAMA_CONFIG (other drama ids raise).
  - this node emits a v0.4 `CompanionExchangePack` (companion_exchange + mouthpiece
    alias) per `docs/CompanionExchangePack_v0.1_Contract.md`, for ANY drama id.

It takes the loop/author output — per-window drafts of the shape
`{moment_id|window_id, companion_lead, reply_candidates:[{display_text,
viewer_motivation, selected_echo, emotion_role, semantic_role, ...}]}` — plus a
review-decision token, and writes the validated companion_exchange onto the
matching moment in `data/dramas/{drama}/moments.v0.1.json`.

P1-A (binding): `review_status=reviewed` may be stamped ONLY when the token is an
approve token from the owner gate. Without an approve token the promoted exchange
stays in a draft state — the node refuses to silently fake an owner review.

Emit-only: the moment scaffolding (source_window, interaction_window, source_drama,
review_state, ...) must already exist on the target moment. This node owns the
`companion_exchange` block and its `action_space.mouthpiece_candidates` alias; it
does not invent reviewed source-window provenance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
    from deadman_backfill_judgment_fields import backfill_moment
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
    from .deadman_backfill_judgment_fields import backfill_moment


REPO_ROOT = find_deadman_root(__file__)

SCHEMA_VERSION = "companion_exchange_pack.v0.1"
MOUTHPIECE_SCHEMA_VERSION = "mouthpiece_candidates.v0.1"
REVIEWED_STATUS = "reviewed"
DRAFT_STATUS = "draft"

# Scene-context lives in a SIDECAR (scene_context.v0.1.json) next to moments.v0.1.json — never
# inside the promoted companion_exchange. Keeping moments.v0.1.json free of the heavy L0–L3 blob
# keeps the reviewed packs byte-stable and out of the public list/summary payload; the runtime
# (pack_store.get_moment) re-attaches it to companion_exchange.scene_context in memory.
SIDECAR_SCHEMA_VERSION = "scene_context.v0.1"
SIDECAR_FILENAME = "scene_context.v0.1.json"

# Only these tokens are owner approvals that may stamp `reviewed` (P1-A). They
# mirror the `human_review_gate` interrupt/resume decision==approve token.
APPROVE_TOKENS = frozenset({"approve", "approved", "owner_approve", "owner_reviewed"})

# Pack-level defaults the contract requires to be present and non-empty. Drafts may
# override them, but a draft never has to carry the boilerplate forbidden-claim copy.
DEFAULT_BLOCKED_CLAIMS = [
    "Do not claim what happens in later episodes.",
    "Do not infer hidden motives from visual context alone.",
    "Do not turn the reply into a new story branch.",
]
DEFAULT_CONSTRAINT_REFS = ["current_scene_only", "no_future_episode_claim"]
DEFAULT_CANDIDATE_CONSTRAINT_REFS = [
    "current_scene_only",
    "no_branch_rewrite",
    "source_window_grounding",
]
DEFAULT_CUSTOM_REPLY_POLICY = {
    "allowed": True,
    "scope": "local credible consequence only",
    "reject_or_soften": [
        "continuous branch rewrite",
        "unbounded system/power escalation",
        "claims not grounded in source window",
    ],
    "runtime_personalization": "bounded",
}


class PromoteError(RuntimeError):
    """Raised when a draft cannot be promoted into a valid companion_exchange."""


# The four L1 (this-beat) fields build_scene_context() emits flat at the card top level. They get
# reshaped under the sidecar card's `l1` key so the persisted card has a clean layered shape
# (l0_canon / l1 / l2_recent_events / l3_series_spine) instead of L1 fields floating at the root.
_SCENE_CONTEXT_L1_FIELDS = ("whats_happening", "audience_already_knows", "relationship_state", "grounding_note")


def reshape_scene_context(card: dict[str, Any] | None) -> dict[str, Any] | None:
    """Reshape a build_scene_context() card into the persisted (sidecar) scene_context card shape.

    build_scene_context() returns the four L1 fields flat at the top level alongside l0_canon,
    l3_series_spine, l2_recent_events (+ prior_window_asr/knowledge_horizon). The persisted card
    (stored in the per-drama scene_context.v0.1.json sidecar, re-attached at runtime to
    companion_exchange.scene_context) nests the L1 fields under `l1`:

        {"l0_canon": {premise, protagonist},
         "l1": {whats_happening, audience_already_knows, relationship_state, grounding_note},
         "l3_series_spine": [...], "l2_recent_events": [...]}

    Returns None for a None/non-dict/empty card so callers persist a card only when there is content
    (never write an empty scene_context). prior_window_asr/knowledge_horizon are carried through when
    present.
    """
    if not isinstance(card, dict) or not card:
        return None
    l1 = {field: card[field] for field in _SCENE_CONTEXT_L1_FIELDS if field in card}
    shaped: dict[str, Any] = {
        "l0_canon": card.get("l0_canon") or {},
        "l1": l1,
        "l3_series_spine": list(card.get("l3_series_spine") or []),
        "l2_recent_events": list(card.get("l2_recent_events") or []),
    }
    for carry in ("prior_window_asr", "knowledge_horizon"):
        if card.get(carry):
            shaped[carry] = card[carry]
    return shaped


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_backfill_template() -> dict[str, Any]:
    template_path = REPO_ROOT / "data" / "dramas" / "huangnian" / "moments.v0.1.json"
    template_pack = load_json(template_path)
    moments = template_pack.get("moments") if isinstance(template_pack, dict) else None
    if not isinstance(moments, list) or not moments or not isinstance(moments[0], dict):
        raise PromoteError(f"runtime field template is missing or invalid: {template_path}")
    return moments[0]


def pack_path_for(drama_id: str, *, data_root: Path | None = None) -> Path:
    root = data_root or (REPO_ROOT / "data" / "dramas")
    return root / drama_id / "moments.v0.1.json"


def is_approve_token(token: str | None) -> bool:
    """A token grants owner-reviewed promotion only when it is an approve token (P1-A)."""
    return bool(token) and str(token).strip().lower() in APPROVE_TOKENS


def resolved_review_status(token: str | None) -> str:
    """reviewed iff a real approve token is presented; otherwise the default draft state."""
    return REVIEWED_STATUS if is_approve_token(token) else DRAFT_STATUS


def _str(value: Any) -> str:
    return str(value or "").strip()


def _draft_moment_id(draft: dict[str, Any]) -> str:
    return _str(draft.get("moment_id") or draft.get("window_id") or draft.get("item_id"))


def build_reply_candidate(
    index: int,
    reply: dict[str, Any],
    *,
    moment_id: str,
    action_type: str,
    evidence_refs: list[str],
    constraint_refs: list[str],
) -> dict[str, Any]:
    """Map one accepted draft reply into a contract-shaped reply candidate."""
    display_text = _str(reply.get("display_text"))
    if not display_text:
        raise PromoteError(f"{moment_id} reply_candidates[{index}] is missing display_text")
    selected_echo = _str(reply.get("selected_echo"))
    if not selected_echo:
        raise PromoteError(f"{moment_id} reply_candidates[{index}] is missing selected_echo")
    semantic_role = _str(reply.get("semantic_role")) or f"stance_{index}"
    viewer_motivation = _str(reply.get("viewer_motivation"))
    distinctness = (
        _str(reply.get("distinctness_rationale"))
        or viewer_motivation
        or f"Distinct viewer posture {index + 1} into this beat."
    )
    candidate: dict[str, Any] = {
        "candidate_id": _str(reply.get("candidate_id")) or f"preset_{index}",
        "display_text": display_text,
        "action_payload": {
            "text": _str(reply.get("action_payload_text")) or display_text,
            "action_type": action_type,
            "intent": semantic_role,
            "target_actors": list(reply.get("target_actors") or ["scene_focus"]),
            "risk_posture": _str(reply.get("risk_posture")) or "balanced",
        },
        "emotion_role": _str(reply.get("emotion_role")),
        "semantic_role": semantic_role,
        "distinctness_rationale": distinctness,
        "evidence_refs": list(reply.get("evidence_refs") or evidence_refs),
        "constraint_refs": list(reply.get("constraint_refs") or constraint_refs),
        "selected_echo": selected_echo,
    }
    if viewer_motivation:
        candidate["viewer_motivation"] = viewer_motivation
    # friend_voice_seed mirrors the reviewed echo, matching existing reviewed packs.
    candidate["friend_voice_seed"] = selected_echo
    return candidate


def build_companion_exchange(
    draft: dict[str, Any],
    moment: dict[str, Any],
    *,
    review_token: str | None,
) -> dict[str, Any]:
    """Assemble a contract-valid companion_exchange from an accepted per-window draft.

    `review_token` is the ONLY thing that can produce `review_status=reviewed` (P1-A).
    """
    moment_id = _draft_moment_id(draft) or _str(moment.get("moment_id"))
    lead = _str(draft.get("companion_lead"))
    if not lead:
        raise PromoteError(f"{moment_id} draft is missing companion_lead")

    replies = draft.get("reply_candidates")
    if not isinstance(replies, list) or len(replies) != 3:
        count = len(replies) if isinstance(replies, list) else "non-list"
        raise PromoteError(
            f"{moment_id} draft must carry exactly 3 reply_candidates (got {count}); "
            "Studio/CAB drafts curate down to three before promotion"
        )

    existing = moment.get("companion_exchange") if isinstance(moment.get("companion_exchange"), dict) else {}
    action_space = moment.get("action_space") if isinstance(moment.get("action_space"), dict) else {}
    action_type = _str(action_space.get("action_type")) or "other"

    # scene_signal + window_rationale are window-scaffold facts (they describe the window, not the
    # authored copy). The author draft carries them when available; otherwise fall back to an existing
    # exchange, then to the reviewed moment scaffold so a FRESH window (no prior exchange) still
    # produces the bridge-required non-empty fields instead of failing the gate.
    review_state = moment.get("review_state") if isinstance(moment.get("review_state"), dict) else {}
    evidence = moment.get("evidence") if isinstance(moment.get("evidence"), dict) else {}
    surface = moment.get("companion_surface") if isinstance(moment.get("companion_surface"), dict) else {}
    scene_signal = (
        _str(draft.get("scene_signal"))
        or _str(existing.get("scene_signal"))
        or _str(surface.get("hook"))
        or _str(surface.get("scene_specificity_check"))
    )
    window_rationale = (
        _str(draft.get("window_rationale"))
        or _str(existing.get("window_rationale"))
        or _str(review_state.get("evidence_notes"))
        or _str(evidence.get("notes"))
    )

    pack_evidence = (
        list(draft.get("evidence_refs") or [])
        or list(existing.get("evidence_refs") or [])
        or [f"{moment_id}_window"]
    )
    pack_constraints = (
        list(draft.get("constraint_refs") or [])
        or list(existing.get("constraint_refs") or [])
        or list(DEFAULT_CONSTRAINT_REFS)
    )
    blocked_claims = (
        list(draft.get("blocked_claims") or [])
        or list(existing.get("blocked_claims") or [])
        or list(DEFAULT_BLOCKED_CLAIMS)
    )
    candidate_evidence = pack_evidence or [f"{moment_id}_window"]
    candidate_constraints = list(DEFAULT_CANDIDATE_CONSTRAINT_REFS)

    candidates = [
        build_reply_candidate(
            index,
            reply if isinstance(reply, dict) else {},
            moment_id=moment_id,
            action_type=action_type,
            evidence_refs=candidate_evidence,
            constraint_refs=candidate_constraints,
        )
        for index, reply in enumerate(replies)
    ]

    seen_ids: set[str] = set()
    seen_roles: set[str] = set()
    for index, candidate in enumerate(candidates):
        if candidate["candidate_id"] in seen_ids:
            raise PromoteError(f"{moment_id} reply_candidates[{index}] has duplicate candidate_id")
        seen_ids.add(candidate["candidate_id"])
        if candidate["semantic_role"] in seen_roles:
            raise PromoteError(f"{moment_id} reply_candidates[{index}] has duplicate semantic_role")
        seen_roles.add(candidate["semantic_role"])

    policy = draft.get("custom_reply_policy")
    if not isinstance(policy, dict):
        policy = existing.get("custom_reply_policy")
    if not isinstance(policy, dict):
        policy = dict(DEFAULT_CUSTOM_REPLY_POLICY)

    exchange: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scene_signal": scene_signal,
        "window_rationale": window_rationale,
        "notice_marker": "!",
        "companion_lead": lead,
        "reply_candidates": candidates,
        "custom_reply_policy": policy,
        "evidence_refs": pack_evidence,
        "constraint_refs": pack_constraints,
        "blocked_claims": blocked_claims,
        "review_status": resolved_review_status(review_token),
    }
    # NOTE: scene_context is NEVER written into the promoted exchange. When a draft carries a
    # build_scene_context() card it goes into the per-drama SIDECAR (see draft_scene_context_card +
    # write_scene_context_sidecar), keyed by moment_id, so moments.v0.1.json stays byte-stable and
    # free of the heavy L0–L3 blob. The runtime re-attaches it at fetch time.
    return exchange


def draft_scene_context_card(draft: dict[str, Any]) -> dict[str, Any] | None:
    """Return the reshaped scene_context card a draft carries, for sidecar persistence, or None.

    The card lives in the SIDECAR, never in the promoted companion_exchange. Returns None when the
    draft has no card (so the sidecar is not touched for that moment)."""
    return reshape_scene_context(
        draft.get("scene_context") if isinstance(draft.get("scene_context"), dict) else None
    )


def sidecar_path_for(drama_id: str, *, data_root: Path | None = None) -> Path:
    """Path to the per-drama scene_context sidecar, alongside moments.v0.1.json."""
    root = data_root or (REPO_ROOT / "data" / "dramas")
    return root / drama_id / SIDECAR_FILENAME


def write_scene_context_sidecar(
    drama_id: str,
    cards_by_moment_id: dict[str, dict[str, Any]],
    *,
    data_root: Path | None = None,
) -> Path:
    """Merge the given moment_id -> card mapping into the per-drama scene_context sidecar.

    Existing entries for other moment ids are preserved; promoted moments' cards are overwritten.
    A missing/corrupt sidecar is treated as empty (and rewritten). Returns the sidecar path."""
    path = sidecar_path_for(drama_id, data_root=data_root)
    sidecar: dict[str, Any] = {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "drama_id": drama_id,
        "scene_context": {},
    }
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("scene_context"), dict):
                sidecar = existing
        except (json.JSONDecodeError, OSError):
            pass  # corrupt sidecar -> start fresh; the merge below repopulates it
    sidecar.setdefault("scene_context", {})
    sidecar["scene_context"].update(cards_by_moment_id)
    path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def mouthpiece_alias(exchange: dict[str, Any]) -> dict[str, Any]:
    """Derive the temporary `mouthpiece_candidates` alias from reply_candidates."""
    alias = []
    for candidate in exchange["reply_candidates"]:
        alias.append(
            {
                "candidate_id": candidate["candidate_id"],
                "display_text": candidate["display_text"],
                "action_payload": candidate["action_payload"],
                "emotion_role": candidate["emotion_role"],
                "semantic_role": candidate["semantic_role"],
                "distinctness_rationale": candidate["distinctness_rationale"],
                "evidence_refs": candidate["evidence_refs"],
                "constraint_refs": candidate["constraint_refs"],
                "selected_echo": candidate["selected_echo"],
            }
        )
    return {
        "mouthpiece_candidates_schema_version": MOUTHPIECE_SCHEMA_VERSION,
        "mouthpiece_candidates": alias,
    }


def apply_to_moment(moment: dict[str, Any], exchange: dict[str, Any]) -> None:
    """Write the exchange + mouthpiece alias + legacy lead onto a moment in place."""
    moment["companion_exchange"] = exchange
    action_space = moment.setdefault("action_space", {})
    alias = mouthpiece_alias(exchange)
    action_space.update(alias)
    action_space["default_options"] = [c["action_payload"]["text"] for c in exchange["reply_candidates"]]
    # Keep legacy companion_surface lead in sync (compatibility only; not required by frontstage).
    surface = moment.setdefault("companion_surface", {})
    surface["companion_lead"] = exchange["companion_lead"]
    surface["notice_marker"] = "!"


def promote_pack(
    drama_id: str,
    drafts: list[dict[str, Any]],
    *,
    review_token: str | None = None,
    data_root: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Promote accepted per-window drafts into the drama's moments pack.

    Returns a summary dict. With `write=False` the pack is assembled and validated
    in memory but not persisted (useful for dry-runs and tests).

    Drama-generic: works for any drama_id whose `moments.v0.1.json` exists. The node
    matches each draft to a moment by `moment_id`/`window_id` and owns only the
    `companion_exchange` block (+ mouthpiece alias). It never fabricates the reviewed
    source-window scaffolding that other gate checks depend on.
    """
    if not drafts:
        raise PromoteError("no accepted drafts to promote")

    path = pack_path_for(drama_id, data_root=data_root)
    if not path.exists():
        raise PromoteError(f"moments pack not found for drama '{drama_id}': {path}")
    pack = load_json(path)
    moments = pack.get("moments")
    if not isinstance(moments, list):
        raise PromoteError(f"{path} has no moments list")
    by_id = {_str(m.get("moment_id")): m for m in moments if isinstance(m, dict)}

    review_status = resolved_review_status(review_token)
    promoted: list[str] = []
    scene_cards: dict[str, dict[str, Any]] = {}
    runtime_template = runtime_backfill_template()
    runtime_backfilled_fields: set[str] = set()
    for draft in drafts:
        moment_id = _draft_moment_id(draft)
        if not moment_id:
            raise PromoteError("draft is missing moment_id/window_id")
        moment = by_id.get(moment_id)
        if moment is None:
            raise PromoteError(
                f"draft moment_id '{moment_id}' has no matching moment in {path.name}; "
                "the reviewed source-window scaffold must exist before promotion"
            )
        exchange = build_companion_exchange(draft, moment, review_token=review_token)
        apply_to_moment(moment, exchange)
        runtime_backfilled_fields.update(backfill_moment(moment, runtime_template))
        promoted.append(moment_id)
        # A scene_context card on the draft goes to the SIDECAR, never into the promoted moment.
        card = draft_scene_context_card(draft)
        if card:
            scene_cards[moment_id] = card

    # Drop un-authored scaffold moments (windows the owner REJECTED at the review gate, or never
    # authored) so the published pack contains ONLY real, consumable moments. Accepted + already-
    # reviewed moments keep their reply_candidates; only the empties go. Otherwise Stage renders a
    # stray marker (an extra red dot, tappable but empty) for a window that was rejected.
    kept = [m for m in moments if (m.get("companion_exchange") or {}).get("reply_candidates")]
    dropped = [_str(m.get("moment_id")) for m in moments if m not in kept]
    if dropped:
        pack["moments"] = kept
        if "moment_count" in pack:
            pack["moment_count"] = len(kept)

    sidecar_written: str | None = None
    if write:
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if scene_cards:
            sidecar_written = str(
                write_scene_context_sidecar(drama_id, scene_cards, data_root=data_root)
            )

    return {
        "drama_id": drama_id,
        "pack_path": str(path),
        "review_status": review_status,
        "owner_reviewed": review_status == REVIEWED_STATUS,
        "promoted_moment_ids": promoted,
        "dropped_unauthored_moment_ids": dropped,
        "runtime_backfilled_fields": sorted(runtime_backfilled_fields),
        "scene_context_sidecar": sidecar_written,
        "written": write,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-id", required=True)
    parser.add_argument(
        "--drafts",
        required=True,
        help="Path to a JSON file: a single draft object or a list of accepted drafts.",
    )
    parser.add_argument(
        "--review-token",
        default="",
        help="Owner gate decision token. Only an approve token (approve/owner_reviewed/...) "
        "stamps review_status=reviewed (P1-A); otherwise the exchange stays draft.",
    )
    parser.add_argument("--data-root", default="", help="Override data/dramas root (for tests).")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing the pack.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = load_json(Path(args.drafts))
    drafts = raw if isinstance(raw, list) else [raw]
    data_root = Path(args.data_root) if args.data_root else None
    result = promote_pack(
        args.drama_id,
        drafts,
        review_token=args.review_token or None,
        data_root=data_root,
        write=not args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
