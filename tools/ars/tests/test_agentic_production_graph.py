"""Smoke tests for the agentic v0.4 production graph (contract step 4/5/8/9).

Offline only — one fake provider implements the three protocols the graph needs
(context-card + Stage A/B authoring via complete_case, the window gate via the same,
and the taste judge via an injected judge_fn). The two load-bearing smokes:

  1. happy path: a valid draft + an accept verdict drives the graph through the
     owner_review_gate (resume=approve) into promote, and the promoted
     companion_exchange moment passes deadman_validate_producer_bridge.

  2. directed self-correction: round-1 judge rejects ONE dimension (lead_taste);
     the revise loop fires and the round-2 Stage A prompt carries the DIRECTED
     revision instruction for that matching layer (companion_lead), then accepts.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.ars import deadman_agentic_production_graph as graph_mod
from tools.ars.deadman_paths import find_deadman_root
from tools.ars.deadman_validate_producer_bridge import BridgeValidator

REPO_ROOT = find_deadman_root(__file__)
SOURCE_DRAMA_DIR = REPO_ROOT / "data" / "dramas" / "huangnian"
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
    """One provider object for the whole authoring chain (context + Stage A + Stage B).

    Dispatches on prompt['task']. Records every Stage A prompt so a test can assert the
    DIRECTED revision instruction reached Stage A on the revise round.
    """

    def __init__(self) -> None:
        self.stage_a_prompts: list[dict] = []
        self.stage_b_prompts: list[dict] = []

    def complete_case(self, prompt: dict, schema: dict) -> dict:
        task = prompt.get("task")
        if task == "build_scene_context_card":
            # non-thin context so the window_gate recommends and authoring has something to ground on.
            return {"payload": {
                "whats_happening": "四蛋懂事地说肉肯定没自己的份，只想闻个味，娘心里发酸。",
                "audience_already_knows": "全村闹饥荒，这家穷得一年没吃过肉。",
                "relationship_state": "母亲与懂事的小儿子四蛋。",
                "grounding_note": "孩子把自己排除在外，娘的心疼是这一刻的张力。"}}
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
            # echo for whichever viewer line this Stage B call is about.
            disp = prompt.get("this_viewer", {}).get("display_text", "")
            echo = next((r["selected_echo"] for r in _valid_replies() if r["display_text"] == disp),
                        "我懂你这句，这份心意值得被看见。")
            return {"payload": {"case_id": prompt.get("case_id", ""),
                                "selected_echo": echo, "echo_rationale": "answers this viewer"}}
        raise AssertionError(f"unexpected author task: {task}")


def _accept_verdict(judge_provider, case: dict) -> dict:
    return {"overall_verdict": "accept", "lead_taste": "acceptable",
            "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
            "rationale_summary": "all good", "item_id": case.get("item_id", "")}


class _ScriptedJudge:
    """An injectable judge_fn: returns scripted verdicts per round. Round numbers are inferred
    from how many times it has been called for the same item (one judge call per author round)."""

    def __init__(self, verdicts_by_round: list[dict]) -> None:
        self.verdicts_by_round = verdicts_by_round
        self.calls = 0

    def __call__(self, judge_provider, case: dict) -> dict:
        v = self.verdicts_by_round[min(self.calls, len(self.verdicts_by_round) - 1)]
        self.calls += 1
        return v


class AgenticProductionGraphSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmp.name) / "dramas"
        shutil.copytree(SOURCE_DRAMA_DIR, self.data_root / DRAMA_ID)
        self.addCleanup(self._tmp.cleanup)

    def _one_candidate(self) -> list[dict]:
        # restrict to the single target window for a fast, deterministic smoke.
        return [{
            "item_id": TARGET_MOMENT_ID, "moment_id": TARGET_MOMENT_ID,
            "drama_id": DRAMA_ID, "drama_title": "荒年", "episode_id": "huangnian_ep12",
            "start_seconds": 10.0, "end_seconds": 20.0,
        }]

    def _run(self, judge_fn, *, review_decision="approve"):
        return graph_mod.run_production(
            DRAMA_ID, FakeAuthorProvider(), judge_provider=None,
            review_decision=review_decision, max_rounds=2, data_root=self.data_root,
            judge_fn=judge_fn, candidates=self._one_candidate(),
        )

    def test_happy_path_reaches_promote_and_passes_bridge(self):
        final = self._run(_accept_verdict)
        report = final["report"]
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(report["promoted_moment_ids"], [TARGET_MOMENT_ID])
        self.assertEqual(report["review_status"], "reviewed")
        self.assertTrue(report["owner_reviewed"])
        self.assertEqual(report["judge_unavailable"], [])
        self.assertEqual(report["flagged_windows"], [])

        # the promoted pack passes the producer-bridge gate (the contract's accept condition).
        bridge = BridgeValidator(self.data_root / DRAMA_ID).validate()
        self.assertEqual(bridge["status"], "pass", msg=f"bridge errors: {bridge['errors']}")
        # and the target moment now carries a reviewed companion_exchange we just authored.
        import json
        pack = json.loads((self.data_root / DRAMA_ID / "moments.v0.1.json").read_text("utf-8"))
        moment = next(m for m in pack["moments"] if m["moment_id"] == TARGET_MOMENT_ID)
        ce = moment["companion_exchange"]
        self.assertEqual(ce["schema_version"], "companion_exchange_pack.v0.1")
        self.assertEqual(ce["review_status"], "reviewed")
        self.assertEqual(ce["companion_lead"], "这孩子懂事得让人鼻子发酸。")
        self.assertEqual(len(ce["reply_candidates"]), 3)

        # the promoted moment carries NO scene_context key — the heavy blob lives in the SIDECAR.
        self.assertNotIn("scene_context", ce)

        # the build_scene_context() card computed during authoring is PERSISTED to the per-drama
        # SIDECAR (scene_context.v0.1.json), keyed by moment_id, reshaped into the layered shape.
        sidecar = json.loads(
            (self.data_root / DRAMA_ID / "scene_context.v0.1.json").read_text("utf-8")
        )
        self.assertEqual(sidecar["schema_version"], "scene_context.v0.1")
        sc = sidecar["scene_context"][TARGET_MOMENT_ID]
        self.assertIn("l0_canon", sc)
        self.assertIn("l3_series_spine", sc)
        self.assertIn("l2_recent_events", sc)
        # the four L1 (this-beat) fields the fake context node returned are nested under l1.
        self.assertEqual(sc["l1"]["whats_happening"],
                         "四蛋懂事地说肉肯定没自己的份，只想闻个味，娘心里发酸。")
        self.assertEqual(sc["l1"]["grounding_note"], "孩子把自己排除在外，娘的心疼是这一刻的张力。")

    def test_round1_reject_fires_directed_revision_then_accepts(self):
        author = FakeAuthorProvider()
        # round 1: reject on lead_taste only; round 2: accept.
        reject_lead = {"overall_verdict": "reject", "lead_taste": "needs_repair",
                       "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                       "rationale_summary": "lead 太像旁白了，没有当场反应", "item_id": TARGET_MOMENT_ID}
        accept = {"overall_verdict": "accept", "lead_taste": "acceptable",
                  "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                  "rationale_summary": "fixed", "item_id": TARGET_MOMENT_ID}
        judge = _ScriptedJudge([reject_lead, accept])

        final = graph_mod.run_production(
            DRAMA_ID, author, judge_provider=None, review_decision="approve",
            max_rounds=2, data_root=self.data_root, judge_fn=judge,
            candidates=self._one_candidate(),
        )

        # the loop cycled: two author rounds, two judge calls.
        self.assertEqual(judge.calls, 2)
        self.assertEqual(len(author.stage_a_prompts), 2)

        # round-1 Stage A is the default (no revision instruction); round-2 carries the DIRECTED
        # revision for the MATCHING layer (companion_lead), proving the per-layer routing fired.
        r1, r2 = author.stage_a_prompts
        self.assertNotIn("revision_feedback", r1)
        self.assertFalse(r1["global_rules"][0].startswith("这是修订轮"))

        self.assertEqual(r2["revision_feedback"], reject_lead["rationale_summary"])
        directed = r2["global_rules"][0]
        self.assertTrue(directed.startswith("这是修订轮"))
        self.assertIn("companion_lead", directed)            # the failing layer is named
        self.assertNotIn("reply_candidates", directed)        # reply was NOT named (single-dim reject)

        # converged to accept -> promoted + reviewed.
        report = final["report"]
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(report["promoted_moment_ids"], [TARGET_MOMENT_ID])
        self.assertEqual(report["review_status"], "reviewed")

    def test_directed_feedback_routes_single_dimension(self):
        # unit-check the verdict->structured-feedback signal Component A routes on.
        fb = graph_mod.directed_feedback({"overall_verdict": "reject", "lead_taste": "needs_repair",
                                          "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
                                          "rationale_summary": "lead 偏弱"})
        self.assertEqual(fb, {"note": "lead 偏弱", "fails": ["lead_taste"]})
        # accept-grade / unavailable -> no directed revision.
        self.assertIsNone(graph_mod.directed_feedback({"overall_verdict": "accept"}))
        self.assertIsNone(graph_mod.directed_feedback({"overall_verdict": "not_available"}))

    def test_judge_unavailable_flags_not_promoted(self):
        # an explicit not_available verdict must flag (judge_unavailable), never silently rewrite/promote.
        def unavailable(judge_provider, case):
            return {"overall_verdict": "not_available", "lead_taste": "not_available",
                    "reply_voice_taste": "not_available", "echo_taste": "not_available",
                    "rationale_summary": "judge down", "item_id": TARGET_MOMENT_ID}

        final = self._run(unavailable)
        report = final["report"]
        self.assertEqual(report["accepted_count"], 0)
        self.assertEqual(report["judge_unavailable"], [TARGET_MOMENT_ID])
        self.assertIn(TARGET_MOMENT_ID, report["flagged_windows"])
        self.assertEqual(report["promoted_moment_ids"], [])

    def test_author_raise_flags_window_and_completes(self):
        # a per-window author/Ark failure must FLAG that window (author_unavailable) and let the
        # graph COMPLETE (emit a report), never crash the whole drama run — mirroring judge_unavailable.
        class _RaisingAuthor(FakeAuthorProvider):
            def complete_case(self, prompt, schema):
                # context card builds fine; Stage A authoring raises (e.g. Ark error / fail-closed).
                if prompt.get("task") == "author_new_drama_hero.stage_a":
                    raise RuntimeError("ark exploded mid-author")
                return super().complete_case(prompt, schema)

        final = graph_mod.run_production(
            DRAMA_ID, _RaisingAuthor(), judge_provider=None, review_decision="approve",
            max_rounds=2, data_root=self.data_root, judge_fn=_accept_verdict,
            candidates=self._one_candidate(),
        )
        # graph completed and produced a report (no crash).
        report = final["report"]
        self.assertEqual(report["accepted_count"], 0)
        self.assertEqual(report["author_unavailable"], [TARGET_MOMENT_ID])
        self.assertIn(TARGET_MOMENT_ID, report["flagged_windows"])
        self.assertIn(TARGET_MOMENT_ID,
                      report["windows_by_status"].get(graph_mod.STATUS_AUTHOR_UNAVAILABLE, []))
        self.assertEqual(report["promoted_moment_ids"], [])

    def test_window_gate_reject_skips_authoring(self):
        # a det window reject (v0.3 rejected_window negative on this item_id) skips author+judge.
        from tools.ars import deadman_agentic_nodes as nodes

        class _RejectGate:
            def complete_case(self, prompt, schema):
                return {"payload": {"window_decision": "reject_window", "rationale_summary": "mechanism-only"}}

        final = graph_mod.run_production(
            DRAMA_ID, FakeAuthorProvider(), judge_provider=None, review_decision="approve",
            max_rounds=2, data_root=self.data_root, judge_fn=_accept_verdict,
            candidates=self._one_candidate(), window_gate_provider=_RejectGate(),
        )
        report = final["report"]
        self.assertEqual(report["accepted_count"], 0)
        self.assertIn(TARGET_MOMENT_ID, report["windows_by_status"].get(nodes.WINDOW_DECISIONS[1], [])
                      + report["windows_by_status"].get("window_rejected", []))
        self.assertEqual(report["promoted_moment_ids"], [])

    def test_reject_token_does_not_stamp_reviewed(self):
        # P1-A + decisions #2/#5: resume with reject -> the accepted pack is NOT promoted at all
        # (no-op), never written-as-draft and never stamped reviewed. The held-back pack stays absent.
        final = self._run(_accept_verdict, review_decision="reject")
        report = final["report"]
        self.assertEqual(report["accepted_count"], 1)  # still authored + accepted by the judge
        self.assertFalse(report["owner_reviewed"])
        self.assertNotEqual(report["review_status"], "reviewed")
        self.assertEqual(report["promoted_moment_ids"], [])  # nothing promoted on an overall reject
        self.assertIn(TARGET_MOMENT_ID, final["promote_result"].get("rejected_moment_ids", []))

    # --- durable start/resume (Track A) — the real cross-HTTP pause + per-pack review --------------

    def _cleanup_run(self, run_id: str) -> None:
        shutil.rmtree(graph_mod._production_run_dir(run_id), ignore_errors=True)

    def test_durable_start_pauses_then_resume_approve_promotes(self):
        # run_production_start drives author_and_judge then PAUSES at owner_review_gate, returning a
        # waiting handle with the produced packs (no auto-resume). A later run_production_resume
        # reopens the SAME SqliteSaver checkpoint and finishes promote+report — proving the durable
        # cross-call pause/resume the console needs.
        run_id = "test-durable-approve"
        self.addCleanup(self._cleanup_run, run_id)
        started = graph_mod.run_production_start(
            DRAMA_ID, FakeAuthorProvider(), judge_provider=None, run_id=run_id,
            max_rounds=2, data_root=self.data_root, judge_fn=_accept_verdict,
            candidates=self._one_candidate(),
        )
        self.assertEqual(started["status"], "waiting_for_review")
        self.assertEqual(len(started["accepted_drafts"]), 1)  # the produced pack the gate renders
        draft = started["accepted_drafts"][0]
        self.assertEqual(draft["moment_id"], TARGET_MOMENT_ID)
        self.assertEqual(draft["companion_lead"], "这孩子懂事得让人鼻子发酸。")
        self.assertEqual(len(draft["reply_candidates"]), 3)

        final = graph_mod.run_production_resume(
            run_id, "approve", FakeAuthorProvider(), judge_provider=None,
            pack_decisions={TARGET_MOMENT_ID: "approve"},
        )
        report = final["report"]
        self.assertEqual(report["promoted_moment_ids"], [TARGET_MOMENT_ID])
        self.assertEqual(report["review_status"], "reviewed")
        self.assertTrue(report["owner_reviewed"])
        # the resumed run wrote the reviewed pack to the same tmp data_root carried in the checkpoint.
        bridge = BridgeValidator(self.data_root / DRAMA_ID).validate()
        self.assertEqual(bridge["status"], "pass", msg=f"bridge errors: {bridge['errors']}")

    def test_per_pack_reject_holds_back_pack(self):
        # The owner can reject an individual pack at the gate (pack_decisions). A per-pack reject
        # means that pack is NOT promoted, even though the overall submit token is approve.
        run_id = "test-perpack-reject"
        self.addCleanup(self._cleanup_run, run_id)
        graph_mod.run_production_start(
            DRAMA_ID, FakeAuthorProvider(), judge_provider=None, run_id=run_id,
            max_rounds=2, data_root=self.data_root, judge_fn=_accept_verdict,
            candidates=self._one_candidate(),
        )
        final = graph_mod.run_production_resume(
            run_id, "approve", FakeAuthorProvider(), judge_provider=None,
            pack_decisions={TARGET_MOMENT_ID: "reject"},
        )
        report = final["report"]
        self.assertEqual(report["promoted_moment_ids"], [])
        self.assertIn(TARGET_MOMENT_ID, final["promote_result"].get("rejected_moment_ids", []))


if __name__ == "__main__":
    unittest.main()
