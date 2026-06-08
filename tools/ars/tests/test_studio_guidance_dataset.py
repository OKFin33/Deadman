from __future__ import annotations

import unittest

from Deadman.tools.ars.deadman_build_studio_guidance_dataset import (
    DEFAULT_OUTPUT_PATH,
    build_guidance_dataset,
    read_json,
)
from Deadman.tools.ars.deadman_validate_studio_guidance_dataset import validate_studio_guidance_dataset


class StudioGuidanceDatasetTests(unittest.TestCase):
    def test_builder_output_passes_guidance_contract(self) -> None:
        dataset = build_guidance_dataset(created_at="2026-06-07T00:00:00Z")

        errors = validate_studio_guidance_dataset(dataset=dataset, dataset_path=DEFAULT_OUTPUT_PATH)

        self.assertEqual(errors, [])
        self.assertEqual(dataset["summary"]["window_gold_examples"], 10)
        self.assertEqual(dataset["summary"]["window_negative_examples"], 50)
        self.assertEqual(dataset["real_provider_proof_plan"]["provider_invocation"], "not_started")
        repair_failures = {
            case["expected_behavior"].replace("avoid ", "", 1)
            for case in dataset["real_provider_proof_plan"]["planned_cases"]
            if case["case_type"] == "phase2_repair_regression"
        }
        self.assertEqual(repair_failures, {"axis_label_no_viewer_voice", "question_shaped_lead_seed"})

    def test_phase2_repairs_do_not_masquerade_as_owner_reviewed_copy(self) -> None:
        dataset = build_guidance_dataset(created_at="2026-06-07T00:00:00Z")

        reply_examples = dataset["splits"]["reply_authoring"]["examples"]
        repaired = [example for example in reply_examples if example["provenance"] == "phase2_repair"]

        self.assertGreaterEqual(len(repaired), 12)
        self.assertTrue(
            all(example["review_status"] == "phase2_repair_auto_applied" for example in repaired)
        )
        self.assertFalse(
            any(example["review_status"] == "owner_reviewed_positive" for example in repaired)
        )

    def test_selected_echo_split_separates_runtime_reviewed_from_phase2_drafts(self) -> None:
        dataset = build_guidance_dataset(created_at="2026-06-07T00:00:00Z")
        echo_split = dataset["splits"]["selected_echo_direction"]

        self.assertEqual(len(echo_split["runtime_reviewed_examples"]), 15)
        self.assertEqual(len(echo_split["draft_examples"]), 30)
        self.assertTrue(
            all(example["provenance"] == "runtime_reviewed" for example in echo_split["runtime_reviewed_examples"])
        )
        self.assertTrue(
            all(example["review_status"] == "reviewed" for example in echo_split["runtime_reviewed_examples"])
        )
        self.assertTrue(
            all(example["provenance"] == "draft_not_owner_reviewed" for example in echo_split["draft_examples"])
        )
        self.assertTrue(
            all(example["review_status"] == "draft_not_owner_reviewed" for example in echo_split["draft_examples"])
        )

    def test_tracked_guidance_dataset_validates_after_generation(self) -> None:
        dataset = read_json(DEFAULT_OUTPUT_PATH)

        errors = validate_studio_guidance_dataset(dataset=dataset, dataset_path=DEFAULT_OUTPUT_PATH)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
