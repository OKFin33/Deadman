"""Step 3 (contract): the taste judge consumes the SAME v0.3 spec the author writes against (closed-loop
taste). The judge's output_contract / verdict levels must stay FROZEN (validator + normalize_verdict depend
on them) — v0.3 is injected as INPUT criteria only."""
import unittest


class TestJudgeV03Wiring(unittest.TestCase):
    def setUp(self):
        from tools.ars.deadman_run_studio_taste_judge import build_judge_prompt
        self.case = {
            "case_id": "c", "case_type": "owner_gold_exchange_authoring", "item_id": "i", "episode_id": "e",
            "draft": {"companion_lead": "L", "reply_candidates": [
                {"display_text": "d", "emotion_role": "", "semantic_role": "", "viewer_motivation": "", "selected_echo": "s"}]},
        }
        self.p = build_judge_prompt(self.case)

    def test_v03_patterns_injected_per_layer(self):
        tp = self.p["v03_taste_patterns"]
        self.assertGreater(len(tp["companion_lead"]["negative"]), 0)
        self.assertGreater(len(tp["companion_lead"]["positive"]), 0)
        self.assertGreater(len(tp["display_text"]["negative"]), 0)
        self.assertGreater(len(tp["display_text"]["positive"]), 0)
        self.assertGreater(len(tp["echo"]["negative"]), 0)
        self.assertGreater(len(tp["echo"]["positive"]), 0)

    def test_binding_instruction_present(self):
        self.assertTrue(any("v03_taste_patterns" in i for i in self.p["instructions"]),
                        "judge must bind its dimensions to the v0.3 patterns")

    def test_output_contract_frozen(self):
        oc = self.p["output_contract"]
        self.assertEqual(set(oc), {"case_id", "lead_taste", "reply_voice_taste", "reply_axis_diversity",
                                   "echo_taste", "overall_verdict", "rationale_summary"})
        self.assertEqual(oc["lead_taste"], ["excellent", "acceptable", "needs_repair"])
        self.assertEqual(oc["overall_verdict"], ["accept", "accept_with_minor_tweak", "reject"])

    def test_author_and_judge_share_one_overlay(self):
        # closed-loop: same finalized v0.3 source feeds both the author and the judge
        from tools.ars.deadman_author_drama_heroes import OVERLAY_PATH as author_path
        from tools.ars.deadman_run_studio_taste_judge import _OVERLAY_V03_PATH as judge_path
        self.assertEqual(author_path.name, judge_path.name)


if __name__ == "__main__":
    unittest.main()
