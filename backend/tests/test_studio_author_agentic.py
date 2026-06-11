"""Server-level test: POST /api/studio/author {agentic:true} runs the agentic wiring and returns
the `rounds` (+ judge_available) field. Offline: the author core + both providers are stubbed so
NO real provider (Ark / Bailian) is called.

Covers:
  - {agentic:true} -> agentic path -> response carries rounds + judge_available + mapped draft.
  - default (no flag) -> the existing single-shot _run_author_prepared path, UNCHANGED (no rounds).
  - agentic path raising inside the loop -> falls back to single-shot, never 500s the console.
  - {agentic:true, background:true} (A⑤) -> returns a run_id immediately; GET status reflects REAL
    discrete progress folded from on_progress events and the final mapped draft (no real provider).
"""
from __future__ import annotations

import time
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import server
from tools.ars import deadman_author_drama_heroes as hero


class _FakeArkProvider:
    @classmethod
    def from_env(cls):
        return cls()


class _FakeJudgeProvider:
    @classmethod
    def from_env(cls):
        return cls()


def _fake_agentic(author_provider, judge_provider, guidance, drama_id, pack, moment, **kwargs):
    # judge_available reflects whether a judge was wired (the server passes the Bailian provider).
    return {
        "companion_lead": "这一刻她终于没忍住。",
        "replies": [
            {"display_text": "替她不值", "selected_echo": "对，这口气憋太久了。",
             "viewer_motivation": "心疼她", "emotion_role": "心疼", "semantic_role": "stance_a"},
            {"display_text": "她该走了", "selected_echo": "嗯，留下只会更耗着。",
             "viewer_motivation": "盼她解脱", "emotion_role": "解气", "semantic_role": "stance_b"},
            {"display_text": "再想想", "selected_echo": "也是，别冲动，先看清。",
             "viewer_motivation": "怕她后悔", "emotion_role": "迟疑", "semantic_role": "fallback"},
        ],
        "rounds": 2,
        "final_verdict": {"overall_verdict": "accept"},
        "judge_available": judge_provider is not None,
    }


def _fake_agentic_with_progress(author_provider, judge_provider, guidance, drama_id, pack, moment,
                                *, on_progress=None, **kwargs):
    """Like _fake_agentic but drives the on_progress callback through a reject->accept run so the
    background-run status test sees REAL folded progress (no real provider). Returns the same shape."""
    emit = on_progress or (lambda _e: None)
    emit({"event": "context_built", "round": None})
    # round 1: stage A/B, judge rejects on the lead layer, revise routes to 开场 (lead)
    emit({"event": "round_start", "round": 1})
    emit({"event": "stage_a_done", "round": 1})
    emit({"event": "stage_b_done", "round": 1})
    emit({"event": "judge_verdict", "round": 1, "verdict": "reject", "accepted": False})
    emit({"event": "revise", "round": 1, "layer": "开场 (lead)", "note": "lead 偏旁白"})
    # round 2: re-author, judge accepts
    emit({"event": "round_start", "round": 2})
    emit({"event": "stage_a_done", "round": 2})
    emit({"event": "stage_b_done", "round": 2})
    emit({"event": "judge_verdict", "round": 2, "verdict": "accept", "accepted": True})
    emit({"event": "done", "round": 2, "verdict": "accept",
          "judge_available": judge_provider is not None})
    return _fake_agentic(author_provider, judge_provider, guidance, drama_id, pack, moment, **kwargs)


class StudioAuthorAgenticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)
        # never reach the real .env / provider
        self._ensure = mock.patch.object(server, "_ensure_provider_env", lambda: None)
        self._ensure.start()
        self.addCleanup(self._ensure.stop)

    def test_agentic_flag_runs_loop_and_returns_rounds(self):
        with mock.patch.object(hero, "author_moment_agentic", _fake_agentic), \
             mock.patch.object(hero, "ArkStudioProofProvider", _FakeArkProvider), \
             mock.patch("tools.ars.deadman_run_studio_taste_judge.BailianTasteJudgeProvider",
                        _FakeJudgeProvider):
            resp = self.client.post("/api/studio/author",
                                    json={"drama_id": "lihun", "agentic": True})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIn("rounds", body)
        self.assertEqual(body["rounds"], 2)
        self.assertTrue(body["judge_available"])            # judge was wired
        self.assertEqual(body["companion_lead"], "这一刻她终于没忍住。")
        self.assertEqual(len(body["replies"]), 3)
        self.assertEqual(body["replies"][0]["echo"], "对，这口气憋太久了。")
        self.assertEqual(body["replies"][0]["coverage"], "core_direction_a")

    def test_agentic_judge_unavailable_degrades_open_not_500(self):
        # Bailian judge can't be built (from_env raises) -> single-shot, judge_available False, 200.
        def _judge_raises():
            raise RuntimeError("bl CLI not found")

        with mock.patch.object(hero, "author_moment_agentic", _fake_agentic), \
             mock.patch.object(hero, "ArkStudioProofProvider", _FakeArkProvider), \
             mock.patch("tools.ars.deadman_run_studio_taste_judge.BailianTasteJudgeProvider.from_env",
                        staticmethod(_judge_raises)):
            resp = self.client.post("/api/studio/author",
                                    json={"drama_id": "lihun", "agentic": True})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["rounds"], 2)
        self.assertFalse(body["judge_available"])           # degraded open

    def test_default_path_unchanged_no_rounds(self):
        # no agentic flag -> existing single-shot path; stub it to confirm it is the one called.
        def _fake_prepared(drama_id, moment_id):
            return {"drama_id": drama_id, "moment_id": "m0", "episode_id": "ep1",
                    "companion_lead": "x", "replies": []}

        with mock.patch.object(server, "_run_author_prepared", _fake_prepared), \
             mock.patch.object(server, "_run_author_agentic",
                               mock.Mock(side_effect=AssertionError("agentic must not run by default"))):
            resp = self.client.post("/api/studio/author", json={"drama_id": "lihun"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertNotIn("rounds", resp.json())

    def test_agentic_failure_falls_back_to_single_shot(self):
        # the agentic path raises -> the endpoint falls back to _run_author_prepared, never 500.
        def _fake_prepared(drama_id, moment_id):
            return {"drama_id": drama_id, "moment_id": "m0", "episode_id": "ep1",
                    "companion_lead": "fallback lead", "replies": []}

        with mock.patch.object(server, "_run_author_agentic",
                               mock.Mock(side_effect=RuntimeError("provider down"))), \
             mock.patch.object(server, "_run_author_prepared", _fake_prepared):
            resp = self.client.post("/api/studio/author",
                                    json={"drama_id": "lihun", "agentic": True})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["companion_lead"], "fallback lead")
        self.assertNotIn("rounds", body)                    # single-shot shape, no rounds

    def test_background_run_returns_run_id_and_status_tracks_real_progress(self):
        # {agentic:true, background:true} -> POST returns a run_id IMMEDIATELY; the background thread
        # folds on_progress events into the run-store; GET status reflects REAL progress + the final
        # mapped draft. The author is mocked to emit simulated progress (no real provider).
        with mock.patch.object(hero, "author_moment_agentic", _fake_agentic_with_progress), \
             mock.patch.object(hero, "ArkStudioProofProvider", _FakeArkProvider), \
             mock.patch("tools.ars.deadman_run_studio_taste_judge.BailianTasteJudgeProvider",
                        _FakeJudgeProvider):
            start = self.client.post("/api/studio/author",
                                     json={"drama_id": "lihun", "agentic": True, "background": True})
            self.assertEqual(start.status_code, 200, start.text)
            run_id = start.json()["run_id"]
            self.assertEqual(start.json()["status"], "running")

            # poll until done (bounded; the thread is local + fast since the author is mocked)
            body = None
            for _ in range(50):
                resp = self.client.get(f"/api/studio/author/status/{run_id}")
                self.assertEqual(resp.status_code, 200, resp.text)
                body = resp.json()
                if body["status"] == "done":
                    break
                time.sleep(0.02)

        self.assertIsNotNone(body)
        self.assertEqual(body["status"], "done")
        # REAL per-round trace folded from on_progress (NOT a fake timer): 2 rounds, round 1 revised
        # 开场 (lead) + rejected, round 2 accepted.
        self.assertEqual(len(body["rounds"]), 2)
        self.assertFalse(body["rounds"][0]["accepted"])
        self.assertEqual(body["rounds"][0]["revised_layer"], "开场 (lead)")
        self.assertTrue(body["rounds"][1]["accepted"])
        self.assertTrue(body["judge_available"])            # judge was wired
        # the final mapped AuthorResult is attached, with rounds kept an INTEGER (backward-compat).
        self.assertEqual(body["result"]["companion_lead"], "这一刻她终于没忍住。")
        self.assertEqual(body["result"]["rounds"], 2)
        self.assertEqual(len(body["result"]["replies"]), 3)

    def test_status_unknown_run_id_is_404(self):
        resp = self.client.get("/api/studio/author/status/au_doesnotexist")
        self.assertEqual(resp.status_code, 404, resp.text)
        self.assertEqual(resp.json()["error"]["code"], "studio_run_not_found")


if __name__ == "__main__":
    unittest.main()
