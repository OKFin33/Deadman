#!/usr/bin/env python3
"""The agentic v0.4 production graph (contract `agentic-production-graph-contract.md`,
节点流 step 4/5/8/9): a LangGraph StateGraph that takes an ALREADY-ASR'd drama and
drives it through

    build_episode_memory -> propose_windows -> [per-window self-correction loop] ->
    collect accepted drafts -> owner_review_gate (interrupt/resume) -> promote -> final_report

reusing the three landed components + the shared v0.4 authoring core:

  - Component C (deadman_agentic_nodes): window_gate (4a) + candidate->scene bridge (4b).
  - Shared core (deadman_author_drama_heroes): author_moment = stage_a_prompt (4c) +
    stage_b_prompt (4d) over a scene_context built ONCE per window (contract P1-B: cached,
    reused across revise rounds — never re-entered per round).
  - taste judge (deadman_run_studio_taste_judge): build_judge_prompt (4e, v0.3) +
    normalize_verdict; the self-correction loop turns its needs_repair dims into DIRECTED
    feedback (Component A: lead/reply->Stage A, echo->Stage B).
  - Component B (deadman_promote_companion_pack): drama-generic promote -> moments.v0.1.json,
    stamped reviewed ONLY from the owner_review_gate's approve token (P1-A).

What this graph deliberately does NOT do yet: ingest + ASR (step 7) and brand-new-drama
reviewed-window scaffolding. Those are a later thin front wrapper; this phase runs the
production line on a drama that is already ASR'd and already has reviewed window moments.

Providers are injectable. `author_provider` drives the context + Stage A/B authoring,
`judge_provider` drives taste_judge, and an optional `window_gate_provider` consults the
window gate. A fake/mock provider (one object implementing the relevant protocols) lets
the whole graph run offline in tests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, TypedDict

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_MAX_ROUNDS = 2

# Verdict constants + directed-feedback signal + the self-correction loop all live in the SHARED
# author core (deadman_author_drama_heroes) so the graph and the Studio console run ONE
# implementation (DRY). Re-exported here for back-compat (graph_mod.directed_feedback) and used by
# the status mapping below.
from tools.ars.deadman_author_drama_heroes import (  # noqa: E402
    _ACCEPT_VERDICTS, _JUDGE_UNAVAILABLE, _REPAIR_DIMS, directed_feedback,
)

# per-window terminal statuses surfaced in the final report.
STATUS_ACCEPTED = "accepted"
STATUS_FLAGGED_MAX_ROUNDS = "flagged_max_rounds"
STATUS_JUDGE_UNAVAILABLE = "judge_unavailable"
STATUS_AUTHOR_UNAVAILABLE = "author_unavailable"
STATUS_WINDOW_REJECTED = "window_rejected"
STATUS_NEEDS_CONTEXT = "needs_context"


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

class ProductionState(TypedDict, total=False):
    """Clean, flat graph state. The per-window loop runs INSIDE one node (a self-contained
    sub-loop) rather than as graph-level cycles, so the main graph stays a readable line and
    the scene_context cache (P1-B) lives in plain locals — one build per window, reused across
    revise rounds."""
    drama_id: str
    drama_title: str
    pack: dict[str, Any]                 # the loaded moments.v0.1.json (in memory)
    candidates: list[dict[str, Any]]     # mined/proposed windows for this drama
    max_rounds: int
    review_token: str                    # owner gate decision token (resume payload)
    pack_decisions: dict[str, str]       # per-pack owner verdict: moment_id -> approve|reject (P1-A per-pack)
    data_root: str                       # override data/dramas root (tests)
    ingest_status: str                   # front node (A2): batch ingest (cached/skipped)
    asr_status: str                      # front node (A2): ASR (cached/skipped)
    scaffold_status: str                 # front node (A2): reviewed-window scaffold (cached/skipped)
    memory_status: str                   # episode-memory node outcome (built/cached/skipped)
    window_results: list[dict[str, Any]] # one entry per candidate window (status + trace)
    accepted_drafts: list[dict[str, Any]]
    promote_result: dict[str, Any]
    report: dict[str, Any]


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

# --- front nodes (A2): ingest -> ASR -> (propose) -> scaffold ------------------------------------
# Decision #4: the ingest/ASR front are REAL graph nodes so the run is ONE graph end-to-end and the
# viz walks upload->playable. They are IDEMPOTENT / skip-if-cached: the upload endpoint
# (/api/studio/batch) stages clips, runs ASR (so the operator can preview proposed windows), and
# builds the scaffold BEFORE the run — so on the console path these report 'cached' and the heavy
# work is never redone. For an already-curated drama they are also no-ops. They never author and
# never raise (a missing artifact degrades to 'skipped', surfaced in the report — never fatal).

def _state_drama_dir(state: ProductionState) -> Path:
    root = Path(state["data_root"]) if state.get("data_root") else (REPO / "data" / "dramas")
    return root / state["drama_id"]


def ingest_batch_node() -> Callable[[ProductionState], ProductionState]:
    """Front node: ensure the drama's clips are staged + media registered. Idempotent."""

    def node(state: ProductionState) -> ProductionState:
        return {"ingest_status": "cached" if _state_drama_dir(state).exists() else "skipped"}

    return node


def asr_node() -> Callable[[ProductionState], ProductionState]:
    """Front node: ensure each episode is transcribed. Idempotent — ASR runs at upload time so window
    proposals can preview, so this reports 'cached'. Uses the committed episode memory as the proxy."""

    def node(state: ProductionState) -> ProductionState:
        from tools.ars.deadman_build_episode_memory import out_path
        return {"asr_status": "cached" if out_path(state["drama_id"]).exists() else "skipped"}

    return node


def build_scaffold_node() -> Callable[[ProductionState], ProductionState]:
    """Front node: ensure reviewed-window scaffold moments (moments.v0.1.json) exist. Idempotent —
    the upload endpoint builds the scaffold before the run (run_production_start loads that pack), so
    this reports 'cached'. Never authors content (that is author_and_judge)."""

    def node(state: ProductionState) -> ProductionState:
        moments = _state_drama_dir(state) / "moments.v0.1.json"
        return {"scaffold_status": "cached" if moments.exists() else "skipped"}

    return node


def build_episode_memory_node() -> Callable[[ProductionState], ProductionState]:
    """Node 3 (reuse deadman_build_episode_memory). Idempotent / skip-if-cached: the memory
    file is the cache, so this node only (re)builds when it's absent. On an already-ASR'd drama
    with committed context_memory it is a no-op. Never authors — it only ensures the layered
    episode memory build_scene_context reads from exists."""

    def node(state: ProductionState) -> ProductionState:
        from tools.ars.deadman_build_episode_memory import out_path

        drama = state["drama_id"]
        if out_path(drama).exists():
            return {"memory_status": "cached"}
        # No committed memory: this phase assumes an already-prepared drama, so we don't
        # silently fabricate it inside a (possibly provider-less) graph run — flag it instead.
        return {"memory_status": "missing_uncached"}

    return node


def propose_windows_node(
    candidates_provider: Callable[[ProductionState], list[dict[str, Any]]] | None = None,
) -> Callable[[ProductionState], ProductionState]:
    """Node 4 (propose_windows). Surfaces the candidate interaction windows for this drama.

    For this phase the candidates are taken from state['candidates'] when pre-supplied (a mined
    list), else derived from the drama's existing reviewed moments (each moment IS a reviewed
    window: episode_id + interaction_window). A custom `candidates_provider` can be injected for
    a real miner. Each candidate carries moment_id + the window fields the bridge needs."""

    def node(state: ProductionState) -> ProductionState:
        if state.get("candidates"):
            return {"candidates": state["candidates"]}
        if candidates_provider is not None:
            return {"candidates": candidates_provider(state)}
        pack = state["pack"]
        drama = state["drama_id"]
        out: list[dict[str, Any]] = []
        for moment in pack.get("moments", []):
            if not isinstance(moment, dict):
                continue
            iw = moment.get("interaction_window") or {}
            sd = moment.get("source_drama") or {}
            out.append({
                "item_id": moment.get("moment_id"),
                "moment_id": moment.get("moment_id"),
                "drama_id": drama,
                "drama_title": pack.get("title"),
                "episode_id": sd.get("episode_id"),
                "start_seconds": iw.get("start_seconds"),
                "end_seconds": iw.get("end_seconds"),
            })
        return {"candidates": out}

    return node


def _run_window_loop(
    state: ProductionState,
    candidate: dict[str, Any],
    author_provider: Any,
    judge_provider: Any,
    guidance: dict[str, Any],
    *,
    max_rounds: int,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """The per-window pipeline (contract 4a/4b + the 4↺ self-correction loop).

    Order: window_gate (4a) -> build candidate->scene context ONCE (4b, P1-B) ->
    author_moment_agentic (4c/4d author -> 4e judge -> DIRECTED revise -> re-judge, bounded) ->
    map its result to the per-window terminal status.

    The author->judge->revise loop is the SHARED implementation author_moment_agentic
    (deadman_author_drama_heroes) — the SAME function the Studio console authors with (DRY). This
    node owns only the graph-specific parts: the window gate and the mined-candidate scene bridge
    (build_scene_context with require_grounding=True), and the status mapping.
    """
    from tools.ars.deadman_agentic_nodes import candidate_scene_context, window_gate
    from tools.ars.deadman_author_drama_heroes import asr_window, author_moment_agentic

    drama = state["drama_id"]
    pack = state["pack"]
    moment_id = str(candidate.get("moment_id") or candidate.get("item_id") or "")
    moment = next((m for m in pack.get("moments", []) if m.get("moment_id") == moment_id), None)
    trace: list[dict[str, Any]] = []

    # --- 4a window_gate: skip non-recommended windows (reject / needs_context) ---------------
    # gate on a thin scene proxy first; the full context build is deferred to recommended windows.
    gate_scene = {"whats_happening": candidate.get("scene_signal") or moment_id,
                  "prior_window_asr": candidate.get("prior_window_asr") or []}
    gate = window_gate(gate_scene, candidate, provider=window_gate_provider)
    trace.append({"step": "window_gate", "decision": gate["decision"], "reason": gate.get("reason")})
    if gate["decision"] == "reject_window":
        return {"moment_id": moment_id, "status": STATUS_WINDOW_REJECTED, "gate": gate, "trace": trace}
    if gate["decision"] == "needs_context":
        return {"moment_id": moment_id, "status": STATUS_NEEDS_CONTEXT, "gate": gate, "trace": trace}

    if moment is None:
        return {"moment_id": moment_id, "status": STATUS_WINDOW_REJECTED,
                "reason": "candidate has no matching reviewed moment to author onto", "trace": trace}

    # --- 4b build the mined-candidate scene context ONCE (P1-B), then run the SHARED loop ------
    # The mined-candidate bridge (require_grounding=True, fail-closed) is graph-specific; we build
    # it here and hand it to author_moment_agentic as the pre-built scene so the loop reuses the
    # SAME cached context across revise rounds (one context build per window, not per round).
    #
    # The scene build + author loop touch the author provider (Ark) and the fail-CLOSED grounding;
    # a per-window raise here (provider error / missing committed grounding) must FLAG only THIS
    # window — STATUS_AUTHOR_UNAVAILABLE — not crash the whole drama run. This mirrors the explicit
    # judge_unavailable flag below: a degraded author is surfaced in the report, never swallowed and
    # never fatal. (The author core's overlay fail-CLOSED invariant is unaffected — that still raises
    # at import; this guards the per-window provider/grounding call.)
    try:
        scene_context = candidate_scene_context(author_provider, candidate)
        iw = moment.get("interaction_window") or {}
        sw = moment.get("source_window") or {}
        ep = (moment.get("source_drama") or {}).get("episode_id") or candidate.get("episode_id") or ""
        # Ground on the BEAT (source_window = the charged content), NOT the interaction window: under
        # react-after the "!" / interaction window sits just AFTER the beat, so reading the interaction
        # window's range would author about post-beat dialogue. source_window is the producer evidence
        # span; fall back to the interaction window (curated moments where they coincide).
        start_ms = int(sw.get("start_ms") if sw.get("start_ms") is not None
                       else float(iw.get("start_seconds") or 0) * 1000)
        end_ms = int(sw.get("end_ms") if sw.get("end_ms") is not None
                     else float(iw.get("end_seconds") or 0) * 1000)
        transcript = asr_window(drama, ep, start_ms, end_ms) or [
            (moment.get("companion_exchange") or {}).get("scene_signal", "") or moment_id]
        scene = {"case_id": f"prod:{moment_id}", "drama_id": drama, "drama_title": pack.get("title"),
                 "episode_id": ep, "transcript": transcript, "scene_context": scene_context}

        result = author_moment_agentic(
            author_provider, judge_provider, guidance, drama, pack, moment,
            max_rounds=max_rounds, judge_fn=judge_fn, scene=scene, on_progress=on_progress,
        )
    except Exception as exc:  # noqa: BLE001 - per-window author/Ark failure -> flag this window, keep going
        trace.append({"step": "author_and_judge", "error": type(exc).__name__, "reason": str(exc)})
        return {"moment_id": moment_id, "status": STATUS_AUTHOR_UNAVAILABLE,
                "reason": f"{type(exc).__name__}: {exc}", "trace": trace}
    lead = result["companion_lead"]
    rcs = result["replies"]
    draft = {"moment_id": moment_id, "companion_lead": lead, "reply_candidates": rcs}
    # Carry the build_scene_context() card (P1-B, built once for this window) onto the draft so the
    # promote node can persist it to the per-drama SIDECAR (scene_context.v0.1.json), keyed by
    # moment_id — NOT into the promoted companion_exchange (moments.v0.1.json stays free of the heavy
    # blob). Only attach when the card is non-empty; promote reshapes it into the layered l0/l1/l2/l3
    # shape, and pack_store re-attaches it at runtime fetch time.
    card = result.get("scene_context") or scene_context
    if isinstance(card, dict) and card:
        draft["scene_context"] = card
    verdict = result.get("final_verdict") or {}
    overall = str(verdict.get("overall_verdict") or "")
    trace.append({"step": "author_and_judge", "rounds": result["rounds"], "verdict": overall,
                  "judge_available": result["judge_available"],
                  "dims": {k: verdict.get(k) for k in _REPAIR_DIMS}})

    # map the shared-loop result to the graph's per-window terminal status.
    if overall == _JUDGE_UNAVAILABLE or not result["judge_available"]:
        # explicit judge_unavailable -> flag; NOT swallowed into a reject->rewrite white-burn.
        return {"moment_id": moment_id, "status": STATUS_JUDGE_UNAVAILABLE,
                "draft": draft, "verdict": verdict, "rounds": result["rounds"], "trace": trace}
    if overall in _ACCEPT_VERDICTS:
        return {"moment_id": moment_id, "status": STATUS_ACCEPTED,
                "draft": draft, "verdict": verdict, "rounds": result["rounds"], "trace": trace}
    return {"moment_id": moment_id, "status": STATUS_FLAGGED_MAX_ROUNDS,
            "draft": draft, "verdict": verdict, "rounds": result["rounds"], "trace": trace}


def author_and_judge_node(
    author_provider: Any,
    judge_provider: Any,
    guidance: dict[str, Any],
    *,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> Callable[[ProductionState], ProductionState]:
    """Nodes 4a-4e + the self-correction loop, per candidate window. Collects the accepted
    companion_exchange drafts; flags the rest with their terminal status.

    `on_progress` (optional) is threaded into the per-window author loop so a live run can publish
    the inner loop events (context_built / stage_a_done / stage_b_done / judge_verdict / revise) to
    the console viz — the SAME event stream the standalone /api/studio/author background run uses."""

    def node(state: ProductionState) -> ProductionState:
        max_rounds = int(state.get("max_rounds") or DEFAULT_MAX_ROUNDS)
        results: list[dict[str, Any]] = []
        accepted: list[dict[str, Any]] = []
        for candidate in state.get("candidates", []):
            result = _run_window_loop(
                state, candidate, author_provider, judge_provider, guidance,
                max_rounds=max_rounds, window_gate_provider=window_gate_provider, judge_fn=judge_fn,
                on_progress=on_progress,
            )
            results.append(result)
            if result["status"] == STATUS_ACCEPTED:
                accepted.append(result["draft"])
        return {"window_results": results, "accepted_drafts": accepted}

    return node


def owner_review_gate_node() -> Callable[[ProductionState], ProductionState]:
    """Node 5 (human-in-the-loop). Reuses the producer graph's interrupt/resume pattern
    (deadman_run_producer_graph.py:2571-2591 interrupt, :2843-2862 run_graph_resume): the graph
    PAUSES here for an owner decision; on resume the approve/reject token is captured into state.
    The reviewed stamp later in promote comes ONLY from this token (P1-A).

    Per-pack (contract decision #2): the resume payload may carry `pack_decisions`
    (moment_id -> "approve"|"reject") so the owner approves/rejects EACH reviewed pack from the
    split review gate; promote then writes only the approved packs. When `pack_decisions` is absent
    every accepted draft inherits the overall `decision` token (back-compat with the one-shot CLI)."""

    def node(state: ProductionState) -> ProductionState:
        from langgraph.types import interrupt

        accepted = state.get("accepted_drafts") or []
        resume_payload = interrupt({
            "status": "waiting_for_review",
            "drama_id": state.get("drama_id"),
            "accepted_count": len(accepted),
            "accepted_moment_ids": [d.get("moment_id") for d in accepted],
        })
        if not isinstance(resume_payload, dict):
            return {"review_token": "reject", "pack_decisions": {}}
        raw = resume_payload.get("pack_decisions") or {}
        pack_decisions = {str(k): str(v).strip() for k, v in raw.items()} if isinstance(raw, dict) else {}
        return {"review_token": str(resume_payload.get("decision") or "").strip(),
                "pack_decisions": pack_decisions}

    return node


def promote_node(write: bool = True) -> Callable[[ProductionState], ProductionState]:
    """Node 6 (promote, Component B). Writes the accepted companion_exchange drafts onto
    moments.v0.1.json. review_status=reviewed is stamped ONLY when the owner gate returned an
    approve token (P1-A); otherwise the exchange stays draft. No accepted drafts -> no-op."""

    def node(state: ProductionState) -> ProductionState:
        from tools.ars.deadman_promote_companion_pack import promote_pack

        accepted = state.get("accepted_drafts") or []
        decision = state.get("review_token") or None
        # Per-pack filter (contract decision #2): keep packs the owner explicitly approved at the
        # split review gate. A pack with no per-pack verdict inherits the overall decision token
        # (so the one-shot CLI / approve-all path is unchanged). Rejected packs are simply not
        # promoted — they stay absent rather than written as draft.
        pack_decisions = state.get("pack_decisions") or {}

        def _approved(d: dict[str, Any]) -> bool:
            verdict = pack_decisions.get(str(d.get("moment_id")))
            if verdict is not None:
                return verdict == "approve"
            return decision == "approve"

        selected = [d for d in accepted if _approved(d)]
        if not selected:
            reason = "no accepted drafts" if not accepted else "no packs approved at review gate"
            return {"promote_result": {"promoted_moment_ids": [], "review_status": "draft",
                                       "owner_reviewed": False, "skipped": reason,
                                       "rejected_moment_ids": [str(d.get("moment_id")) for d in accepted]}}
        data_root = Path(state["data_root"]) if state.get("data_root") else None
        result = promote_pack(
            state["drama_id"], selected,
            review_token=decision,
            data_root=data_root, write=write,
        )
        # surface which accepted packs the owner held back, so the report is honest.
        result["rejected_moment_ids"] = [
            str(d.get("moment_id")) for d in accepted if d not in selected]
        return {"promote_result": result}

    return node


def final_report_node() -> Callable[[ProductionState], ProductionState]:
    """Node 7 (final_report). Sanitized rollup exposing degraded states: judge_unavailable +
    flagged windows are first-class, not hidden."""

    def node(state: ProductionState) -> ProductionState:
        results = state.get("window_results") or []
        by_status: dict[str, list[str]] = {}
        for r in results:
            by_status.setdefault(r["status"], []).append(r["moment_id"])
        promote = state.get("promote_result") or {}
        report = {
            "drama_id": state.get("drama_id"),
            "ingest_status": state.get("ingest_status"),
            "asr_status": state.get("asr_status"),
            "scaffold_status": state.get("scaffold_status"),
            "memory_status": state.get("memory_status"),
            "candidate_count": len(state.get("candidates") or []),
            "window_status_counts": {k: len(v) for k, v in by_status.items()},
            "windows_by_status": by_status,
            "judge_unavailable": by_status.get(STATUS_JUDGE_UNAVAILABLE, []),
            "author_unavailable": by_status.get(STATUS_AUTHOR_UNAVAILABLE, []),
            "flagged_windows": (by_status.get(STATUS_FLAGGED_MAX_ROUNDS, [])
                                + by_status.get(STATUS_JUDGE_UNAVAILABLE, [])
                                + by_status.get(STATUS_AUTHOR_UNAVAILABLE, [])),
            "accepted_count": len(state.get("accepted_drafts") or []),
            "review_token": state.get("review_token"),
            "promoted_moment_ids": promote.get("promoted_moment_ids", []),
            "review_status": promote.get("review_status"),
            "owner_reviewed": promote.get("owner_reviewed", False),
        }
        return {"report": report}

    return node


# ---------------------------------------------------------------------------
# graph
# ---------------------------------------------------------------------------

def build_production_graph(
    author_provider: Any,
    judge_provider: Any,
    guidance: dict[str, Any],
    *,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    candidates_provider: Callable[[ProductionState], list[dict[str, Any]]] | None = None,
    promote_write: bool = True,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
):
    """Compile the agentic v0.4 production StateGraph.

    Node/edge list (linear backbone; the self-correction loop is the sub-loop inside
    author_and_judge):

        START
          -> build_episode_memory   (3, reuse; idempotent/skip-if-cached)
          -> propose_windows        (4)
          -> author_and_judge       (4a window_gate -> 4b scene_context[cached once] ->
                                      4c/4d author -> 4e judge -> revise↺ -> collect)
          -> owner_review_gate      (5, interrupt/resume — graph pauses here)
          -> promote                (6, Component B; reviewed iff approve token)
          -> final_report           (7)
          -> END

    Compile with a checkpointer to use the interrupt at owner_review_gate; without one the gate
    still runs but cannot pause/resume (tests that exercise the gate pass a MemorySaver).
    """
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(ProductionState)
    # front (A2, idempotent): ingest -> asr -> propose -> scaffold so the graph is ONE pipeline.
    builder.add_node("ingest_batch", ingest_batch_node())
    builder.add_node("asr", asr_node())
    builder.add_node("propose_windows", propose_windows_node(candidates_provider))
    builder.add_node("build_scaffold", build_scaffold_node())
    builder.add_node("build_episode_memory", build_episode_memory_node())
    builder.add_node("author_and_judge", author_and_judge_node(
        author_provider, judge_provider, guidance,
        window_gate_provider=window_gate_provider, judge_fn=judge_fn, on_progress=on_progress))
    builder.add_node("owner_review_gate", owner_review_gate_node())
    builder.add_node("promote", promote_node(write=promote_write))
    builder.add_node("final_report", final_report_node())

    builder.add_edge(START, "ingest_batch")
    builder.add_edge("ingest_batch", "asr")
    builder.add_edge("asr", "propose_windows")
    builder.add_edge("propose_windows", "build_scaffold")
    builder.add_edge("build_scaffold", "build_episode_memory")
    builder.add_edge("build_episode_memory", "author_and_judge")
    builder.add_edge("author_and_judge", "owner_review_gate")
    builder.add_edge("owner_review_gate", "promote")
    builder.add_edge("promote", "final_report")
    builder.add_edge("final_report", END)
    return builder


def load_guidance() -> dict[str, Any]:
    from tools.ars.deadman_author_drama_heroes import load
    return load(REPO / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")


def load_pack(drama_id: str, data_root: Path | None = None) -> dict[str, Any]:
    from tools.ars.deadman_author_drama_heroes import load
    root = data_root or (REPO / "data" / "dramas")
    return load(root / drama_id / "moments.v0.1.json")


def run_production(
    drama_id: str,
    author_provider: Any,
    judge_provider: Any,
    *,
    review_decision: str = "approve",
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    data_root: Path | None = None,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    promote_write: bool = True,
) -> dict[str, Any]:
    """Drive the production graph end to end including the owner-review interrupt/resume.

    Compiles with a MemorySaver so the graph pauses at owner_review_gate, then resumes with the
    given review_decision (the approve token is what lets promote stamp reviewed — P1-A). Returns
    the final state (state['report'] is the sanitized rollup)."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    guidance = load_guidance()
    pack = load_pack(drama_id, data_root)
    graph = build_production_graph(
        author_provider, judge_provider, guidance,
        window_gate_provider=window_gate_provider, judge_fn=judge_fn,
        candidates_provider=None, promote_write=promote_write,
    ).compile(checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": f"prod-{drama_id}"}}
    init: ProductionState = {
        "drama_id": drama_id, "drama_title": pack.get("title", ""), "pack": pack,
        "candidates": candidates or [], "max_rounds": max_rounds,
        "data_root": str(data_root) if data_root else "",
    }
    graph.invoke(init, config=config)  # runs up to the owner_review_gate interrupt
    final = graph.invoke(Command(resume={"decision": review_decision}), config=config)
    return final


# ---------------------------------------------------------------------------
# durable start / resume (Track A) — the real cross-HTTP pause at owner_review_gate
# ---------------------------------------------------------------------------
#
# run_production (above) self-resumes in ONE call with a MemorySaver — fine for the CLI/tests, but
# the console needs the graph to PAUSE at owner_review_gate, return a waiting handle over HTTP, and
# RESUME later when the owner submits. That is the durable start/resume split already proven in the
# older producer graph (deadman_run_producer_graph.py: open_checkpointer/run_graph_start/
# run_graph_resume, SqliteSaver under a per-run dir). We port that pattern onto THIS graph.

def _production_run_dir(run_id: str) -> Path:
    safe = "".join(c for c in str(run_id) if c.isalnum() or c in "-_") or "run"
    return REPO / "tmp" / "production_runs" / safe


def _production_checkpoint_path(run_id: str) -> Path:
    return _production_run_dir(run_id) / "checkpoint.sqlite"


def _open_production_checkpointer(run_id: str):
    """SqliteSaver under tmp/production_runs/<run_id>/checkpoint.sqlite (gitignored). Run-scoped
    connection; the caller closes it after each start/resume command (mirrors open_checkpointer)."""
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    run_dir = _production_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_production_checkpoint_path(run_id)), check_same_thread=False)
    return conn, SqliteSaver(conn)


def _write_production_manifest(run_id: str, data: dict[str, Any]) -> None:
    run_dir = _production_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "manifest.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            existing = {}
    existing.update(data)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")


def read_production_manifest(run_id: str) -> dict[str, Any]:
    path = _production_run_dir(run_id) / "manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _stream_until_interrupt(graph, command, config, on_node) -> bool:
    """Stream a (start or resume) command node-by-node, reporting each node via `on_node`, until the
    graph interrupts or ends. Returns True if it paused at an interrupt, False if it ran to END."""
    interrupted = False
    for chunk in graph.stream(command, config=config, stream_mode="updates"):
        if not isinstance(chunk, dict):
            continue
        if "__interrupt__" in chunk:
            interrupted = True
            continue
        for node_name, update in chunk.items():
            if on_node is not None:
                try:
                    on_node(str(node_name), update if isinstance(update, dict) else {})
                except Exception:  # noqa: BLE001 — progress reporting must never break the run
                    pass
    return interrupted


def run_production_start(
    drama_id: str,
    author_provider: Any,
    judge_provider: Any,
    *,
    run_id: str,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    data_root: Path | None = None,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    promote_write: bool = True,
    on_node: Callable[[str, dict[str, Any]], None] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Start a production run and PAUSE at owner_review_gate, returning a waiting handle (does NOT
    auto-resume). `on_node` reports each graph node (front-node walk + the spine) for the viz;
    `on_progress` reports the inner author-loop events (stage_a/stage_b/judge/revise) within
    author_and_judge so the viz animates the self-correction loop live. Compiles with a durable SqliteSaver keyed by run_id so a later
    run_production_resume(run_id, ...) — even from a different request — reopens the same checkpoint.

    Returns {run_id, status: "waiting_for_review"|"done", drama_id, accepted_drafts, window_results,
    report}. accepted_drafts are the produced packs (lead + reply_candidates[+echo] + scene_context)
    the split review gate renders; the owner's per-pack verdicts come back through
    run_production_resume."""
    conn, checkpointer = _open_production_checkpointer(run_id)
    try:
        guidance = load_guidance()
        pack = load_pack(drama_id, data_root)
        graph = build_production_graph(
            author_provider, judge_provider, guidance,
            window_gate_provider=window_gate_provider, judge_fn=judge_fn,
            candidates_provider=None, promote_write=promote_write, on_progress=on_progress,
        ).compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": f"prod-{run_id}"}}
        init: ProductionState = {
            "drama_id": drama_id, "drama_title": pack.get("title", ""), "pack": pack,
            "candidates": candidates or [], "max_rounds": max_rounds,
            "data_root": str(data_root) if data_root else "",
        }
        _write_production_manifest(run_id, {
            "run_id": run_id, "drama_id": drama_id,
            "data_root": str(data_root) if data_root else "",
            "max_rounds": max_rounds, "promote_write": promote_write, "status": "running"})
        interrupted = _stream_until_interrupt(graph, init, config, on_node)
        snapshot = graph.get_state(config)
        values = dict(snapshot.values) if snapshot is not None else {}
        status = "waiting_for_review" if interrupted else "done"
        _write_production_manifest(run_id, {"status": status})
        return {
            "run_id": run_id,
            "status": status,
            "drama_id": drama_id,
            "accepted_drafts": values.get("accepted_drafts") or [],
            "window_results": values.get("window_results") or [],
            "report": values.get("report") or {},
        }
    finally:
        conn.close()


def run_production_resume(
    run_id: str,
    decision: str,
    author_provider: Any,
    judge_provider: Any,
    *,
    pack_decisions: dict[str, str] | None = None,
    window_gate_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    promote_write: bool = True,
    on_node: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Resume a paused production run with the owner's decision. Reopens the SAME SqliteSaver +
    thread_id (so the checkpointed accepted_drafts / pack / candidates are restored from disk — no
    need to re-pass them) and drives promote -> final_report. `pack_decisions` (moment_id ->
    approve|reject) lets promote write only the owner-approved packs (P1-A per-pack)."""
    from langgraph.types import Command

    conn, checkpointer = _open_production_checkpointer(run_id)
    try:
        guidance = load_guidance()
        graph = build_production_graph(
            author_provider, judge_provider, guidance,
            window_gate_provider=window_gate_provider, judge_fn=judge_fn,
            candidates_provider=None, promote_write=promote_write,
        ).compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": f"prod-{run_id}"}}
        resume_payload = {"decision": decision, "pack_decisions": pack_decisions or {}}
        _write_production_manifest(run_id, {"status": "running", "review_decision": decision})
        _stream_until_interrupt(graph, Command(resume=resume_payload), config, on_node)
        snapshot = graph.get_state(config)
        values = dict(snapshot.values) if snapshot is not None else {}
        _write_production_manifest(run_id, {"status": "done"})
        return {
            "run_id": run_id,
            "status": "done",
            "decision": decision,
            "report": values.get("report") or {},
            "promote_result": values.get("promote_result") or {},
        }
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drama-id", required=True)
    ap.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    ap.add_argument("--review-decision", default="approve",
                    help="owner gate decision used on resume (approve stamps reviewed; P1-A)")
    ap.add_argument("--data-root", default="",
                    help="override the data/dramas root (e.g. a safe TMP copy) so the run reads + "
                         "writes there instead of the tracked packs; makes the safe-TMP run first-class.")
    ap.add_argument("--dry-run", action="store_true", help="do not write the promoted pack")
    args = ap.parse_args()

    from tools.ars.deadman_studio_cab_loop_spike import _load_env
    _load_env()
    from tools.ars.deadman_author_drama_heroes import ArkStudioProofProvider
    from tools.ars.deadman_run_studio_taste_judge import BailianTasteJudgeProvider

    author_provider = ArkStudioProofProvider.from_env()
    judge_provider = BailianTasteJudgeProvider.from_env()
    data_root = Path(args.data_root) if args.data_root else None
    final = run_production(
        args.drama_id, author_provider, judge_provider,
        review_decision=args.review_decision, max_rounds=args.max_rounds,
        data_root=data_root, promote_write=not args.dry_run,
    )
    print(json.dumps(final.get("report", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
