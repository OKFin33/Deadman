import unittest

from tools.ars.deadman_build_review_dataset import build, moment_gate


class ReviewDatasetTests(unittest.TestCase):
    def test_gate_classification(self):
        self.assertEqual(moment_gate({"window": "reject"}), "window_reject")
        self.assertEqual(moment_gate({"window": "accept", "direction": "reject"}), "direction_reject")
        self.assertEqual(moment_gate({"window": "accept"}), "detailed")

    def test_window_reject_carries_no_elements(self):
        ds = build({"m1": {"window": "reject", "window_note": "不该打断", "lead": {"v": "ok"}}})
        rec = ds["moments"][0]
        self.assertEqual(rec["gate"], "window_reject")
        self.assertNotIn("elements", rec)  # short-circuit: per-element dropped even if present
        self.assertEqual(ds["summary"]["element_verdicts"], 0)
        self.assertEqual(ds["window_taste"][0]["verdict"], "reject")

    def test_direction_reject_carries_no_elements(self):
        ds = build({"m1": {"window": "accept", "direction": "reject", "direction_note": "读法错", "says": [{"v": "ok"}]}})
        rec = ds["moments"][0]
        self.assertEqual(rec["gate"], "direction_reject")
        self.assertNotIn("elements", rec)
        self.assertEqual(ds["summary"]["element_verdicts"], 0)

    def test_detailed_flattens_elements_and_tallies_patterns(self):
        ds = build({"m1": {
            "window": "accept",
            "lead": {"v": "ok", "note": "好"},
            "says": [{"v": "ok"}, {"v": "bad", "tag": "display_low_emotion"}, {"v": "ok"}],
            "echoes": [{"v": "bad", "tag": "echo_promotes_show"}, {"v": "ok"}, {"v": "ok"}],
        }})
        rec = ds["moments"][0]
        self.assertEqual(rec["gate"], "detailed")
        self.assertEqual(len(rec["elements"]), 7)
        self.assertEqual(ds["summary"]["element_pass"], 5)
        self.assertEqual(ds["summary"]["element_bad"], 2)
        self.assertEqual(ds["pattern_tally"], {"echo_promotes_show": 1, "display_low_emotion": 1})

    def test_abstain_excluded_from_pass_and_bad(self):
        ds = build({"m1": {
            "window": "accept",
            "lead": {"v": "abstain"},
            "says": [{"v": "ok"}, {"v": "bad", "tag": "display_low_emotion"}, {"v": "abstain"}],
            "echoes": [{"v": "ok"}, {"v": "ok"}, {"v": "ok"}],
        }})
        s = ds["summary"]
        self.assertEqual(s["element_abstain"], 2)
        self.assertEqual(s["element_pass"], 4)
        self.assertEqual(s["element_bad"], 1)

    def test_unlabeled_skipped(self):
        ds = build({"m1": {}, "m2": {"lead": {}}})
        self.assertEqual(ds["summary"]["moments_labeled"], 0)


if __name__ == "__main__":
    unittest.main()
