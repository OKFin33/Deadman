import unittest

from tools.ars.deadman_build_overlay_deltas import collect, merge

FAKE_MOMENT = {
    "moment_id": "huangnian_ep07_m001",
    "companion_surface": {"companion_lead": "这桌饭看得人火气上来了"},
    "action_space": {"mouthpiece_candidates": [
        {"display_text": "凭什么啊", "selected_echo": "就是啊"},
        {"display_text": "气死了", "selected_echo": "对啊我也想护住她"},
        {"display_text": "心疼她", "selected_echo": "她太难了"},
    ]},
    "source_window": {"transcript_refs": [{"text": "你根本不配上桌吃饭"}]},
}


def mock_resolver(_drama, _mid):
    return FAKE_MOMENT


class OverlayDeltaTests(unittest.TestCase):
    def test_collect_extracts_bad_text_note_tag(self):
        labels = {
            "huangnian_ep07_m001": {"window": "accept", "lead": {"v": "ok"},
                "says": [{"v": "ok"}, {"v": "bad", "tag": "display_rpg_or_action_menu", "note": "RPG"}, {"v": "ok"}],
                "echoes": [{"v": "ok"}, {"v": "bad", "note": "附和RPG"}, {"v": "ok"}]},
            "huangnian_ep03_m001": {"window": "accept", "lead": {"v": "ok"}, "says": [{"v": "ok"}], "echoes": [{"v": "ok"}]},
        }
        bad, gold = collect(labels, resolver=mock_resolver)
        self.assertEqual(len(bad), 2)
        say = next(b for b in bad if b["layer"] == "display_text")
        self.assertEqual(say["text"], "气死了")
        self.assertEqual(say["owner_tag"], "display_rpg_or_action_menu")
        echo = next(b for b in bad if b["layer"] == "echo")
        self.assertEqual(echo["owner_note"], "附和RPG")
        self.assertEqual(echo["text"], "对啊我也想护住她")
        self.assertIn(("huangnian", "huangnian_ep03_m001"), gold)

    def test_gate_reject_skips_elements(self):
        bad, gold = collect({"m": {"window": "reject", "says": [{"v": "bad", "note": "x"}]}}, resolver=mock_resolver)
        self.assertEqual(bad, [])
        self.assertEqual(gold, [])

    def test_merge_additive_and_idempotent(self):
        overlay = {"named_negatives": [{"negative_type": "echo_too_long", "illustrative_examples": ["a"]}], "gold_examples": []}
        proposal = {"named_negatives": [
            {"negative_type": "echo_rpg_or_action_menu", "illustrative_examples": ["附和RPG"]},
            {"negative_type": "echo_too_long", "illustrative_examples": ["a"]},
        ], "gold_examples": [{"moment_id": "m1"}]}
        overlay, add_n, add_g = merge(overlay, proposal)
        self.assertEqual((add_n, add_g), (1, 1))
        self.assertEqual(len(overlay["named_negatives"]), 2)
        overlay, add_n2, add_g2 = merge(overlay, proposal)
        self.assertEqual((add_n2, add_g2), (0, 0))


if __name__ == "__main__":
    unittest.main()
