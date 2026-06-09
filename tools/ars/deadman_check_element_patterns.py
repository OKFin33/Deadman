#!/usr/bin/env python3
"""Element-level pattern gate for runtime packs, grounded in the field_verdicts taste taxonomy.

Checks every lead / display_text / echo of every runtime moment against the MECHANICALLY decidable
sub-patterns from data/review/studio_cab_field_verdicts.v0.1*.json (the owner-reviewed taste taxonomy):

  lead_question_shape · echo_too_long · echo_formulaic_opening · echo_paraphrases_display ·
  echo_promotes_show · display_paraphrases_lead · display_not_distinct

The subtle patterns (echo_weak_responsiveness, echo_awkward_phrasing, *_exaggeration, low_emotion ...)
need owner/judge taste and are out of scope here — this gate only catches the gross, regressable ones.

Exit non-zero if any tracked runtime pack trips a gross pattern. Run before commit, like the other gates.
Full taxonomy + rationale: docs/context/taste-pattern-findings.md
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHOW_WORDS = ("节奏", "这部", "演技", "剧情拉", "追剧", "这剧", "本剧", "爽剧", "短剧",
              "台词", "代入感", "拍得", "镜头", "这段戏", "演得", "这段拍")
Q_WORDS = ("该不该", "要不要", "是不是该")
ECHO_MAX_CHARS = 40


def _overlap(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(1, len(sa | sb))


def _elements(moment: dict):
    a = moment.get("action_space") or {}
    cs = (moment.get("companion_exchange") or {}).get("reply_candidates") or a.get("mouthpiece_candidates") or []
    lead = (moment.get("companion_exchange") or {}).get("companion_lead") or (moment.get("companion_surface") or {}).get("companion_lead") or ""
    says = [c.get("display_text", "") for c in cs]
    echoes = [(c.get("selected_echo") or c.get("friend_voice_seed") or "") for c in cs]
    return lead, says, echoes


def check_moment(moment: dict) -> list[dict]:
    lead, says, echoes = _elements(moment)
    flags: list[dict] = []

    def flag(loc, pattern, text):
        flags.append({"moment_id": moment.get("moment_id"), "element": loc, "pattern": pattern, "text": text[:60]})

    if lead and (lead.rstrip().endswith(("吗", "呢")) or lead.rstrip().endswith("吗？") or any(q in lead for q in Q_WORDS)):
        flag("lead", "lead_question_shape", lead)

    nonempty = [e for e in echoes if e]
    if len(nonempty) >= 2:
        lcp = nonempty[0]
        for e in nonempty[1:]:
            i = 0
            while i < len(lcp) and i < len(e) and lcp[i] == e[i]:
                i += 1
            lcp = lcp[:i]
        if len(lcp) >= 2:  # shared opening phrase across the echoes (e.g. 对啊… / 可不是…)
            flag("echo[all]", "echo_formulaic_opening", " / ".join(echoes))
    for i, e in enumerate(echoes):
        if not e:
            continue
        if len(e) > ECHO_MAX_CHARS:
            flag(f"echo[{i}]", "echo_too_long", e)
        if any(w in e for w in SHOW_WORDS):
            flag(f"echo[{i}]", "echo_promotes_show", e)
        if says[i] and _overlap(e, says[i]) > 0.72:
            flag(f"echo[{i}]", "echo_paraphrases_display", e)

    for i, s in enumerate(says):
        if s and lead and _overlap(s, lead) > 0.6:
            flag(f"say[{i}]", "display_paraphrases_lead", s)
    for i in range(len(says)):
        for j in range(i + 1, len(says)):
            if says[i] and says[j] and _overlap(says[i], says[j]) > 0.7:
                flag(f"say[{i}]~say[{j}]", "display_not_distinct", f"{says[i]} ~ {says[j]}")
    return flags


def check_all(data_root: Path) -> list[dict]:
    flags: list[dict] = []
    for f in sorted(data_root.glob("*/moments.v0.1.json")):
        for m in json.load(open(f)).get("moments", []):
            flags.extend(check_moment(m))
    return flags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default=str(REPO / "data/dramas"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    flags = check_all(Path(args.data_root))
    if args.json:
        print(json.dumps(flags, ensure_ascii=False, indent=2))
    else:
        for fl in flags:
            print(f"  ⚠ {fl['moment_id']:24} {fl['element']:14} {fl['pattern']:26} {fl['text']}")
        print(f"\n{'PASS — no gross element-pattern flags' if not flags else f'FAIL — {len(flags)} flag(s)'}")
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
