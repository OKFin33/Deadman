"""Regression tests for the Studio L3 pack-build helpers in server.py.

These guard three bugs found during the v0.4 milestone audit:
- candidate_id collision on from-scratch (uploaded) moments → only 1 of 3 replies tappable;
- uploaded interaction_window violating the player contract notice_at <= start <= end;
- missing source_window.start_ms/end_ms → adapter_mapping_invalid on the judgment path.
"""

import json
import shutil
import unittest

from server import (
    _apply_draft_to_moment,
    _build_upload_moment,
    _sanitize_windows,
    STUDIO_UPLOAD_ROOT,
)


class StudioPackBuildTests(unittest.TestCase):
    def test_apply_draft_assigns_unique_candidate_ids_from_scratch(self):
        moment = {"companion_exchange": {"reply_candidates": []}, "companion_surface": {}, "action_space": {}}
        draft = {
            "companion_lead": "lead",
            "replies": [
                {"display_text": "A", "echo": "ea", "coverage": "core_direction_a"},
                {"display_text": "B", "echo": "eb", "coverage": "core_direction_b"},
                {"display_text": "C", "echo": "ec", "coverage": "fallback"},
            ],
        }
        _apply_draft_to_moment(moment, draft)
        cands = moment["companion_exchange"]["reply_candidates"]
        ids = [c["candidate_id"] for c in cands]
        self.assertEqual(ids, ["preset_0", "preset_1", "preset_2"])
        # the runtime requires action.text == candidate.display_text on a preset tap
        for c in cands:
            self.assertEqual(c["action_payload"]["text"], c["display_text"])
        alias_ids = [c["candidate_id"] for c in moment["action_space"]["mouthpiece_candidates"]]
        self.assertEqual(len(set(alias_ids)), 3)

    def test_sanitize_windows_clamps_to_duration_and_caps_at_three(self):
        transcript = {"duration": 60000, "utterances": [{"start_time": 0, "end_time": 60000, "text": "x"}]}
        raw = [{"start_seconds": 5, "end_seconds": 25, "notice_at_seconds": 12, "scene_signal": "s", "rationale": "r"}] * 5
        out = _sanitize_windows(raw, transcript)
        self.assertLessEqual(len(out), 3)
        for w in out:
            self.assertLessEqual(w["end_seconds"], 60)

    def test_build_upload_moment_enforces_player_window_contract(self):
        job = "up_testfixture01"
        job_dir = STUDIO_UPLOAD_ROOT / job
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            (job_dir / "transcript.json").write_text(
                json.dumps({"duration": 60000, "utterances": [{"start_time": 20000, "end_time": 40000, "text": "台词"}]}),
                encoding="utf-8",
            )
            (job_dir / "meta.json").write_text(json.dumps({"video": "source.mp4"}), encoding="utf-8")
            # LLM-style window: notice at the peak (mid-window) — violates notice<=start before remap
            window = {"start_seconds": 20, "end_seconds": 40, "notice_at_seconds": 33, "transcript_excerpt": "台词"}
            moment, *_ = _build_upload_moment(job, window)
            iw = moment["interaction_window"]
            self.assertLessEqual(iw["notice_at_seconds"], iw["start_seconds"])
            self.assertLessEqual(iw["start_seconds"], iw["end_seconds"])
            sw = moment["source_window"]
            self.assertIn("start_ms", sw)
            self.assertLess(sw["start_ms"], sw["end_ms"])
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
