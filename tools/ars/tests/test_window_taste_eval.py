from __future__ import annotations

import unittest

from Deadman.tools.ars.deadman_build_window_taste_eval import (
    build_dataset,
    load_candidates,
    load_windows,
    opening_hypothesis_for_window_review,
    window_review_groups,
)
from Deadman.tools.ars.deadman_validate_window_taste_eval import (
    DEFAULT_EVAL_PATH,
    validate_window_taste_eval,
)
from Deadman.tools.ars.deadman_validate_v04_authoring_proof import read_json


class WindowTasteEvalTests(unittest.TestCase):
    def test_tracked_window_taste_eval_validates(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)

        errors = validate_window_taste_eval(dataset)

        self.assertEqual(errors, [])

    def test_first_pass_contains_owner_anchors_and_draft_counts(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)
        items = dataset["items"]
        by_id = {item["item_id"]: item for item in items}

        self.assertEqual(by_id["taste_gold_owner_huangnian_ep03_0033"]["anchor_ms"], 33000)
        self.assertEqual(by_id["taste_gold_owner_huangnian_ep04_0149"]["anchor_ms"], 109000)
        self.assertEqual(by_id["taste_gold_owner_huangnian_ep06_0103"]["anchor_ms"], 63000)
        self.assertEqual(by_id["taste_gold_owner_huangnian_ep07_0021"]["anchor_ms"], 21000)
        self.assertGreaterEqual(len([item for item in items if item["label"] == "gold"]), 10)
        self.assertGreaterEqual(len([item for item in items if item["label"] == "hard_negative"]), 50)
        self.assertEqual(
            by_id["taste_gold_owner_huangnian_ep03_0033"]["context_card"]["agent_input_readiness"],
            "owner_confirmed",
        )
        self.assertEqual(
            by_id["taste_gold_proposed_huangnian_ep02_0125"]["context_card"]["agent_input_readiness"],
            "owner_confirmed",
        )
        self.assertEqual(
            by_id["taste_negative_huangnian_ep12_skip_context"]["context_card"]["agent_input_readiness"],
            "context_insufficient",
        )
        self.assertEqual(
            by_id["taste_gold_owner_huangnian_ep03_0033"]["window_review"]["decision"],
            "accepted_best",
        )
        self.assertEqual(
            by_id["taste_gold_owner_huangnian_ep03_0033"]["window_review"]["decision_source"],
            "owner_seed",
        )
        self.assertEqual(
            by_id["taste_gold_proposed_huangnian_ep02_0125"]["window_review"]["decision"],
            "accepted_best",
        )
        self.assertEqual(
            by_id["taste_gold_proposed_huangnian_ep02_0125"]["window_review"]["episode_rank"],
            "best",
        )
        self.assertEqual(
            by_id["taste_negative_huangnian_ep12_skip_context"]["window_review"]["decision"],
            "context_insufficient",
        )
        self.assertEqual(
            by_id["taste_negative_huangnian_ep12_skip_context"]["window_review"]["decision_source"],
            "owner_context_review",
        )
        ep02 = by_id["taste_gold_proposed_huangnian_ep02_0125"]
        self.assertEqual(ep02["context_card"]["owner_review_outcome"], "understood_gold_with_revision")
        seed = ep02["context_card"]["authoring_seed"]
        self.assertEqual(seed["companion_lead_seed"], "他们居然还先把吃的端给娘。")
        self.assertIn("open enough", seed["lead_style_policy"])
        self.assertIn("first two preset replies", seed["reply_set_policy"])
        self.assertIn("viewing companions", seed["viewer_stance_policy"])
        self.assertIn("reviewed echo", seed["preset_echo_policy"])
        self.assertIn("rejected_lead_examples", seed)
        self.assertEqual(
            [reply["display_text"] for reply in seed["reply_candidate_seeds"]],
            ["是呀，也太孝顺了", "这么坏，是我早不理她了", "有点夸张"],
        )
        self.assertIn(
            "刚才那一下，你是不是想说：",
            [lead["display_text"] for lead in seed["rejected_lead_examples"]],
        )
        ep08 = by_id["taste_gold_proposed_huangnian_ep08_0148"]
        self.assertEqual(ep08["context_card"]["owner_review_outcome"], "understood_wrong_taste")
        self.assertEqual(
            [reply["display_text"] for reply in ep08["context_card"]["authoring_seed"]["reply_candidate_seeds"]],
            ["这孩子也太容易满足了", "以前是多缺夸啊", "这一下看得我心软"],
        )
        self.assertIn(
            "有点暖，但别太煽",
            [lead["display_text"] for lead in ep08["context_card"]["authoring_seed"]["rejected_lead_examples"]],
        )
        self.assertIn(
            "他这反应有点戳人",
            [reply["display_text"] for reply in ep08["context_card"]["authoring_seed"]["rejected_reply_examples"]],
        )
        ep09 = by_id["taste_gold_proposed_huangnian_ep09_0044"]
        self.assertEqual(ep09["context_card"]["owner_review_outcome"], "understood_wrong_taste")
        self.assertEqual(
            [reply["display_text"] for reply in ep09["context_card"]["authoring_seed"]["reply_candidate_seeds"]],
            ["就是，这小孩嘴好毒", "原主自己孩子都不宠，有点离谱", "听着都替他难受"],
        )
        self.assertIn(
            "这话有点损过头了",
            [reply["display_text"] for reply in ep09["context_card"]["authoring_seed"]["rejected_reply_examples"]],
        )
        ep10 = by_id["taste_gold_proposed_huangnian_ep10_0027"]
        self.assertEqual(ep10["context_card"]["owner_review_outcome"], "understood_gold_with_revision")
        self.assertEqual(ep10["context_card"]["authoring_seed"]["companion_lead_seed"], "坐等看戏。")
        self.assertEqual(
            [reply["display_text"] for reply in ep10["context_card"]["authoring_seed"]["reply_candidate_seeds"]],
            ["还真是，现在不是原主了", "确实，主角肯定会护着四蛋", "经典打脸剧情"],
        )
        ep14 = by_id["taste_gold_proposed_huangnian_ep14_0048"]
        self.assertEqual(ep14["context_card"]["owner_review_outcome"], "understood_gold_with_revision")
        self.assertIn("speaker diarization", ep14["context_card"]["dependency_note"])
        self.assertEqual(
            [reply["display_text"] for reply in ep14["context_card"]["authoring_seed"]["reply_candidate_seeds"]],
            ["这口碑也是没谁了", "原主那个人设，也难怪婆婆防备", "婆婆嘴硬归嘴硬，粮是真给了"],
        )
        ep17 = by_id["taste_gold_proposed_huangnian_ep17_0048"]
        self.assertEqual(ep17["context_card"]["owner_review_outcome"], "understood_wrong_taste")
        self.assertEqual(ep17["context_card"]["authoring_seed"]["companion_lead_seed"], "以前家里鸡蛋都被原主吃了？")
        self.assertEqual(
            [reply["display_text"] for reply in ep17["context_card"]["authoring_seed"]["reply_candidate_seeds"]],
            ["这原主，自私到骨子里了", "他连一小口都不敢直接要", "原主人设又稳得离谱"],
        )
        self.assertIn(
            "鸡蛋都自己吃，也太离谱了",
            [reply["display_text"] for reply in ep17["context_card"]["authoring_seed"]["rejected_reply_examples"]],
        )
        rejected_terms = ("护住", "点出", "接住", "交付")
        for item_id in (
            "taste_gold_proposed_huangnian_ep08_0148",
            "taste_gold_proposed_huangnian_ep09_0044",
            "taste_gold_proposed_huangnian_ep10_0027",
            "taste_gold_proposed_huangnian_ep14_0048",
            "taste_gold_proposed_huangnian_ep17_0048",
        ):
            seed = by_id[item_id]["context_card"]["authoring_seed"]
            rejected = {reply["display_text"] for reply in seed["rejected_reply_examples"]}
            for reply in seed["reply_candidate_seeds"]:
                self.assertFalse(any(term in reply["display_text"] for term in rejected_terms))
                self.assertNotIn(reply["display_text"], rejected)

    def test_context_cards_include_review_surface_fields(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)
        for item in dataset["items"]:
            window_review = item["window_review"]
            self.assertEqual(window_review["review_version"], "window_review.v0.1")
            self.assertTrue(window_review["reason"])
            self.assertTrue(window_review["owner_review_prompt"])
            card = item["context_card"]
            self.assertEqual(card["card_version"], "context_card.v0.2")
            self.assertGreater(len(card["episode_context"]), 20)
            self.assertGreater(len(card["scene_function"]), 12)
            self.assertGreater(len(card["character_relationship_state"]), 12)
            self.assertGreater(len(card["adjacent_asr"]["current"]), 20)
            seed = card["authoring_seed"]
            if item["label"] == "gold":
                self.assertEqual(seed["applicability"], "authoring_reference")
                self.assertTrue(seed["companion_lead_seed"])
                self.assertTrue(seed["lead_style_policy"])
                self.assertTrue(seed["reply_set_policy"])
                self.assertTrue(seed["viewer_stance_policy"])
                self.assertTrue(seed["preset_echo_policy"])
                self.assertIn("rejected_lead_examples", seed)
                self.assertIn("rejected_reply_examples", seed)
                self.assertGreaterEqual(len(seed["reply_candidate_seeds"]), 2)

    def test_window_review_records_owner_phase15_decisions(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)
        agent_proposed = [
            item
            for item in dataset["items"]
            if item["label"] == "gold" and item["source_origin"] == "agent_proposed"
        ]
        owner_rejected = [
            item
            for item in dataset["items"]
            if item["label"] == "hard_negative"
            and item["window_review"]["decision_source"] == "owner_episode_review"
        ]

        self.assertEqual(len(agent_proposed), 6)
        self.assertTrue(all(item["review_status"] == "owner_confirmed" for item in agent_proposed))
        self.assertTrue(all(item["window_review"]["decision"] == "accepted_best" for item in agent_proposed))
        self.assertTrue(all(item["window_review"]["decision_source"] == "owner_episode_review" for item in agent_proposed))
        self.assertTrue(all(item["window_review"]["needs_video_review"] is False for item in agent_proposed))
        self.assertEqual(len(owner_rejected), 16)
        self.assertTrue(all("owner_phase15_rejected" in item["reject_dimensions"] for item in owner_rejected))

    def test_window_review_groups_are_episode_scoped(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)

        groups = window_review_groups(dataset["items"])

        self.assertEqual(
            [group["episode_id"] for group in groups],
            [
                "huangnian_ep02",
                "huangnian_ep08",
                "huangnian_ep09",
                "huangnian_ep10",
                "huangnian_ep14",
                "huangnian_ep17",
            ],
        )
        self.assertEqual(groups[0]["primary_item_id"], "taste_gold_proposed_huangnian_ep02_0125")
        self.assertGreaterEqual(len(groups[0]["candidates"]), 2)
        for group in groups:
            self.assertTrue(group["episode_context"])
            self.assertTrue(group["relationship_state"])
            self.assertEqual(group["candidates"][0]["item_id"], group["primary_item_id"])
            self.assertEqual(group["candidates"][0]["window_review"]["decision"], "accepted_best")
            self.assertEqual(group["candidates"][0]["window_review"]["decision_source"], "owner_episode_review")

    def test_window_review_opening_hypothesis_prefers_current_lead_seed(self) -> None:
        dataset = read_json(DEFAULT_EVAL_PATH)
        by_id = {item["item_id"]: item for item in dataset["items"]}

        ep10 = by_id["taste_gold_proposed_huangnian_ep10_0027"]

        self.assertEqual(opening_hypothesis_for_window_review(ep10), "坐等看戏。")
        self.assertNotEqual(
            opening_hypothesis_for_window_review(ep10),
            ep10["context_card"]["mouthpiece_pressure"],
        )

    def test_builder_output_validates_against_current_local_candidates(self) -> None:
        dataset = build_dataset(
            windows=load_windows(__import__("pathlib").Path("tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.2.json")),
            candidates=load_candidates(__import__("pathlib").Path("tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json")),
        )

        errors = validate_window_taste_eval(dataset)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
