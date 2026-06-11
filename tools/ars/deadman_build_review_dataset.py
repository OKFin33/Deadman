#!/usr/bin/env python3
"""Process in-player review labels into a structured taste dataset, honoring the short-circuit gates.

Reads the review labels (default tmp/studio_review_labels.json) and emits a dataset where every moment
is classified by gate — so downstream consumers NEVER expect per-element data on short-circuited moments:
  window_reject    : window==reject       -> window-taste negative only
  direction_reject : direction==reject     -> content-direction negative only
  detailed         : per-element lead/say/echo verdicts (+ sub-pattern tags) -> element-taste signal

momentGate() here mirrors frontend reviewApi.ts exactly. Out: data/review/studio_review_dataset.v0.1.json
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_IN = REPO / "tmp/studio_review_labels.json"
DEFAULT_OUT = REPO / "data/review/studio_review_dataset.v0.1.json"


def moment_gate(label: dict) -> str:
    if (label or {}).get("window") == "reject":
        return "window_reject"
    if (label or {}).get("direction") == "reject":
        return "direction_reject"
    return "detailed"


def flatten_elements(label: dict) -> list[dict]:
    out: list[dict] = []
    lead = label.get("lead")
    if isinstance(lead, dict) and lead.get("v"):
        out.append({"element": "lead", "kind": "lead", "v": lead["v"], "tag": lead.get("tag", ""), "note": lead.get("note", "")})
    for key, kind in (("says", "say"), ("echoes", "echo")):
        for i, e in enumerate(label.get(key) or []):
            if isinstance(e, dict) and e.get("v"):
                out.append({"element": f"{kind}{i + 1}", "kind": kind, "v": e["v"], "tag": e.get("tag", ""), "note": e.get("note", "")})
    return out


def build(labels: dict) -> dict:
    moments, element_verdicts, window_taste = [], [], []
    gates, pattern_tally = Counter(), Counter()
    el_pass = el_bad = el_bad_untagged = el_abstain = 0
    untagged_notes: list[dict] = []

    for mid, label in (labels or {}).items():
        if not isinstance(label, dict):
            continue
        window = label.get("window")
        if not window and not label.get("direction") and not flatten_elements(label):
            continue  # entirely unlabeled — skip
        gate = moment_gate(label)
        gates[gate] += 1
        if window:
            window_taste.append({"moment_id": mid, "verdict": window, "note": label.get("window_note", "")})
        rec = {"moment_id": mid, "gate": gate, "window": window,
               "window_note": label.get("window_note", ""),
               "direction": label.get("direction"), "direction_note": label.get("direction_note", "")}
        if gate == "detailed":
            els = flatten_elements(label)
            rec["elements"] = els
            for e in els:
                element_verdicts.append({"moment_id": mid, **e})
                if e["v"] == "ok":
                    el_pass += 1
                elif e["v"] == "abstain":
                    el_abstain += 1  # owner saw it but didn't rule — not pass, not bad
                else:
                    el_bad += 1
                    if e.get("tag"):
                        pattern_tally[e["tag"]] += 1
                    else:
                        el_bad_untagged += 1
                        if e.get("note"):
                            untagged_notes.append({"moment_id": mid, "element": e["element"], "note": e["note"]})
        moments.append(rec)

    return {
        "schema_version": "studio_review_dataset.v0.1",
        "claim_boundary": "Owner in-player review labels, gate-classified. Per-element data only on 'detailed' moments; short-circuited moments carry window/direction reject + reason only.",
        "summary": {
            "moments_labeled": len(moments),
            "gates": dict(gates),
            "element_verdicts": len(element_verdicts),
            "element_pass": el_pass,
            "element_bad": el_bad,
            "element_abstain": el_abstain,  # owner couldn't/wouldn't rule — excluded from pass/bad
            "element_bad_untagged": el_bad_untagged,  # bads with free-text only — structured signal incomplete
        },
        "moments": moments,
        "window_taste": window_taste,
        "element_verdicts": element_verdicts,
        "pattern_tally": dict(pattern_tally.most_common()),
        "untagged_bad_notes": untagged_notes,  # free-text rejects not yet captured as a pattern tag
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", default=str(DEFAULT_IN))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    inp = Path(args.inp)
    if not inp.exists():
        print(f"no labels at {inp} — nothing to build")
        return 0
    ds = build(json.loads(inp.read_text(encoding="utf-8")))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ds, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(f"  summary: {ds['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
