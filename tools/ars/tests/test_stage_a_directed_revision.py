"""Tests for Stage-A directed revision (contract P0-A / Agentic#2).

Before this, a critic's verdict reached only echo/Stage B (stage_b_prompt injected
revision_feedback); a rejected lead/reply could only be blind-resampled. Now a judge
critique threads into stage_a_prompt and, when the FAILING layer is lead/reply, prepends
a directed-revision instruction that names that layer (mirroring Stage B). The load-bearing
invariants:
  - default (no feedback) leaves the Stage A prompt byte-for-byte unchanged;
  - a single-dimension lead/reply reject puts a directed-revision instruction for the
    MATCHING layer into Stage A;
  - an echo-only reject does NOT perturb Stage A (it routes to Stage B instead).
"""
import unittest

from tools.ars.deadman_author_drama_heroes import _layer_feedback, stage_a_prompt, stage_b_prompt

SCENE = {"case_id": "hero:test_m001", "transcript": ["甲：你怎么能这样", "乙：我没有"]}
LEADS = [{"lead_text": "这家人真闹心", "scene_signal": "冲突"}]
REPLIES = [{"display_text": "我也想说", "emotion_role": "共情", "semantic_role": "stance"}]
TARGET = {"display_text": "我也想说", "emotion_role": "共情", "semantic_role": "stance", "viewer_motivation": "想被接住"}


def _stage_a(feedback=None):
    return stage_a_prompt(SCENE, LEADS, REPLIES, feedback)


class TestStageADirectedRevision(unittest.TestCase):
    def test_no_feedback_prompt_unchanged(self):
        """Default path: no revision_feedback key, no injected revision rule — identical to old behavior."""
        base = _stage_a()
        self.assertNotIn("revision_feedback", base)
        self.assertEqual(_stage_a(None), base)  # None and default are the same prompt
        # the first global_rule is the original lead rule, not a 修订轮 instruction
        self.assertFalse(base["global_rules"][0].startswith("这是修订轮"))

    def test_lead_reject_carries_directed_revision_for_lead(self):
        """A single-dimension lead_taste reject -> Stage A names companion_lead and injects the critique."""
        fb = {"note": "lead 太像旁白了，没有当场反应", "fails": ["lead_taste"]}
        prompt = _stage_a(fb)
        self.assertEqual(prompt["revision_feedback"], fb["note"])
        instruction = prompt["global_rules"][0]
        self.assertTrue(instruction.startswith("这是修订轮"))
        self.assertIn("companion_lead", instruction)
        self.assertNotIn("reply_candidates", instruction)  # reply was NOT named

    def test_reply_reject_carries_directed_revision_for_reply(self):
        """A single-dimension reply_voice_taste reject -> Stage A names reply_candidates only."""
        fb = {"note": "三句太像，不是三种姿态", "fails": ["reply_voice_taste"]}
        prompt = _stage_a(fb)
        self.assertEqual(prompt["revision_feedback"], fb["note"])
        instruction = prompt["global_rules"][0]
        self.assertTrue(instruction.startswith("这是修订轮"))
        self.assertIn("reply_candidates", instruction)
        self.assertNotIn("companion_lead", instruction)  # lead was NOT named

    def test_echo_only_reject_leaves_stage_a_untouched(self):
        """An echo_taste-only reject belongs to Stage B; Stage A must stay on the default path."""
        fb = {"note": "echo 复述了 display_text", "fails": ["echo_taste"]}
        self.assertEqual(_stage_a(fb), _stage_a())  # no Stage A perturbation
        self.assertNotIn("revision_feedback", _stage_a(fb))

    def test_both_lead_and_reply_named_when_both_fail(self):
        fb = {"note": "lead 和三句都偏弱", "fails": ["lead_taste", "reply_voice_taste"]}
        instruction = _stage_a(fb)["global_rules"][0]
        self.assertIn("companion_lead", instruction)
        self.assertIn("reply_candidates", instruction)

    def test_bare_string_feedback_reaches_stage_a(self):
        """Legacy/spike flat critique (no dimension split) is conservatively routed to Stage A too."""
        prompt = _stage_a("上一稿整体偏弱，重写")
        self.assertEqual(prompt["revision_feedback"], "上一稿整体偏弱，重写")
        self.assertTrue(prompt["global_rules"][0].startswith("这是修订轮"))


class TestLayerFeedbackRouting(unittest.TestCase):
    def test_none_is_inert(self):
        self.assertEqual(_layer_feedback(None, ("lead", "reply")), ("", set()))

    def test_dimension_routes_only_to_owning_layer(self):
        note, layers = _layer_feedback({"note": "x", "fails": ["lead_taste"]}, ("lead", "reply"))
        self.assertEqual((note, layers), ("x", {"lead"}))
        # echo critique does not match the lead/reply request
        self.assertEqual(_layer_feedback({"note": "x", "fails": ["echo_taste"]}, ("lead", "reply")), ("", set()))

    def test_echo_request_matches_echo_dimension(self):
        note, layers = _layer_feedback({"note": "e", "fails": ["echo_taste"]}, ("echo",))
        self.assertEqual((note, layers), ("e", {"echo"}))

    def test_bare_string_matches_every_requested_layer(self):
        self.assertEqual(_layer_feedback("flat", ("lead", "reply"))[1], {"lead", "reply"})
        self.assertEqual(_layer_feedback("flat", ("echo",))[1], {"echo"})

    def test_empty_note_is_inert(self):
        self.assertEqual(_layer_feedback({"fails": ["lead_taste"]}, ("lead",)), ("", set()))


class TestStageBComplementaryRouting(unittest.TestCase):
    def test_echo_reject_reaches_stage_b(self):
        prompt = stage_b_prompt(SCENE, "这家人真闹心", TARGET, [], [], [],
                                {"note": "echo 复述了", "fails": ["echo_taste"]})
        self.assertEqual(prompt["revision_feedback"], "echo 复述了")
        self.assertTrue(prompt["echo_rules"][0].startswith("这是修订轮"))

    def test_lead_only_reject_leaves_stage_b_untouched(self):
        base = stage_b_prompt(SCENE, "这家人真闹心", TARGET, [], [], [], None)
        leadonly = stage_b_prompt(SCENE, "这家人真闹心", TARGET, [], [], [],
                                  {"note": "lead 偏弱", "fails": ["lead_taste"]})
        self.assertNotIn("revision_feedback", leadonly)
        self.assertEqual(leadonly, base)  # echo path unperturbed by a lead-only critique

    def test_bare_string_still_revises_stage_b(self):
        """Backward-compat with the M4 spike: a flat critique still drives the echo revision."""
        prompt = stage_b_prompt(SCENE, "这家人真闹心", TARGET, [], [], [], "整体重写")
        self.assertEqual(prompt["revision_feedback"], "整体重写")


if __name__ == "__main__":
    unittest.main()
