"""Unit tests for the SHARED agentic self-correction author core
(deadman_author_drama_heroes.author_moment_agentic) — the ONE loop the production graph and the
Studio console both run (DRY).

Offline only: a fake author provider (records every Stage A prompt so the test can assert the
DIRECTED revision instruction reached Stage A on the revise round) + a fake judge_fn. A pre-built
`scene` is passed so the loop does not touch real ASR / context-memory on disk — the unit under
test is the author->judge->directed-revise->re-judge loop, not the context node.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.ars import deadman_author_drama_heroes as hero
from tools.ars.deadman_paths import find_deadman_root

REPO_ROOT = find_deadman_root(__file__)
DRAMA_ID = "huangnian"
TARGET_MOMENT_ID = "huangnian_ep12_m001"


def _valid_replies() -> list[dict]:
    return [
        {"display_text": "四蛋该吃肉", "viewer_motivation": "心疼这个懂事的孩子",
         "selected_echo": "对，这孩子懂事到先把自己排除了，这口肉不能再让他干闻着。",
         "emotion_role": "心疼孩子", "semantic_role": "include_child_first"},
        {"display_text": "别让娃白懂事", "viewer_motivation": "想先保住孩子这份心意",
         "selected_echo": "嗯，孩子不是来交差的，他这点心意得被看见。",
         "emotion_role": "不忍亏待", "semantic_role": "preserve_child"},
        {"display_text": "功劳算孩子的", "viewer_motivation": "想让家里人认这份功劳",
         "selected_echo": "这句我懂，孩子出力了，就该让他被家里人认真看见一次。",
         "emotion_role": "给孩子撑腰", "semantic_role": "name_child_contribution"},
    ]


class FakeAuthorProvider:
    """Stage A + Stage B over complete_case(prompt, schema). Records Stage A prompts so a test can
    assert the directed revision reached Stage A on the revise round."""

    def __init__(self) -> None:
        self.stage_a_prompts: list[dict] = []
        self.stage_b_prompts: list[dict] = []

    def complete_case(self, prompt: dict, schema: dict) -> dict:
        task = prompt.get("task")
        if task == "author_new_drama_hero.stage_a":
            self.stage_a_prompts.append(prompt)
            replies = _valid_replies()
            return {"payload": {
                "case_id": prompt.get("scene", {}).get("case_id", ""),
                "window_decision": "recommend_window",
                "companion_lead": "这孩子懂事得让人鼻子发酸。",
                "reply_candidates": [
                    {k: r[k] for k in ("display_text", "emotion_role", "semantic_role", "viewer_motivation")}
                    for r in replies],
                "failure_buckets": [], "rationale_summary": "scene-grounded", "repair_notes": []}}
        if task == "author_new_drama_hero.stage_b":
            self.stage_b_prompts.append(prompt)
            disp = prompt.get("this_viewer", {}).get("display_text", "")
            echo = next((r["selected_echo"] for r in _valid_replies() if r["display_text"] == disp),
                        "我懂你这句，这份心意值得被看见。")
            return {"payload": {"case_id": prompt.get("case_id", ""),
                                "selected_echo": echo, "echo_rationale": "answers this viewer"}}
        raise AssertionError(f"unexpected author task: {task}")


class _ScriptedJudge:
    """A judge_fn returning scripted verdicts per round; one call per author round."""

    def __init__(self, verdicts: list[dict]) -> None:
        self.verdicts = verdicts
        self.calls = 0

    def __call__(self, judge_provider, case: dict) -> dict:
        v = self.verdicts[min(self.calls, len(self.verdicts) - 1)]
        self.calls += 1
        return v


def _scene() -> dict:
    # a pre-built scene so the loop never touches real ASR / context memory on disk.
    return {"case_id": f"hero:{TARGET_MOMENT_ID}", "drama_id": DRAMA_ID, "drama_title": "荒年",
            "episode_id": "huangnian_ep12",
            "transcript": ["四蛋：娘，这肉肯定没我的份，我闻闻味儿就行。"],
            "scene_context": {
                "whats_happening": "四蛋懂事地说肉肯定没自己的份，只想闻个味，娘心里发酸。",
                "audience_already_knows": "全村闹饥荒，这家穷得一年没吃过肉。",
                "relationship_state": "母亲与懂事的小儿子四蛋。",
                "l0_canon": {"premise": "荒年求生", "protagonist": {}},
                "l3_series_spine": [], "l2_recent_events": [], "prior_window_asr": [],
                "knowledge_horizon": "only up to ep12"}}


def _load_inputs():
    guidance = hero.load(REPO_ROOT / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")
    pack = hero.load(REPO_ROOT / f"data/dramas/{DRAMA_ID}/moments.v0.1.json")
    moment = next(m for m in pack["moments"] if m["moment_id"] == TARGET_MOMENT_ID)
    return guidance, pack, moment


class AuthorMomentAgenticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.guidance, self.pack, self.moment = _load_inputs()

    def test_round1_reject_fires_directed_revision_then_accepts(self):
        author = FakeAuthorProvider()
        reject_lead = {"overall_verdict": "reject", "lead_taste": "needs_repair",
                       "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                       "rationale_summary": "lead 太像旁白了，没有当场反应"}
        accept = {"overall_verdict": "accept", "lead_taste": "acceptable",
                  "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                  "rationale_summary": "fixed"}
        judge = _ScriptedJudge([reject_lead, accept])

        result = hero.author_moment_agentic(
            author, judge_provider=None, guidance=self.guidance, drama_id=DRAMA_ID,
            pack=self.pack, moment=self.moment, max_rounds=2, judge_fn=judge, scene=_scene())

        # loop cycled exactly twice: two author rounds, two judge calls.
        self.assertEqual(result["rounds"], 2)
        self.assertEqual(judge.calls, 2)
        self.assertEqual(len(author.stage_a_prompts), 2)
        self.assertTrue(result["judge_available"])
        self.assertEqual(result["final_verdict"]["overall_verdict"], "accept")
        self.assertEqual(result["companion_lead"], "这孩子懂事得让人鼻子发酸。")
        self.assertEqual(len(result["replies"]), 3)
        self.assertTrue(all(r.get("selected_echo") for r in result["replies"]))

        # round-1 Stage A is default (no revision); round-2 carries the DIRECTED revision for the
        # MATCHING layer (companion_lead) only — proving per-layer routing fired.
        r1, r2 = author.stage_a_prompts
        self.assertNotIn("revision_feedback", r1)
        self.assertFalse(r1["global_rules"][0].startswith("这是修订轮"))
        self.assertEqual(r2["revision_feedback"], reject_lead["rationale_summary"])
        directed = r2["global_rules"][0]
        self.assertTrue(directed.startswith("这是修订轮"))
        self.assertIn("companion_lead", directed)          # the failing layer is named
        self.assertNotIn("reply_candidates", directed)      # reply was NOT named (single-dim reject)

    def test_judge_error_degrades_to_single_shot_open(self):
        # a judge that errors -> provider_failure_verdict -> overall=not_available -> the loop
        # fails OPEN to single-shot: one author round, judge_available=False, no second round.
        author = FakeAuthorProvider()

        def erroring_judge(judge_provider, case):
            raise RuntimeError("judge backend down")

        result = hero.author_moment_agentic(
            author, judge_provider=None, guidance=self.guidance, drama_id=DRAMA_ID,
            pack=self.pack, moment=self.moment, max_rounds=2, judge_fn=erroring_judge, scene=_scene())

        self.assertFalse(result["judge_available"])
        self.assertEqual(result["rounds"], 1)               # single-shot degrade, no revise round
        self.assertEqual(len(author.stage_a_prompts), 1)
        self.assertEqual(result["companion_lead"], "这孩子懂事得让人鼻子发酸。")
        self.assertEqual(len(result["replies"]), 3)

    def test_no_judge_provider_single_shot_open(self):
        # no judge wired at all (judge_provider=None, judge_fn=None) -> single-shot, judge_available=False.
        author = FakeAuthorProvider()
        result = hero.author_moment_agentic(
            author, judge_provider=None, guidance=self.guidance, drama_id=DRAMA_ID,
            pack=self.pack, moment=self.moment, max_rounds=2, scene=_scene())
        self.assertFalse(result["judge_available"])
        self.assertEqual(result["rounds"], 1)
        self.assertIsNone(result["final_verdict"])
        self.assertEqual(len(author.stage_a_prompts), 1)

    def test_on_progress_emits_discrete_events_with_round_and_layer(self):
        # the OPTIONAL on_progress callback (A⑤ real progress) emits one event per discrete loop
        # step; default None (the other tests) is byte-for-byte unchanged. Here a reject->accept
        # run emits: context_built, then per round round_start/stage_a_done/stage_b_done/judge_verdict,
        # a revise carrying the routed layer label on the rejected round, and a final done.
        author = FakeAuthorProvider()
        reject_lead = {"overall_verdict": "reject", "lead_taste": "needs_repair",
                       "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                       "rationale_summary": "lead 偏旁白"}
        accept = {"overall_verdict": "accept", "lead_taste": "acceptable",
                  "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                  "rationale_summary": "fixed"}
        judge = _ScriptedJudge([reject_lead, accept])
        events: list[dict] = []

        result = hero.author_moment_agentic(
            author, judge_provider=None, guidance=self.guidance, drama_id=DRAMA_ID,
            pack=self.pack, moment=self.moment, max_rounds=2, judge_fn=judge, scene=_scene(),
            on_progress=events.append)

        names = [e["event"] for e in events]
        self.assertEqual(names[0], "context_built")
        # two full author rounds before the accept
        self.assertEqual(names.count("round_start"), 2)
        self.assertEqual(names.count("stage_a_done"), 2)
        self.assertEqual(names.count("stage_b_done"), 2)
        self.assertEqual(names.count("judge_verdict"), 2)
        self.assertEqual(names[-1], "done")
        # the reject round emitted a revise naming the lead layer (single-dim lead_taste reject)
        revise = next(e for e in events if e["event"] == "revise")
        self.assertEqual(revise["round"], 1)
        self.assertEqual(revise["layer"], "开场 (lead)")
        # the first judge_verdict was a reject (accepted False), the second accepted True
        jvs = [e for e in events if e["event"] == "judge_verdict"]
        self.assertFalse(jvs[0]["accepted"])
        self.assertTrue(jvs[1]["accepted"])
        # the loop result is unchanged by progress observation
        self.assertEqual(result["rounds"], 2)
        self.assertTrue(result["judge_available"])

    def test_on_progress_callback_exception_never_breaks_authoring(self):
        # a throwing callback must be swallowed (best-effort progress) — authoring still returns.
        author = FakeAuthorProvider()

        def boom(_event):
            raise RuntimeError("observer blew up")

        result = hero.author_moment_agentic(
            author, judge_provider=None, guidance=self.guidance, drama_id=DRAMA_ID,
            pack=self.pack, moment=self.moment, max_rounds=2, scene=_scene(), on_progress=boom)
        self.assertEqual(len(result["replies"]), 3)
        self.assertEqual(result["rounds"], 1)

    def test_directed_feedback_routes_single_dimension(self):
        fb = hero.directed_feedback({"overall_verdict": "reject", "lead_taste": "needs_repair",
                                     "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                                     "rationale_summary": "lead 偏弱"})
        self.assertEqual(fb, {"note": "lead 偏弱", "fails": ["lead_taste"]})
        self.assertIsNone(hero.directed_feedback({"overall_verdict": "accept"}))
        self.assertIsNone(hero.directed_feedback({"overall_verdict": "not_available"}))


if __name__ == "__main__":
    unittest.main()
