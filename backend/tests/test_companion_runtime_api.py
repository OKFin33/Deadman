from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from Deadman.backend.api import create_app
from Deadman.backend.judgment import CabRuntimeJudgmentService, DeterministicJudgmentService
from Deadman.backend.models import JudgmentRequest, JudgmentResponse
from Deadman.backend.pack_store import DeadmanPackStore, PackStoreError
from Deadman.backend.runtime_client import CabRuntimeResult


DRAMA_ID = "huangnian"
MOMENT_ID = "huangnian_ep12_m001"
ACTION_TEXT = "今晚分兔肉，先让四蛋确认自己也有份"
EP03_MOMENT_ID = "huangnian_ep03_m001"
EP07_MOMENT_ID = "huangnian_ep07_m001"
EP07_ACTION_TEXT = "当场让儿媳上桌，直接推翻旧规矩"


class CompanionRuntimeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine_patch = patch.dict("os.environ", {"DEADMAN_JUDGMENT_ENGINE": "demo_deterministic"})
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.store = DeadmanPackStore()
        self.client = TestClient(create_app(store=self.store))

    def test_session_start_and_notice_and_tap_are_headless_runtime_events(self) -> None:
        start = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start", playback_time_seconds=0),
        )
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.json()["status"], "ok")
        self.assertEqual(start.json()["companion"]["next_state"], "idle")
        self.assertEqual(start.json()["engine"]["cab_session_id"], "deadman-viewer-test-session")

        notice = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("moment_notice", event_id="evt-notice", playback_time_seconds=15),
        )
        self.assertEqual(notice.status_code, 200)
        self.assertEqual(notice.json()["status"], "ok")
        self.assertEqual(notice.json()["companion"]["next_state"], "notice_exclaim")
        self.assertFalse(notice.json()["companion"]["should_interrupt"])
        self.assertEqual(notice.json()["moment"]["default_options"][0], ACTION_TEXT)
        self.assertEqual(notice.json()["moment"]["mouthpiece_candidates_schema_version"], "mouthpiece_candidates.v0.1")
        self.assertEqual(notice.json()["moment"]["mouthpiece_candidates"][0]["display_text"], "四蛋该吃肉")

        tap = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("companion_tap", event_id="evt-tap", playback_time_seconds=15),
        )
        self.assertEqual(tap.status_code, 200)
        self.assertEqual(tap.json()["status"], "ok")
        self.assertEqual(tap.json()["companion"]["next_state"], "stand_bubble")
        self.assertEqual(tap.json()["moment"]["default_options"][0], ACTION_TEXT)
        self.assertEqual(tap.json()["moment"]["mouthpiece_candidates"][0]["candidate_id"], "preset_0")

    def test_user_action_returns_single_narrative_result_surface(self) -> None:
        self._start_session()
        candidate_action = self._candidate_action()
        response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-action",
                playback_time_seconds=5,
                action=candidate_action,
            ),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["judgment"]["action"]["source"], "preset_candidate")
        self.assertEqual(body["judgment"]["action"]["candidate_id"], "preset_0")
        self.assertEqual(body["companion"]["next_state"], "verdict")
        self.assertEqual(body["result_surface"]["mode"], "single_narrative")
        self.assertEqual(body["result_surface"]["continue_label"], "继续看")
        self.assertFalse(body["result_surface"]["text"].startswith("这手可以，"))
        self.assertFalse(body["result_surface"]["text"].startswith("这想法够猛"))
        self.assertFalse(body["result_surface"]["text"].startswith("这手能聊"))
        self.assertTrue(
            any(token in body["result_surface"]["text"] for token in ("这顿饭", "孩子", "荒年")),
            body["result_surface"]["text"],
        )
        self.assertEqual(body["result_surface"]["micro_cue"]["kind"], "aggregate_hint")
        self.assertRegex(body["result_surface"]["micro_cue"]["text"], r"有\d+%其他观众也这么想。")
        self.assertTrue(body["session_memory"]["safe_to_reference"])
        self.assertNotIn("verdict", body["result_surface"])
        self.assertNotIn("原剧情", self._json_text(body["result_surface"]))
        self.assertNotIn("后面剧集", self._json_text(body["result_surface"]))
        self.assertIn("judgment", body)

    def test_humiliation_moment_uses_scene_specific_result_surface(self) -> None:
        self._start_session()
        event = self._event(
            "user_action",
            event_id="evt-ep07-action",
            playback_time_seconds=21,
            action={"source": "preset", "text": EP07_ACTION_TEXT, "option_index": 0},
        )
        event["episode_id"] = "huangnian_ep07"
        event["moment_id"] = EP07_MOMENT_ID

        response = self.client.post("/api/deadman/runtime/session/event", json=event)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        text = body["result_surface"]["text"]
        self.assertLessEqual(len(text), 64)
        self.assertIn("羞辱", self._json_text(body["judgment"]))
        self.assertIn("底线", text)
        self.assertNotIn("单纯资源", self._json_text(body["result_surface"]))
        self.assertNotIn("关...", text)

    def test_cab_runtime_result_surface_uses_judgment_reaction_not_local_lead_bank(self) -> None:
        runtime_client = FakeCabRuntimeClient(
            {
                "request_id": "huangnian:huangnian_ep07_m001:preset:0",
                "verdict": "credible_costly_win",
                "result_text": "当场让儿媳上桌可以成立，但要先护住人，再给桌上其他人留台阶。",
                "companion_reaction": "这不是桌规小事，是先把儿媳从这口气里护出来。",
                "why_this_happens": ["CABRuntime used the humiliation moment fields."],
                "time_horizon": "current_scene_or_immediate_aftermath",
                "watch_flow_rationale": "结果只解释当前场景。",
                "used_fields": ["companion_entry", "critical_stakes_state"],
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
        client = TestClient(
            create_app(
                store=self.store,
                judgment_service=CabRuntimeJudgmentService(self.store, runtime_client=runtime_client),
            )
        )
        client.post("/api/deadman/runtime/session/event", json=self._event("session_start", event_id="evt-start-cab"))
        event = self._event(
            "user_action",
            event_id="evt-ep07-cab-action",
            playback_time_seconds=21,
            action={"source": "preset", "text": EP07_ACTION_TEXT, "option_index": 0},
        )
        event["episode_id"] = "huangnian_ep07"
        event["moment_id"] = EP07_MOMENT_ID

        response = client.post("/api/deadman/runtime/session/event", json=event)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["judgment"]["engine"]["mode"], "cab_runtime")
        self.assertEqual(body["result_surface"]["text"], "这不是桌规小事，是先把儿媳从这口气里护出来。")
        self.assertIsNone(body["result_surface"]["micro_cue"])
        self.assertNotIn("这种羞辱不能干看着", body["result_surface"]["text"])

    def test_custom_action_defaults_to_no_micro_cue_and_sanitizes_disclaimers(self) -> None:
        self._start_session()
        response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-custom",
                playback_time_seconds=5,
                action={"source": "custom", "text": "直接公开系统，一键暴富，让后面全部剧情改写"},
            ),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        text = body["result_surface"]["text"]
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["result_surface"]["micro_cue"]["kind"], "cost_hint")
        self.assertIn("系统那口气", text)
        self.assertIn("这段先别替剧情往后编", text)
        self.assertNotIn("后面剧集", text)
        self.assertNotIn("未来分支", text)
        self.assertNotIn("原剧情", text)
        self.assertNotIn("分支剧情", text)
        self.assertNotIn("policy", self._json_text(body["result_surface"]).lower())
        self.assertNotIn("CAB", self._json_text(body["result_surface"]))

    def test_custom_action_echoes_specific_ep03_feeling(self) -> None:
        self._start_session()
        event = self._event(
            "user_action",
            event_id="evt-ep03-custom-specific",
            playback_time_seconds=5,
            action={"source": "custom", "text": "孩子都怕成这样了，别再把最后一口野菜送走了"},
        )
        event["episode_id"] = "huangnian_ep03"
        event["moment_id"] = EP03_MOMENT_ID

        response = self.client.post("/api/deadman/runtime/session/event", json=event)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        text = body["result_surface"]["text"]
        self.assertEqual(body["status"], "ok")
        self.assertIn("孩子", text)
        self.assertIn("最后这口", text)
        self.assertNotEqual(text, "这句我懂，但这段先别替剧情往后编。")
        self.assertIsNone(body["result_surface"]["micro_cue"])
        self.assertNotIn("当前场景", text)
        self.assertNotIn("后面剧集", text)
        self.assertNotIn("CAB", self._json_text(body["result_surface"]))

    def test_custom_action_uses_fallback_only_when_ungrounded(self) -> None:
        self._start_session()
        event = self._event(
            "user_action",
            event_id="evt-custom-low-signal",
            playback_time_seconds=5,
            action={"source": "custom", "text": "哈哈"},
        )
        event["episode_id"] = "huangnian_ep03"
        event["moment_id"] = EP03_MOMENT_ID

        response = self.client.post("/api/deadman/runtime/session/event", json=event)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["result_surface"]["text"], "这句我懂，但这段先别替剧情往后编。")
        self.assertIsNone(body["result_surface"]["micro_cue"])

    def test_moment_notice_outside_window_returns_idle_without_interrupt(self) -> None:
        self._start_session()
        response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("moment_notice", event_id="evt-notice-late", playback_time_seconds=25),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["companion"]["next_state"], "idle")
        self.assertFalse(body["companion"]["should_interrupt"])
        self.assertFalse(body["moment"]["interaction_window_active"])

    def test_duplicate_moment_notice_is_throttled_by_backend_session(self) -> None:
        self._start_session()
        first = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("moment_notice", event_id="evt-notice-first", playback_time_seconds=15),
        )
        second = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("moment_notice", event_id="evt-notice-second", playback_time_seconds=16),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["companion"]["next_state"], "notice_exclaim")
        self.assertEqual(second.json()["status"], "ok")
        self.assertEqual(second.json()["companion"]["next_state"], "idle")
        self.assertEqual(second.json()["companion"]["utterance"], "")
        self.assertFalse(second.json()["companion"]["should_interrupt"])
        self.assertTrue(second.json()["moment"]["interaction_window_active"])

    def test_runtime_event_auto_creates_session_when_session_start_races(self) -> None:
        response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-race-action",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["engine"]["cab_session_id"], "deadman-viewer-test-session")
        self.assertEqual(body["companion"]["next_state"], "verdict")

    def test_host_should_persist_false_blocks_session_memory_update(self) -> None:
        no_persist_service = NoPersistRuntimeJudgmentService(self.store)
        client = TestClient(create_app(store=self.store, judgment_service=no_persist_service))
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )

        first = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-no-persist-1",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )
        second = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-no-persist-2",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["session_memory"]["safe_to_reference"])
        self.assertEqual(first.json()["session_memory"]["last_choice_summary"], "")
        self.assertEqual(no_persist_service.call_count, 2)
        self.assertEqual(no_persist_service.runtime_context["host_state"]["previous_choice_summary"], "")

    def test_continue_watching_returns_idle_and_preserves_safe_summary(self) -> None:
        self._start_session()
        action_response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-before-continue",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )
        continue_response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("continue_watching", event_id="evt-continue"),
        )

        self.assertEqual(action_response.status_code, 200)
        self.assertEqual(continue_response.status_code, 200)
        body = continue_response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["companion"]["next_state"], "idle")
        self.assertTrue(body["session_memory"]["safe_to_reference"])
        self.assertIn("你上一手", body["session_memory"]["last_choice_summary"])

    def test_runtime_failure_returns_companion_error_without_demo_fallback(self) -> None:
        client = TestClient(
            create_app(
                store=self.store,
                judgment_service=FailingRuntimeJudgmentService(),
            )
        )
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )

        response = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-fail",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"]["code"], "cab_worker_timeout")
        self.assertEqual(body["error"]["retryable"], True)
        self.assertEqual(body["companion"]["next_state"], "error")
        self.assertNotIn("demo_deterministic", self._json_text(body))
        self.assertIsNone(body["judgment"])
        self.assertIsNone(body["result_surface"])

    def test_unhandled_runtime_exception_returns_structured_error(self) -> None:
        client = TestClient(
            create_app(
                store=self.store,
                judgment_service=ExplodingRuntimeJudgmentService(),
            )
        )
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )

        response = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id="evt-explode",
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"]["code"], "runtime_unhandled_error")
        self.assertFalse(body["error"]["retryable"])
        self.assertIsNone(body["judgment"])
        self.assertIsNone(body["result_surface"])

    def test_same_event_id_is_idempotent_for_user_action(self) -> None:
        counting_service = CountingJudgmentService(self.store)
        client = TestClient(create_app(store=self.store, judgment_service=counting_service))
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )
        payload = self._event(
            "user_action",
            event_id="evt-repeat",
            action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
        )

        first = client.post("/api/deadman/runtime/session/event", json=payload)
        second = client.post("/api/deadman/runtime/session/event", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(counting_service.call_count, 1)
        self.assertEqual(first.json()["result_surface"], second.json()["result_surface"])

    def test_runtime_retry_after_success_does_not_return_cached_success(self) -> None:
        counting_service = CountingJudgmentService(self.store)
        client = TestClient(create_app(store=self.store, judgment_service=counting_service))
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )
        action_payload = self._event(
            "user_action",
            event_id="evt-success",
            action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
        )

        action_response = client.post("/api/deadman/runtime/session/event", json=action_payload)
        retry_response = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("runtime_retry", event_id="evt-success"),
        )

        self.assertEqual(action_response.status_code, 200)
        self.assertEqual(action_response.json()["status"], "ok")
        self.assertEqual(retry_response.status_code, 200)
        self.assertEqual(retry_response.json()["status"], "error")
        self.assertEqual(retry_response.json()["error"]["code"], "runtime_retry_not_available")
        self.assertEqual(counting_service.call_count, 1)

    def test_runtime_retry_replays_stored_retryable_failure_once(self) -> None:
        flaky_service = FlakyRuntimeJudgmentService(self.store)
        client = TestClient(create_app(store=self.store, judgment_service=flaky_service))
        client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )
        event_id = "evt-flaky"

        first = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event(
                "user_action",
                event_id=event_id,
                action={"source": "preset", "text": ACTION_TEXT, "option_index": 0},
            ),
        )
        retry = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("runtime_retry", event_id=event_id),
        )
        retry_after_success = client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("runtime_retry", event_id=event_id),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "error")
        self.assertEqual(first.json()["error"]["code"], "cab_worker_timeout")
        self.assertTrue(first.json()["error"]["retryable"])
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["status"], "ok")
        self.assertEqual(retry.json()["companion"]["next_state"], "verdict")
        self.assertEqual(flaky_service.call_count, 2)
        self.assertEqual(retry_after_success.status_code, 200)
        self.assertEqual(retry_after_success.json()["status"], "error")
        self.assertEqual(retry_after_success.json()["error"]["code"], "runtime_retry_not_available")

    def _start_session(self) -> None:
        response = self.client.post(
            "/api/deadman/runtime/session/event",
            json=self._event("session_start", event_id="evt-start"),
        )
        self.assertEqual(response.status_code, 200)

    def _candidate_action(self, moment_id: str = MOMENT_ID, candidate_index: int = 0) -> dict[str, object]:
        moment = self.store.get_moment(DRAMA_ID, moment_id)
        candidates = moment["action_space"]["mouthpiece_candidates"]
        candidate = candidates[candidate_index]
        return {
            "source": "preset_candidate",
            "candidate_id": candidate["candidate_id"],
            "text": candidate["display_text"],
            "action_payload": candidate["action_payload"],
        }

    def _event(
        self,
        event_type: str,
        *,
        event_id: str,
        playback_time_seconds: float = 5,
        action: dict[str, object] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "viewer_session_id": "test-session",
            "event_id": event_id,
            "event_type": event_type,
            "drama_id": DRAMA_ID,
            "episode_id": "huangnian_ep12",
            "playback_time_seconds": playback_time_seconds,
            "moment_id": MOMENT_ID,
            "companion_state": "idle",
            "viewer_profile": {"tone": "friend", "risk_preference": "balanced"},
        }
        if action is not None:
            payload["action"] = action
        return payload

    def _json_text(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False)


class CountingJudgmentService(DeterministicJudgmentService):
    def __init__(self, store: DeadmanPackStore) -> None:
        super().__init__(store)
        self.call_count = 0
        self.runtime_context: dict[str, object] = {}

    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, object] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        self.call_count += 1
        self.runtime_context = {
            "viewer_session_id": viewer_session_id,
            "event_id": event_id,
            "host_state": host_state or {},
        }
        return self.judge(request), True


class NoPersistRuntimeJudgmentService(CountingJudgmentService):
    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, object] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        judgment, _ = super().judge_for_runtime(
            request,
            viewer_session_id=viewer_session_id,
            event_id=event_id,
            host_state=host_state,
        )
        return judgment, False


class FakeCabRuntimeClient:
    def __init__(self, adapter_output: dict[str, object]) -> None:
        self.adapter_output = adapter_output

    def judge(
        self,
        adapter_input: dict[str, object],
        *,
        viewer_session_id: str | None = None,
        event_id: str | None = None,
        host_state: dict[str, object] | None = None,
    ) -> CabRuntimeResult:
        return CabRuntimeResult(
            adapter_output=self.adapter_output,
            worker_response={"status": "ok"},
            session_payload={"status": "ok"},
            host_should_persist=True,
            persisted_by_cab=True,
        )


class FlakyRuntimeJudgmentService(CountingJudgmentService):
    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, object] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        self.call_count += 1
        if self.call_count == 1:
            raise PackStoreError("cab_worker_timeout", "CAB timed out.", status_code=502, retryable=True)
        self.runtime_context = {
            "viewer_session_id": viewer_session_id,
            "event_id": event_id,
            "host_state": host_state or {},
        }
        return self.judge(request), True


class FailingRuntimeJudgmentService:
    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, object] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        raise PackStoreError("cab_worker_timeout", "CAB timed out.", status_code=502, retryable=True)


class ExplodingRuntimeJudgmentService:
    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, object] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        raise RuntimeError("provider response parse failed")


if __name__ == "__main__":
    unittest.main()
