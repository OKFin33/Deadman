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
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from Deadman.tools.ars.deadman_run_studio_real_provider_proof import (  # noqa: E402
    ArkStudioProofProvider, TWO_LAYER_SEMANTICS, stage_a_output_schema, stage_b_output_schema,
)

# v2 taste overlay: additive owner-taste deltas (read on top of frozen v1). The
# durable place taste accumulates — not the prompt scaffolding below.
OVERLAY_PATH = REPO / "data" / "datasets" / "studio_guidance" / "studio_cab_taste_overlay.v0.2.json"
OVERLAY = json.loads(OVERLAY_PATH.read_text(encoding="utf-8")) if OVERLAY_PATH.exists() else {}

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


def stage_a_prompt(scene, leads, replies):
    return {
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
            "For each reply also write viewer_motivation: one short phrase naming the posture/feeling of the viewer who'd pick this display_text and what they hope to hear back.",
            "Author the companion beat PURELY from scene.transcript — that dialogue is what is actually on screen. Read who is speaking and the real feeling of THIS beat, and surface what a viewer would want to say to it. Do not invent a theme (e.g. a power/identity reveal) that is not in the transcript. Every draft is draft_not_owner_reviewed.",
            "Avoid the display_text failure PATTERNS in negative_display_patterns — each names a failure SITUATION, not an exact string. Do not produce any display_text that falls into a pattern, including new wordings/variants; illustrative_examples only show the kind. (severity hard = never; soft_preference = lean away.)",
            "Avoid the companion_lead failure PATTERNS in negative_lead_patterns the same way — react in the moment as a co-watcher; don't recap/narrate the segment.",
            "Compose the three reply_candidates for COVERAGE per reply_set_composition (two core directions + one fallback).",
            *OVERLAY.get("lead_rules_addendum", []),
            *OVERLAY.get("display_text_rules_addendum", []),
            *OVERLAY.get("reply_set_rules_addendum", []),
        ],
        "reply_set_composition": OVERLAY.get("reply_set_rules_addendum", []),
        "negative_display_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "display_text"],
        "negative_lead_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "companion_lead"],
        "output_contract": {"case_id": scene["case_id"], "window_decision": "recommend_window",
            "companion_lead": "short friend-style lead",
            "reply_candidates": [{"display_text": "...", "emotion_role": "...", "semantic_role": "...", "viewer_motivation": "..."}],
            "failure_buckets": [], "rationale_summary": "...", "repair_notes": []},
    }


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
            *OVERLAY.get("echo_rules_addendum", []),
        ],
        "negative_echo_patterns": [{"pattern": n.get("pattern"), "severity": n.get("severity"), "illustrative_examples": n.get("illustrative_examples", [])} for n in OVERLAY.get("named_negatives", []) if n.get("layer") == "echo"],
        "output_contract": {"case_id": scene["case_id"], "selected_echo": "...", "echo_rationale": "..."},
    }
    if feedback:  # M4 directed revision: a critic rejected the prior draft — fix the echo specifically
        prompt["revision_feedback"] = str(feedback)
        prompt["echo_rules"] = [
            "这是修订轮：上一稿的 echo 被评审拒了。严格按 revision_feedback 重写这条 echo，专门修它点名的毛病，别再犯同样的。",
            *prompt["echo_rules"],
        ]
    return prompt


def author_moment(provider, guidance, drama, pack, moment, feedback=None):
    mid = moment["moment_id"]
    ep = moment["source_drama"]["episode_id"]
    iw = moment["interaction_window"]
    start_ms, end_ms = int(iw["start_seconds"]) * 1000, int(iw["end_seconds"]) * 1000
    transcript = asr_window(drama, ep, start_ms, end_ms) or [moment["companion_exchange"].get("scene_signal", "")]
    trig = moment["action_space"].get("action_type", "other")
    scene = {"case_id": f"hero:{mid}", "drama_id": drama, "drama_title": pack.get("title"),
             "episode_id": ep, "transcript": transcript}  # author from real ASR only; mined hook dropped
    leads, replies, echoes = few_shot(guidance)
    a_out = call_json(provider, stage_a_prompt(scene, leads, replies), stage_a_output_schema())
    lead = str(a_out.get("companion_lead") or "")
    rcs = [r for r in a_out.get("reply_candidates", []) if isinstance(r, dict)][:3]
    disp = [str(r.get("display_text") or "") for r in rcs]
    prior: list[str] = []
    for i, r in enumerate(rcs):
        sib = [d for j, d in enumerate(disp) if j != i]
        b = call_json(provider, stage_b_prompt(scene, lead, r, sib, list(prior), echoes, feedback), stage_b_output_schema())
        r["selected_echo"] = str(b.get("selected_echo") or "")
        prior.append(r["selected_echo"])
    return scene, lead, rcs


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
