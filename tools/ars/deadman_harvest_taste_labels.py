#!/usr/bin/env python3
"""Harvest ALL owner taste labels (v1 splits + v2 field_verdicts/trays + new in-player) ->
normalize -> dedup (authority inplayer > v1 > v2) -> "全量" at data/review/taste_labels_full.v0.1.json.

Deterministic + testable. checkpoint① of the v0.3 rebuild (docs/context/dataset-rebuild-v03-contract.md):
harvest -> print N/distribution + text_unresolved -> STOP for owner review. Does NOT touch LLM or v0.3.

口径 (binding): NO label loss. Verdicts/notes are preserved even when copy text cannot be joined
(routed to `text_unresolved`, not dropped). Cross-source/round conflicts are RECORDED (authority
resolves which wins, but the loser is kept in `conflicts`). Frozen v1 is read-only — never mutated.

Join notes (why this is non-trivial):
  - v2 field_verdicts store verdict+negative_type but NOT the copy text -> join the SAME-ROUND
    real_provider_proof draft by case_id (the proof_ref field is unreliable for round4/5 — it points at
    base — so we join by round token from the filename instead).
  - in-player labels store v/tag/note but NOT the copy text -> resolve from the data/dramas pack.
  - trays are markdown; only round1 carries real owner verdicts (rounds 2-6 are all `abstain`, owner
    moved to the field_verdicts JSON path). We harvest the non-abstain ones (moment-level) so the early
    owner taste that predates field_verdicts is not lost.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

V1_PATH = REPO / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"
OVERLAY_PATH = REPO / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.2.json"
FIELD_GLOB = "studio_cab_field_verdicts.v0.1*.json"
TRAY_GLOB = "studio_cab_owner_taste_tray.v0.1*.md"
REVIEW_DIR = REPO / "data/review"
PROOF_DIR = REPO / "data/evals"
INPLAYER_PATH = REPO / "tmp/studio_review_labels.json"
OUT_PATH = REVIEW_DIR / "taste_labels_full.v0.1.json"

LAYER_MAP = {"lead": "companion_lead", "say": "display_text", "echo": "echo"}
# authority: inplayer (newest) > v1 (owner_reviewed_frozen) > v2 (field/tray; tray made-process uncertain)
SOURCE_RANK = {"inplayer": 3, "v1": 2, "v2_field": 1, "v2_tray": 0}
GOLD_WORDS = {"accept", "accept_with_minor_tweak", "gold", "ok"}
REJECT_WORDS = {"reject", "bad"}


# ---------------------------------------------------------------- normalizers
def norm_text(t: str) -> str:
    """Dedup key: drop all whitespace + trailing CN/EN sentence punctuation."""
    return re.sub(r"\s+", "", t or "").rstrip("。.!！?？，,、")


def norm_verdict(v: str) -> str:
    v = (v or "").strip().lower()
    if v in GOLD_WORDS:
        return "gold"
    if v in REJECT_WORDS:
        return "reject"
    return "abstain"


def _s(v) -> str:
    """Coerce any field value to a string (some v1 fields like context_summary are dicts)."""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return "" if v is None else str(v)


def rec(source, layer, element, text, verdict, *, item_id="", rnd=None, pattern=None,
        note="", correction=None, scene="", episode_id="", provenance=""):
    t = (text or "").strip()
    return {
        "source": source, "round": rnd, "item_id": item_id, "layer": layer, "element": element,
        "text": t, "verdict": verdict, "pattern": pattern or None, "note": note or "",
        "correction_hint": correction or None, "scene": (scene or "")[:200],
        "episode_id": episode_id, "provenance": provenance, "text_resolved": bool(t),
    }


def token_of(name: str) -> str:
    m = re.search(r"\.(round\d+)\.", name)
    if m:
        return m.group(1)
    if "_production" in name:
        return "production"
    return "base"


def round_int(token: str):
    return int(re.sub(r"\D", "", token)) if token.startswith("round") else None


# ------------------------------------------------------------------ v1 splits
def v1_records(doc: dict) -> list[dict]:
    sp = doc.get("splits", {}) or {}
    out: list[dict] = []

    def emit(split, key, layer, text_fields, verdict):
        for it in (sp.get(split, {}) or {}).get(key) or []:
            if not isinstance(it, dict):
                continue
            text = next((_s(it[f]) for f in text_fields if it.get(f)), "")
            out.append(rec("v1", layer, f"{split}.{key}", text, verdict,
                           item_id=it.get("item_id", ""),
                           pattern=it.get("negative_type") or it.get("window_review_decision"),
                           note=_s(it.get("reject_reason") or it.get("why_bad") or it.get("policy") or ""),
                           correction=it.get("correction_hint"),
                           scene=_s(it.get("context_summary") or it.get("scene_signal") or ""),
                           episode_id=it.get("episode_id", ""), provenance=it.get("provenance", "")))

    # gold / positive
    emit("lead_authoring", "examples", "companion_lead", ["lead_text", "display_text"], "gold")
    emit("reply_authoring", "examples", "display_text", ["display_text"], "gold")
    for ek in ("runtime_reviewed_examples", "owner_reviewed_examples", "draft_examples"):
        emit("selected_echo_direction", ek, "echo", ["selected_echo", "display_text"], "gold")
    # window has no copy text -> key on the unique item_id (time_range collides across episodes);
    # the real context lives in scene/note/pattern.
    emit("window_selection", "gold_examples", "window", ["item_id", "time_range"], "gold")
    # reject / negative
    emit("lead_authoring", "rejected_examples", "companion_lead", ["display_text", "lead_text"], "reject")
    emit("reply_authoring", "rejected_examples", "display_text", ["display_text"], "reject")
    emit("selected_echo_direction", "rejected_examples", "echo", ["selected_echo", "display_text"], "reject")
    emit("window_selection", "negative_examples", "window", ["item_id", "time_range"], "reject")
    # repair: the bad_text is a reject; replacement_text is the correction
    for split, layer in (("lead_authoring", "companion_lead"), ("reply_authoring", "display_text")):
        for it in (sp.get(split, {}) or {}).get("repair_examples") or []:
            if not isinstance(it, dict):
                continue
            out.append(rec("v1", layer, f"{split}.repair", it.get("bad_text", ""), "reject",
                           item_id=it.get("item_id", ""), pattern=it.get("failure_type"),
                           note=it.get("reason", ""), correction=it.get("replacement_text"),
                           episode_id=it.get("episode_id", ""), provenance=it.get("provenance", "repair")))
    return out


# ----------------------------------------------------- v2 field_verdicts + join
def proof_path_for(token: str) -> Path:
    suffix = "" if token in (None, "base") else f".{token}"
    return PROOF_DIR / f"studio_cab_real_provider_proof.v0.1{suffix}.json"


def load_proof_drafts(token: str) -> dict:
    """case_id -> case_result (carries .draft and .episode_id)."""
    p = proof_path_for(token)
    if not p.exists():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    return {c.get("case_id"): c for c in doc.get("case_results", []) if isinstance(c, dict)}


def field_records(doc: dict, token: str, drafts: dict) -> list[dict]:
    rnd = round_int(token)
    out: list[dict] = []
    for cid, case in (doc.get("cases") or {}).items():
        if not isinstance(case, dict):
            continue
        cr = drafts.get(cid) or {}
        draft = cr.get("draft") or {}
        epi = cr.get("episode_id", "")
        cands = draft.get("reply_candidates") or []
        lead = case.get("lead") or {}
        if lead.get("verdict"):
            out.append(rec("v2_field", "companion_lead", "lead", draft.get("companion_lead", ""),
                           norm_verdict(lead["verdict"]), item_id=cid, rnd=rnd,
                           note=lead.get("note", ""), episode_id=epi, provenance="owner_field_verdict"))
        for i, rep in enumerate(case.get("replies") or []):
            if not isinstance(rep, dict):
                continue
            cand = cands[i] if i < len(cands) else {}
            if rep.get("display_text_verdict"):
                out.append(rec("v2_field", "display_text", f"say{i + 1}", cand.get("display_text", ""),
                               norm_verdict(rep["display_text_verdict"]), item_id=cid, rnd=rnd,
                               pattern=rep.get("display_text_negative_type"),
                               note=rep.get("display_text_note", ""),
                               correction=rep.get("display_text_correction_hint"),
                               episode_id=epi, provenance="owner_field_verdict"))
            if rep.get("echo_verdict"):
                out.append(rec("v2_field", "echo", f"echo{i + 1}",
                               cand.get("selected_echo") or cand.get("friend_voice_seed", ""),
                               norm_verdict(rep["echo_verdict"]), item_id=cid, rnd=rnd,
                               pattern=rep.get("echo_negative_type"), note=rep.get("echo_note", ""),
                               correction=rep.get("echo_correction_hint"),
                               episode_id=epi, provenance="owner_field_verdict"))
    return out


# ------------------------------------------------------------------ v2 trays
_CASE_RE = re.compile(r"case_id\**:[ \t]*`([^`]+)`")
# [ \t]* not \s* — \s crosses the newline and would swallow the closing ``` fence as the note/verdict.
_VERD_RE = re.compile(r"^owner_verdict:[ \t]*(\S+)", re.M)
_NOTE_RE = re.compile(r"^owner_notes:[ \t]*(.*)$", re.M)
_LEAD_RE = re.compile(r"###\s*companion_lead\s*\n+>\s*(.+)")
_EPI_RE = re.compile(r"(huangnian|lihun|yunmiao)_ep\d+")


def tray_records(text: str, token: str) -> tuple[list[dict], int]:
    """-> (records with real signal, abstain_count). Moment-level; non-abstain or noted only."""
    rnd = round_int(token)
    out: list[dict] = []
    abstain = 0
    blocks = re.split(r"^## Draft ", text, flags=re.M)[1:]
    for b in blocks:
        mv = _VERD_RE.search(b)
        verd = mv.group(1).strip() if mv else "abstain"
        mn = _NOTE_RE.search(b)
        note = (mn.group(1).strip() if mn else "")
        if verd == "abstain" and not note:
            abstain += 1
            continue
        mc = _CASE_RE.search(b)
        cid = mc.group(1) if mc else ""
        ml = _LEAD_RE.search(b)
        lead = ml.group(1).strip() if ml else ""
        me = _EPI_RE.search(cid or b)
        epi = me.group(0) if me else ""
        out.append(rec("v2_tray", "moment", "moment", lead or cid, norm_verdict(verd),
                       item_id=cid, rnd=rnd, note=note, scene=lead, episode_id=epi,
                       provenance="owner_tray"))
    return out, abstain


# --------------------------------------------------------------- in-player join
def inplayer_records(labels: dict, resolver) -> list[dict]:
    from tools.ars.deadman_build_overlay_deltas import _element_text, _scene
    out: list[dict] = []
    for mid, l in (labels or {}).items():
        if not isinstance(l, dict):
            continue
        drama = mid.split("_")[0]
        m = resolver(drama, mid) or {}
        scene = _scene(m) if m else ""
        epi = (m.get("source_drama", {}) or {}).get("episode_id", "") or mid.rsplit("_", 1)[0]
        if l.get("window") == "reject":
            out.append(rec("inplayer", "window", "window", l.get("window_note") or mid, "reject",
                           item_id=mid, note=l.get("window_note", ""), scene=scene,
                           episode_id=epi, provenance="inplayer_window"))
        if l.get("direction") == "reject":
            out.append(rec("inplayer", "moment", "direction", l.get("direction_note") or mid, "reject",
                           item_id=mid, note=l.get("direction_note", ""), scene=scene,
                           episode_id=epi, provenance="inplayer_direction"))

        def el(kind, idx, e):
            if not isinstance(e, dict) or not e.get("v"):
                return
            txt = _element_text(m, kind, idx) if m else ""
            out.append(rec("inplayer", LAYER_MAP[kind], "lead" if kind == "lead" else f"{kind}{idx + 1}",
                           txt, norm_verdict(e["v"]), item_id=mid, pattern=e.get("tag"),
                           note=e.get("note", ""), scene=scene, episode_id=epi,
                           provenance="inplayer_element"))

        if isinstance(l.get("lead"), dict):
            el("lead", 0, l["lead"])
        for i, e in enumerate(l.get("says") or []):
            el("say", i, e)
        for i, e in enumerate(l.get("echoes") or []):
            el("echo", i, e)
    return out


# --------------------------------------------------------------------- dedup
def _slim(r: dict) -> dict:
    return {k: r[k] for k in ("source", "round", "item_id", "layer", "element", "text", "verdict",
                              "pattern", "note") if r.get(k) not in (None, "")}


def dedup(records: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Group by (layer, norm_text); keep most-authoritative; record verdict conflicts."""
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r["layer"], norm_text(r["text"])), []).append(r)
    kept, conflicts, merged = [], [], 0
    for grp in groups.values():
        ordered = sorted(grp, key=lambda r: (SOURCE_RANK.get(r["source"], 0), r["round"] or 0,
                                             1 if r["source"] == "v2_field" else 0), reverse=True)
        winner, others = ordered[0], ordered[1:]
        kept.append(winner)
        merged += len(others)
        if others and len({r["verdict"] for r in grp}) > 1:
            conflicts.append({"layer": winner["layer"], "text": winner["text"],
                              "kept": _slim(winner), "dropped": [_slim(o) for o in others]})
    return kept, conflicts, merged


# --------------------------------------------------------------- distribution
def _tally(records, key):
    out: dict = {}
    for r in records:
        out[r.get(key) or "—"] = out.get(r.get(key) or "—", 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def build(v1_doc, field_files, tray_files, inplayer, resolver, overlay):
    raw: list[dict] = []
    raw_by_source: dict = {}
    tray_abstain = 0

    v1r = v1_records(v1_doc)
    raw += v1r
    raw_by_source["v1"] = len(v1r)

    fr_total = 0
    for f in field_files:
        token = token_of(f.name)
        recs = field_records(json.loads(f.read_text(encoding="utf-8")), token, load_proof_drafts(token))
        raw += recs
        fr_total += len(recs)
    raw_by_source["v2_field"] = fr_total

    tr_total = 0
    for f in tray_files:
        recs, ab = tray_records(f.read_text(encoding="utf-8"), token_of(f.name))
        raw += recs
        tr_total += len(recs)
        tray_abstain += ab
    raw_by_source["v2_tray"] = tr_total

    ipr = inplayer_records(inplayer, resolver)
    raw += ipr
    raw_by_source["inplayer"] = len(ipr)

    resolved = [r for r in raw if r["text_resolved"]]
    unresolved = []
    for r in raw:
        if not r["text_resolved"]:
            u = _slim(r)
            u["unresolved_reason"] = "copy text could not be joined (missing draft/pack/case)"
            unresolved.append(u)

    kept, conflicts, merged = dedup(resolved)

    rejects = [r for r in kept if r["verdict"] == "reject"]
    golds = [r for r in kept if r["verdict"] == "gold"]
    abstains = [r for r in kept if r["verdict"] == "abstain"]

    pri = {
        "note": "v2 overlay distillations (named_negatives/gold/addenda) — RECONCILE during clustering, "
                "do NOT treat as new raw instances. v0.3 supersedes these.",
        "named_negatives": overlay.get("named_negatives", []),
        "gold_examples": overlay.get("gold_examples", []),
        "addenda": {k: overlay.get(k) for k in overlay if k.endswith("_rules_addendum")},
    }

    out = {
        "schema_version": "taste_labels_full.v0.1",
        "note": "全量 harvested+normalized+deduped owner taste labels (v1+v2_field+v2_tray+inplayer). "
                "checkpoint① of the v0.3 rebuild — owner reviews N/distribution/conflicts/unresolved "
                "BEFORE coherent clustering into overlay v0.3. Not a runtime artifact. Frozen v1 untouched.",
        "authority_order": ["inplayer", "v1", "v2_field", "v2_tray"],
        "raw_counts": raw_by_source,
        "tray_abstain_skipped": tray_abstain,
        "distribution": {
            "raw_total": len(raw),
            "unique_after_dedup": len(kept),
            "merged_exact_dups": merged,
            "conflicts": len(conflicts),
            "text_unresolved": len(unresolved),
            "by_source": _tally(kept, "source"),
            "by_layer": _tally(kept, "layer"),
            "by_verdict": _tally(kept, "verdict"),
            "by_pattern": _tally([r for r in kept if r["pattern"]], "pattern"),
            # "gold" is mixed-provenance: owner_confirmed (true gold) vs phase2_repair_auto / runtime_reviewed
            # (provisional — some of these are exactly what the owner's new review now rejects).
            "by_gold_provenance": _tally(golds, "provenance"),
            "reject": len(rejects), "gold": len(golds), "abstain": len(abstains),
        },
        "records": kept,
        "conflicts": conflicts,
        "text_unresolved": unresolved,
        "prior_distillations": pri,
    }
    return out


# ---------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    from tools.ars.deadman_build_overlay_deltas import _moment

    v1_doc = json.loads(V1_PATH.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8")) if OVERLAY_PATH.exists() else {}
    field_files = sorted(REVIEW_DIR.glob(FIELD_GLOB))
    tray_files = sorted(REVIEW_DIR.glob(TRAY_GLOB))
    inplayer = json.loads(INPLAYER_PATH.read_text(encoding="utf-8")) if INPLAYER_PATH.exists() else {}

    out = build(v1_doc, field_files, tray_files, inplayer, _moment, overlay)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.quiet:
        d = out["distribution"]
        print("=" * 64)
        print("checkpoint① — 全量 taste labels harvested (deterministic, no LLM)")
        print("=" * 64)
        print(f"raw per source     : {out['raw_counts']}  (tray abstain skipped: {out['tray_abstain_skipped']})")
        print(f"raw total          : {d['raw_total']}")
        print(f"unique after dedup : {d['unique_after_dedup']}  "
              f"(merged exact dups: {d['merged_exact_dups']}, conflicts: {d['conflicts']}, "
              f"text_unresolved: {d['text_unresolved']})")
        print(f"by verdict         : {d['by_verdict']}")
        print(f"by source          : {d['by_source']}")
        print(f"by layer           : {d['by_layer']}")
        print(f"by pattern (tagged): {d['by_pattern']}")
        print(f"gold provenance    : {d['by_gold_provenance']}  (<- not all 'gold' is owner-confirmed)")
        if out["conflicts"]:
            print("\nconflicts (authority-resolved, loser kept):")
            for c in out["conflicts"][:12]:
                losers = ", ".join(f"{o['source']}:{o['verdict']}" for o in c["dropped"])
                print(f"  [{c['layer']}] {c['text'][:34]!r}  "
                      f"kept={c['kept']['source']}:{c['kept']['verdict']}  vs {losers}")
        if out["text_unresolved"]:
            print(f"\ntext_unresolved ({len(out['text_unresolved'])}) — verdict kept, copy text needs a join fix:")
            for u in out["text_unresolved"][:20]:
                print(f"  {u['source']} {u.get('item_id','')[:46]} [{u['layer']}/{u.get('element','')}] "
                      f"{u['verdict']}  {u.get('note','')[:30]}")
        print(f"\nwrote {out_path.relative_to(REPO) if out_path.is_absolute() else out_path}")
        print("STOP — checkpoint①. Owner reviews before coherent clustering -> v0.3. (v1 frozen untouched.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
