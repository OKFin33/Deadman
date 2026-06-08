from __future__ import annotations

import unittest

from Deadman.tools.ars.deadman_build_v04_authoring_proof import (
    DEFAULT_GOLD_MOMENT_ID,
    DEFAULT_MOMENTS_PATH,
    DEFAULT_NON_GOLD_MOMENT_ID,
    DEFAULT_OUTPUT_PATH,
    MockMomentPackDraftProvider,
    build_authoring_proof,
    load_moments,
    read_json,
)
from Deadman.tools.ars.deadman_validate_v04_authoring_proof import validate_authoring_proof


class V04AuthoringProofTests(unittest.TestCase):
    def test_tracked_authoring_proof_validates(self) -> None:
        proof = read_json(DEFAULT_OUTPUT_PATH)

        errors = validate_authoring_proof(proof)

        self.assertEqual(errors, [])
        roles = {run["run_role"] for run in proof["runs"]}
        self.assertIn("ep03_gold_smoke", roles)
        self.assertIn("non_gold_authoring_proof", roles)
        non_gold = next(run for run in proof["runs"] if run["run_role"] == "non_gold_authoring_proof")
        self.assertEqual(non_gold["moment_id"], DEFAULT_NON_GOLD_MOMENT_ID)
        self.assertFalse(non_gold["is_gold_reference"])
        self.assertEqual(non_gold["final_status"]["published_review_status"], "reviewed")

    def test_builder_keeps_non_gold_proof_separate_from_ep03_smoke(self) -> None:
        proof = build_authoring_proof(
            moments=load_moments(DEFAULT_MOMENTS_PATH),
            provider=MockMomentPackDraftProvider(),
            gold_moment_id=DEFAULT_GOLD_MOMENT_ID,
            non_gold_moment_id=DEFAULT_NON_GOLD_MOMENT_ID,
            created_at="2026-06-06T00:00:00Z",
        )

        errors = validate_authoring_proof(proof)

        self.assertEqual(errors, [])
        self.assertEqual(proof["proof_status"], "pass")
        self.assertTrue(proof["authoring_runtime"]["provider"]["mock_provider"])
        self.assertIn("not a live external LLM/CAB provider claim", proof["authoring_runtime"]["claim_boundary"])
        moment_ids = {run["moment_id"] for run in proof["runs"]}
        self.assertEqual(moment_ids, {DEFAULT_GOLD_MOMENT_ID, DEFAULT_NON_GOLD_MOMENT_ID})


if __name__ == "__main__":
    unittest.main()
