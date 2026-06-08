from __future__ import annotations

import unittest

from Deadman.tools.ars.deadman_build_phase2_eval import (
    DEFAULT_WINDOW_TASTE_PATH,
    EXCHANGE_REPAIR_OUTPUT_PATH,
    PHASE2_EVAL_OUTPUT_PATH,
    build_phase2_outputs,
    read_json,
)
from Deadman.tools.ars.deadman_validate_phase2_eval import validate_phase2_artifacts


class Phase2EvalTests(unittest.TestCase):
    def test_builder_outputs_pass_phase2_contract(self) -> None:
        dataset = read_json(DEFAULT_WINDOW_TASTE_PATH)

        result = build_phase2_outputs(
            dataset=dataset,
            dataset_path=DEFAULT_WINDOW_TASTE_PATH,
            created_at="2026-06-07T00:00:00Z",
        )

        errors = validate_phase2_artifacts(
            window_report=result["window_judge_report"],
            exchange_report=result["exchange_report"],
            phase2_eval=result["phase2_eval"],
            exchange_repairs=result["exchange_repair_candidates"],
        )
        self.assertEqual(errors, [])
        self.assertEqual(result["window_judge_report"]["acceptance_gate"]["status"], "pass")
        self.assertEqual(result["exchange_report"]["acceptance_gate"]["status"], "pass")
        self.assertFalse(result["phase2_eval"]["review_gates"]["gate_a"]["needed"])
        self.assertFalse(result["phase2_eval"]["review_gates"]["gate_b"]["needed"])

    def test_exchange_authoring_repairs_raw_seed_axis_labels_without_promotion(self) -> None:
        dataset = read_json(DEFAULT_WINDOW_TASTE_PATH)

        result = build_phase2_outputs(
            dataset=dataset,
            dataset_path=DEFAULT_WINDOW_TASTE_PATH,
            created_at="2026-06-07T00:00:00Z",
        )

        repairs = result["exchange_repair_candidates"]["items"]
        failure_types = {repair["failure_type"] for repair in repairs}
        self.assertIn("axis_label_no_viewer_voice", failure_types)
        self.assertIn("question_shaped_lead_seed", failure_types)

        phase2_eval = result["phase2_eval"]
        self.assertEqual(
            phase2_eval["goal_gate_summary"]["runtime_pack_promotion"],
            "not_performed_phase3_only",
        )
        self.assertGreaterEqual(len(phase2_eval["phase3_demo_pack_candidates"]), 3)
        self.assertLessEqual(len(phase2_eval["phase3_demo_pack_candidates"]), 5)
        self.assertTrue(
            all(
                candidate["promotion_status"] == "nominated_only_not_promoted"
                for candidate in phase2_eval["phase3_demo_pack_candidates"]
            )
        )

    def test_tracked_phase2_outputs_validate_after_generation(self) -> None:
        window_report = read_json(PHASE2_EVAL_OUTPUT_PATH.parent / "window_taste_phase2_judge_report.v0.1.json")
        exchange_report = read_json(PHASE2_EVAL_OUTPUT_PATH.parent / "studio_cab_exchange_authoring_phase2.v0.1.json")
        phase2_eval = read_json(PHASE2_EVAL_OUTPUT_PATH)
        exchange_repairs = read_json(EXCHANGE_REPAIR_OUTPUT_PATH) if EXCHANGE_REPAIR_OUTPUT_PATH.exists() else None

        errors = validate_phase2_artifacts(
            window_report=window_report,
            exchange_report=exchange_report,
            phase2_eval=phase2_eval,
            exchange_repairs=exchange_repairs,
        )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
