#!/usr/bin/env python3
"""看剧搭子 · Studio dogfood demo — the agentic authoring backstage → the deterministic Stage.

ONE command that walks the full Studio→Stage bridge for a live 答辩. It narrates five
stages using REAL artifacts, runs the CAB authoring LIVE on one window, and ends by
showing the Stage runtime serve the reviewed pack to a viewer:

  1. 窗口      a圈选+评审过的 ~20s 情绪点（真 ASR）—— the input
  2. CAB 授权  the 2-stage CAB authoring runs LIVE (lead + 3「我想说」+ 每条 echo),
              grounded in real ASR + the owner taste overlay
  3. taste 评审 the owner taste spec (rules + failure-pattern negatives + gold) AND the
              harness's discrimination (the recorded 8-case proof rejects bad windows)
  4. promote   the owner-approved CompanionExchangePack on disk (the bridge artifact)
  5. 落进 Stage the runtime serves that pack; a viewer taps a「我想说」→ hears the echo

Live authoring needs the Ark provider:   set -a; . ./.env; set +a
Offline rehearsal / safe fallback:        --no-live   (uses the reviewed pack, no provider)

  python3 tools/ars/deadman_studio_dogfood_demo.py                       # live, 云渺 grief beat
  python3 tools/ars/deadman_studio_dogfood_demo.py --drama-id lihun --moment-id lihun_ep06_m001
  python3 tools/ars/deadman_studio_dogfood_demo.py --no-live             # offline rehearsal
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

OVERLAY = REPO / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.2.json"
GUIDANCE = REPO / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json"
PROOF = REPO / "data/evals/studio_cab_graph_proof.v0.1.verify-20260609.json"


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def banner(step: str, title: str) -> None:
    print("\n" + "═" * 72)
    print(f"  [{step}/5]  {title}")
    print("═" * 72)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--drama-id", default="yunmiao")
    ap.add_argument("--moment-id", default="yunmiao_ep17_m001")
    ap.add_argument("--no-live", action="store_true",
                    help="offline: show the reviewed pack content instead of a live CAB call")
    args = ap.parse_args()

    pack = load(REPO / f"data/dramas/{args.drama_id}/moments.v0.1.json")
    moment = next((m for m in pack["moments"] if m["moment_id"] == args.moment_id), pack["moments"][0])
    ce = moment["companion_exchange"]
    ep = moment["source_drama"]["episode_id"]
    iw = moment["interaction_window"]

    print("\n" + "█" * 72)
    print("  看剧搭子 · STUDIO DOGFOOD —— agentic 授权 backstage → deterministic Stage")
    print("  Studio 把一个剧情瞬间，变成一份审过的 CompanionExchangePack。")
    print("█" * 72)
    print(f"  剧: {pack.get('title')}    集: {ep}    moment: {moment['moment_id']}")
    print(f"  模式: {'离线（--no-live，用已评审内容）' if args.no_live else '在线（CAB 授权实跑）'}")

    # ---- 1. 窗口 -----------------------------------------------------------
    banner("1", "窗口 WINDOW —— 一个圈选+评审过的 ~20s 情绪点（真 ASR）")
    print(f"  scene_signal : {ce.get('scene_signal')}")
    print(f"  window       : {iw['start_seconds']}–{iw['end_seconds']}s  "
          f"({iw.get('source')}, confidence={iw.get('confidence')})")
    try:
        from Deadman.tools.ars.deadman_author_drama_heroes import asr_window
        asr = asr_window(args.drama_id, ep, int(iw["start_seconds"]) * 1000, int(iw["end_seconds"]) * 1000)
    except Exception:
        asr = []
    print(f"  ASR          : {(' '.join(asr) or ce.get('scene_signal', ''))[:220]}")

    # ---- 2. CAB 授权 -------------------------------------------------------
    banner("2", "CAB 授权 AUTHORING —— 2 段式 CAB（Doubao/Ark），grounded in 真 ASR + taste overlay")
    if args.no_live:
        print("  [--no-live] 离线：展示 pack 里已 CAB 授权 + owner 评审过的内容：")
        print(f"  companion_lead : {ce.get('companion_lead')}")
        for i, r in enumerate(ce.get("reply_candidates", []), 1):
            print(f"    [{i}] 我想说「{r.get('display_text')}」 → echo: {r.get('selected_echo')}")
    else:
        try:
            from Deadman.tools.ars.deadman_author_drama_heroes import (
                author_moment, ArkStudioProofProvider,
            )
            guidance = load(GUIDANCE)
            provider = ArkStudioProofProvider.from_env()
            print("  …CAB authoring LIVE（stage A: lead + 3「我想说」; stage B: 每条 echo）…\n")
            _scene, lead, rcs = author_moment(provider, guidance, args.drama_id, pack, moment)
            print(f"  companion_lead : {lead}")
            for i, r in enumerate(rcs, 1):
                print(f"    [{i}] 我想说「{r.get('display_text')}」  (motiv: {r.get('viewer_motivation')})")
                print(f"        echo → {r.get('selected_echo')}")
            print("\n  ↳ 这是 draft_not_owner_reviewed —— 接着进 owner taste 评审门 ↓")
        except Exception as exc:  # provider/env missing — degrade gracefully
            print(f"  [live 授权不可用: {exc}]")
            print("  → 没 source .env? 跑:  set -a; . ./.env; set +a   ；或加 --no-live 离线演。")

    # ---- 3. taste 评审 -----------------------------------------------------
    banner("3", "taste 评审 REVIEW —— owner 品味规约（积累的资产）+ harness 的判别力")
    if OVERLAY.exists():
        ov = load(OVERLAY)
        negs = ov.get("named_negatives", [])
        golds = ov.get("gold_examples", [])
        rule_blocks = [k for k in ov if k.endswith("rules_addendum")]
        hard = sum(1 for n in negs if n.get("severity") == "hard")
        print(f"  taste overlay v0.2: {len(rule_blocks)} 规则块 · "
              f"{len(negs)} 条模式负例（{hard} hard / {len(negs) - hard} soft）· {len(golds)} 条 gold")
        print("  —— 负例是『一类失败模式』，不是某句原文（能泛化到新变体）:")
        for n in negs[:3]:
            print(f"     ✗ [{n.get('severity')}|{n.get('layer')}] {n.get('negative_type')}: {str(n.get('pattern'))[:64]}")
    if PROOF.exists():
        proof = load(PROOF)["proof_report"]
        buckets = {b["bucket"]: b for b in proof.get("failure_buckets", [])}
        rejected = sum(buckets.get(k, {}).get("count", 0) for k in ("expected_rejection_pass", "context_boundary_pass"))
        print(f"\n  harness 判别力（recorded 8-case 绿 proof，real provider）:")
        print(f"     {proof.get('completed_case_count')}/{proof.get('planned_case_count')} 通过 —— "
              f"其中 {rejected} 个 taste-负例窗口被【正确拒绝】。会挑，不是无脑生成。")

    # ---- 4. promote --------------------------------------------------------
    banner("4", "promote —— owner 批准后，落成审过的 CompanionExchangePack（5 文件）")
    for f in sorted((REPO / f"data/dramas/{args.drama_id}").rglob("*.json")):
        print(f"     {f.relative_to(REPO)}")
    print(f"  review_status={ce.get('review_status')}   content_status={ce.get('content_status', '-')}")

    # ---- 5. 落进 Stage -----------------------------------------------------
    banner("5", "落进 STAGE —— runtime 服务这份 pack；观众点一句「我想说」→ 听到授权好的 echo")
    os.environ.setdefault("DEADMAN_JUDGMENT_ENGINE", "demo_deterministic")
    from fastapi.testclient import TestClient
    from backend.api import create_app

    client = TestClient(create_app())
    cand = ce["reply_candidates"][0]
    payload = {
        "viewer_session_id": "dogfood-demo", "event_id": "evt-1", "event_type": "user_action",
        "drama_id": args.drama_id, "episode_id": ep, "moment_id": moment["moment_id"],
        "playback_time_seconds": int(iw["start_seconds"]),
        "action": {"source": "preset_candidate", "candidate_id": cand["candidate_id"],
                   "text": cand["display_text"], "action_payload": cand["action_payload"]},
    }
    resp = client.post("/api/deadman/runtime/session/event", json=payload).json()
    print(f"  搭子开场  : {ce.get('companion_lead')}")
    print(f"  观众点    : 我想说「{cand['display_text']}」")
    print(f"  搭子接住  : {(resp.get('result_surface') or {}).get('text')}")
    if resp.get("error"):
        print(f"  [error: {resp['error']}]")

    print("\n" + "─" * 72)
    print("  口径: LangGraph studio-cab 图 = 授权 harness（8-case 绿 proof 已证，会拒负例）；")
    print("        4 个 hero 用 taste-overlay 单发路径（deadman_author_drama_heroes）授权。")
    print("        Studio 重而 agentic（后台）· Stage 轻而确定（前台）· CompanionExchangePack 为桥。")
    print("─" * 72 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
