from __future__ import annotations

import os
import unittest
from pathlib import Path

from Deadman.backend.adapter_mapping import build_adapter_input
from Deadman.backend.models import JudgmentRequest, UserAction
from Deadman.backend.pack_store import DeadmanPackStore
from Deadman.backend.runtime_client import CabRuntimeWorkerClient


RUN_CAB_INTEGRATION = os.environ.get("DEADMAN_RUN_CAB_RUNTIME_INTEGRATION") == "1"
CAB_PROJECT = Path(__file__).resolve().parents[4] / "CABRuntime" / "examples" / "v041-deadman-moment-judgment"


@unittest.skipUnless(RUN_CAB_INTEGRATION, "Set DEADMAN_RUN_CAB_RUNTIME_INTEGRATION=1 to run CABRuntime worker dogfood.")
class DeadmanCabRuntimeClientIntegrationTests(unittest.TestCase):
    def test_worker_client_returns_deadman_adapter_output_for_real_adapter_input(self) -> None:
        self.assertTrue(CAB_PROJECT.exists(), f"CAB project missing: {CAB_PROJECT}")
        store = DeadmanPackStore()
        pack = store.get_drama("huangnian")
        moment = pack.moments_by_id["huangnian_ep12_m001"]
        request = JudgmentRequest(
            drama_id="huangnian",
            moment_id="huangnian_ep12_m001",
            action=UserAction(
                source="preset",
                text="今晚分兔肉，先让四蛋确认自己也有份",
                option_index=0,
            ),
        )
        adapter_input = build_adapter_input(
            request_id="deadman-backend-dogfood-ep12-preset-0",
            drama_pack=pack,
            moment=moment,
            request=request,
        )

        result = CabRuntimeWorkerClient().judge(adapter_input)

        output = result.adapter_output
        self.assertEqual(output["request_id"], "deadman-backend-dogfood-ep12-preset-0")
        self.assertEqual(output["time_horizon"], "current_scene_or_immediate_aftermath")
        self.assertIn(output["verdict"], {"credible_win", "credible_costly_win", "mixed"})
        self.assertIn("future episodes follow this branch", output["blocked_claims"])
        self.assertEqual(output["visual_result_plan"]["proof_eligibility"], "never")
        self.assertEqual(result.session_payload["session_state_out"]["persisted_by_cab"], True)
        self.assertEqual(result.session_payload["session_state_out"]["host_should_persist"], True)
        self.assertEqual(result.persisted_by_cab, True)
        self.assertEqual(result.host_should_persist, True)

    def test_worker_client_softens_overpowered_custom_adapter_input(self) -> None:
        self.assertTrue(CAB_PROJECT.exists(), f"CAB project missing: {CAB_PROJECT}")
        store = DeadmanPackStore()
        pack = store.get_drama("huangnian")
        moment = pack.moments_by_id["huangnian_ep03_m001"]
        request = JudgmentRequest(
            drama_id="huangnian",
            moment_id="huangnian_ep03_m001",
            action=UserAction(
                source="custom",
                text="直接公开系统，一键暴富，让后面全部剧情改写",
            ),
        )
        adapter_input = build_adapter_input(
            request_id="deadman-backend-dogfood-ep03-custom-overpowered",
            drama_pack=pack,
            moment=moment,
            request=request,
        )

        result = CabRuntimeWorkerClient().judge(adapter_input)

        output = result.adapter_output
        self.assertEqual(output["request_id"], "deadman-backend-dogfood-ep03-custom-overpowered")
        self.assertEqual(output["verdict"], "invalid_or_overpowered")
        self.assertIn("不承诺后续剧情被改写", output["result_text"])
        self.assertIn("generated images prove branch facts", output["blocked_claims"])
        self.assertEqual(output["visual_result_plan"]["proof_eligibility"], "never")


if __name__ == "__main__":
    unittest.main()
