"""Offline orchestration test for deadman_ingest_pipeline.

Fully stubbed — NO ffmpeg, NO real ASR, NO real Ark/Bailian provider. The heavy/credentialed
steps are injected (prepare_runner / asr_runner / memory_runner / windows_override) and authoring
runs through the SAME run_production offline path the agentic-graph smoke test uses (a fake author
provider + an injected judge_fn + the scaffolded candidates). The test asserts:

  1. the orchestration ORDER (steps 0..8 in sequence),
  2. a NEW drama-id is used (not one of the 3 curated ids),
  3. the curated drama dirs (huangnian/lihun/yunmiao) are NOT written / unchanged,
  4. the seam actually scaffolds a fresh moments.v0.1.json with the upload provenance, and
  5. the agentic graph fills + reviews companion_exchange and the pack passes the bridge gate,
  6. --dry-run refuses a curated id and writes nothing.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.ars import deadman_ingest_pipeline as ingest_mod
from tools.ars.deadman_paths import find_deadman_root

REPO_ROOT = find_deadman_root(__file__)
CURATED = ("huangnian", "lihun", "yunmiao")
DRAMA_ID = "uploaded_demo_test"
DRAMA_NAME = "上传样片（测试）"
EPISODE_ID = f"{DRAMA_ID}_ep01"


def _valid_replies() -> list[dict]:
    return [
        {"display_text": "这口气得有人接", "viewer_motivation": "想接住这一刻的情绪",
         "selected_echo": "对，这一下确实憋得慌，得有人替你把这句说出来。",
         "emotion_role": "替观众出口气", "semantic_role": "voice_the_tension"},
        {"display_text": "她不该忍这下", "viewer_motivation": "心疼她还在硬撑",
         "selected_echo": "嗯，她明明可以不忍的，这份委屈不该她一个人扛。",
         "emotion_role": "心疼", "semantic_role": "side_with_her"},
        {"display_text": "看他怎么收场", "viewer_motivation": "想看对方接下来的反应",
         "selected_echo": "这句我懂，就想盯着看他这回打算怎么圆回去。",
         "emotion_role": "等反转", "semantic_role": "await_response"},
    ]


class _FakeAuthorProvider:
    """One provider for the whole authoring chain (context card + Stage A + Stage B),
    dispatching on prompt['task'] — mirrors the agentic-graph smoke test's fake."""

    def complete_case(self, prompt: dict, schema: dict) -> dict:
        task = prompt.get("task")
        if task == "build_scene_context_card":
            return {"payload": {
                "whats_happening": "她当众被为难，强忍着没有发作。",
                "audience_already_knows": "这家人一直在拿捏她。",
                "relationship_state": "她与一直压着她的那家人。",
                "grounding_note": "忍而未发，是这一刻的张力。"}}
        if task == "author_new_drama_hero.stage_a":
            replies = _valid_replies()
            return {"payload": {
                "case_id": prompt.get("scene", {}).get("case_id", ""),
                "window_decision": "recommend_window",
                "companion_lead": "这一下她忍得我都替她憋屈。",
                "reply_candidates": [
                    {k: r[k] for k in ("display_text", "emotion_role", "semantic_role", "viewer_motivation")}
                    for r in replies],
                "failure_buckets": [], "rationale_summary": "scene-grounded", "repair_notes": []}}
        if task == "author_new_drama_hero.stage_b":
            disp = prompt.get("this_viewer", {}).get("display_text", "")
            echo = next((r["selected_echo"] for r in _valid_replies() if r["display_text"] == disp),
                        "我懂你这句，这份情绪值得被接住。")
            return {"payload": {"case_id": prompt.get("case_id", ""),
                                "selected_echo": echo, "echo_rationale": "answers this viewer"}}
        raise AssertionError(f"unexpected author task: {task}")


def _accept_verdict(judge_provider, case: dict) -> dict:
    return {"overall_verdict": "accept", "lead_taste": "acceptable",
            "reply_voice_taste": "acceptable", "echo_taste": "acceptable",
            "rationale_summary": "all good", "item_id": case.get("item_id", "")}


class IngestPipelineOfflineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.data_root = self.tmp / "dramas"
        self.analysis = ingest_mod.analysis_dir_for(DRAMA_ID)
        self.video_dir = ingest_mod.video_stage_dir_for(DRAMA_ID)
        # a dummy "video" file so stage_videos has something to copy (it never runs ffmpeg here).
        self.fake_video = self.tmp / "clip.mp4"
        self.fake_video.write_bytes(b"\x00fake-mp4-bytes")
        # capture the committed-curated dir state so we can prove it is untouched.
        self._curated_before = {d: self._dir_snapshot(REPO_ROOT / "data" / "dramas" / d) for d in CURATED}
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        self._tmp.cleanup()
        for scratch in (self.analysis, self.video_dir):
            shutil.rmtree(scratch, ignore_errors=True)
        # never leave a synopsis residue / context-memory residue for the throwaway id.
        ctx = REPO_ROOT / "data" / "review" / "context_memory" / f"{DRAMA_ID}.v0.1.json"
        ctx.unlink(missing_ok=True)

    @staticmethod
    def _dir_snapshot(d: Path) -> dict[str, int]:
        if not d.exists():
            return {}
        return {str(p.relative_to(d)): p.stat().st_mtime_ns for p in sorted(d.rglob("*")) if p.is_file()}

    def test_known_uploaded_drama_reuses_bundled_cover(self) -> None:
        self.assertEqual(
            ingest_mod.infer_cover_image_url("drama_test", "云渺E2E最终样片"),
            "/assets/covers/yunmiao.png",
        )
        self.assertEqual(
            ingest_mod.infer_cover_image_url("lihun_live_test", "上传样片"),
            "/assets/covers/xingde.png",
        )
        self.assertEqual(
            ingest_mod.infer_cover_image_url("brand_new", "上传样片"),
            "/assets/covers/deadman-demo.png",
        )

    # --- injected (offline) heavy steps -------------------------------------------------------
    def _prepare_runner(self, drama_id, drama_name, video_dir, analysis_dir, **_kw) -> Path:
        # stub deadman_prepare_drama_assets: just write a media_index.json (no ffmpeg).
        analysis_dir.mkdir(parents=True, exist_ok=True)
        media_index = [{
            "episode_id": EPISODE_ID, "episode_title": "第1集",
            "video_path": str(self.fake_video), "duration_ms": 60000, "duration_s": 60.0,
            "size_bytes": 123, "width": 720, "height": 1280,
            "video_codec": "h264", "audio_codec": "aac", "fps": "30/1",
        }]
        path = analysis_dir / "media_index.json"
        path.write_text(json.dumps(media_index, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _asr_runner(self, analysis_dir, episode_ids) -> dict:
        # stub deadman_volc_asr_flash: stage a normalized ASR file where asr_window globs.
        out_dir = analysis_dir / "volc_asr" / "normalized"
        out_dir.mkdir(parents=True, exist_ok=True)
        normalized = {"provider": "stub", "duration": 60000, "text": "她忍住了没有发作",
                      "utterances": [
                          {"start_time": 8000, "end_time": 12000, "text": "你以为我会一直忍着吗"},
                          {"start_time": 12000, "end_time": 16000, "text": "这次我不会再让着你了"}]}
        for eid in episode_ids:
            (out_dir / f"{eid}.normalized.json").write_text(
                json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
            (out_dir / f"{eid}.json").write_text(
                json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
        return {eid: out_dir / f"{eid}.normalized.json" for eid in episode_ids}

    def _memory_runner(self, drama_id, through) -> Path:
        # stub deadman_build_episode_memory: write a context_memory file (no Ark call).
        path = REPO_ROOT / "data" / "review" / "context_memory" / f"{drama_id}.v0.1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_version": "episode_memory.v0.1", "drama_id": drama_id, "title": DRAMA_NAME,
            "premise": "测试剧情", "episodes": {
                EPISODE_ID: {"episode_id": EPISODE_ID, "l3_one_line": "她终于不再忍让",
                             "l2_event_log": ["她被为难", "她当众反击"], "asr_utterances": 2}}},
            ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _windows_override(self) -> list[dict]:
        return [{
            "episode_id": EPISODE_ID, "start_seconds": 8, "end_seconds": 18, "notice_at_seconds": 10,
            "scene_signal": "她终于不忍了", "rationale": "情绪顶点",
            "transcript_excerpt": "你以为我会一直忍着吗 这次我不会再让着你了",
        }]

    # --- the orchestration test ---------------------------------------------------------------
    def test_full_pipeline_offline_order_and_isolation(self):
        report = ingest_mod.ingest(
            videos=[self.fake_video], drama_id=DRAMA_ID, drama_name=DRAMA_NAME,
            synopsis="测试剧情：她终于不再忍让。", data_root=self.data_root,
            max_windows=1, through=1,
            write_committed_synopsis=True, restore_committed_synopsis=True,  # throwaway-id safe
            author_provider=_FakeAuthorProvider(), judge_provider=None, judge_fn=_accept_verdict,
            prepare_runner=self._prepare_runner, asr_runner=self._asr_runner,
            memory_runner=self._memory_runner, windows_override=self._windows_override(),
        )

        # (1) orchestration ORDER: all 9 steps fired in sequence.
        self.assertEqual(report["order"], [
            "stage_videos", "prepare_assets", "real_asr", "register_synopsis", "propose_windows",
            "build_scaffold", "build_episode_memory", "author_and_promote", "validate",
        ])

        # (2) a NEW drama-id was used (not a curated one).
        self.assertEqual(report["drama_id"], DRAMA_ID)
        self.assertNotIn(DRAMA_ID, CURATED)
        self.assertTrue(report["curated_untouched"])

        # (3) the curated drama dirs are byte-for-byte unchanged + nothing was written under them.
        for d in CURATED:
            self.assertEqual(self._dir_snapshot(REPO_ROOT / "data" / "dramas" / d),
                             self._curated_before[d], msg=f"curated dir {d} changed")
        # the new pack lives under the TMP data-root, not the committed data/dramas.
        self.assertTrue((self.data_root / DRAMA_ID / "moments.v0.1.json").exists())
        self.assertFalse((REPO_ROOT / "data" / "dramas" / DRAMA_ID).exists())

        # (4) the seam scaffolded a fresh, PUBLISH-SAFE moment (bridge-complete provenance).
        pack = json.loads((self.data_root / DRAMA_ID / "moments.v0.1.json").read_text("utf-8"))
        moment = pack["moments"][0]
        self.assertEqual(moment["interaction_window"]["source"], "manual_p0_fallback")
        self.assertEqual(moment["source_window"]["provenance_status"], "publish_safe_sanitized")
        self.assertIn(f"#{moment['moment_id']}", moment["source_refs"]["reviewed_demo_node"])
        # the paired evidence node exists and matches.
        nodes = json.loads(
            (self.data_root / DRAMA_ID / "evidence" / "reviewed_demo_nodes.v0.1.json").read_text("utf-8"))
        self.assertEqual([n["moment_id"] for n in nodes["demo_nodes"]], [moment["moment_id"]])
        iw = moment["interaction_window"]
        # player constraint: notice_at <= start <= end.
        self.assertLessEqual(iw["notice_at_seconds"], iw["start_seconds"])
        self.assertLessEqual(iw["start_seconds"], iw["end_seconds"])

        # (5) the agentic graph filled + reviewed companion_exchange and the pack passes the bridge.
        graph_report = report["graph_report"]
        self.assertEqual(graph_report["accepted_count"], 1)
        self.assertEqual(graph_report["review_status"], "reviewed")
        ce = moment["companion_exchange"]
        self.assertEqual(ce["schema_version"], "companion_exchange_pack.v0.1")
        self.assertEqual(ce["review_status"], "reviewed")
        self.assertEqual(len(ce["reply_candidates"]), 3)
        for field in (
            "outcome_response_contract", "judgment_policy", "visual_result_policy",
            "optional_modules", "canon_baseline", "actor_context", "local_constraints",
            "score_axes", "result_media",
        ):
            self.assertIn(field, moment)
        self.assertEqual(
            moment["outcome_response_contract"]["time_horizon"],
            "current scene or immediate aftermath",
        )
        self.assertEqual(report["validation_status"], "pass",
                         msg=f"bridge errors: {report.get('validation_errors')}")

        # committed synopsis was restored (no residue for the throwaway id).
        syn = json.loads(ingest_mod.SYNOPSES_PATH.read_text("utf-8"))
        self.assertNotIn(DRAMA_ID, syn)

    def test_dry_run_refuses_curated_and_writes_nothing(self):
        before = self._dir_snapshot(REPO_ROOT / "data" / "dramas" / "huangnian")
        rc = ingest_mod.main([
            "--drama-id", "huangnian", "--drama-name", "x", "--video", str(self.fake_video), "--dry-run",
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(self._dir_snapshot(REPO_ROOT / "data" / "dramas" / "huangnian"), before)

    def test_ingest_refuses_curated_drama_id(self):
        with self.assertRaises(ingest_mod.IngestError):
            ingest_mod.ingest(videos=[self.fake_video], drama_id="huangnian", drama_name="x",
                              data_root=self.data_root)

    def test_ark_window_failure_falls_back_to_deterministic_scaffold(self):
        with patch.object(
            ingest_mod,
            "propose_windows_ark",
            side_effect=ingest_mod.IngestError("Ark window picker returned no usable windows"),
        ), patch.object(
            ingest_mod,
            "propose_windows_deterministic",
            return_value=self._windows_override(),
        ):
            report = ingest_mod.ingest(
                videos=[self.fake_video],
                drama_id=DRAMA_ID,
                drama_name=DRAMA_NAME,
                synopsis="测试剧情：她终于不再忍让。",
                data_root=self.data_root,
                max_windows=1,
                through=1,
                use_ark_windows=True,
                author=False,
                write_committed_synopsis=True,
                restore_committed_synopsis=True,
                prepare_runner=self._prepare_runner,
                asr_runner=self._asr_runner,
                memory_runner=self._memory_runner,
            )

        self.assertEqual(report["window_source"], "deterministic_fallback_after_ark")
        self.assertEqual(report["window_count"], 1)
        self.assertTrue((self.data_root / DRAMA_ID / "moments.v0.1.json").exists())
        self.assertIn("build_scaffold", report["order"])

    def test_batch_memory_failure_writes_fallback_memory_for_preview(self):
        def fail_memory(_drama_id, _through):
            raise RuntimeError("ark request failed with status 401")

        report = ingest_mod.ingest(
            videos=[self.fake_video],
            drama_id=DRAMA_ID,
            drama_name=DRAMA_NAME,
            synopsis="测试剧情：她终于不再忍让。",
            data_root=self.data_root,
            max_windows=1,
            through=1,
            author=False,
            write_committed_synopsis=True,
            restore_committed_synopsis=True,
            prepare_runner=self._prepare_runner,
            asr_runner=self._asr_runner,
            memory_runner=fail_memory,
            windows_override=self._windows_override(),
        )

        self.assertEqual(report["memory_source"], "fallback_from_asr_no_provider")
        self.assertEqual(report["memory_fallback_error_type"], "RuntimeError")
        memory = json.loads(
            (REPO_ROOT / "data" / "review" / "context_memory" / f"{DRAMA_ID}.v0.1.json")
            .read_text("utf-8")
        )
        self.assertEqual(memory["source"], "fallback_from_asr_no_provider")
        self.assertIn(EPISODE_ID, memory["episodes"])
        self.assertTrue((self.data_root / DRAMA_ID / "moments.v0.1.json").exists())


if __name__ == "__main__":
    unittest.main()
