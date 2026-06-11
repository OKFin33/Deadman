"""Deterministic tests for the v0.3 clustering assembly (the LLM call itself is not unit-tested).

Locks the owner checkpoint① rulings into code: gold = owner-confirmed only; provisional excluded;
rejects (incl. the owner-flipped v1-gold) form the negative pool; v0.3 carries v2 gold + v1 stays frozen.
"""
import unittest

from tools.ars.deadman_build_overlay_v03 import partition, assemble_v03, _is_owner_gold, guard_gold


def _r(layer, verdict, prov, text="t"):
    return {"layer": layer, "verdict": verdict, "provenance": prov, "text": text,
            "item_id": "i", "element": "e", "note": "", "pattern": None}


class TestPartition(unittest.TestCase):
    def test_owner_gold_filter(self):
        self.assertTrue(_is_owner_gold(_r("echo", "gold", "owner_confirmed")))
        self.assertTrue(_is_owner_gold(_r("echo", "gold", "inplayer_element")))
        self.assertTrue(_is_owner_gold(_r("echo", "gold", "owner_tray")))
        self.assertTrue(_is_owner_gold(_r("echo", "gold", "owner_reviewed")))
        # provisional -> NOT gold (ruling #1)
        self.assertFalse(_is_owner_gold(_r("echo", "gold", "runtime_reviewed")))
        self.assertFalse(_is_owner_gold(_r("echo", "gold", "phase2_repair")))
        self.assertFalse(_is_owner_gold(_r("echo", "gold", "draft_not_owner_reviewed")))

    def test_partition_splits_rejects_gold_provisional(self):
        full = {"records": [
            _r("echo", "reject", "inplayer_element", "bad echo"),       # the flipped kind
            _r("display_text", "reject", "owner_reviewed_reject", "bad say"),
            _r("echo", "gold", "owner_confirmed", "good echo"),
            _r("echo", "gold", "runtime_reviewed", "provisional echo"),  # excluded from gold
            _r("companion_lead", "abstain", "x", "meh"),                 # ignored
        ]}
        rejects_by_layer, owner_gold, provisional = partition(full)
        self.assertEqual(sorted(rejects_by_layer), ["display_text", "echo"])
        self.assertEqual(len(rejects_by_layer["echo"]), 1)
        self.assertEqual(len(owner_gold), 1)
        self.assertEqual(owner_gold[0]["text"], "good echo")
        self.assertEqual(len(provisional), 1)
        self.assertEqual(provisional[0]["text"], "provisional echo")


class TestAssemble(unittest.TestCase):
    def test_structure_and_carry(self):
        overlay_v2 = {
            "named_negatives": [{"negative_type": "old_one"}],
            "gold_examples": [{"moment_id": "m1"}, {"moment_id": "m2"}],
            "echo_rules_addendum": ["r1"],
            "reflow_mechanism": "rm",
        }
        owner_gold = [_r("echo", "gold", "owner_confirmed", "g1"),
                      _r("display_text", "gold", "inplayer_element", "g2")]
        rejects_by_layer = {"echo": [_r("echo", "reject", "inplayer_element")]}
        llm = [{"negative_type": "echo_rpg_or_action_menu", "severity": "hard"}]
        v03 = assemble_v03(llm, overlay_v2, owner_gold, rejects_by_layer, provisional_n=7)
        self.assertEqual(v03["schema_version"], "studio_cab_taste_overlay.v0.3")
        self.assertEqual(v03["status"], "proposed_awaiting_owner_review")
        self.assertIn("v0.1", v03["base_frozen"])  # v1 referenced as frozen, never mutated here
        self.assertEqual(v03["supersedes"], "studio_cab_taste_overlay.v0.2.json")
        self.assertEqual(v03["named_negatives"], llm)              # LLM taxonomy passed through
        self.assertEqual(len(v03["gold_examples"]), 2)            # v2 owner gold carried
        self.assertEqual(len(v03["gold_exemplars"]), 2)          # element-level owner positives
        self.assertEqual(v03["echo_rules_addendum"], ["r1"])     # addenda carried
        self.assertEqual(v03["build_meta"]["provisional_gold_excluded"], 7)
        self.assertEqual(v03["build_meta"]["owner_gold_kept"], 2)

    def test_gold_exemplars_dedup(self):
        overlay_v2 = {"gold_examples": []}
        owner_gold = [_r("echo", "gold", "owner_confirmed", "same"),
                      _r("echo", "gold", "owner_tray", "same")]  # same (layer,text) -> dedup
        v03 = assemble_v03([], overlay_v2, owner_gold, {}, 0)
        self.assertEqual(len(v03["gold_exemplars"]), 1)


class TestGuard(unittest.TestCase):
    def test_detects_gold_copy_that_was_rejected(self):
        v = {"gold_examples": [{"moment_id": "m1", "companion_lead": "好引子",
                                "reply_candidates": [{"display_text": "坏句", "selected_echo": "好回声"}]}],
             "gold_exemplars": []}
        full = {"records": [{"verdict": "reject", "layer": "display_text", "text": "坏句。",  # punct -> norm matches
                             "item_id": "x", "note": "bad"}]}
        col = guard_gold(v, full)
        self.assertEqual(len(col), 1)
        self.assertEqual(col[0]["layer"], "display_text")
        self.assertIn("say1", col[0]["where"])

    def test_clean_when_no_overlap(self):
        v = {"gold_examples": [{"moment_id": "m", "companion_lead": "独特引子", "reply_candidates": []}],
             "gold_exemplars": []}
        full = {"records": [{"verdict": "reject", "layer": "companion_lead", "text": "别的句", "item_id": "y"}]}
        self.assertEqual(guard_gold(v, full), [])

    def test_gold_exemplar_also_checked(self):
        v = {"gold_examples": [], "gold_exemplars": [{"layer": "echo", "text": "坏回声", "item_id": "e"}]}
        full = {"records": [{"verdict": "reject", "layer": "echo", "text": "坏回声", "item_id": "z", "note": "n"}]}
        self.assertEqual(len(guard_gold(v, full)), 1)


if __name__ == "__main__":
    unittest.main()
