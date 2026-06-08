from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from Deadman.backend.api import LOCAL_MEDIA_ROOT, create_app, _safe_local_media_path
from Deadman.backend.judgment import CabRuntimeJudgmentService
from Deadman.backend.pack_store import DeadmanPackStore
from Deadman.backend.runtime_client import CabRuntimeResult, RuntimeClientError


class DeadmanJudgmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine_patch = patch.dict("os.environ", {"DEADMAN_JUDGMENT_ENGINE": "demo_deterministic"})
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.client = TestClient(create_app())

    def test_health_and_catalog_load_huangnian(self) -> None:
        health = self.client.get("/api/deadman/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertIn("huangnian", health.json()["dramas"])
        self.assertIn("media", health.json())
        self.assertIn("deployment_ready", health.json()["media"])
        self.assertIn("DEADMAN_MEDIA_BASE_URL", health.json()["media"]["requirement"])
        self.assertEqual(health.json()["judgment"]["engine"], "demo_deterministic")
        self.assertFalse(health.json()["judgment"]["formal_runtime_enabled"])
        self.assertIn("DEADMAN_JUDGMENT_ENGINE=cab_runtime", health.json()["judgment"]["requirement"])

        dramas = self.client.get("/api/deadman/dramas")
        self.assertEqual(dramas.status_code, 200)
        ids = {item["drama_id"] for item in dramas.json()}
        self.assertIn("huangnian", ids)

        detail = self.client.get("/api/deadman/dramas/huangnian")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["drama_id"], "huangnian")
        self.assertIn("core_constraints", body["context"])
        self.assertEqual(body["manifest_summary"]["moment_packs"]["count"], 5)
        self.assertEqual(
            body["manifest_summary"]["ingestion_status"]["producer_media_registry"],
            "implemented_local_registry_v0.1",
        )

        media = self.client.get("/api/deadman/dramas/huangnian/media-registry")
        self.assertEqual(media.status_code, 200)
        self.assertEqual(media.json()["schema_version"], "deadman_media_registry.v0.1")
        self.assertGreaterEqual(media.json()["episode_count"], 5)
        self.assertNotIn("producer_media", self._json_text(media.json()))
        self.assertNotIn("tmp/", self._json_text(media.json()))
        self.assertNotIn("/@fs/", self._json_text(media.json()))

    def test_deployment_entrypoint_mounts_deadman_api(self) -> None:
        from server import app as deployed_app

        client = TestClient(deployed_app)
        response = client.get("/api/deadman/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("huangnian", response.json()["dramas"])

    def test_local_vite_dev_ports_are_allowed_by_cors(self) -> None:
        response = self.client.options(
            "/api/deadman/judgment",
            headers={
                "Origin": "http://127.0.0.1:5176",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:5176")

        localhost_response = self.client.options(
            "/api/deadman/judgment",
            headers={
                "Origin": "http://localhost:5199",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(localhost_response.status_code, 200)
        self.assertEqual(localhost_response.headers["access-control-allow-origin"], "http://localhost:5199")

        blocked = self.client.options(
            "/api/deadman/judgment",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertNotIn("access-control-allow-origin", blocked.headers)

    def test_registered_tmp_media_path_resolves_under_deadman_tmp(self) -> None:
        media_path = _safe_local_media_path("tmp/视频素材/荒年/第12集.mp4")
        self.assertIsNotNone(media_path)
        assert media_path is not None
        self.assertTrue(media_path.is_relative_to(LOCAL_MEDIA_ROOT))
        self.assertEqual(media_path.name, "第12集.mp4")

    def test_moment_lookup_returns_summaries_and_full_pack(self) -> None:
        moments = self.client.get("/api/deadman/dramas/huangnian/moments")
        self.assertEqual(moments.status_code, 200)
        body = moments.json()
        self.assertEqual(len(body), 5)
        self.assertEqual(body[0]["drama_id"], "huangnian")
        self.assertIn("default_options", body[0])
        self.assertEqual(body[0]["mouthpiece_candidates_schema_version"], "mouthpiece_candidates.v0.1")
        self.assertEqual(len(body[0]["mouthpiece_candidates"]), 3)
        self.assertEqual(body[0]["mouthpiece_candidates"][0]["candidate_id"], "preset_0")
        self.assertEqual(body[0]["mouthpiece_candidates"][0]["display_text"], "四蛋该吃肉")
        self.assertEqual(
            body[0]["mouthpiece_candidates"][0]["action_payload"]["text"],
            "今晚分兔肉，先让四蛋确认自己也有份",
        )
        self.assertIn("interaction_window", body[0])
        self.assertIn("result_media", body[0])
        self.assertRegex(
            body[0]["source_drama"]["runtime_video_url"],
            r"^(/api/deadman/media/huangnian/huangnian_ep|https?://)",
        )
        self.assertEqual(body[0]["interaction_window"]["source"], "reviewed_ars")
        self.assertEqual(len(body[0]["result_media"]["preset_options"]), 3)

        full = self.client.get("/api/deadman/dramas/huangnian/moments/huangnian_ep12_m001")
        self.assertEqual(full.status_code, 200)
        self.assertEqual(full.json()["moment_id"], "huangnian_ep12_m001")
        self.assertIn("local_constraints", full.json())
        self.assertIn("source_refs", full.json())
        self.assertNotIn("producer_refs", full.json())
        self.assertNotIn("tmp/", self._json_text(full.json()))

    def test_promoted_pack_has_windows_and_runtime_safe_refs(self) -> None:
        moments = self.client.get("/api/deadman/dramas/huangnian/moments").json()
        self.assertEqual(len(moments), 5)
        for summary in moments:
            window = summary["interaction_window"]
            self.assertLessEqual(window["notice_at_seconds"], window["start_seconds"])
            self.assertLessEqual(window["start_seconds"], window["end_seconds"])
            self.assertGreaterEqual(window["end_seconds"] - window["start_seconds"], 8)
            self.assertLessEqual(window["end_seconds"] - window["start_seconds"], 30)

            full = self.client.get(
                f"/api/deadman/dramas/huangnian/moments/{summary['moment_id']}"
            ).json()
            self.assertNotIn("tmp/", self._json_text(full["source_refs"]))
            self.assertNotIn("tmp/", self._json_text(full["source_window"]))
            self.assertNotIn("producer_refs", full)

        detail = self.client.get("/api/deadman/dramas/huangnian").json()
        self.assertNotIn("tmp/", self._json_text(detail["context"]))
        self.assertNotIn("tmp/", self._json_text(detail["manifest_summary"]))

    def test_preset_judgment_returns_structured_result(self) -> None:
        payload = {
            "drama_id": "huangnian",
            "moment_id": "huangnian_ep12_m001",
            "action": {
                "source": "preset",
                "text": "今晚分兔肉，先让四蛋确认自己也有份",
                "option_index": 0,
            },
            "viewer_profile": {"tone": "friend", "risk_preference": "balanced"},
        }
        response = self.client.post("/api/deadman/judgment", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["drama_id"], "huangnian")
        self.assertEqual(body["moment_id"], "huangnian_ep12_m001")
        self.assertEqual(body["engine"]["mode"], "demo_deterministic")
        self.assertIn(body["verdict"]["stance"], {"support", "caution"})
        self.assertEqual(body["canon_anchor"]["safe_to_continue"], True)
        self.assertIn("原剧情把兔子处理成家人信任修复的一步", body["canon_anchor"]["original_plot_note"])
        self.assertIn("爽度", body["scores"])
        self.assertIn("judgment_basis", body)
        self.assertEqual(body["aggregate_stats"]["mode"], "demo_static")
        self.assertEqual(sum(choice["percent"] for choice in body["aggregate_stats"]["choices"]), 100)
        self.assertTrue(body["aggregate_stats"]["choices"][0]["selected"])
        self.assertNotIn("adapter_input", body)
        self.assertNotIn("debug", body)
        self.assertEqual(body["media"]["status"], "placeholder")
        self.assertEqual(body["media"]["image_url"], "")
        self.assertIn("option 0", body["media"]["prompt"])
        self.assertNotIn("tmp/", self._json_text(body["judgment_basis"]["evidence_refs"]))

    def test_overpowered_custom_action_is_softened(self) -> None:
        payload = {
            "drama_id": "huangnian",
            "moment_id": "huangnian_ep03_m001",
            "action": {
                "source": "custom",
                "text": "直接公开系统，一键暴富，让后面全部剧情改写",
            },
            "viewer_profile": {"tone": "friend", "risk_preference": "bold"},
        }
        response = self.client.post("/api/deadman/judgment", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["verdict"]["stance"], "reject_softly")
        self.assertTrue(body["canon_anchor"]["safe_to_continue"])
        self.assertEqual(body["consequence"]["watch_flow_fit"], "low")
        self.assertIn("野菜/最后一点吃的", body["consequence"]["text"])
        self.assertIn("不把系统、后续剧集", body["consequence"]["text"])
        self.assertNotIn("system can convert", body["consequence"]["text"])
        self.assertNotIn("keep hidden", body["consequence"]["text"])
        self.assertEqual(body["media"]["status"], "not_available")
        self.assertIn("文字后果", body["media"]["fallback_text"])
        self.assertFalse(any(choice["selected"] for choice in body["aggregate_stats"]["choices"]))
        self.assertTrue(any("softened" in note for note in body["judgment_basis"]["inference_notes"]))
        self.assertTrue(any("exceeds local evidence" in warning for warning in body["judgment_basis"]["warnings"]))

    def test_invalid_moment_returns_structured_error(self) -> None:
        payload = {
            "drama_id": "huangnian",
            "moment_id": "not_real",
            "action": {
                "source": "custom",
                "text": "先稳住眼前人",
            },
        }
        response = self.client.post("/api/deadman/judgment", json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "moment_not_found")
        self.assertEqual(response.json()["error"]["retryable"], False)

    def test_invalid_preset_option_returns_structured_422(self) -> None:
        payload = {
            "drama_id": "huangnian",
            "moment_id": "huangnian_ep12_m001",
            "action": {
                "source": "preset",
                "text": "今晚分兔肉，先让四蛋确认自己也有份",
                "option_index": 99,
            },
        }
        response = self.client.post("/api/deadman/judgment", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "preset_option_invalid")

    def test_preset_candidate_judgment_verifies_reviewed_payload(self) -> None:
        moments = self.client.get("/api/deadman/dramas/huangnian/moments").json()
        candidate = moments[0]["mouthpiece_candidates"][0]
        payload = {
            "drama_id": "huangnian",
            "moment_id": "huangnian_ep12_m001",
            "action": {
                "source": "preset_candidate",
                "candidate_id": candidate["candidate_id"],
                "text": candidate["display_text"],
                "action_payload": candidate["action_payload"],
            },
        }

        response = self.client.post("/api/deadman/judgment", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["action"]["source"], "preset_candidate")
        self.assertEqual(body["action"]["candidate_id"], "preset_0")
        self.assertEqual(body["action"]["text"], "四蛋该吃肉")
        self.assertTrue(body["aggregate_stats"]["choices"][0]["selected"])

        bad_payload = {
            **payload,
            "action": {
                **payload["action"],
                "action_payload": {
                    **candidate["action_payload"],
                    "intent": "client_forged_intent",
                },
            },
        }
        bad_response = self.client.post("/api/deadman/judgment", json=bad_payload)
        self.assertEqual(bad_response.status_code, 422)
        self.assertEqual(bad_response.json()["error"]["code"], "preset_candidate_payload_mismatch")

    def _json_text(self, value: Any) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)


class DeadmanCabRuntimeJudgmentApiTests(unittest.TestCase):
    def test_unset_engine_defaults_to_cab_runtime(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            client = TestClient(create_app(store=DeadmanPackStore()))

        response = client.get("/api/deadman/health")
        self.assertEqual(response.status_code, 200)
        judgment = response.json()["judgment"]
        self.assertEqual(judgment["engine"], "cab_runtime")
        self.assertTrue(judgment["formal_runtime_enabled"])
        self.assertFalse(judgment["demo_deterministic_enabled"])
        self.assertIn("cab_runtime_config_valid", judgment)

    def test_health_reports_cab_runtime_readiness_when_engine_enabled(self) -> None:
        with patch.dict("os.environ", {"DEADMAN_JUDGMENT_ENGINE": "cab_runtime"}):
            client = TestClient(create_app(store=DeadmanPackStore()))

        response = client.get("/api/deadman/health")
        self.assertEqual(response.status_code, 200)
        judgment = response.json()["judgment"]
        self.assertEqual(judgment["engine"], "cab_runtime")
        self.assertTrue(judgment["formal_runtime_enabled"])
        self.assertFalse(judgment["demo_deterministic_enabled"])
        self.assertIn("cab_runtime_config_valid", judgment)
        if judgment["cab_runtime_config_valid"]:
            self.assertIn("cab_project", judgment)
        else:
            self.assertIn("cab_runtime_error", judgment)

    def test_cab_runtime_service_returns_existing_public_response_shape(self) -> None:
        runtime_client = FakeRuntimeClient(
            {
                "request_id": "huangnian:huangnian_ep12_m001:preset:0",
                "verdict": "credible_costly_win",
                "result_text": "这一口兔肉能成立，但只能落在当前这顿饭里。",
                "companion_reaction": "这步可以，爽点是四蛋这一刻被看见。",
                "why_this_happens": ["当前场景证据足够支撑局部关系修复。"],
                "time_horizon": "current_scene_or_immediate_aftermath",
                "watch_flow_rationale": "结果只按当前场景证据判定，不生成后续分支。",
                "used_fields": ["companion_entry", "source_ref:huangnian_ep12_u001"],
                "blocked_claims": [
                    "future episodes follow this branch",
                    "canon was wrong",
                    "the branch continues automatically",
                    "generated images prove branch facts",
                    "producer-only scores are viewer evidence",
                ],
                "visual_result_plan": {
                    "mode": "preset_slot",
                    "truth_level": "illustrative_result",
                    "proof_eligibility": "never",
                    "must_not_be_used_as_proof": True,
                    "fallback": "placeholder_slot",
                    "latency_budget_ms": 0,
                    "provider_policy": "not_connected",
                    "preset_slot_id": "preset_0",
                    "visual_prompt_plan": {
                        "prompt_source": "preset",
                        "prompt_text": "",
                        "negative_constraints": [],
                        "style_policy": "short_drama_result_card",
                        "provider_policy": "not_connected",
                    },
                },
                "engine_metadata": {
                    "mode": "deterministic",
                    "schema_version": "deadman_judgment_adapter_output.v0.1",
                    "provider": "fake-test",
                },
            }
        )
        store = DeadmanPackStore()
        client = TestClient(
            create_app(
                store=store,
                judgment_service=CabRuntimeJudgmentService(store, runtime_client=runtime_client),
            )
        )

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
        self.assertEqual(body["engine"]["mode"], "cab_runtime")
        self.assertEqual(body["engine"]["schema_version"], "deadman_judgment_adapter_output.v0.1")
        self.assertEqual(body["aggregate_stats"], None)
        self.assertEqual(body["media"]["status"], "placeholder")
        self.assertEqual(body["verdict"]["stance"], "support")
        self.assertNotIn("adapter_input", body)
        self.assertNotIn("debug", body)
        self.assertNotIn("score_axes", self._json_text(body))
        self.assertEqual(runtime_client.adapter_input["runtime_policy"]["allow_future_branch_claims"], False)

    def test_cab_runtime_failure_is_structured_error_without_demo_fallback(self) -> None:
        store = DeadmanPackStore()
        client = TestClient(
            create_app(
                store=store,
                judgment_service=CabRuntimeJudgmentService(store, runtime_client=FailingRuntimeClient()),
            )
        )

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

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(body["error"]["code"], "cab_worker_timeout")
        self.assertEqual(body["error"]["retryable"], True)
        self.assertNotIn("demo_deterministic", self._json_text(body))
        self.assertNotIn("worker_response", self._json_text(body))
        self.assertNotIn("session_payload", self._json_text(body))
        self.assertNotIn("raw_stdout", self._json_text(body))
        self.assertNotIn("raw_stderr", self._json_text(body))

    def test_cab_runtime_bad_root_is_structured_error_without_demo_fallback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DEADMAN_JUDGMENT_ENGINE": "cab_runtime",
                "DEADMAN_CAB_RUNTIME_ROOT": "/tmp/missing-deadman-cab-runtime-root",
            },
        ):
            client = TestClient(create_app(store=DeadmanPackStore()))
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

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(body["error"]["code"], "cab_runtime_root_invalid")
        self.assertEqual(body["error"]["retryable"], False)
        self.assertNotIn("demo_deterministic", self._json_text(body))

    def test_cab_runtime_bad_timeout_is_structured_error_without_demo_fallback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DEADMAN_JUDGMENT_ENGINE": "cab_runtime",
                "DEADMAN_CAB_RUNTIME_TIMEOUT_SECONDS": "not-an-int",
            },
        ):
            client = TestClient(create_app(store=DeadmanPackStore()))
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

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(body["error"]["code"], "cab_runtime_config_invalid")
        self.assertEqual(body["error"]["retryable"], False)
        self.assertNotIn("demo_deterministic", self._json_text(body))

    def _json_text(self, value: Any) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)


class FakeRuntimeClient:
    def __init__(self, adapter_output: dict[str, Any]) -> None:
        self.adapter_output = adapter_output
        self.adapter_input: dict[str, Any] = {}

    def judge(self, adapter_input: dict[str, Any]) -> CabRuntimeResult:
        self.adapter_input = adapter_input
        return CabRuntimeResult(
            adapter_output=self.adapter_output,
            worker_response={"status": "ok"},
            session_payload={"status": "ok"},
        )


class FailingRuntimeClient:
    def judge(self, adapter_input: dict[str, Any]) -> CabRuntimeResult:
        raise RuntimeClientError("cab_worker_timeout", "CAB timed out.", retryable=True)


if __name__ == "__main__":
    unittest.main()
