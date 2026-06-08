from __future__ import annotations

import unittest

from Deadman.tools.ars.deadman_apply_taste_reflow import (
    build_delta,
    merge_delta,
    recompute_summary,
)


def _dataset() -> dict:
    return {
        "summary": {
            "window_gold_examples": 0,
            "window_negative_examples": 0,
            "owner_reviewed_window_negative_or_context_examples": 0,
            "lead_examples": 0,
            "lead_rejected_examples": 0,
            "lead_repair_examples": 0,
            "reply_examples": 1,
            "reply_rejected_examples": 0,
            "reply_repair_examples": 0,
            "runtime_reviewed_selected_echo_examples": 0,
            "owner_reviewed_selected_echo_examples": 0,
            "draft_selected_echo_examples": 0,
            "real_provider_proof_cases_planned": 0,
        },
        "splits": {
            "window_selection": {"gold_examples": [], "negative_examples": []},
            "lead_authoring": {"examples": [], "rejected_examples": [], "repair_examples": []},
            "reply_authoring": {
                # a pre-existing Phase 2.5 gold seed WITHOUT viewer_motivation
                "examples": [
                    {"item_id": "it1", "episode_id": "huangnian_ep14", "provenance": "phase2_repair",
                     "review_status": "phase2_repair_auto_applied", "display_text": "这口碑也是没谁了"}
                ],
                "rejected_examples": [],
                "repair_examples": [],
            },
            "selected_echo_direction": {
                "runtime_reviewed_examples": [], "owner_reviewed_examples": [],
                "draft_examples": [], "rejected_examples": [],
            },
            "custom_input_policy": {}, "release_gate_rules": {},
        },
        "real_provider_proof_plan": {"planned_cases": []},
    }


def _proof() -> dict:
    return {
        "case_results": [
            {
                "case_id": "c1", "item_id": "it1", "episode_id": "huangnian_ep14",
                "case_type": "owner_gold_exchange_authoring", "provenance": "owner_confirmed",
                "draft": {
                    "companion_lead": "连婆婆都怕她把东西补贴娘家",
                    "reply_candidates": [
                        {"display_text": "这口碑也是没谁了", "emotion_role": "吐槽",
                         "semantic_role": "rep", "viewer_motivation": "想吐槽离谱风评",
                         "selected_echo": "短echo"},
                        {"display_text": "另一条要被拒的", "emotion_role": "x",
                         "semantic_role": "y", "viewer_motivation": "m", "selected_echo": "e2"},
                    ],
                },
            }
        ]
    }


class TasteReflowTests(unittest.TestCase):
    def test_accept_enriches_existing_gold_with_motivation(self) -> None:
        verdicts = {"cases": {"c1": {
            "lead": {"verdict": "accept"},
            "replies": [
                {"display_text_verdict": "accept", "echo_verdict": "abstain"},
                {"display_text_verdict": "reject", "display_text_negative_type": "bad", "echo_verdict": "abstain"},
            ],
        }}}
        delta = build_delta(verdicts=verdicts, drafts_by_case={c["case_id"]: c for c in _proof()["case_results"]},
                            verdict_ref="data/review/v.json", created_at="t")
        dataset = _dataset()
        merged, applied = merge_delta(dataset, delta)

        # The pre-existing seed gained viewer_motivation and owner_confirmed provenance (L3 seed).
        seed = merged["splits"]["reply_authoring"]["examples"][0]
        self.assertEqual(seed["viewer_motivation"], "想吐槽离谱风评")
        self.assertEqual(seed["provenance"], "owner_confirmed")
        self.assertEqual(applied["reply_examples"], {"added": 0, "enriched": 1})

    def test_reject_overrides_and_removes_matching_gold(self) -> None:
        # Owner now rejects the exact text that is currently gold -> demote.
        verdicts = {"cases": {"c1": {
            "lead": {"verdict": "abstain"},
            "replies": [
                {"display_text_verdict": "reject", "display_text_negative_type": "low_emotion", "echo_verdict": "abstain"},
                {"display_text_verdict": "abstain", "echo_verdict": "abstain"},
            ],
        }}}
        delta = build_delta(verdicts=verdicts, drafts_by_case={c["case_id"]: c for c in _proof()["case_results"]},
                            verdict_ref="data/review/v.json", created_at="t")
        dataset = _dataset()
        merged, applied = merge_delta(dataset, delta)
        recompute_summary(merged)

        golds = [r["display_text"] for r in merged["splits"]["reply_authoring"]["examples"]]
        rejects = [r["display_text"] for r in merged["splits"]["reply_authoring"]["rejected_examples"]]
        self.assertNotIn("这口碑也是没谁了", golds)  # demoted out of gold
        self.assertIn("这口碑也是没谁了", rejects)
        self.assertEqual(merged["summary"]["reply_examples"], 0)
        self.assertEqual(merged["summary"]["reply_rejected_examples"], 1)


if __name__ == "__main__":
    unittest.main()
