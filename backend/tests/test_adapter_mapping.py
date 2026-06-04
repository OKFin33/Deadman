from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from Deadman.backend.adapter_mapping import (
    AdapterMappingError,
    build_adapter_input,
    build_typed_moment_pack,
)
from Deadman.backend.api import create_app
from Deadman.backend.models import JudgmentRequest, UserAction
from Deadman.backend.pack_store import DeadmanPackStore


class DeadmanAdapterMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine_patch = patch.dict("os.environ", {"DEADMAN_JUDGMENT_ENGINE": "demo_deterministic"})
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.store = DeadmanPackStore()
        self.pack = self.store.get_drama("huangnian")
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_all_promoted_huangnian_moments_map_to_v03_adapter_inputs(self) -> None:
        mapped = [
            self._adapter_input(moment, option_index=0)
            for moment in self.pack.moments_by_id.values()
        ]
        self.assertEqual(len(mapped), 5)
        for adapter_input in mapped:
            moment_pack = adapter_input["moment_pack"]
            self.assertEqual(moment_pack["schema_version"], "moment_causality_pack.v0.3.draft")
            self.assertEqual(adapter_input["runtime_policy"]["allow_future_branch_claims"], False)
            self.assertEqual(adapter_input["runtime_policy"]["allow_visual_as_proof"], False)
            self.assertEqual(adapter_input["runtime_policy"]["time_horizon"], "current_scene_or_immediate_aftermath")
            for key in (
                "source_window",
                "review_and_provenance",
                "companion_entry",
                "action_space",
                "response_contract",
                "visual_result_policy",
                "actor_local_state",
                "critical_stakes_state",
                "local_constraint_state",
                "escalation_risk",
                "canon_baseline",
                "watch_flow_rationale",
            ):
                self.assertIn(key, moment_pack)

            self.assertEqual(moment_pack["visual_result_policy"]["provider_policy"], "not_connected")
            self.assertEqual(
                moment_pack["visual_result_policy"]["visual_prompt_plan"]["provider_policy"],
                "not_connected",
            )
            self.assertEqual(moment_pack["visual_result_policy"]["must_not_be_used_as_proof"], True)
            self.assertEqual(moment_pack["visual_result_policy"]["proof_eligibility"], "never")

            self.assertTypedSubkeys(moment_pack["critical_stakes_state"], {
                "stake_type",
                "stake_owner",
                "time_pressure",
                "scarcity_or_risk_level",
                "irreversibility",
                "risk_if_action",
                "risk_if_no_action",
            })
            self.assertTypedSubkeys(moment_pack["escalation_risk"], {
                "risk_type",
                "risk_source",
                "immediacy",
                "severity",
                "mitigation",
                "who_can_escalate",
            })
            self.assertTypedSubkeys(moment_pack["watch_flow_rationale"], {
                "why_original_still_works",
                "viewer_return_line",
                "must_not_claim",
            })
            self.assertIn("future episodes follow this branch", moment_pack["watch_flow_rationale"]["must_not_claim"])
            self.assertIn("canon was wrong", moment_pack["watch_flow_rationale"]["must_not_claim"])
            self.assertIn("the branch continues automatically", moment_pack["watch_flow_rationale"]["must_not_claim"])

    def test_mapped_packs_validate_against_v03_json_schema(self) -> None:
        schema = json.loads(
            (self.repo_root / "data/schemas/moment_causality_pack.v0.3.draft.json").read_text()
        )
        validator = Draft202012Validator(schema)
        for moment in self.pack.moments_by_id.values():
            moment_pack = build_typed_moment_pack(drama_pack=self.pack, moment=moment)
            errors = sorted(validator.iter_errors(moment_pack), key=lambda error: list(error.path))
            self.assertEqual(
                errors,
                [],
                f"{moment_pack['pack_id']} schema errors: "
                + "; ".join(f"{list(error.path)} {error.message}" for error in errors[:5]),
            )

    def test_preset_action_maps_to_stable_preset_id(self) -> None:
        moment = self.pack.moments_by_id["huangnian_ep12_m001"]
        adapter_input = self._adapter_input(moment, option_index=2)
        self.assertEqual(adapter_input["user_action"]["origin"], "preset")
        self.assertEqual(adapter_input["user_action"]["preset_id"], "preset_2")
        self.assertEqual(adapter_input["requested_output"]["visual_result"], "preset_slot")
        self.assertEqual(
            adapter_input["moment_pack"]["action_space"]["preset_options"][2]["text"],
            "把兔子当成四蛋的功劳，只少量处理给全家尝味",
        )

    def test_custom_action_maps_without_future_branch_claims(self) -> None:
        moment = self.pack.moments_by_id["huangnian_ep03_m001"]
        request = JudgmentRequest(
            drama_id=self.pack.drama_id,
            moment_id=moment["moment_id"],
            action=UserAction(source="custom", text="先小范围试一下系统，不让旁人看见"),
        )
        adapter_input = build_adapter_input(
            request_id="test-custom",
            drama_pack=self.pack,
            moment=moment,
            request=request,
        )
        self.assertEqual(adapter_input["user_action"]["origin"], "custom")
        self.assertIsNone(adapter_input["user_action"]["preset_id"])
        self.assertEqual(adapter_input["requested_output"]["visual_result"], "plan_only")
        self.assertEqual(adapter_input["runtime_policy"]["allow_future_branch_claims"], False)
        self.assertIn("future episodes follow this branch", adapter_input["moment_pack"]["watch_flow_rationale"]["must_not_claim"])

    def test_missing_source_window_start_ms_fails_closed(self) -> None:
        moment = copy.deepcopy(self.pack.moments_by_id["huangnian_ep12_m001"])
        del moment["source_window"]["start_ms"]
        with self.assertRaises(AdapterMappingError) as raised:
            build_typed_moment_pack(drama_pack=self.pack, moment=moment)
        self.assertEqual(raised.exception.code, "adapter_mapping_invalid")
        self.assertIn("source_window.start_ms", raised.exception.message)

    def test_missing_critical_stakes_source_material_fails_closed(self) -> None:
        moment = copy.deepcopy(self.pack.moments_by_id["huangnian_ep12_m001"])
        moment.pop("optional_modules", None)
        moment.pop("actor_context", None)
        moment.pop("local_constraints", None)
        moment.pop("canon_baseline", None)
        with self.assertRaises(AdapterMappingError) as raised:
            build_typed_moment_pack(drama_pack=self.pack, moment=moment)
        self.assertEqual(raised.exception.code, "adapter_mapping_missing_stakes")

    def test_score_axes_are_producer_or_debug_only(self) -> None:
        moment = self.pack.moments_by_id["huangnian_ep04_m001"]
        adapter_input = self._adapter_input(moment, option_index=0)
        score_axes_paths = self._paths_for_key(adapter_input, "score_axes")
        self.assertEqual(
            sorted(score_axes_paths),
            sorted(["debug.score_axes", "moment_pack.producer_only.score_axes"]),
        )
        viewer_text = json.dumps(
            {
                "user_action": adapter_input["user_action"],
                "runtime_policy": adapter_input["runtime_policy"],
                "requested_output": adapter_input["requested_output"],
                "moment_pack_without_producer": {
                    key: value
                    for key, value in adapter_input["moment_pack"].items()
                    if key != "producer_only"
                },
            },
            ensure_ascii=False,
        )
        self.assertNotIn("score_axes", viewer_text)

    def test_public_judgment_api_keeps_existing_response_shape(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/api/deadman/judgment",
            json={
                "drama_id": "huangnian",
                "moment_id": "huangnian_ep12_m001",
                "action": {
                    "source": "preset",
                    "text": "今晚分兔肉，先让四蛋确认自己也有份",
                    "option_index": 0,
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {
                "drama_id",
                "moment_id",
                "action",
                "verdict",
                "consequence",
                "canon_anchor",
                "scores",
                "result_card",
                "media",
                "aggregate_stats",
                "judgment_basis",
                "engine",
            },
        )
        self.assertEqual(body["engine"]["mode"], "demo_deterministic")
        self.assertNotIn("adapter_input", body)
        self.assertNotIn("debug", body)

    def _adapter_input(self, moment: dict[str, Any], *, option_index: int) -> dict[str, Any]:
        option_text = moment["action_space"]["default_options"][option_index]
        request = JudgmentRequest(
            drama_id=self.pack.drama_id,
            moment_id=moment["moment_id"],
            action=UserAction(source="preset", text=option_text, option_index=option_index),
        )
        return build_adapter_input(
            request_id=f"test-{moment['moment_id']}-{option_index}",
            drama_pack=self.pack,
            moment=moment,
            request=request,
        )

    def assertTypedSubkeys(self, value: dict[str, Any], required: set[str]) -> None:
        self.assertTrue(required.issubset(value.keys()))
        for key in required:
            self.assertNotEqual(value[key], "")

    def _paths_for_key(self, value: Any, target_key: str, prefix: str = "") -> list[str]:
        paths: list[str] = []
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if key == target_key:
                    paths.append(path)
                paths.extend(self._paths_for_key(child, target_key, path))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                path = f"{prefix}.{index}" if prefix else str(index)
                paths.extend(self._paths_for_key(child, target_key, path))
        return paths


if __name__ == "__main__":
    unittest.main()
