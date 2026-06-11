import unittest
from pathlib import Path

from tools.ars.deadman_check_element_patterns import check_all, check_moment, hard_flags

REPO = Path(__file__).resolve().parents[3]


class ElementPatternGateTests(unittest.TestCase):
    def test_production_packs_have_no_gross_element_flags(self):
        # The gate scans EVERY drama under data/dramas — curated + uploaded alike (the 3 curated
        # packs are just pre-seeded uploads, no different from user uploads). Only HARD (gross)
        # flags fail it; soft craft hints (e.g. echo_formulaic_opening — a review-time signal that is
        # invisible to a viewer who only ever sees the one echo paired with their say) are advisory
        # and never red the gate.
        hard = hard_flags(check_all(REPO / "data/dramas"))
        self.assertEqual(hard, [], f"runtime packs tripped gross element patterns: {hard}")

    def test_formulaic_opening_is_soft_not_hard(self):
        m = {"moment_id": "z", "companion_exchange": {"companion_lead": "这一下真戳人",
             "reply_candidates": [
                 {"display_text": "她长得真好看", "selected_echo": "可不是，气质也压全场"},
                 {"display_text": "这场面真大", "selected_echo": "可不是，连引路都放轻了脚步"},
                 {"display_text": "传得真久", "selected_echo": "可不是，七十多年全府都记着"},
             ]}}
        flags = check_moment(m)
        formulaic = [f for f in flags if f["pattern"] == "echo_formulaic_opening"]
        self.assertEqual(len(formulaic), 1)
        self.assertEqual(formulaic[0]["severity"], "soft")  # advisory, not gate-failing
        self.assertEqual(hard_flags(flags), [])             # per-pair-fit echoes → no hard flag

    def test_detects_question_lead(self):
        m = {"moment_id": "x", "companion_surface": {"companion_lead": "你觉得他这样对不对呢"},
             "action_space": {"mouthpiece_candidates": []}}
        pats = {f["pattern"] for f in check_moment(m)}
        self.assertIn("lead_question_shape", pats)

    def test_detects_formulaic_and_promotes_show(self):
        m = {"moment_id": "y", "companion_surface": {"companion_lead": "这一下真戳人"},
             "action_space": {"mouthpiece_candidates": [
                 {"display_text": "太惨了", "selected_echo": "对啊这部剧节奏真好"},
                 {"display_text": "气死了", "selected_echo": "对啊我也这么想"},
                 {"display_text": "心疼她", "selected_echo": "对啊她太难了"},
             ]}}
        pats = {f["pattern"] for f in check_moment(m)}
        self.assertIn("echo_formulaic_opening", pats)
        self.assertIn("echo_promotes_show", pats)


if __name__ == "__main__":
    unittest.main()
