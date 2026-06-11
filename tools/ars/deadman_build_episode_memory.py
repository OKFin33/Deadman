#!/usr/bin/env python3
"""Build the layered episode-memory index (L3 one-line spine + L2 detailed event log) per episode,
from full-episode ASR. Cached to data/review/context_memory/{drama}.v0.1.json (producer-local, one-time).

Part of the layered context memory (owner design 2026-06-10):
  L0 canon (static, data/dramas/{d}/context.v0.1.json) / L3 series spine / L2 recent detail / L1 window beat,
  with a KNOWLEDGE HORIZON — the assembler injects only content <= the current window's airing position
  (never later), so the companion's knowledge == the viewer's knowledge (no spoilers, no fake 揭晓).

This tool builds the L2/L3 layers (one provider call per episode = one_line_summary + event_log together).
The assembler (the context node in deadman_author_drama_heroes.py) injects them gated.

  --drama huangnian [--through 12] [--dry-run]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

CTX_DIR = REPO / "data/review/context_memory"
FULL_EP_MS = 3_600_000   # pull the whole episode (short-drama eps are ~1 min)
MAX_UTT = 240            # safety cap (eps are ~45-55 utts, so this never truncates)


def out_path(drama: str) -> Path:
    return CTX_DIR / f"{drama}.v0.1.json"


def canon_title_premise(drama: str) -> tuple[str, str]:
    from tools.ars.deadman_author_drama_heroes import load_synopsis
    syn = load_synopsis(drama)  # official synopsis = authoritative premise (covers all 3 dramas)
    f = REPO / f"data/dramas/{drama}/context.v0.1.json"
    c = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return (syn.get("title") or c.get("title") or drama), (syn.get("synopsis") or c.get("premise", ""))


def episode_ids(drama: str, through: int) -> list[str]:
    """ep01..epNN that actually have ASR (asr_window returns utterances)."""
    from tools.ars.deadman_author_drama_heroes import asr_window
    eps = []
    for n in range(1, through + 1):
        eid = f"{drama}_ep{n:02d}"
        if asr_window(drama, eid, 0, FULL_EP_MS):
            eps.append(eid)
    return eps


def mem_prompt(episode_id: str, drama_title: str, premise: str, asr: list[str]) -> dict:
    return {
        "system_prompt": (
            "You build EPISODE MEMORY for a short-drama watching-companion (看剧搭子). Given one episode's full "
            "dialogue (ASR, mostly conversation), produce: (1) one_line_summary — ONE Chinese sentence capturing the "
            "episode's key event/turn (a 'story so far' spine entry the viewer would remember); (2) event_log — a "
            "concise ORDERED list (~4-8 items) of the concrete plot events/turns a viewer would track: who did what, "
            "key reveals and reversals, in Chinese. Plot FACTS, not commentary or evaluation. NOTE: the ASR often "
            "mis-recognizes proper names (人名) — use drama_premise for correct character identities and map garbled "
            "ASR names to it; prefer roles/relationships when a name is uncertain. Return ONE strict JSON object."),
        "task": "build_episode_memory", "product": "看剧搭子",
        "episode_id": episode_id, "drama_title": drama_title, "drama_premise": premise,
        "episode_asr": asr,
        "output_contract": {"one_line_summary": "一句话本集关键转折", "event_log": ["按序的具体事件1", "事件2"]},
    }


def mem_schema() -> dict:
    return {"type": "object", "properties": {
        "one_line_summary": {"type": "string"},
        "event_log": {"type": "array", "items": {"type": "string"}},
    }, "required": ["one_line_summary", "event_log"]}


def build(drama: str, through: int, dry_run: bool) -> int:
    from tools.ars.deadman_author_drama_heroes import asr_window
    title, premise = canon_title_premise(drama)
    eps = episode_ids(drama, through)
    print(f"{drama} 「{title}」: {len(eps)} episodes with ASR (through ep{through:02d}): "
          f"{[e.split('_')[-1] for e in eps]}")
    if not eps:
        print("no episodes with ASR — check tmp/ars_{drama}_analysis/volc_asr*/")
        return 1

    if dry_run:
        eid = eps[0]
        asr = asr_window(drama, eid, 0, FULL_EP_MS)[:MAX_UTT]
        print(f"\nDRY RUN — sample input for {eid} ({len(asr)} utts):")
        print("  premise:", premise[:60])
        print("  asr 头:", (" ".join(asr))[:160])
        print(f"\nwould make {len(eps)} provider calls (1/episode). re-run without --dry-run.")
        return 0

    from tools.ars.deadman_build_overlay_v03 import _load_env
    _load_env()
    from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider
    from tools.ars.deadman_author_drama_heroes import call_json
    provider = ArkStudioProofProvider.from_env()

    existing = json.loads(out_path(drama).read_text(encoding="utf-8")) if out_path(drama).exists() else {}
    episodes = existing.get("episodes", {}) if isinstance(existing, dict) else {}
    for eid in eps:
        if eid in episodes:  # idempotent: skip already-built episodes
            print(f"  {eid}: cached, skip")
            continue
        asr = asr_window(drama, eid, 0, FULL_EP_MS)[:MAX_UTT]
        out = call_json(provider, mem_prompt(eid, title, premise, asr), mem_schema())
        out = out if isinstance(out, dict) else {}
        episodes[eid] = {"episode_id": eid, "l3_one_line": out.get("one_line_summary", ""),
                         "l2_event_log": out.get("event_log", []), "asr_utterances": len(asr)}
        print(f"  {eid}: L3=「{out.get('one_line_summary', '')[:40]}」 L2={len(out.get('event_log', []))} events")

    index = {"schema_version": "episode_memory.v0.1", "drama_id": drama, "title": title,
             "premise": premise, "episodes": dict(sorted(episodes.items()))}
    out_path(drama).parent.mkdir(parents=True, exist_ok=True)
    out_path(drama).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path(drama).relative_to(REPO)}  ({len(episodes)} episodes)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drama", required=True)
    ap.add_argument("--through", type=int, default=20, help="build episodes ep01..epNN")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return build(a.drama, a.through, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
