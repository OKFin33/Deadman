"""Deterministic tests for the全量 taste-label harvest (checkpoint① of the v0.3 rebuild).

Covers the load-bearing join/normalize/dedup logic with synthetic data — no dependency on the real
artifacts, so the harvest stays trustworthy as those evolve.
"""
import unittest

from tools.ars.deadman_harvest_taste_labels import (
    norm_text, norm_verdict, v1_records, field_records, tray_records, inplayer_records, dedup,
)


class TestNormalizers(unittest.TestCase):
    def test_norm_text_strips_ws_and_trailing_punct(self):
        self.assertEqual(norm_text(" 这 句 话。"), "这句话")
        self.assertEqual(norm_text("ok!！"), "ok")
        self.assertEqual(norm_text(""), "")

    def test_norm_verdict(self):
        self.assertEqual(norm_verdict("accept"), "gold")
        self.assertEqual(norm_verdict("accept_with_minor_tweak"), "gold")
        self.assertEqual(norm_verdict("ok"), "gold")
        self.assertEqual(norm_verdict("reject"), "reject")
        self.assertEqual(norm_verdict("bad"), "reject")
        self.assertEqual(norm_verdict("abstain"), "abstain")
        self.assertEqual(norm_verdict(""), "abstain")


class TestV1(unittest.TestCase):
    def setUp(self):
        self.doc = {"splits": {
            "lead_authoring": {
                "examples": [{"item_id": "g1", "lead_text": "好引子", "provenance": "owner"}],
                "rejected_examples": [{"item_id": "r1", "display_text": "问号引子？",
                                       "negative_type": "question_shaped_lead",
                                       "reject_reason": "问句", "correction_hint": "改陈述"}],
                "repair_examples": [{"item_id": "p1", "bad_text": "坏引子",
                                     "replacement_text": "好引子2", "failure_type": "q",
                                     "reason": "fix"}],
            },
            "reply_authoring": {"examples": [{"item_id": "g2", "display_text": "想说的一句"}]},
            "selected_echo_direction": {"rejected_examples": [
                {"item_id": "r2", "selected_echo": "复述回声", "negative_type": "echo_paraphrases_display_text"}]},
            "window_selection": {"negative_examples": [
                {"item_id": "w1", "context_summary": {"episode_context": "上下文不足"},
                 "window_review_decision": "context_insufficient", "why_bad": "miss"}]},
        }}

    def test_gold_reject_repair_and_layers(self):
        recs = v1_records(self.doc)
        by = {(r["layer"], r["verdict"]): r for r in recs}
        self.assertEqual(by[("companion_lead", "gold")]["text"], "好引子")
        # companion_lead has TWO reject records (rejected_examples + repair) — pick by element
        lead_rej = next(r for r in recs if r["element"] == "lead_authoring.rejected_examples")
        self.assertEqual(lead_rej["text"], "问号引子？")
        self.assertEqual(lead_rej["pattern"], "question_shaped_lead")
        self.assertEqual(by[("display_text", "gold")]["text"], "想说的一句")
        self.assertEqual(by[("echo", "reject")]["pattern"], "echo_paraphrases_display_text")
        win_rej = by[("window", "reject")]
        self.assertEqual(win_rej["text"], "w1")  # item_id is the stable window key (time_range collides)
        self.assertEqual(win_rej["pattern"], "context_insufficient")
        self.assertIn("上下文不足", win_rej["scene"])  # dict context_summary coerced into scene
        # repair: the bad_text becomes a reject carrying the replacement as correction_hint
        repair = next(r for r in recs if r["element"].endswith(".repair"))
        self.assertEqual(repair["text"], "坏引子")
        self.assertEqual(repair["verdict"], "reject")
        self.assertEqual(repair["correction_hint"], "好引子2")

    def test_all_v1_records_have_source_v1(self):
        self.assertTrue(all(r["source"] == "v1" for r in v1_records(self.doc)))


class TestFieldVerdictJoin(unittest.TestCase):
    def test_join_by_case_id_and_index(self):
        doc = {"cases": {"c1": {
            "lead": {"verdict": "accept", "note": "好"},
            "replies": [{"display_text_verdict": "accept", "echo_verdict": "reject",
                         "echo_negative_type": "echo_awkward_phrasing", "echo_note": "怪"}],
        }}}
        drafts = {"c1": {"episode_id": "huangnian_ep03", "draft": {
            "companion_lead": "L", "reply_candidates": [{"display_text": "D", "selected_echo": "E"}]}}}
        recs = field_records(doc, "round6", drafts)
        by = {(r["layer"], r["element"]): r for r in recs}
        self.assertEqual(by[("companion_lead", "lead")]["text"], "L")
        self.assertEqual(by[("companion_lead", "lead")]["verdict"], "gold")
        self.assertEqual(by[("display_text", "say1")]["text"], "D")
        echo = by[("echo", "echo1")]
        self.assertEqual(echo["text"], "E")
        self.assertEqual(echo["verdict"], "reject")
        self.assertEqual(echo["pattern"], "echo_awkward_phrasing")
        self.assertTrue(all(r["round"] == 6 for r in recs))

    def test_missing_draft_yields_unresolved_text_but_keeps_verdict(self):
        doc = {"cases": {"cX": {"lead": {"verdict": "reject", "note": "n"}, "replies": []}}}
        recs = field_records(doc, "round4", {})  # no draft for cX
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["text"], "")
        self.assertFalse(recs[0]["text_resolved"])
        self.assertEqual(recs[0]["verdict"], "reject")  # verdict preserved -> goes to text_unresolved


class TestTrays(unittest.TestCase):
    def test_non_abstain_harvested_abstain_skipped(self):
        md = (
            "intro\n\n"
            "## Draft 1 / 2: huangnian_ep03 — item\n"
            "- **case_id**: `real_provider_gold:taste_huangnian_ep03_0033`\n\n"
            "### companion_lead\n\n> 这是引子\n\n"
            "### owner verdict\n```\nowner_verdict: reject\nowner_notes: echo 完全在复述 display_text\n```\n\n"
            "## Draft 2 / 2: huangnian_ep10 — item2\n"
            "- **case_id**: `c2`\n\n### companion_lead\n\n> 引子二\n\n"
            "```\nowner_verdict: abstain\nowner_notes: \n```\n"
        )
        recs, abstain = tray_records(md, "round1")
        self.assertEqual(len(recs), 1)
        self.assertEqual(abstain, 1)
        r = recs[0]
        self.assertEqual(r["verdict"], "reject")
        self.assertEqual(r["text"], "这是引子")
        self.assertEqual(r["note"], "echo 完全在复述 display_text")
        self.assertEqual(r["episode_id"], "huangnian_ep03")
        self.assertEqual(r["round"], 1)
        self.assertEqual(r["layer"], "moment")


class TestInplayer(unittest.TestCase):
    def setUp(self):
        self.m = {
            "companion_exchange": {"companion_lead": "LEAD", "reply_candidates": [
                {"display_text": "S1", "selected_echo": "E1"},
                {"display_text": "S2", "selected_echo": "E2"},
                {"display_text": "S3", "selected_echo": "E3"}]},
            "source_drama": {"episode_id": "huangnian_ep07"},
            "source_window": {"transcript_refs": [{"text": "scene text"}]},
        }
        self.resolver = lambda drama, mid: self.m

    def test_elements_and_window_reject(self):
        labels = {
            "huangnian_ep07_m001": {"window": "accept", "lead": {"v": "ok"},
                                    "says": [{"v": "ok"}, {"v": "bad", "note": "RPG成分过高"}],
                                    "echoes": [{"v": "ok"}, {"v": "bad", "tag": "echo_rpg_or_action_menu"}]},
            "huangnian_ep12_m001": {"window": "reject", "window_note": "窗口不对"},
        }
        recs = inplayer_records(labels, self.resolver)
        by = {(r["item_id"], r["element"]): r for r in recs}
        self.assertEqual(by[("huangnian_ep07_m001", "lead")]["text"], "LEAD")
        self.assertEqual(by[("huangnian_ep07_m001", "lead")]["verdict"], "gold")
        say2 = by[("huangnian_ep07_m001", "say2")]
        self.assertEqual(say2["text"], "S2")
        self.assertEqual(say2["verdict"], "reject")
        self.assertEqual(say2["note"], "RPG成分过高")
        echo2 = by[("huangnian_ep07_m001", "echo2")]
        self.assertEqual(echo2["pattern"], "echo_rpg_or_action_menu")
        win = by[("huangnian_ep12_m001", "window")]
        self.assertEqual(win["layer"], "window")
        self.assertEqual(win["verdict"], "reject")
        self.assertEqual(win["text"], "窗口不对")

    def test_abstain_element_maps_to_abstain(self):
        labels = {"huangnian_ep07_m001": {"window": "accept", "says": [{"v": "abstain", "note": "略奇怪"}]}}
        recs = inplayer_records(labels, self.resolver)
        self.assertEqual(recs[0]["verdict"], "abstain")


class TestDedup(unittest.TestCase):
    def _r(self, source, layer, text, verdict, rnd=None):
        return {"source": source, "round": rnd, "item_id": "i", "layer": layer, "element": "e",
                "text": text, "verdict": verdict, "pattern": None, "note": "", "correction_hint": None,
                "scene": "", "episode_id": "", "provenance": "", "text_resolved": True}

    def test_authority_inplayer_beats_v2_and_records_conflict(self):
        recs = [self._r("v2_field", "display_text", "同一句话", "gold"),
                self._r("inplayer", "display_text", "同一句话。", "reject")]  # punct differs -> same key
        kept, conflicts, merged = dedup(recs)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["source"], "inplayer")  # newest wins
        self.assertEqual(kept[0]["verdict"], "reject")
        self.assertEqual(merged, 1)
        self.assertEqual(len(conflicts), 1)

    def test_v1_beats_v2(self):
        recs = [self._r("v2_tray", "echo", "回声", "gold"),
                self._r("v1", "echo", "回声", "reject")]
        kept, conflicts, _ = dedup(recs)
        self.assertEqual(kept[0]["source"], "v1")

    def test_exact_dup_same_verdict_merges_without_conflict(self):
        recs = [self._r("v1", "echo", "回声", "reject"),
                self._r("v1", "echo", "回声", "reject")]
        kept, conflicts, merged = dedup(recs)
        self.assertEqual(len(kept), 1)
        self.assertEqual(merged, 1)
        self.assertEqual(len(conflicts), 0)

    def test_field_beats_tray_on_same_authority_tier(self):
        recs = [self._r("v2_tray", "display_text", "句", "gold"),
                self._r("v2_field", "display_text", "句", "reject")]
        kept, _, _ = dedup(recs)
        self.assertEqual(kept[0]["source"], "v2_field")


if __name__ == "__main__":
    unittest.main()
