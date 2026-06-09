import unittest
from pathlib import Path

from tools.ars.deadman_check_element_patterns import check_all, check_moment

REPO = Path(__file__).resolve().parents[3]


class ElementPatternGateTests(unittest.TestCase):
    def test_production_packs_have_no_gross_element_flags(self):
        flags = check_all(REPO / "data/dramas")
        self.assertEqual(flags, [], f"runtime packs tripped gross element patterns: {flags}")

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
