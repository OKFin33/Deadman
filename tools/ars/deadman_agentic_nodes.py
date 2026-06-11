#!/usr/bin/env python3
"""Component C — the candidate->scene bridge + window_gate for the agentic v0.4
production graph (contract step 4 node 4b + step 6 node 4a).

Two net-new pieces the existing flows don't cover:

  1. candidate_scene_context(provider, candidate) — bridge a MINED candidate
     (carries episode_id / start_ms / end_ms + drama_id) into the shared context
     node build_scene_context(provider, drama, ep, start_ms, end_ms, title).
     This is DISTINCT from deadman_run_studio_real_provider_proof._scene_context_for_case,
     which reads a curated window out of the guidance dataset (find_window_example),
     NOT a mined candidate (contract 复用-vs-新建 #6).

  2. window_gate(scene_context, candidate, provider=None) — the 4a agent判 that
     decides recommend_window / reject_window / needs_context, consuming the v0.3
     overlay's window_negatives + the direction signal (layer 'window'/'moment').
     Deterministic skeleton is testable on its own; the LLM judgment is an injectable
     hook (build the prompt, let a provider be passed in) so the graph can run det-only
     in tests and provider-backed in production.

This module only READS from deadman_author_drama_heroes (build_scene_context) and the
v0.3 overlay; it does not touch shared signatures.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]

# Same finalized v0.3 taste source the author + judge consume (closed-loop taste).
_OVERLAY_V03_PATH = REPO / "data" / "datasets" / "studio_guidance" / "studio_cab_taste_overlay.v0.3.json"

WINDOW_DECISIONS = ("recommend_window", "reject_window", "needs_context")

# v0.3 window_negatives patterns (overlay window_negatives[].pattern) routed to a gate decision.
# rejected_window / rejected_framing = a window the owner declined (don't re-open it);
# context_insufficient = not enough prior ASR to author safely (ask for more context, don't reject outright).
_REJECT_PATTERNS = frozenset({"rejected_window", "rejected_framing"})
_NEEDS_CONTEXT_PATTERNS = frozenset({"context_insufficient"})


def _load_overlay(path: Path = _OVERLAY_V03_PATH) -> dict[str, Any]:
    """Fail-CLOSED (P0-B): the gate must NOT silently pass windows without the taste spec."""
    if not path.exists():
        raise FileNotFoundError(
            f"v0.3 taste overlay missing at {path} — window_gate is fail-closed and will not gate "
            "windows without the taste spec (see docs/context/dataset-rebuild-v03-contract.md).")
    return json.loads(path.read_text(encoding="utf-8"))


_OVERLAY_V03 = _load_overlay()


def window_negatives(overlay: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The v0.3 window-layer negatives: owner-declined windows + context-insufficient calibration.
    Sourced from the top-level overlay 'window_negatives' (a window/moment-layer list, separate
    from named_negatives which only covers companion_lead/display_text/echo)."""
    src = (overlay if overlay is not None else _OVERLAY_V03).get("window_negatives", [])
    return [w for w in src if isinstance(w, dict)]


# ---------------------------------------------------------------------------
# (1) candidate -> scene bridge  (contract node 4b)
# ---------------------------------------------------------------------------

def _candidate_field(candidate: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """First present, non-empty value among keys, looking at the candidate top level then
    its source_drama / interaction_window sub-dicts (a mined candidate may be flat or moment-shaped)."""
    nests = [candidate]
    for nest_key in ("source_drama", "interaction_window"):
        nest = candidate.get(nest_key)
        if isinstance(nest, dict):
            nests.append(nest)
    for source in nests:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
    return default


def _ms(value: Any) -> int:
    """Coerce a candidate time field to int milliseconds. *_seconds fields are scaled up;
    *_ms / *_millis fields pass through."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def resolve_candidate_window(candidate: dict[str, Any]) -> dict[str, Any]:
    """Extract (drama, episode_id, start_ms, end_ms, drama_title) from a mined candidate.

    Accepts both the flat mined shape (episode_id / start_ms / end_ms / drama_id, see
    deadman_studio_cab_loop_spike.py:54) and the moment shape (source_drama.episode_id +
    interaction_window.start_seconds/end_seconds). drama is taken from drama_id, falling back
    to the episode_id prefix (yunmiao_ep17 -> yunmiao), matching the proof bridge's heuristic."""
    episode_id = str(_candidate_field(candidate, "episode_id", default="") or "")
    drama = str(_candidate_field(candidate, "drama_id", "drama", default="") or "")
    if not drama and episode_id:
        drama = episode_id.split("_")[0]
    start_ms = _ms(_candidate_field(candidate, "start_ms", "start_millis", default=None))
    if not start_ms:
        start_ms = _ms(_candidate_field(candidate, "start_seconds", default=0)) * 1000
    end_ms = _ms(_candidate_field(candidate, "end_ms", "end_millis", default=None))
    if not end_ms:
        end_ms = _ms(_candidate_field(candidate, "end_seconds", default=0)) * 1000
    title = str(_candidate_field(candidate, "drama_title", "title", default="") or "")
    if not title:
        sd = candidate.get("source_drama")
        if isinstance(sd, dict):
            title = str(sd.get("title") or "")
    return {"drama": drama, "episode_id": episode_id, "start_ms": start_ms,
            "end_ms": end_ms, "drama_title": title or drama}


def candidate_scene_context(provider: Any, candidate: dict[str, Any]) -> dict[str, Any]:
    """Bridge a mined candidate -> the shared context node build_scene_context.

    NEW (contract 复用-vs-新建 #6): the proof flow's _scene_context_for_case sources a curated
    window from guidance (find_window_example); this sources from the mined candidate's own
    episode_id/start_ms/end_ms so a freshly-mined window (no guidance entry yet) still gets the
    same knowledge-horizon-gated layered context the hero flow builds."""
    from tools.ars.deadman_author_drama_heroes import build_scene_context

    win = resolve_candidate_window(candidate)
    return build_scene_context(
        provider, win["drama"], win["episode_id"],
        win["start_ms"], win["end_ms"], win["drama_title"],
        # P0-B: this is the production-graph context node — the committed synopsis + episode-memory
        # grounding is fail-CLOSED here (raise if absent) so the layered context cannot silently no-op.
        require_grounding=True,
    )


# ---------------------------------------------------------------------------
# (2) window_gate  (contract node 4a)
# ---------------------------------------------------------------------------

def _scene_context_thin(scene_context: dict[str, Any]) -> bool:
    """Deterministic 'not enough to author' signal: no synthesized beat AND no prior-window ASR
    means the context node had nothing to ground on (knowledge horizon empty at this position)."""
    if not isinstance(scene_context, dict):
        return True
    whats = str(scene_context.get("whats_happening") or "").strip()
    prior = scene_context.get("prior_window_asr") or []
    return not whats and not prior


def deterministic_window_gate(scene_context: dict[str, Any], candidate: dict[str, Any],
                              overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    """The det skeleton of node 4a: a rule over the v0.3 window_negatives + the direction signal.

    Rules (in order):
      - candidate item_id matches a v0.3 window_negative whose pattern is a reject pattern
        (rejected_window / rejected_framing) -> reject_window (owner already declined this shape).
      - candidate matches a context_insufficient window_negative, OR scene_context is too thin
        to author from -> needs_context.
      - otherwise -> recommend_window.

    Returns a decision dict (decision + reason + the matched negative + window_negatives_count)
    that the graph routes on and that the LLM hook can override/confirm."""
    negatives = window_negatives(overlay)
    item_id = str(_candidate_field(candidate, "item_id", "candidate_id", "moment_id", default="") or "")
    matched = next((w for w in negatives if item_id and w.get("item_id") == item_id), None)
    pattern = str((matched or {}).get("pattern") or "")

    if matched and pattern in _REJECT_PATTERNS:
        decision, reason = "reject_window", f"v0.3 window_negative match (pattern={pattern})"
    elif (matched and pattern in _NEEDS_CONTEXT_PATTERNS) or _scene_context_thin(scene_context):
        decision = "needs_context"
        reason = (f"v0.3 window_negative match (pattern={pattern})" if matched
                  else "scene_context too thin to author (no beat + no prior ASR)")
    else:
        decision, reason = "recommend_window", "no v0.3 window_negative match; context present"

    return {
        "decision": decision,
        "reason": reason,
        "matched_negative": ({"item_id": matched.get("item_id"), "pattern": pattern,
                              "note": matched.get("note")} if matched else None),
        "window_negatives_count": len(negatives),
        "direction_signal": "window",  # the overlay layer this gate consumes
        "source": "deterministic",
    }


def build_window_gate_prompt(scene_context: dict[str, Any], candidate: dict[str, Any],
                             overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    """The LLM half of node 4a (injectable): an agent判 prompt that decides open/reject/needs-context
    for THIS window, given the v0.3 window_negatives as failure SITUATIONS to avoid. Built so a provider
    can be injected; the deterministic gate runs with no provider at all."""
    negatives = window_negatives(overlay)
    win = resolve_candidate_window(candidate)
    return {
        "system_prompt": (
            "You are a Deadman Studio/CAB window gate for 看剧搭子. Decide whether THIS scene window is "
            "worth opening a companion beat on. Return exactly one strict JSON object, no prose. "
            "recommend_window only when there is a real, in-scene feeling a viewer would want to chime in on; "
            "reject_window when the window is mechanism-only / a duplicate of a stronger beat in the same "
            "episode / an action-menu framing; needs_context when the prior context is too thin to judge safely."),
        "task": "window_gate.decide", "product": "看剧搭子",
        "window": win,
        "scene_context": scene_context,
        "v03_window_negatives": [
            {"pattern": w.get("pattern"), "note": w.get("note")} for w in negatives
        ],
        "direction_signal": "window",
        "decision_rules": [
            "Avoid the failure SITUATIONS named in v03_window_negatives — each .pattern/.note names a kind "
            "of window the owner has declined (rejected_window = duplicate/weaker beat in-episode; "
            "rejected_framing = action-menu/RPG surface; context_insufficient = not enough prior ASR).",
            "Respect the KNOWLEDGE HORIZON in scene_context — judge only on what the viewer knows by this "
            "window; do not justify the window with a later reveal.",
            "If prior context is thin or absent, prefer needs_context over guessing.",
        ],
        "output_contract": {
            "window_decision": "recommend_window|reject_window|needs_context",
            "rationale_summary": "short sanitized reason",
        },
    }


def normalize_gate_decision(value: Any) -> str:
    decision = str(value or "")
    return decision if decision in WINDOW_DECISIONS else "needs_context"


def window_gate(scene_context: dict[str, Any], candidate: dict[str, Any],
                provider: Any = None, overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    """Node 4a: gate a mined candidate window into recommend_window / reject_window / needs_context.

    Deterministic-first: the det rule (v0.3 window_negatives + thin-context check) always runs and
    is the answer when no provider is injected (and is authoritative on a hard reject). When a provider
    IS injected, its judgment is consulted on otherwise-recommendable windows so the agent can still
    decline a mechanism-only beat the det rule has no negative for; a provider failure FAILS SAFE to
    needs_context (never silently recommends). The returned decision is always one of WINDOW_DECISIONS."""
    det = deterministic_window_gate(scene_context, candidate, overlay)
    if provider is None or det["decision"] == "reject_window":
        return det  # det reject is authoritative; no provider => det-only

    prompt = build_window_gate_prompt(scene_context, candidate, overlay)
    try:
        result = provider.complete_case(prompt, _gate_output_schema())
        payload = result.get("payload") if isinstance(result, dict) else {}
        llm_decision = normalize_gate_decision((payload or {}).get("window_decision"))
        rationale = str((payload or {}).get("rationale_summary") or "")
    except Exception as exc:  # noqa: BLE001 - fail safe, never silently recommend
        out = dict(det)
        out.update(decision="needs_context", source="llm_unavailable",
                   reason=f"window_gate provider unavailable: {type(exc).__name__}")
        return out

    out = dict(det)
    out.update(decision=llm_decision, source="llm", llm_rationale=rationale,
               deterministic_decision=det["decision"])
    return out


def _gate_output_schema() -> dict[str, Any]:
    return {
        "title": "Deadman Window Gate Decision",
        "type": "object",
        "required": ["window_decision", "rationale_summary"],
        "properties": {
            "window_decision": {"type": "string"},
            "rationale_summary": {"type": "string"},
        },
    }
