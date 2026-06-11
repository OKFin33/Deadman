#!/usr/bin/env python3
"""Step 3: CAB dogfood — author a real companion_exchange for a promoted drama's
hero window.

Reuses the Studio CAB provider + two-stage prompt pattern + huangnian owner-gold
as CROSS-DRAMA style few-shot, but sources the window from the new drama's real
ASR. This tests whether the Studio authoring taste generalizes beyond huangnian.

Dry-run (default) prints the draft for owner taste check; --apply injects it into
the pack (only run --apply AFTER the owner approves, so review_status=reviewed is
honest). Requires provider env:  set -a; . ./.env; set +a

  python3 tools/ars/deadman_author_drama_heroes.py --drama-id yunmiao
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from Deadman.tools.ars.deadman_run_studio_real_provider_proof import (  # noqa: E402
    ArkStudioProofProvider, TWO_LAYER_SEMANTICS, stage_a_output_schema, stage_b_output_schema,
)

# v2 taste overlay: additive owner-taste deltas (read on top of frozen v1). The
# durable place taste accumulates — not the prompt scaffolding below.
OVERLAY_PATH = REPO / "data" / "datasets" / "studio_guidance" / "studio_cab_taste_overlay.v0.3.json"


def _require_overlay(path):
    """Fail-CLOSED (P0-B): the author core must NOT silently author without the taste spec.
    A fresh clone / CI missing the overlay errors loudly instead of producing taste-less drafts."""
    if not path.exists():
        raise FileNotFoundError(
            f"v0.3 taste overlay missing at {path} — author core is fail-closed and will not author "
            "without the taste spec. Restore/generate it (see docs/context/dataset-rebuild-v03-contract.md).")
    return json.loads(path.read_text(encoding="utf-8"))


OVERLAY = _require_overlay(OVERLAY_PATH)

CROSS_DRAMA_NOTE = (
    "The lead/reply/echo examples below are from a DIFFERENT drama (荒年/famine survival). "
    "Use them ONLY for the friend-voice register, the two-layer format, and taste. "
    "Author for THIS scene's own drama and content; do not transplant famine content."
)


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def call_json(provider, prompt, schema, attempts: int = 3):
    """Provider occasionally returns non-strict JSON; retry a few times."""
    last = None
    for _ in range(attempts):
        try:
            return provider.complete_case(prompt, schema)["payload"]
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise last


def asr_window(drama: str, episode_id: str, start_ms: int, end_ms: int) -> list[str]:
    pats = glob.glob(str(REPO / f"tmp/ars_{drama}_analysis/volc_asr*/**/{episode_id}*.json"), recursive=True)
    for p in sorted(pats):
        try:
            d = load(Path(p))
        except Exception:
            continue
        utts = d.get("utterances") if isinstance(d, dict) else None
        if not utts:
            continue
        for scale in (1, 1000):  # try ms, then seconds
            out = []
            for u in utts:
                s = int(u.get("start_time") or 0) * scale
                e = int(u.get("end_time") or 0) * scale
                if s < end_ms and e > start_ms:
                    t = str(u.get("text") or "").strip()
                    if t:
                        out.append(t)
            if out:
                return out
    return []


def few_shot(guidance: dict, n: int = 4):
    sp = guidance["splits"]
    leads = [{k: e[k] for k in ("lead_text", "scene_signal") if k in e}
             for e in sp["lead_authoring"].get("examples", [])[:n]]
    replies = [{k: e[k] for k in ("display_text", "emotion_role", "semantic_role") if k in e}
               for e in sp["reply_authoring"].get("examples", [])[:n]]
    echo_src = sp["selected_echo_direction"].get("runtime_reviewed_examples") \
        or sp["selected_echo_direction"].get("examples", [])
    echoes = [{k: e[k] for k in ("companion_lead", "display_text", "selected_echo") if k in e}
              for e in echo_src[:n]]
    return leads, replies, echoes


# Map a judge's per-dimension verdict key -> the authoring layer that owns it. lead/reply are
# Stage A's (display layer); echo is Stage B's. Used to ROUTE a directed-revision critique to the
# layer that actually failed, instead of blind-resampling everything (contract Agentic#2 / P0-A).
_DIM_TO_LAYER = {"lead_taste": "lead", "reply_voice_taste": "reply", "echo_taste": "echo"}


def _layer_feedback(feedback, layers):
    """Resolve a judge critique into (note, failing_layers∩layers).

    feedback may be:
      - None            -> ("", set())                 no revision (default path unchanged).
      - a plain string  -> the string applies to ALL layers (legacy/spike shape: a flat critique
                           with no machine-readable dimension split — be conservative, route it
                           everywhere so the rejected layer always sees it).
      - a dict          -> {"note"/"text": str, "fails": ["lead_taste", ...]}: route only to the
                           layers whose dimension is in `fails`. An empty/absent `fails` means
                           the note applies to all layers.
    Returns ("", set()) when nothing pertinent to `layers` failed, so the caller leaves the
    default (no-feedback) prompt untouched.
    """
    if not feedback:
        return "", set()
    want = set(layers)
    if isinstance(feedback, dict):
        note = str(feedback.get("note") or feedback.get("text") or feedback.get("feedback") or "").strip()
        fails = feedback.get("fails")
        failing = {_DIM_TO_LAYER.get(d, d) for d in fails} if isinstance(fails, list) and fails else want | {"echo"}
    else:  # plain string critique with no dimension split -> applies to every layer
        note, failing = str(feedback).strip(), want | {"echo"}
    matched = failing & want
    if not note or not matched:
        return "", set()
    return note, matched


def stage_a_prompt(scene, leads, replies, feedback=None):
    prompt = {
        "system_prompt": ("You are a Deadman Studio/CAB authoring unit for 看剧搭子, working layer 1. "
            "Return exactly one strict JSON object, no prose. Do not predict future plot, expose mechanism, "
            "or turn replies into RPG actions or questions. Do NOT author selected_echo in this stage."),
        "task": "author_new_drama_hero.stage_a", "product": "看剧搭子",
        "scene": scene, "cross_drama_style_note": CROSS_DRAMA_NOTE,
        "lead_style_examples_other_drama": leads, "reply_style_examples_other_drama": replies,
        "two_layer_semantics": TWO_LAYER_SEMANTICS,
        "global_rules": [
            "companion_lead: one short friend-style line that surfaces THIS scene's tension/feeling and makes the viewer want to chime in. Not a question, not a UI prompt.",
            "Each display_text is the viewer's own about-to-say line (Layer 1) for THIS scene. Three genuinely different viewer postures into the same beat. Not a label/evaluation, not a question.",
            "display_text is shown on a small companion surface: keep each one SHORT — at most 14 Chinese characters (hard limit; aim for ~6-12). It must still read as a complete, natural spoken line, just compact — trim filler, don't pad. Do NOT use narration/product words (剧情/原剧/分支/角色/主角/观众/玩家/系统/互动/本集/接下来/请你 …); speak in the moment, not about the show.",
            "For each reply also write viewer_motivation: one short phrase naming the posture/feeling of the viewer who'd pick this display_text and what they hope to hear back.",
            "Author the companion beat PURELY from scene.transcript — that dialogue is what is actually on screen. Read who is speaking and the real feeling of THIS beat, and surface what a viewer would want to say to it. Do not invent a theme (e.g. a power/identity reveal) that is not in the transcript. Every draft is draft_not_owner_reviewed.",
            "GROUND in scene.scene_context, a layered memory: l0_canon (premise/characters) + l3_series_spine (one line per PRIOR episode = story so far) + l2_recent_events (last 2 episodes' events) + prior_window_asr (what just happened right before this window) + whats_happening (this beat). KNOWLEDGE HORIZON (scene.scene_context.knowledge_horizon): you know the show ONLY up to this window — NEVER reference, hint at, or 'reveal' anything later, and do NOT act surprised by something the spine/events already establish (no 原来如此/真相大白 when there is no real reveal).",
            "Refer to people by ROLE / relationship / pronoun (她、这家人、大舅、孩子) — do NOT put specific proper NAMES in the line: ASR mis-recognizes names, and the companion voice is natural and general anyway.",
            "Avoid the display_text failure PATTERNS in negative_display_patterns — each names a failure SITUATION, not an exact string. Do not produce any display_text that falls into a pattern, including new wordings/variants; illustrative_examples only show the kind. (severity hard = never; soft_preference = lean away.)",
            "Avoid the companion_lead failure PATTERNS in negative_lead_patterns the same way — react in the moment as a co-watcher; don't recap/narrate the segment.",
            "AIM FOR the positive patterns in positive_lead_patterns / positive_display_patterns — each names a SITUATION + what a good line does right; when this scene matches a pattern's situation, write in that shape. Examples show the texture; do not copy them verbatim.",
            "Compose the three reply_candidates for COVERAGE per reply_set_composition (two core directions + one fallback).",
            *OVERLAY.get("lead_rules_addendum", []),
            *OVERLAY.get("display_text_rules_addendum", []),
            *OVERLAY.get("reply_set_rules_addendum", []),
        ],
        "reply_set_composition": OVERLAY.get("reply_set_rules_addendum", []),
        "negative_display_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "display_text"],
        "negative_lead_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "companion_lead"],
        "positive_display_patterns": [{"pattern": n.get("pattern"), "when": n.get("when"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_positives", []) if n.get("layer") == "display_text"],
        "positive_lead_patterns": [{"pattern": n.get("pattern"), "when": n.get("when"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_positives", []) if n.get("layer") == "companion_lead"],
        "output_contract": {"case_id": scene["case_id"], "window_decision": "recommend_window",
            "companion_lead": "short friend-style lead",
            "reply_candidates": [{"display_text": "...", "emotion_role": "...", "semantic_role": "...", "viewer_motivation": "..."}],
            "failure_buckets": [], "rationale_summary": "...", "repair_notes": []},
    }
    note, dims = _layer_feedback(feedback, ("lead", "reply"))  # lead/reply failures route to Stage A
    if note:  # directed revision (mirrors Stage B :167-172): a critic rejected lead/reply — fix THAT layer
        layers = "、".join(d for d in ("companion_lead" if "lead" in dims else "",
                                       "reply_candidates" if "reply" in dims else "") if d) or "companion_lead/reply_candidates"
        prompt["revision_feedback"] = note
        prompt["global_rules"] = [
            f"这是修订轮：上一稿的 {layers} 被评审拒了。严格按 revision_feedback 重写点名的那层，"
            "专门修它点名的不达标维度，别再犯同样的毛病；没被点名的层保持原意、别改坏。",
            *prompt["global_rules"],
        ]
    return prompt


def stage_b_prompt(scene, lead, target, siblings, prior, echoes, feedback=None):
    prompt = {
        "system_prompt": ("You are a Deadman Studio/CAB authoring unit for 看剧搭子, layer 2. You reply, as the "
            "co-watching host, to ONE specific viewer who just said the given display_text. Return one strict JSON object, no prose."),
        "task": "author_new_drama_hero.stage_b", "product": "看剧搭子", "case_id": scene["case_id"],
        "scene": scene, "companion_lead": lead,
        "this_viewer": {k: target.get(k, "") for k in ("display_text", "emotion_role", "semantic_role", "viewer_motivation")},
        "other_viewer_display_texts": siblings, "echoes_already_written_this_case": prior,
        "echo_style_examples_other_drama": echoes, "cross_drama_style_note": CROSS_DRAMA_NOTE,
        "two_layer_semantics": TWO_LAYER_SEMANTICS,
        "echo_rules": [
            "Reply to THIS viewer (who said this_viewer.display_text), not a second comment on the scene.",
            "(a) acknowledge their specific point; (b) extend one notch with a concrete scene detail or feeling they'd want to hear.",
            "Do not merely restate the display_text (复述); do not change topic ignoring them (脱节).",
            "Vary the opening across the three echoes so they don't sound identical.",
            "Short and spoken, about 30 Chinese characters or fewer. One breath, one beat.",
            "Avoid the echo failure PATTERNS in negative_echo_patterns — each names a failure SITUATION (not an exact string); do not fall into one, including new variants.",
            "AIM FOR the positive patterns in positive_echo_patterns — catch the viewer's line then extend one notch the way the matching pattern's situation describes. Examples show texture, don't copy verbatim.",
            "Ground the echo in scene.scene_context's layered memory (l3_series_spine / l2_recent_events / prior_window_asr) and respect the KNOWLEDGE HORIZON — the echo must not 'reveal' or act surprised by something already established, nor reference anything later than this window.",
            *OVERLAY.get("echo_rules_addendum", []),
        ],
        "negative_echo_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "echo"],
        "positive_echo_patterns": [{"pattern": n.get("pattern"), "when": n.get("when"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_positives", []) if n.get("layer") == "echo"],
        "output_contract": {"case_id": scene["case_id"], "selected_echo": "...", "echo_rationale": "..."},
    }
    note, _ = _layer_feedback(feedback, ("echo",))  # only echo-layer critiques revise Stage B
    if note:  # M4 directed revision: a critic rejected the prior draft — fix the echo specifically
        prompt["revision_feedback"] = note
        prompt["echo_rules"] = [
            "这是修订轮：上一稿的 echo 被评审拒了。严格按 revision_feedback 重写这条 echo，专门修它点名的毛病，别再犯同样的。",
            *prompt["echo_rules"],
        ]
    return prompt


# --- context node: derive per-window scene context from raw ASR + drama canon (does NOT rely on
#     pre-curated moment fields, so it works for any new window). Runs BEFORE stage_a. -------------
BEFORE_MS = 90_000  # ~90s of dialogue before the window ≈ what the audience has just watched


def _require_committed(f: Path, kind: str):
    """Fail-CLOSED (P0-B): a load-bearing committed input the production-graph context grounding
    depends on is absent. RAISE loudly instead of letting build_scene_context silently produce
    empty l0_canon/l3_series_spine/l2_recent_events (anti-spoiler grounding degrading to nothing
    on a fresh clone). Mirrors the overlay guard. See docs/context/agentic-production-graph-contract.md P0-B."""
    raise FileNotFoundError(
        f"{kind} missing at {f} — context grounding is fail-closed (require=True) and will not "
        "silently no-op the layered context. Commit/restore it (see "
        "docs/context/dataset-rebuild-v03-contract.md).")


def load_synopsis(drama, require: bool = False):
    f = REPO / "data/review/drama_synopses.v0.1.json"
    if not f.exists():
        if require:  # production-graph path: a missing committed synopsis must NOT silently no-op
            _require_committed(f, "drama synopses")
        return {}
    return json.loads(f.read_text(encoding="utf-8")).get(drama, {})


def drama_canon(drama, require: bool = False):
    syn = load_synopsis(drama, require=require)  # official synopsis = authoritative premise + correct character identities (all 3 dramas)
    f = REPO / f"data/dramas/{drama}/context.v0.1.json"
    c = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return {
        "premise": syn.get("synopsis") or c.get("premise", ""),  # prefer official synopsis (covers yunmiao/lihun too)
        "premise_source": syn.get("title", ""),
        "protagonist": c.get("protagonist", {}),
        "relationship_map": c.get("relationship_map", []),
        "core_constraints": [x.get("constraint") for x in c.get("core_constraints", []) if isinstance(x, dict)][:4],
    }


def context_prompt(drama_title, canon, prior_asr, current_asr):
    return {
        "system_prompt": (
            "You build a per-window SCENE CONTEXT card for authoring a short-drama watching-companion (看剧搭子). "
            "Given the drama canon, the dialogue JUST BEFORE this window (what the audience has already seen), and the "
            "current window dialogue, synthesize: (1) what is happening at THIS beat; (2) crucially WHAT THE AUDIENCE "
            "ALREADY KNOWS coming in — so a companion line is not written as if discovering something already "
            "established (no fake 揭晓/原来如此 when there is no real reveal); (3) the relationship state at play; "
            "(4) a one-line grounding_note for the author. Be concrete, grounded in the dialogue. Write all four "
            "card fields in Chinese (Simplified) — the product is Chinese and the owner reviews these. Return ONE strict JSON object."),
        "task": "build_scene_context_card", "product": "看剧搭子",
        "drama_title": drama_title, "drama_canon": canon,
        "prior_window_asr_what_audience_just_saw": prior_asr,
        "current_window_asr": current_asr,
        "name_handling": ("ASR often MIS-RECOGNIZES proper names (人名); trust drama_canon.premise for correct "
                          "character identities and map garbled ASR names to it. The premise gives setup/identities "
                          "only — actual plot state is bounded by the prior ASR (knowledge horizon)."),
        "output_contract": {"whats_happening": "...", "audience_already_knows": "...",
                            "relationship_state": "...", "grounding_note": "..."},
    }


def context_schema():
    props = {k: {"type": "string"} for k in
             ("whats_happening", "audience_already_knows", "relationship_state", "grounding_note")}
    return {"type": "object", "properties": props, "required": list(props)}


def episode_num(episode_id):
    m = re.search(r"ep(\d+)", episode_id or "")
    return int(m.group(1)) if m else 0


def load_episode_memory(drama, require: bool = False):
    f = REPO / f"data/review/context_memory/{drama}.v0.1.json"
    if not f.exists():
        if require:  # production-graph path: a missing committed memory must NOT silently no-op the spine
            _require_committed(f, f"episode context memory for {drama}")
        return {}
    return json.loads(f.read_text(encoding="utf-8")).get("episodes", {})


def gated_memory(eps, cur):
    """KNOWLEDGE HORIZON gating: L3 = every episode STRICTLY BEFORE cur (anti-spoiler series spine);
    L2 = the previous 2 episodes (recent detail). Episodes >= cur are NEVER returned."""
    l3 = [{"episode": e, "summary": v.get("l3_one_line", "")}
          for e, v in sorted(eps.items()) if 0 < episode_num(e) < cur]
    l2 = [{"episode": e, "events": v.get("l2_event_log", [])}
          for e, v in sorted(eps.items()) if cur - 2 <= episode_num(e) < cur]
    return l3, l2


def build_scene_context(provider, drama, ep, start_ms, end_ms, drama_title, require_grounding: bool = False):
    """The context node / ASSEMBLER: synthesizes L1 (this beat) + injects the layered episode memory,
    gated by the KNOWLEDGE HORIZON — only content at-or-before this window's airing position is included,
    so the companion knows exactly what the viewer knows (no spoilers, no fake 揭晓).

    require_grounding (P0-B, production-graph path): when True, the committed synopsis + episode-memory
    inputs are fail-CLOSED — absent means RAISE, so the layered context cannot silently degrade to empty
    l0_canon/l3_series_spine/l2_recent_events on a fresh clone. Default False preserves the eval/dry-run
    fail-open behavior for dramas that legitimately lack these inputs."""
    prior = asr_window(drama, ep, max(0, start_ms - BEFORE_MS), start_ms)
    current = asr_window(drama, ep, start_ms, end_ms)
    canon = drama_canon(drama, require=require_grounding)
    try:  # L1: synthesize this beat from prior+current ASR + canon
        out = call_json(provider, context_prompt(drama_title, canon, prior, current), context_schema())
    except Exception:
        out = {}
    card = out if isinstance(out, dict) else {}
    # L0 canon (static): premise + protagonist
    card["l0_canon"] = {"premise": canon.get("premise", ""), "protagonist": canon.get("protagonist", {})}
    # L3/L2 layered episode memory, gated by the knowledge horizon (see gated_memory)
    card["l3_series_spine"], card["l2_recent_events"] = gated_memory(load_episode_memory(drama, require=require_grounding), episode_num(ep))
    card["prior_window_asr"] = prior  # current-episode pre-window dialogue (time-gated within the episode)
    card["knowledge_horizon"] = (f"You know the show ONLY up to {ep} ~{start_ms // 1000}s. "
                                 "Never reference, hint at, or 'reveal' anything that happens later.")
    return card


def build_authoring_scene(provider, guidance, drama, pack, moment):
    """Build the per-moment authoring scene ONCE (context node + ASR transcript) and the few-shot
    sets. Split out of author_moment so the agentic self-correction loop can build the scene a
    single time (contract P1-B) and re-run only Stage A/B across revise rounds on the SAME scene,
    instead of rebuilding context (a wasted provider call) every round."""
    mid = moment["moment_id"]
    ep = moment["source_drama"]["episode_id"]
    iw = moment["interaction_window"]
    start_ms, end_ms = int(iw["start_seconds"]) * 1000, int(iw["end_seconds"]) * 1000
    transcript = asr_window(drama, ep, start_ms, end_ms) or [moment["companion_exchange"].get("scene_signal", "")]
    scene_context = build_scene_context(provider, drama, ep, start_ms, end_ms, pack.get("title"))  # context node
    scene = {"case_id": f"hero:{mid}", "drama_id": drama, "drama_title": pack.get("title"),
             "episode_id": ep, "transcript": transcript,  # author from real ASR only; mined hook dropped
             "scene_context": scene_context}  # derived per-window context (what's happening + what audience already knows)
    leads, replies, echoes = few_shot(guidance)
    return scene, leads, replies, echoes


def _emit(on_progress, **event):
    """Best-effort progress emit: a callback exception must NEVER break authoring (contract A⑤:
    on_progress is optional + non-fatal). No-op when on_progress is None (default = unchanged)."""
    if on_progress is None:
        return
    try:
        on_progress(dict(event))
    except Exception:  # noqa: BLE001 - progress is observational only; never fail authoring on it
        pass


def author_on_scene(provider, scene, leads, replies, echoes, feedback=None, *, on_progress=None, rnd=None):
    """Run the two-stage author over an already-built scene: Stage A (lead + 3 viewer lines) then
    per-reply Stage B (echo). `feedback` (None default = unchanged behavior) drives the DIRECTED
    revision — a rejected lead/reply routes to Stage A, a rejected echo routes to Stage B
    (contract Agentic#2 / P0-A). Returns (companion_lead, reply_candidates).

    `on_progress` (None default = byte-for-byte unchanged) is an optional best-effort callback;
    when set it emits `stage_a_done` after Stage A returns lead+3 and `stage_b_done` after the
    per-reply Stage B loop completes (contract A⑤). `rnd` is the 1-based round threaded through so
    those events carry the current round."""
    a_out = call_json(provider, stage_a_prompt(scene, leads, replies, feedback), stage_a_output_schema())
    lead = str(a_out.get("companion_lead") or "")
    rcs = [r for r in a_out.get("reply_candidates", []) if isinstance(r, dict)][:3]
    _emit(on_progress, event="stage_a_done", round=rnd)
    disp = [str(r.get("display_text") or "") for r in rcs]
    prior: list[str] = []
    for i, r in enumerate(rcs):
        sib = [d for j, d in enumerate(disp) if j != i]
        b = call_json(provider, stage_b_prompt(scene, lead, r, sib, list(prior), echoes, feedback), stage_b_output_schema())
        r["selected_echo"] = str(b.get("selected_echo") or "")
        prior.append(r["selected_echo"])
    _emit(on_progress, event="stage_b_done", round=rnd)
    return lead, rcs


def author_moment(provider, guidance, drama, pack, moment, feedback=None):
    # Directed revision (contract Agentic#2 / P0-A): a rejected lead/reply now drives a targeted Stage A
    # rewrite instead of a blind resample; echo-only critiques still route to Stage B inside author_on_scene.
    scene, leads, replies, echoes = build_authoring_scene(provider, guidance, drama, pack, moment)
    lead, rcs = author_on_scene(provider, scene, leads, replies, echoes, feedback)
    return scene, lead, rcs


# ---------------------------------------------------------------------------
# Agentic self-correction loop (shared core) — contract 4↺ / M4 judge-loop.
# The SAME loop the production graph's author_and_judge node runs, factored here so both the
# graph and the Studio API import ONE implementation (DRY). Author Stage A+B -> v0.3 taste judge
# -> directed revision routed by the verdict's failing dimensions -> re-author on the cached scene
# -> re-judge -> accept / max-rounds. Reuses the existing author core + the v0.3 judge; it does
# NOT reimplement taste.
# ---------------------------------------------------------------------------

# the three judge dims the loop routes on (the _DIM_TO_LAYER keys above): a single failing dim
# only perturbs its owning layer's next author round.
_REPAIR_DIMS = ("lead_taste", "reply_voice_taste", "echo_taste")
# verdict overall values that mean "good enough to accept" (vs. revise/flag).
_ACCEPT_VERDICTS = frozenset({"accept", "accept_with_minor_tweak"})
# judge-unavailable marker (normalize_verdict / provider_failure_verdict emit this).
_JUDGE_UNAVAILABLE = "not_available"


def directed_feedback(verdict):
    """Turn a judge verdict into the STRUCTURED directed-feedback the author core routes per layer.

    Emits `{"note": <rationale>, "fails": [<dim>, ...]}` that _layer_feedback routes to the owning
    layer (lead_taste/reply_voice_taste -> Stage A, echo_taste -> Stage B), so a single-dimension
    reject only perturbs its layer. Returns None when the verdict is accept-grade or unavailable
    (nothing to revise)."""
    overall = str(verdict.get("overall_verdict") or "")
    if overall in _ACCEPT_VERDICTS or overall == _JUDGE_UNAVAILABLE:
        return None
    fails = [dim for dim in _REPAIR_DIMS if verdict.get(dim) == "needs_repair"]
    note = str(verdict.get("rationale_summary") or "").strip()
    if not note:
        note = f"上一稿 verdict={overall}；不达标维度={fails or ['整体偏弱']}；按点名层重写。"
    return {"note": note, "fails": fails}


def _judge_case(moment, lead, rcs):
    """Wrap a draft into the build_judge_prompt input case (mirrors the spike's _draft_case)."""
    return {
        "case_id": f"hero:{moment.get('moment_id')}",
        "case_type": "gold_authoring",
        "item_id": moment.get("moment_id", ""),
        "episode_id": (moment.get("source_drama") or {}).get("episode_id", ""),
        "expected_behavior": "scene-grounded companion: in-scene lead + 3 viewer lines + echoes",
        "provider_status": "completed",
        "draft": {"companion_lead": lead, "reply_candidates": rcs},
    }


def _judge_draft(judge_provider, case):
    """taste_judge (4e, v0.3): build_judge_prompt -> provider -> normalize_verdict. A provider
    failure becomes an explicit not_available verdict, never a silent reject (the loop reads that
    as judge_unavailable and stops revising rather than white-burning rounds)."""
    from tools.ars.deadman_run_studio_taste_judge import (
        build_judge_prompt, call_judge_provider, normalize_verdict, provider_failure_verdict,
    )

    prompt = build_judge_prompt(case)
    try:
        payload, meta = call_judge_provider(judge_provider, prompt)
    except Exception as exc:  # noqa: BLE001 - explicit judge_unavailable, do not swallow into reject
        return provider_failure_verdict(case, "", exc)
    return normalize_verdict(case, payload, meta, "")


# human-facing revise-layer labels (match the frontend AgenticPipelineViz REVISE_LAYERS /
# RoundTrace.revised_layer strings exactly) keyed by the owning layer that _DIM_TO_LAYER maps to.
_LAYER_LABEL = {"lead": "开场 (lead)", "reply": "三条 (replies)", "echo": "接话 (echo)"}


def _revised_layer_label(feedback):
    """Map directed_feedback()['fails'] (judge dims) -> the human revise-layer label the viz shows.
    Picks the primary (first) failing dim; falls back to lead. Returns None when nothing to revise."""
    if not feedback:
        return None
    fails = feedback.get("fails") if isinstance(feedback, dict) else None
    layer = "lead"
    if isinstance(fails, list) and fails:
        layer = _DIM_TO_LAYER.get(fails[0], "lead")
    return _LAYER_LABEL.get(layer, _LAYER_LABEL["lead"])


def author_moment_agentic(author_provider, judge_provider, guidance, drama_id, pack, moment,
                          *, max_rounds=2, judge_fn=None, scene=None, on_progress=None):
    """Run the PROVEN self-correction loop for ONE moment and return a console-ready draft.

    Loop: build scene ONCE (P1-B) -> author Stage A+B -> v0.3 taste judge -> if reject &
    rounds-left: directed revision routed by the verdict's failing dims -> re-author on the cached
    scene -> re-judge -> accept / max-rounds. Reuses the existing author core (author_on_scene) +
    the v0.3 judge (_judge_draft); does NOT reimplement taste.

    Graceful degrade (fail-OPEN to existing single-shot behavior, NOT fail-closed): if
    judge_provider is None, or building/calling the judge raises, author exactly once and return
    judge_available=False. (The overlay-missing fail-CLOSED invariant in the author core stays;
    only the OPTIONAL judge half degrades open here so the console never loses its existing
    single-shot author path.)

    judge_fn is an injectable judge (tests pass a fake); defaults to the real v0.3 judge.
    scene is an optional pre-built authoring scene: the production graph passes its
    candidate->scene bridge result (build once per window, P1-B) so the loop runs over the mined
    candidate's context instead of re-deriving the scene from the moment. Default None builds the
    scene from the moment (the hero/console path).

    on_progress (None default = byte-for-byte unchanged behavior; the Phase-C-owned graph passes
    None) is an OPTIONAL best-effort callback invoked with a `{event, round, ...}` dict at each
    discrete loop step (context_built, round_start, stage_a_done, stage_b_done, judge_verdict,
    revise, done). A callback exception NEVER breaks authoring (see _emit). This is purely
    observational — it does NOT change the loop, the return shape, or the graph.

    Returns {companion_lead, replies, scene_context, rounds, final_verdict, judge_available}, where
    replies is the list of reply_candidate dicts (display_text + selected_echo + viewer_motivation +
    roles) and scene_context is the build_scene_context() card built ONCE for this window (P1-B), so
    the production graph can thread it through promote and persist it additively onto the moment."""
    if scene is not None:
        leads, replies_fs, echoes = few_shot(guidance)
    else:
        scene, leads, replies_fs, echoes = build_authoring_scene(author_provider, guidance, drama_id, pack, moment)
    # scene/context is now built (the context node done); emit once (P1-B). window_gate is implicitly done.
    _emit(on_progress, event="context_built", round=None)
    judge = judge_fn if judge_fn is not None else _judge_draft
    # the per-window scene_context card (P1-B, built once); threaded out so promote can persist it.
    scene_context = scene.get("scene_context") if isinstance(scene, dict) else None

    # Single-shot degrade (fail-OPEN): no judge wired -> author once, no loop, judge_available=False.
    if judge_provider is None and judge_fn is None:
        _emit(on_progress, event="round_start", round=1)
        lead, rcs = author_on_scene(author_provider, scene, leads, replies_fs, echoes, None,
                                    on_progress=on_progress, rnd=1)
        _emit(on_progress, event="done", round=1, verdict=None, judge_available=False)
        return {"companion_lead": lead, "replies": rcs, "scene_context": scene_context, "rounds": 1,
                "final_verdict": None, "judge_available": False}

    feedback = None
    lead, rcs = "", []
    last_verdict = {}
    for rnd in range(1, max(1, int(max_rounds)) + 1):
        _emit(on_progress, event="round_start", round=rnd)
        lead, rcs = author_on_scene(author_provider, scene, leads, replies_fs, echoes, feedback,
                                    on_progress=on_progress, rnd=rnd)
        try:
            verdict = judge(judge_provider, _judge_case(moment, lead, rcs))
        except Exception:  # noqa: BLE001 - judge raised -> fail-OPEN to single-shot (NOT fail-closed)
            _emit(on_progress, event="done", round=rnd, verdict=None, judge_available=False)
            return {"companion_lead": lead, "replies": rcs, "scene_context": scene_context,
                    "rounds": rnd, "final_verdict": None, "judge_available": False}
        last_verdict = verdict
        overall = str(verdict.get("overall_verdict") or "")
        accepted = overall in _ACCEPT_VERDICTS
        _emit(on_progress, event="judge_verdict", round=rnd, verdict=overall, accepted=accepted)
        if overall == _JUDGE_UNAVAILABLE:
            # judge unavailable -> fail-OPEN to single-shot: keep this round's draft, stop revising,
            # surface judge_available=False (do NOT swallow into a reject->rewrite white-burn).
            _emit(on_progress, event="done", round=rnd, verdict=overall, judge_available=False)
            return {"companion_lead": lead, "replies": rcs, "scene_context": scene_context,
                    "rounds": rnd, "final_verdict": verdict, "judge_available": False}
        if accepted:
            _emit(on_progress, event="done", round=rnd, verdict=overall, judge_available=True)
            return {"companion_lead": lead, "replies": rcs, "scene_context": scene_context,
                    "rounds": rnd, "final_verdict": verdict, "judge_available": True}
        # needs_repair: build DIRECTED feedback for the failing layer(s), then re-author (if rounds left).
        feedback = directed_feedback(verdict)
        # name which layer this round routes its directed rewrite into (lead/reply/echo) so the viz
        # can mark this round's revised_layer (only when there IS another round to spend).
        if rnd < max(1, int(max_rounds)):
            _emit(on_progress, event="revise", round=rnd,
                  layer=_revised_layer_label(feedback),
                  note=str(verdict.get("rationale_summary") or "").strip())

    # exhausted max_rounds without an accept-grade verdict: return the last (best-effort) draft.
    _emit(on_progress, event="done", round=max(1, int(max_rounds)),
          verdict=str(last_verdict.get("overall_verdict") or "") or None, judge_available=True)
    return {"companion_lead": lead, "replies": rcs, "scene_context": scene_context,
            "rounds": max(1, int(max_rounds)), "final_verdict": last_verdict, "judge_available": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drama-id", required=True)
    ap.add_argument("--moment-id", default="")
    ap.add_argument("--apply", action="store_true", help="inject into pack (run ONLY after owner approves)")
    a = ap.parse_args()

    guidance = load(REPO / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")
    pack_path = REPO / f"data/dramas/{a.drama_id}/moments.v0.1.json"
    pack = load(pack_path)
    moment = next((m for m in pack["moments"] if m["moment_id"] == a.moment_id), pack["moments"][0])

    provider = ArkStudioProofProvider.from_env()
    scene, lead, rcs = author_moment(provider, guidance, a.drama_id, pack, moment)

    print(f"\n=== CAB dogfood draft: {moment['moment_id']}  ({pack.get('title')} / {scene['episode_id']}) ===")
    print("scene (ASR):", (" ".join(scene["transcript"]) or "(no transcript)")[:240])
    print("companion_lead:", lead)
    for i, r in enumerate(rcs, 1):
        print(f"  [{i}] 我想说「{r.get('display_text')}」  (motiv: {r.get('viewer_motivation')})")
        print(f"      echo → {r.get('selected_echo')}")
    dd = REPO / "data" / "review" / "drafts"
    dd.mkdir(parents=True, exist_ok=True)
    (dd / f"{moment['moment_id']}.draft.json").write_text(
        json.dumps({"drama_id": a.drama_id, "moment_id": moment["moment_id"], "episode_id": scene["episode_id"],
                    "companion_lead": lead, "reply_candidates": rcs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n(draft_not_owner_reviewed — saved data/review/drafts/{moment['moment_id']}.draft.json)")

    if a.apply:
        cands = []
        for i, r in enumerate(rcs):
            echo = str(r.get("selected_echo") or "")
            cands.append({
                "candidate_id": f"preset_{i}", "display_text": str(r.get("display_text") or ""),
                "action_payload": {"text": str(r.get("display_text") or ""), "action_type": moment["action_space"].get("action_type", "other"),
                                   "intent": str(r.get("semantic_role") or "stance"), "target_actors": ["scene_focus"], "risk_posture": "balanced"},
                "emotion_role": str(r.get("emotion_role") or ""), "semantic_role": str(r.get("semantic_role") or ""),
                "distinctness_rationale": "CAB-authored (Studio dogfood), owner-reviewed",
                "evidence_refs": [f"{moment['moment_id']}_u001", "current_scene_window"],
                "constraint_refs": ["current_scene_only", "no_branch_rewrite", "source_window_grounding"],
                "viewer_motivation": str(r.get("viewer_motivation") or ""),
                "friend_voice_seed": echo, "selected_echo": echo,
            })
        ce = moment["companion_exchange"]
        ce["companion_lead"] = lead
        ce["reply_candidates"] = cands
        ce["content_status"] = "cab_authored_owner_reviewed"
        moment["companion_surface"]["companion_lead"] = lead
        moment["companion_surface"]["hook"] = lead
        moment["action_space"]["default_options"] = [c["action_payload"]["text"] for c in cands]
        moment["action_space"]["mouthpiece_candidates"] = cands
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nAPPLIED to {moment['moment_id']} -> {pack_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
