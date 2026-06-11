#!/usr/bin/env python3
"""Adapter: owner in-player review labels -> overlay v2 typed deltas (方案①: LLM propose -> owner edit -> commit).

Closes M4's dataset half: owner's strict review -> generalizable named_negatives + gold_examples in the
crown-jewel taste overlay (additive; NEVER touches frozen v1). See docs/context/overlay-adapter-contract.md.
口径: method professional + generalizable; N small is fine (a professional pivot, not a data-volume claim).

  --propose : cluster+generalize bad labels into proposed named_negatives (LLM/Ark) + gold from accepted
              moments -> data/review/overlay_deltas_proposed.v0.1.json  (OWNER reviews/edits this).
  --commit  : append the owner-reviewed proposal into overlay v2 (additive, idempotent).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
LABELS = REPO / "tmp/studio_review_labels.json"
PROPOSAL = REPO / "data/review/overlay_deltas_proposed.v0.1.json"
OVERLAY = REPO / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.2.json"
LAYER_MAP = {"lead": "companion_lead", "say": "display_text", "echo": "echo"}


def _load_env():
    for v in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(v, None)
    env = REPO / ".env"
    if env.exists() and not os.environ.get("ARK_API_KEY"):
        for raw in env.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, val = s.partition("=")
                os.environ.setdefault(k.strip(), val.strip())


def _moment(drama: str, mid: str):
    f = REPO / f"data/dramas/{drama}/moments.v0.1.json"
    if not f.exists():
        return None
    return next((m for m in json.loads(f.read_text(encoding="utf-8")).get("moments", []) if m.get("moment_id") == mid), None)


def _candidates(m):
    a = m.get("action_space") or {}
    return (m.get("companion_exchange") or {}).get("reply_candidates") or a.get("mouthpiece_candidates") or []


def _scene(m):
    return ((m.get("source_window") or {}).get("transcript_refs") or [{}])[0].get("text", "").strip()


def _lead(m):
    return (m.get("companion_exchange") or {}).get("companion_lead") or (m.get("companion_surface") or {}).get("companion_lead") or ""


def _element_text(m, kind, idx):
    if kind == "lead":
        return _lead(m)
    cs = _candidates(m)
    if idx < len(cs):
        return cs[idx].get("display_text", "") if kind == "say" else (cs[idx].get("selected_echo") or cs[idx].get("friend_voice_seed") or "")
    return ""


def collect(labels, resolver=_moment):
    """-> (bad_instances, gold_moment_ids). Element-level only on non-short-circuited (window/direction ok) moments."""
    bad, gold = [], []
    for mid, l in (labels or {}).items():
        if not isinstance(l, dict):
            continue
        drama = mid.split("_")[0]
        m = resolver(drama, mid)
        if not m:
            continue
        if l.get("window") == "reject" or l.get("direction") == "reject":
            continue  # short-circuited — no element signal
        scene = _scene(m)

        def add(kind, idx, e):
            if isinstance(e, dict) and e.get("v") == "bad":
                bad.append({"layer": LAYER_MAP[kind], "element": "lead" if kind == "lead" else f"{kind}{idx + 1}",
                            "moment_id": mid, "text": _element_text(m, kind, idx),
                            "owner_note": e.get("note", ""), "owner_tag": e.get("tag", ""), "scene": scene[:220]})
        if isinstance(l.get("lead"), dict):
            add("lead", 0, l["lead"])
        for i, e in enumerate(l.get("says") or []):
            add("say", i, e)
        for i, e in enumerate(l.get("echoes") or []):
            add("echo", i, e)

        els = [e for e in [l.get("lead"), *(l.get("says") or []), *(l.get("echoes") or [])] if isinstance(e, dict) and e.get("v")]
        if l.get("window") == "accept" and els and all(e.get("v") == "ok" for e in els):
            gold.append((drama, mid))
    return bad, gold


def gold_example(drama, mid):
    m = _moment(drama, mid) or {}
    return {
        "drama_id": drama, "moment_id": mid, "episode_id": m.get("source_drama", {}).get("episode_id", ""),
        "provenance": "owner_confirmed", "review_status": "owner_reviewed_in_player",
        "companion_lead": _lead(m),
        "reply_candidates": [{"display_text": c.get("display_text"), "viewer_motivation": c.get("viewer_motivation", ""),
                              "selected_echo": c.get("selected_echo") or c.get("friend_voice_seed", ""),
                              "coverage": c.get("semantic_role", "")} for c in _candidates(m)],
        "taste_note": "owner-approved via in-player review (window accept + all elements 达标)",
    }


def propose_prompt(instances):
    return {
        "system_prompt": (
            "You curate a taste FAILURE-PATTERN dataset for 看剧搭子 (a short-drama watching-companion). "
            "Product thesis: the viewer says the line the scene made them want to say (我想说一句) — NOT choosing a "
            "plot branch / 改剧情 (an archived anti-pattern). Given owner-flagged element failures, cluster them into "
            "GENERALIZABLE failure patterns (a pattern names a failure SITUATION, never a verbatim string) and emit each "
            "as a typed named_negative. Return ONE strict JSON object, no prose."),
        "task": "curate_named_negatives_from_owner_review",
        "layer_meaning": {"companion_lead": "搭子开场引子", "display_text": "观众自己想说的一句", "echo": "搭子对某条观众选择的回应"},
        "owner_flagged_failures": instances,
        "instructions": [
            "Cluster instances of the SAME failure into ONE named_negative (group across moments/elements).",
            "negative_type: use the owner's tag when present; else infer a short snake_case type.",
            "when: the triggering SITUATION (what scene/role/what-it-responded-to surfaces this failure).",
            "pattern: the generalizable failure description (a kind, not a verbatim string).",
            "why_bad: why it hurts the product (tie to 我想说一句 / non-改剧情 thesis where relevant).",
            "corrected_direction: what to author instead.",
            "severity: 'hard' if it breaks the core thesis (RPG/action-menu/改剧情/overclaim), else 'soft_preference'.",
            "illustrative_examples: copy the flagged text(s) verbatim. source_provenance: the {moment_id, element} of each.",
        ],
        "output_contract": {"named_negatives": [{
            "layer": "echo", "negative_type": "echo_rpg_or_action_menu", "severity": "hard",
            "when": "...", "pattern": "...", "why_bad": "...", "corrected_direction": "...",
            "illustrative_examples": ["..."], "source_provenance": [{"moment_id": "...", "element": "..."}]}]},
    }


def propose_schema():
    item = {"type": "object", "properties": {k: {"type": "string"} for k in
            ("layer", "negative_type", "severity", "when", "pattern", "why_bad", "corrected_direction")}}
    item["properties"]["illustrative_examples"] = {"type": "array", "items": {"type": "string"}}
    item["properties"]["source_provenance"] = {"type": "array", "items": {"type": "object"}}
    item["required"] = ["layer", "negative_type", "severity", "when", "pattern", "why_bad", "corrected_direction"]
    return {"type": "object", "properties": {"named_negatives": {"type": "array", "items": item}}, "required": ["named_negatives"]}


def cmd_propose():
    _load_env()
    if not LABELS.exists():
        print(f"no labels at {LABELS}")
        return 1
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    bad, gold = collect(labels)
    proposed = []
    if bad:
        from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider
        from tools.ars.deadman_author_drama_heroes import call_json
        provider = ArkStudioProofProvider.from_env()
        out = call_json(provider, propose_prompt(bad), propose_schema())
        proposed = out.get("named_negatives", []) if isinstance(out, dict) else []
    proposal = {
        "schema_version": "overlay_deltas_proposed.v0.1",
        "source": "in-player owner review labels",
        "review_note": "方案①: LLM-proposed from owner labels — OWNER EDIT before --commit. N small = professional pivot, not a volume claim.",
        "named_negatives": proposed,
        "gold_examples": [gold_example(d, m) for d, m in gold],
    }
    PROPOSAL.parent.mkdir(parents=True, exist_ok=True)
    PROPOSAL.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {PROPOSAL.relative_to(REPO)}  ({len(proposed)} named_negatives, {len(proposal['gold_examples'])} gold) — review/edit, then --commit")
    return 0


def merge(overlay: dict, proposal: dict) -> tuple[dict, int, int]:
    seen_neg = {(n.get("negative_type"), tuple(n.get("illustrative_examples", []))) for n in overlay.get("named_negatives", [])}
    seen_gold = {g.get("moment_id") for g in overlay.get("gold_examples", [])}
    add_n = add_g = 0
    for n in proposal.get("named_negatives", []):
        key = (n.get("negative_type"), tuple(n.get("illustrative_examples", [])))
        if key not in seen_neg:
            overlay.setdefault("named_negatives", []).append(n)
            seen_neg.add(key)
            add_n += 1
    for g in proposal.get("gold_examples", []):
        if g.get("moment_id") not in seen_gold:
            overlay.setdefault("gold_examples", []).append(g)
            seen_gold.add(g.get("moment_id"))
            add_g += 1
    return overlay, add_n, add_g


def cmd_commit():
    if not PROPOSAL.exists():
        print(f"no proposal at {PROPOSAL} — run --propose first")
        return 1
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    overlay, add_n, add_g = merge(overlay, proposal)
    OVERLAY.write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"appended {add_n} named_negatives + {add_g} gold_examples to overlay v2 (additive; frozen v1 untouched)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if args.commit:
        return cmd_commit()
    return cmd_propose()


if __name__ == "__main__":
    raise SystemExit(main())
