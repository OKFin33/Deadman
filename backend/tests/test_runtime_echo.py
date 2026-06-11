"""Tests for the runtime custom-input echo (bounded runtime adaptation).

These tests NEVER call a real provider. They inject a fake Ark provider by monkeypatching the
symbols ``runtime_echo`` lazily imports, and force the env gate / creds check on, so the echo
path is exercised deterministically. The end-to-end FSM tests confirm a custom action uses the
echo when one is produced and the existing template otherwise.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from Deadman.backend import runtime_echo as runtime_echo_module
from Deadman.backend.api import create_app
from Deadman.backend.pack_store import DeadmanPackStore
from Deadman.backend.runtime_echo import runtime_custom_echo


# Minimal archived L0–L3 scene_context card (the build_scene_context() output shape).
SCENE_CONTEXT = {
    "whats_happening": "饭桌上孩子先把自己那份让出去。",
    "audience_already_knows": "这家正逢荒年，孩子一直很懂事。",
    "relationship_state": "母亲与孩子，家里资源紧张。",
    "grounding_note": "孩子的懂事是怕，不是不饿。",
    "l0_canon": {"premise": "荒年求生", "protagonist": {"name": "母亲"}},
    "l3_series_spine": [{"episode": "huangnian_ep01", "summary": "荒年开局，家里断粮。"}],
    "l2_recent_events": [{"episode": "huangnian_ep02", "events": ["孩子开始省口粮"]}],
    "prior_window_asr": ["你们先吃。"],
    "knowledge_horizon": "You know the show ONLY up to huangnian_ep03.",
}


def _moment_with_scene_context() -> dict:
    return {
        "moment_id": "huangnian_ep03_m001",
        "pack_id": "huangnian_ep03_m001",
        "companion_exchange": {
            "companion_lead": "原主的人设有点离谱",
            "scene_context": dict(SCENE_CONTEXT),
            "custom_reply_policy": {"allowed": True},
            "reply_candidates": [
                {"candidate_id": "preset_0", "display_text": "这妈当得离谱", "selected_echo": "哈哈真的离谱。"},
                {"candidate_id": "preset_1", "display_text": "孩子都吓成这样", "selected_echo": "心疼，孩子是怕。"},
                {"candidate_id": "preset_2", "display_text": "先别管大舅了", "selected_echo": "对，先保住孩子。"},
            ],
        },
    }


class _FakeProvider:
    """Stand-in for ArkStudioProofProvider: records the prompt and returns a canned echo."""

    last_prompt: dict | None = None

    def __init__(self, payload: dict | None = None, *, raises: Exception | None = None) -> None:
        self._payload = payload or {}
        self._raises = raises
        self.inner = object()
        self.call_count = 0

    @classmethod
    def with_echo(cls, echo: str) -> "_FakeProvider":
        return cls(payload={"selected_echo": echo})

    def from_env_factory(self):
        # Returned object must expose .inner for dataclasses.replace; we bypass that by also
        # patching dataclasses.replace via _install (see _install_fake_provider).
        return self

    def complete_case(self, prompt, schema):
        self.__class__.last_prompt = prompt
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return {"payload": self._payload, "provider": {"name": "fake"}}


class _install_fake_provider:
    """Context manager: patch runtime_echo's lazy imports to use a fake provider.

    Patches the upstream module symbols (where ``from X import Y`` resolves), forces the env
    gate + creds check on, and makes dataclasses.replace/ArkStudioProofProvider(...) a no-op
    wrapper so the per-call-timeout clone path stays exercisable without a real frozen dataclass.
    """

    def __init__(self, provider: _FakeProvider) -> None:
        self.provider = provider
        self._patches: list = []

    def __enter__(self):
        from Deadman.tools.ars import deadman_run_studio_real_provider_proof as proof_mod

        provider = self.provider

        class _FakeArkStudioProofProvider:
            @staticmethod
            def from_env():
                return provider

            def __new__(cls, *args, **kwargs):  # ArkStudioProofProvider(inner=...) -> same fake
                return provider

        def _fake_schema():
            return {"type": "object", "properties": {"selected_echo": {"type": "string"}}}

        def _fake_replace(obj, **changes):  # dataclasses.replace(base.inner, timeout_seconds=4.0)
            return obj

        self._patches = [
            patch.object(proof_mod, "ArkStudioProofProvider", _FakeArkStudioProofProvider),
            patch.object(proof_mod, "stage_b_output_schema", _fake_schema),
            patch.object(runtime_echo_module, "_ark_creds_present", lambda: True),
            patch("dataclasses.replace", _fake_replace),
            patch.dict("os.environ", {"DEADMAN_RUNTIME_ECHO": "1"}),
        ]
        for p in self._patches:
            p.start()
        return self.provider

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        return False


class RuntimeCustomEchoUnitTests(unittest.TestCase):
    def test_success_uses_provider_echo(self) -> None:
        provider = _FakeProvider.with_echo("孩子那点怕你接住了，这口野菜先留着，让他知道有人护他。")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertEqual(out, "孩子那点怕你接住了，这口野菜先留着，让他知道有人护他。")
        self.assertEqual(provider.call_count, 1)

    def test_stage_b_prompt_mapping_swaps_only_target_display_text(self) -> None:
        provider = _FakeProvider.with_echo("好，先护住孩子这口。")
        with _install_fake_provider(provider):
            runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        prompt = _FakeProvider.last_prompt
        self.assertIsNotNone(prompt)
        # target.display_text = the viewer line; other posture keys empty.
        self.assertEqual(prompt["this_viewer"]["display_text"], "孩子都怕成这样了，别再送菜了")
        self.assertEqual(prompt["this_viewer"]["emotion_role"], "")
        self.assertEqual(prompt["this_viewer"]["viewer_motivation"], "")
        # lead / siblings / prior come straight from the window's reviewed pack.
        self.assertEqual(prompt["companion_lead"], "原主的人设有点离谱")
        self.assertEqual(prompt["other_viewer_display_texts"], ["这妈当得离谱", "孩子都吓成这样", "先别管大舅了"])
        self.assertEqual(prompt["echoes_already_written_this_case"], ["哈哈真的离谱。", "心疼，孩子是怕。", "对，先保住孩子。"])
        # scene == the archived scene_context, passed straight through.
        self.assertEqual(prompt["scene"]["scene_context"], SCENE_CONTEXT)
        self.assertTrue(prompt["case_id"].startswith("runtime:"))

    def test_provider_timeout_or_error_falls_back_to_template(self) -> None:
        provider = _FakeProvider(raises=TimeoutError("ark timed out"))
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)

    def test_future_plot_echo_is_rejected(self) -> None:
        provider = _FakeProvider.with_echo("放心，后面剧集里她会替孩子翻盘，主线就靠这一步。")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)

    def test_rpg_flavored_echo_output_now_passes(self) -> None:
        # Softened: the broad _is_unsupported OUTPUT reject is removed — the prompt is the guard and
        # a friend vibing along is fine. (A blatant FUTURE-plot output is still stripped by sanitize,
        # see test_future_plot_echo_is_rejected.)
        provider = _FakeProvider.with_echo("太爽了，就该这么收拾他们")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNotNone(out)
        self.assertIn("收拾", out or "")

    def test_empty_echo_falls_back_to_template(self) -> None:
        provider = _FakeProvider.with_echo("   ")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)

    def test_missing_scene_context_falls_back_to_template(self) -> None:
        provider = _FakeProvider.with_echo("不该触发。")
        moment = _moment_with_scene_context()
        del moment["companion_exchange"]["scene_context"]
        with _install_fake_provider(provider):
            out = runtime_custom_echo(moment, "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)
        self.assertEqual(provider.call_count, 0)

    def test_future_or_rpg_input_now_reaches_provider(self) -> None:
        # Softened (owner 6/11): a future-plot / 改剧情 / RPG-flavored line is NO LONGER pre-rejected.
        # The friend responds (prompt-bounded to speculate, never assert future as fact), so the
        # input reaches Stage B instead of dropping straight to a template.
        provider = _FakeProvider.with_echo("哈哈那不就乱套了")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "直接开挂复仇把全村弄死")
        self.assertIsNotNone(out)
        self.assertIn("乱套", out or "")
        self.assertEqual(provider.call_count, 1)

    def test_casual_input_now_reaches_provider(self) -> None:
        # Softened (owner 6/11): a casual "哈哈" no longer gates out — the friend riffs along. Only
        # TRULY empty input falls back (test_empty_input_returns_none).
        provider = _FakeProvider.with_echo("哈哈对吧，这场面是有点逗")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "哈哈")
        self.assertIsNotNone(out)
        self.assertEqual(provider.call_count, 1)

    def test_empty_input_returns_none(self) -> None:
        provider = _FakeProvider.with_echo("不该触发。")
        with _install_fake_provider(provider):
            out = runtime_custom_echo(_moment_with_scene_context(), "   …  ")
        self.assertIsNone(out)
        self.assertEqual(provider.call_count, 0)

    def test_policy_disallowed_never_calls_provider(self) -> None:
        provider = _FakeProvider.with_echo("不该触发。")
        moment = _moment_with_scene_context()
        moment["companion_exchange"]["custom_reply_policy"] = {"allowed": False}
        with _install_fake_provider(provider):
            out = runtime_custom_echo(moment, "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)
        self.assertEqual(provider.call_count, 0)

    def test_env_gate_off_returns_none(self) -> None:
        provider = _FakeProvider.with_echo("不该触发。")
        with _install_fake_provider(provider):
            with patch.dict("os.environ", {"DEADMAN_RUNTIME_ECHO": "0"}):
                out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)
        self.assertEqual(provider.call_count, 0)

    def test_no_ark_creds_returns_none_without_import(self) -> None:
        # No creds patched -> real _ark_creds_present() returns False in the test env -> None,
        # and the heavy tools import is never reached. This is the CI/test-green guarantee.
        with patch.dict("os.environ", {"DEADMAN_RUNTIME_ECHO": "1"}, clear=False):
            out = runtime_custom_echo(_moment_with_scene_context(), "孩子都怕成这样了，别再送菜了")
        self.assertIsNone(out)


DRAMA_ID = "huangnian"
EP03_MOMENT_ID = "huangnian_ep03_m001"


class RuntimeEchoFsmWiringTests(unittest.TestCase):
    """End-to-end through the runtime FSM: the custom branch uses the echo when produced."""

    def setUp(self) -> None:
        self.engine_patch = patch.dict("os.environ", {"DEADMAN_JUDGMENT_ENGINE": "demo_deterministic"})
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.store = DeadmanPackStore()
        self.client = TestClient(create_app(store=self.store))

    def _custom_event(self, text: str) -> dict:
        return {
            "viewer_session_id": "test-session",
            "event_id": "evt-echo-custom",
            "event_type": "user_action",
            "drama_id": DRAMA_ID,
            "episode_id": "huangnian_ep03",
            "playback_time_seconds": 5,
            "moment_id": EP03_MOMENT_ID,
            "companion_state": "idle",
            "viewer_profile": {"tone": "friend", "risk_preference": "balanced"},
            "action": {"source": "custom", "text": text},
        }

    def _start(self) -> None:
        self.client.post(
            "/api/deadman/runtime/session/event",
            json={
                "viewer_session_id": "test-session",
                "event_id": "evt-start",
                "event_type": "session_start",
                "drama_id": DRAMA_ID,
                "episode_id": "huangnian_ep03",
                "playback_time_seconds": 0,
                "moment_id": EP03_MOMENT_ID,
                "companion_state": "idle",
                "viewer_profile": {"tone": "friend", "risk_preference": "balanced"},
            },
        )

    def test_custom_uses_runtime_echo_when_available(self) -> None:
        self._start()
        # The real packs have no scene_context yet, so patch runtime_custom_echo at the
        # friend_voice call site to confirm the wiring (its output becomes the surface text).
        # friend_voice imports runtime_custom_echo lazily inside the custom branch, so patch the
        # source symbol; the `from .runtime_echo import runtime_custom_echo` picks it up at call time.
        with patch(
            "Deadman.backend.runtime_echo.runtime_custom_echo",
            return_value="孩子那点怕你替他接住了，这口先留着。",
        ):
            response = self.client.post(
                "/api/deadman/runtime/session/event",
                json=self._custom_event("孩子都怕成这样了，别再把最后一口野菜送走了"),
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["result_surface"]["text"], "孩子那点怕你替他接住了，这口先留着。")
        # custom stays echo-centric: no heavy result-card; light micro_cue stays None here.
        self.assertIsNone(body["result_surface"]["micro_cue"])

    def test_custom_falls_back_to_friend_line_when_echo_none(self) -> None:
        self._start()
        with patch("Deadman.backend.runtime_echo.runtime_custom_echo", return_value=None):
            response = self.client.post(
                "/api/deadman/runtime/session/event",
                json=self._custom_event("孩子都怕成这样了，别再把最后一口野菜送走了"),
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        text = body["result_surface"]["text"]
        # Softened (owner 6/11): a runtime-echo miss degrades to a casual friend line, NOT a
        # content-policy template ("别替剧情往后编").
        self.assertEqual(text, "哎呀，我没get到你的意思…")


if __name__ == "__main__":
    unittest.main()
