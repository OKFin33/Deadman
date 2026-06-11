"""Server-level tests for the graph-run API (Track E): /api/studio/batch + /run/start|status|resume.

Offline: the providers + the durable run_production_start/resume are stubbed so NO real provider
(Ark / Bailian) and NO real graph run happen — we assert the endpoint wiring, validation, the
run-store, the review-payload join, and the resume result shape.
"""
from __future__ import annotations

import json
import shutil
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import server
from tools.ars import deadman_agentic_production_graph as graph_mod
from tools.ars import deadman_ingest_pipeline as ingest_mod

TEST_DRAMA = "_test_e_run"
TEST_DRAMA_DIR = Path(server.BASE_DIR) / "data" / "dramas" / TEST_DRAMA


def _scaffold_moment() -> dict:
    return {
        "moment_id": "m1",
        "source_drama": {"episode_id": f"{TEST_DRAMA}_ep01"},
        "interaction_window": {"start_seconds": 10, "end_seconds": 20, "notice_at_seconds": 11},
        "companion_exchange": {"scene_signal": "她终于没忍住开口"},
    }


def _fake_started() -> dict:
    return {
        "run_id": "x", "status": "waiting_for_review", "drama_id": TEST_DRAMA,
        "accepted_drafts": [{
            "moment_id": "m1", "companion_lead": "她这一句憋太久了。",
            "reply_candidates": [
                {"display_text": "替她不值", "selected_echo": "对，这口气该出。"},
                {"display_text": "她该走了", "selected_echo": "嗯，别耗着了。"},
                {"display_text": "再想想", "selected_echo": "也是，先看清。"},
            ],
        }],
        "window_results": [{"moment_id": "m1", "status": "accepted", "rounds": 2}],
        "report": {},
    }


class GraphRunApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)
        TEST_DRAMA_DIR.mkdir(parents=True, exist_ok=True)
        (TEST_DRAMA_DIR / "moments.v0.1.json").write_text(
            json.dumps({"moments": [_scaffold_moment()]}, ensure_ascii=False), "utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(TEST_DRAMA_DIR, ignore_errors=True)
        with server._PROD_RUNS_LOCK:
            server._PROD_RUNS.clear()

    # --- validation / wiring --------------------------------------------------------------------

    def test_run_start_missing_scaffold_404(self) -> None:
        r = self.client.post("/api/studio/run/start", json={"drama_id": "_no_such_drama_xyz"})
        self.assertEqual(r.status_code, 404)

    def test_run_start_curated_400(self) -> None:
        r = self.client.post("/api/studio/run/start", json={"drama_id": "huangnian"})
        self.assertEqual(r.status_code, 400)

    def test_run_status_unknown_404(self) -> None:
        self.assertEqual(self.client.get("/api/studio/run/status/nope").status_code, 404)

    def test_run_resume_unknown_404(self) -> None:
        r = self.client.post("/api/studio/run/resume/nope", json={"decision": "approve"})
        self.assertEqual(r.status_code, 404)

    def test_batch_curated_400(self) -> None:
        r = self.client.post("/api/studio/batch", data={"drama_id": "yunmiao", "drama_name": "x"},
                             files=[("files", ("a.mp4", b"x", "video/mp4"))])
        self.assertEqual(r.status_code, 400)

    def test_batch_resets_runtime_store_after_scaffold_write(self) -> None:
        tmp_root = Path("tmp/test_studio_batch_reset")
        shutil.rmtree(tmp_root, ignore_errors=True)
        fake_body = {
            "batch_id": "batch_test",
            "drama_id": TEST_DRAMA,
            "drama_name": "测试剧",
            "episodes": [],
        }
        try:
            with mock.patch.object(server, "STUDIO_BATCH_ROOT", tmp_root), \
                 mock.patch.object(server, "_ensure_provider_env"), \
                 mock.patch.object(server, "_batch_prepare", return_value=fake_body), \
                 mock.patch.object(
                     server.deadman_app.state.deadman_store,
                     "reset",
                     wraps=server.deadman_app.state.deadman_store.reset,
                 ) as reset_store:
                r = self.client.post(
                    "/api/studio/batch",
                    data={"drama_id": TEST_DRAMA, "drama_name": "测试剧"},
                    files=[("files", ("a.mp4", b"x", "video/mp4"))],
                )
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), fake_body)
            reset_store.assert_called_once()
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    # --- pure helpers ---------------------------------------------------------------------------

    def test_episode_name_from_id(self) -> None:
        self.assertEqual(server._episode_name_from_id("foo_ep01"), "第1集")
        self.assertEqual(server._episode_name_from_id("bar_ep12"), "第12集")

    def test_batch_prepare_returns_media_index_duration(self) -> None:
        analysis_dir = ingest_mod.analysis_dir_for(TEST_DRAMA)
        shutil.rmtree(analysis_dir, ignore_errors=True)
        analysis_dir.mkdir(parents=True, exist_ok=True)
        try:
            (analysis_dir / "media_index.json").write_text(
                json.dumps([{
                    "episode_id": f"{TEST_DRAMA}_ep01",
                    "duration_s": 142.5,
                }], ensure_ascii=False),
                "utf-8",
            )
            with mock.patch.object(
                ingest_mod,
                "ingest",
                return_value={"windows": [{
                    "episode_id": f"{TEST_DRAMA}_ep01",
                    "start_seconds": 10,
                    "end_seconds": 20,
                    "notice_at_seconds": 11,
                    "transcript_excerpt": "她终于开口",
                }]},
            ):
                body = server._batch_prepare(
                    Path("tmp/test_batch_prepare"),
                    TEST_DRAMA,
                    "测试剧",
                    [(Path("tmp/test_batch_prepare/ep01.mp4"), "第1集")],
                )
            self.assertEqual(body["episodes"][0]["duration_seconds"], 142.5)
        finally:
            shutil.rmtree(analysis_dir, ignore_errors=True)

    def test_synth_rounds_lights_reject_when_revised(self) -> None:
        # a window that took 2 rounds -> a rejected round precedes its accepted outcome.
        traces = server._synth_rounds([{"moment_id": "m1", "status": "accepted", "rounds": 2}])
        self.assertTrue(any(t["accepted"] is False for t in traces))
        self.assertTrue(any(t["accepted"] is True for t in traces))
        # a clean 1-round window -> no rejected trace.
        clean = server._synth_rounds([{"moment_id": "m2", "status": "accepted", "rounds": 1}])
        self.assertFalse(any(t["accepted"] is False for t in clean))

    def test_build_run_review_joins_scaffold(self) -> None:
        review = server._build_run_review(TEST_DRAMA, _fake_started()["accepted_drafts"])
        self.assertEqual(review["drama_id"], TEST_DRAMA)
        self.assertEqual(len(review["packs"]), 1)
        pack = review["packs"][0]
        self.assertEqual(pack["moment_id"], "m1")
        self.assertEqual(pack["episode_name"], "第1集")
        self.assertEqual(pack["companion_lead"], "她这一句憋太久了。")
        self.assertEqual(pack["scene_signal"], "她终于没忍住开口")          # joined from the scaffold
        self.assertEqual(pack["interaction_window"]["start_seconds"], 10)  # joined from the scaffold
        self.assertEqual(len(pack["reply_candidates"]), 3)
        self.assertEqual(pack["reply_candidates"][0]["selected_echo"], "对，这口气该出。")

    # --- start -> status(review) -> resume (graph + providers stubbed) ---------------------------

    def test_start_pauses_then_status_carries_review(self) -> None:
        with mock.patch.object(server, "_prod_providers", return_value=(object(), object())), \
             mock.patch.object(graph_mod, "run_production_start", return_value=_fake_started()):
            r = self.client.post("/api/studio/run/start", json={"drama_id": TEST_DRAMA})
            self.assertEqual(r.status_code, 200)
            run_id = r.json()["run_id"]
            # poll until the background thread folds the waiting handle in.
            status = {}
            for _ in range(50):
                status = self.client.get(f"/api/studio/run/status/{run_id}").json()
                if status.get("status") == "waiting_for_review":
                    break
                time.sleep(0.02)
        self.assertEqual(status["status"], "waiting_for_review")
        self.assertEqual(status["current_node"], "owner_review_gate")
        self.assertIsNotNone(status["review"])
        self.assertEqual(status["review"]["packs"][0]["moment_id"], "m1")

    def test_resume_returns_promoted_and_stage_url(self) -> None:
        # seed a waiting run, then resume with a per-pack approve.
        server._new_prod_run("prod_test1", TEST_DRAMA)
        with server._PROD_RUNS_LOCK:
            server._PROD_RUNS["prod_test1"]["status"] = "waiting_for_review"
        fake_final = {"report": {"drama_id": TEST_DRAMA, "promoted_moment_ids": ["m1"]},
                      "promote_result": {"promoted_moment_ids": ["m1"]}}
        with mock.patch.object(server, "_prod_providers", return_value=(object(), object())), \
             mock.patch.object(graph_mod, "run_production_resume", return_value=fake_final) as rp:
            r = self.client.post("/api/studio/run/resume/prod_test1",
                                 json={"decision": "approve", "pack_decisions": {"m1": "approve"}})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["promoted_moment_ids"], ["m1"])
        self.assertIn(f"dramaId={TEST_DRAMA}", body["stage_url"])
        # the per-pack decision reached run_production_resume.
        _args, kwargs = rp.call_args
        self.assertEqual(kwargs.get("pack_decisions"), {"m1": "approve"})


if __name__ == "__main__":
    unittest.main()
