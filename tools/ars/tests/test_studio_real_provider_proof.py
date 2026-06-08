from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from Deadman.tools.ars.deadman_run_studio_real_provider_proof import (
    DEFAULT_GUIDANCE_PATH,
    build_real_provider_proof_report,
    read_json,
)
from Deadman.tools.ars.deadman_validate_studio_real_provider_proof import (
    validate_studio_real_provider_proof,
)


class FakeStudioProofProvider:
    name = "ark"
    model = "fake-real-provider"
    mock_provider = False

    _META = {
        "name": "ark",
        "model": "fake-real-provider",
        "mock_provider": False,
        "latency_ms": 1200,
        "token_usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }

    def complete_case(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        if prompt.get("stage") == "stage_b_echo":
            viewer = prompt.get("this_viewer", {}) if isinstance(prompt.get("this_viewer"), dict) else {}
            motivation = str(viewer.get("viewer_motivation") or "")
            return {
                "payload": {
                    "case_id": prompt.get("case_id"),
                    "selected_echo": f"懂你这点，{motivation[:8]}，这段确实戳人。",
                    "echo_rationale": "answer this viewer",
                },
                "provider": dict(self._META),
            }
        case = prompt["case"]
        if case["case_type"] == "owner_reviewed_window_reject":
            payload = {
                "case_id": case["case_id"],
                "window_decision": "reject_window",
                "companion_lead": "",
                "reply_candidates": [],
                "failure_buckets": [],
                "rationale_summary": "Owner boundary says this window should not open.",
                "repair_notes": [],
            }
        else:
            payload = {
                "case_id": case["case_id"],
                "window_decision": "recommend_window",
                "companion_lead": "这一下挺有戏。",
                "reply_candidates": [
                    {
                        "display_text": "这人设确实有点离谱",
                        "emotion_role": "viewer_callout",
                        "semantic_role": "persona_callout",
                        "viewer_motivation": "想吐槽原主，盼搭子接梗",
                    },
                    {
                        "display_text": "现在就看她怎么圆",
                        "emotion_role": "viewer_watch",
                        "semantic_role": "watch_flow",
                        "viewer_motivation": "好奇接下来怎么发展",
                    },
                    {
                        "display_text": "这段节奏挺短剧",
                        "emotion_role": "viewer_genre",
                        "semantic_role": "genre_read",
                        "viewer_motivation": "老剧迷想确认爽点",
                    },
                ],
                "failure_buckets": [],
                "rationale_summary": "Scene-bound viewer reaction with three short replies.",
                "repair_notes": [],
            }
        return {"payload": payload, "provider": dict(self._META)}


class BadShapeProvider(FakeStudioProofProvider):
    def complete_case(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        if prompt.get("stage") == "stage_b_echo":
            return {
                "payload": {
                    "case_id": prompt.get("case_id"),
                    "selected_echo": "",
                    "echo_rationale": "",
                },
                "provider": dict(self._META),
            }
        case = prompt["case"]
        return {
            "payload": {
                "case_id": case["case_id"],
                "window_decision": "recommend_window",
                "companion_lead": "你是不是想说这段该不该改？",
                "reply_candidates": [
                    {
                        "display_text": "吐槽原主吃独食",
                        "emotion_role": "axis",
                        "semantic_role": "axis",
                        "viewer_motivation": "axis-shaped, not a viewer voice",
                    }
                ],
                "failure_buckets": [],
                "rationale_summary": "Bad shape fixture.",
                "repair_notes": [],
            },
            "provider": dict(self._META),
        }


class StudioRealProviderProofTests(unittest.TestCase):
    def test_fake_provider_report_passes_contract(self) -> None:
        guidance = read_json(DEFAULT_GUIDANCE_PATH)
        report = build_real_provider_proof_report(
            guidance=guidance,
            guidance_path=DEFAULT_GUIDANCE_PATH,
            provider=FakeStudioProofProvider(),
            created_at="2026-06-07T00:00:00Z",
        )

        errors = validate_studio_real_provider_proof(
            proof=report,
            proof_path=Path("data/evals/studio_cab_real_provider_proof.v0.1.json"),
        )

        self.assertEqual(errors, [])
        self.assertEqual(report["planned_case_count"], 8)
        self.assertEqual(report["attempted_case_count"], 8)
        self.assertEqual(report["completed_case_count"], 8)
        self.assertEqual(report["publication_decision"], "no_runtime_promotion")
        self.assertTrue(
            all(case["draft_review_status"] == "draft_not_owner_reviewed" for case in report["case_results"])
        )

    def test_bad_provider_output_is_compressed_into_repair_candidates(self) -> None:
        guidance = read_json(DEFAULT_GUIDANCE_PATH)
        report = build_real_provider_proof_report(
            guidance=guidance,
            guidance_path=DEFAULT_GUIDANCE_PATH,
            provider=BadShapeProvider(),
            created_at="2026-06-07T00:00:00Z",
            case_limit=1,
        )

        errors = validate_studio_real_provider_proof(
            proof=report,
            proof_path=Path("tmp/test_studio_cab_real_provider_proof.v0.1.json"),
        )

        self.assertEqual(errors, [])
        buckets = set(report["case_results"][0]["failure_buckets"])
        self.assertIn("wrong_lead_shape", buckets)
        self.assertIn("wrong_reply_shape", buckets)
        self.assertTrue(report["repair_candidates"])
        self.assertTrue(
            all(repair["provenance"] == "real_provider_proof" for repair in report["repair_candidates"])
        )


if __name__ == "__main__":
    unittest.main()
