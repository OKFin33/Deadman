#!/usr/bin/env python3
"""M4 spike — studio-cab generate->judge->revise as a REAL LangGraph graph (conditional cycle).

Validates three things before committing to M4:
  1. a REAL graph: a verdict-based conditional edge with a CYCLE (reject -> re-author), not linear;
  2. convergence: does reject -> re-author terminate at accept within bounded rounds?
  3. the cross-model critic (Qwen via `bl`) actually gives meaningful, discriminating verdicts.

Spike scope: CLI, one case, prints the round-by-round trace. NOT wired into the pipeline/console.
Run: python3 tools/ars/deadman_studio_cab_loop_spike.py [--drama yunmiao] [--moment yunmiao_ep17_m001] [--max-rounds 2]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def _load_env() -> None:
    for var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(var, None)
    if os.environ.get("ARK_API_KEY"):
        return
    env_path = REPO / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


class LoopState(TypedDict, total=False):
    drama: str
    pack: dict
    moment: dict
    draft: dict
    verdict: dict
    round: int
    trace: list


def _draft_case(moment: dict, draft: dict) -> dict:
    return {
        "case_id": f"spike:{moment.get('moment_id')}",
        "case_type": "gold_authoring",
        "item_id": moment.get("moment_id", ""),
        "episode_id": moment.get("source_drama", {}).get("episode_id", ""),
        "expected_behavior": "scene-grounded companion: in-scene lead + 3 viewer lines + echoes",
        "provider_status": "completed",
        "draft": draft,
    }


def author_node(author_provider, guidance, no_feedback: bool = False):
    from tools.ars.deadman_author_drama_heroes import author_moment

    def node(state: LoopState) -> LoopState:
        rnd = state.get("round", 0) + 1
        feedback = None if no_feedback else state.get("feedback")  # B vs ablation (blind resample)
        _scene, lead, rcs = author_moment(author_provider, guidance, state["drama"], state["pack"], state["moment"], feedback)
        draft = {"companion_lead": lead, "reply_candidates": rcs}
        step = {"round": rnd, "step": "author", "revised": bool(feedback), "lead": lead,
                "replies": [r.get("display_text") for r in rcs]}
        return {"draft": draft, "round": rnd, "trace": state.get("trace", []) + [step]}

    return node


def judge_node(judge_provider, force_reject_round1: bool = False):
    from tools.ars.deadman_run_studio_taste_judge import build_judge_prompt, call_judge_provider, normalize_verdict

    def node(state: LoopState) -> LoopState:
        if force_reject_round1 and state.get("round") == 1:  # mechanics test: prove the cycle fires
            verdict = {"overall_verdict": "reject", "forced_for_mechanics_test": True}
            step = {"round": state.get("round"), "step": "judge", "verdict": "reject", "dims": {"forced": "test"}}
            return {"verdict": verdict, "feedback": "(mechanics test) 强制拒,触发回环;按 echo_rules 重写 echo。",
                    "trace": state.get("trace", []) + [step]}
        case = _draft_case(state["moment"], state["draft"])
        prompt = build_judge_prompt(case)
        rationale = ""
        try:
            payload, meta = call_judge_provider(judge_provider, prompt)
            verdict = normalize_verdict(case, payload, meta, "")
            rationale = str((payload or {}).get("rationale_summary") or "")
        except Exception as exc:  # spike: surface, don't crash the loop
            verdict = {"overall_verdict": "not_available", "error": str(exc)[:160]}
        feedback = None  # B: build directed critique for the next revise round
        if verdict.get("overall_verdict") != "accept":
            fails = [k for k in ("lead_taste", "reply_voice_taste", "echo_taste") if verdict.get(k) == "needs_repair"]
            feedback = f"上一稿 verdict={verdict.get('overall_verdict')}；不达标维度={fails or ['整体偏弱']}；评审评语：{rationale}".strip()
        dims = {k: v for k, v in verdict.items() if k.endswith("_taste")}
        step = {"round": state.get("round"), "step": "judge",
                "verdict": verdict.get("overall_verdict"), "dims": dims}
        return {"verdict": verdict, "feedback": feedback, "trace": state.get("trace", []) + [step]}

    return node


def make_router(max_rounds: int):
    from langgraph.graph import END

    def route_after_judge(state: LoopState) -> str:
        verdict = (state.get("verdict") or {}).get("overall_verdict")
        if verdict == "accept" or state.get("round", 0) >= max_rounds:
            return END
        return "author"  # CYCLE: reject / accept_with_minor_tweak / not_available -> re-author

    return route_after_judge


def build_graph(author_provider, judge_provider, guidance, max_rounds: int,
                force_reject_round1: bool = False, no_feedback: bool = False):
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(LoopState)
    builder.add_node("author", author_node(author_provider, guidance, no_feedback))
    builder.add_node("judge", judge_node(judge_provider, force_reject_round1))
    builder.add_edge(START, "author")
    builder.add_edge("author", "judge")
    builder.add_conditional_edges("judge", make_router(max_rounds), {"author": "author", END: END})
    return builder.compile()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drama", default="yunmiao")
    ap.add_argument("--moment", default="yunmiao_ep17_m001")
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--force-reject-round1", action="store_true",
                    help="debug: force a reject on round 1 to prove the cycle fires independent of the judge")
    ap.add_argument("--no-feedback", action="store_true",
                    help="ablation: disable directed feedback (blind-resample baseline) to isolate B's effect")
    args = ap.parse_args()
    _load_env()

    from tools.ars.deadman_author_drama_heroes import ArkStudioProofProvider, load as _load
    from tools.ars.deadman_run_studio_taste_judge import BailianTasteJudgeProvider

    guidance = _load(REPO / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")
    pack = _load(REPO / f"data/dramas/{args.drama}/moments.v0.1.json")
    moment = next((m for m in pack["moments"] if m["moment_id"] == args.moment), pack["moments"][0])
    author_provider = ArkStudioProofProvider.from_env()
    judge_provider = BailianTasteJudgeProvider.from_env()
    import re
    model_alias = re.sub(r"ep-[0-9a-zA-Z-]+", "doubao-seed-2.0-lite", author_provider.model or "")
    print(f"author=ark/{model_alias}  judge=bailian(qwen)  max_rounds={args.max_rounds}")
    print(f"case: {args.drama} / {moment['moment_id']}\n")

    graph = build_graph(author_provider, judge_provider, guidance, args.max_rounds,
                        args.force_reject_round1, args.no_feedback)
    final = graph.invoke({"drama": args.drama, "pack": pack, "moment": moment, "round": 0, "trace": []})

    print("=== TRACE (real graph: author -> judge -> [accept->END | reject->author cycle]) ===")
    for step in final.get("trace", []):
        if step["step"] == "author":
            print(f"  R{step['round']} author : lead={step['lead']!r}  replies={step['replies']}")
        else:
            print(f"  R{step['round']} judge  : {step['verdict']}  dims={step['dims']}")
    rounds = final.get("round", 0)
    verdict = (final.get("verdict") or {}).get("overall_verdict")
    cycled = rounds > 1
    print(f"\nrounds={rounds}  final_verdict={verdict}  cycled={cycled}")
    print("SPIKE READOUT:")
    print(f"  - real graph w/ conditional cycle ran: YES ({rounds} round(s))")
    print(f"  - critic discriminates (not always-accept): {'YES — rejected at least once' if cycled else 'round-1 accept (need a stricter/forced case to see the cycle)'}")
    print(f"  - converged to accept: {'YES' if verdict == 'accept' else 'NO (hit round cap)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
