"""Headless user-side companion runtime for Deadman."""

from __future__ import annotations

from typing import Any

from .friend_voice import FriendVoiceComposer
from .models import ErrorPayload, JudgmentRequest
from .pack_store import DeadmanPackStore, PackStoreError
from .runtime_models import (
    CompanionPayload,
    ResultSurface,
    RuntimeEnginePayload,
    RuntimeEventRequest,
    RuntimeEventResponse,
    RuntimeMomentPayload,
    RuntimeSessionMemoryPayload,
)
from .viewer_session import LastActionMemory, ViewerSession, ViewerSessionError, ViewerSessionStore


class CompanionRuntime:
    def __init__(
        self,
        *,
        store: DeadmanPackStore,
        judgment_service: Any,
        session_store: ViewerSessionStore | None = None,
        friend_voice: FriendVoiceComposer | None = None,
    ) -> None:
        self.store = store
        self.judgment_service = judgment_service
        self.sessions = session_store or ViewerSessionStore()
        self.friend_voice = friend_voice or FriendVoiceComposer()

    def handle_event(self, request: RuntimeEventRequest) -> RuntimeEventResponse:
        if request.event_type == "session_start":
            session = self.sessions.get_or_create(request.viewer_session_id)
            session.notified_moment_ids.clear()
            self.sessions.touch(
                session,
                drama_id=request.drama_id,
                episode_id=request.episode_id,
                moment_id=request.moment_id,
                companion_state="idle",
            )
            return self._ok(
                request,
                session,
                companion=CompanionPayload(next_state="idle", should_interrupt=False),
                moment=self._moment_payload(request),
            )

        session = self.sessions.get(request.viewer_session_id)
        if session is None:
            session = self.sessions.get_or_create(request.viewer_session_id)
            self.sessions.touch(
                session,
                drama_id=request.drama_id,
                episode_id=request.episode_id,
                moment_id=request.moment_id,
                companion_state=request.companion_state,
            )

        if request.event_type == "player_tick":
            self.sessions.touch(
                session,
                drama_id=request.drama_id,
                episode_id=request.episode_id,
                moment_id=request.moment_id,
                companion_state=request.companion_state,
            )
            return self._ok(
                request,
                session,
                companion=CompanionPayload(next_state=request.companion_state or "idle", should_interrupt=False),
                moment=self._moment_payload(request),
            )

        if request.event_type == "moment_notice":
            return self._handle_moment_notice(request, session)

        if request.event_type == "companion_tap":
            moment_payload = self._moment_payload(request)
            next_state = "stand_bubble" if moment_payload.interaction_window_active else "idle"
            self.sessions.touch(session, moment_id=request.moment_id, companion_state=next_state)
            return self._ok(
                request,
                session,
                companion=CompanionPayload(
                    next_state=next_state,
                    marker=self._notice_marker(request),
                    utterance=self._hook(request),
                    should_interrupt=next_state == "stand_bubble",
                ),
                moment=moment_payload,
            )

        if request.event_type == "user_action":
            return self._handle_user_action(request, session)

        if request.event_type == "runtime_retry":
            if (
                session.retryable_user_action is not None
                and isinstance(session.retryable_user_action, RuntimeEventRequest)
                and session.retryable_user_action.event_id == request.event_id
            ):
                return self._handle_user_action(session.retryable_user_action, session)
            return self._error(
                request,
                code="runtime_retry_not_available",
                message="No retryable event is stored for this event_id.",
                retryable=False,
                next_state="error",
            )

        if request.event_type == "continue_watching":
            self.sessions.touch(session, companion_state="idle")
            return self._ok(
                request,
                session,
                companion=CompanionPayload(next_state="idle", should_interrupt=False),
                moment=self._moment_payload(request),
            )

        return self._error(
            request,
            code="runtime_event_unsupported",
            message=f"Unsupported runtime event type: {request.event_type}",
            retryable=False,
            next_state="error",
        )

    def _handle_moment_notice(self, request: RuntimeEventRequest, session: ViewerSession) -> RuntimeEventResponse:
        moment_payload = self._moment_payload(request)
        marker = self._notice_marker(request)
        next_state = "notice_exclaim" if marker == "!" else "notice_question"
        if not moment_payload.interaction_window_active:
            next_state = "idle"
        notice_key = self._notice_key(request)
        if notice_key and moment_payload.interaction_window_active:
            if notice_key in session.notified_moment_ids:
                self.sessions.touch(session, moment_id=request.moment_id, companion_state="idle")
                return self._ok(
                    request,
                    session,
                    companion=CompanionPayload(next_state="idle", marker=marker, should_interrupt=False),
                    moment=moment_payload,
                )
            session.notified_moment_ids.add(notice_key)
        self.sessions.touch(session, moment_id=request.moment_id, companion_state=next_state)
        return self._ok(
            request,
            session,
            companion=CompanionPayload(
                next_state=next_state,
                marker=marker,
                utterance=self._hook(request),
                should_interrupt=False,
            ),
            moment=moment_payload,
        )

    def _handle_user_action(self, request: RuntimeEventRequest, session: ViewerSession) -> RuntimeEventResponse:
        cached = session.completed_event_responses.get(request.event_id)
        if cached is not None:
            return cached
        if request.action is None:
            return self._error(
                request,
                code="action_required",
                message="user_action events require action.",
                retryable=False,
                next_state="error",
            )
        if not request.moment_id:
            return self._error(
                request,
                code="moment_required",
                message="user_action events require moment_id.",
                retryable=False,
                next_state="error",
            )
        try:
            moment = self.store.get_moment(request.drama_id, request.moment_id)
            judgment_request = JudgmentRequest(
                drama_id=request.drama_id,
                moment_id=request.moment_id,
                action=request.action,
                viewer_profile=request.viewer_profile,
            )
            judge_for_runtime = getattr(self.judgment_service, "judge_for_runtime", None)
            if callable(judge_for_runtime):
                judgment, host_should_persist = judge_for_runtime(
                    judgment_request,
                    viewer_session_id=request.viewer_session_id,
                    event_id=request.event_id,
                    host_state={
                        "deadman_runtime_event": request.event_type,
                        "previous_choice_summary": session.last_action.summary_for_next_moment
                        if session.last_action
                        else "",
                    },
                )
            else:
                judgment = self.judgment_service.judge(judgment_request)
                host_should_persist = True
            previous_summary = session.last_action.summary_for_next_moment if session.last_action else ""
            voice = self.friend_voice.compose(
                judgment,
                moment=moment,
                previous_summary=previous_summary if self._safe_to_reference(session) else "",
                host_should_persist=host_should_persist,
            )
            if voice.safe_to_reference:
                session.last_action = LastActionMemory(
                    moment_id=request.moment_id,
                    text=request.action.text,
                    source=request.action.source,
                    summary_for_next_moment=voice.summary_for_next_moment,
                )
            self.sessions.touch(session, moment_id=request.moment_id, companion_state="verdict")
            response = self._ok(
                request,
                session,
                companion=CompanionPayload(next_state="verdict", should_interrupt=True),
                moment=self._moment_payload(request),
                judgment=judgment,
                result_surface=voice.result_surface,
                session_memory=RuntimeSessionMemoryPayload(
                    last_choice_summary=voice.summary_for_next_moment,
                    safe_to_reference=voice.safe_to_reference,
                ),
            )
            session.completed_event_responses[request.event_id] = response
            session.retryable_user_action = None
            return response
        except PackStoreError as exc:
            if exc.retryable:
                session.retryable_user_action = request
            response = self._error(
                request,
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                next_state="error",
            )
            return response
        except Exception:
            return self._error(
                request,
                code="runtime_unhandled_error",
                message="Deadman runtime failed while judging this action.",
                retryable=False,
                next_state="error",
            )

    def _moment_payload(self, request: RuntimeEventRequest) -> RuntimeMomentPayload:
        if not request.moment_id:
            return RuntimeMomentPayload()
        try:
            moment = self.store.get_moment(request.drama_id, request.moment_id)
        except PackStoreError:
            return RuntimeMomentPayload(moment_id=request.moment_id)
        return RuntimeMomentPayload(
            moment_id=request.moment_id,
            interaction_window_active=self._is_window_active(moment, request.playback_time_seconds),
            default_options=_default_options(moment),
            hook=self._hook_from_moment(moment),
        )

    def _is_window_active(self, moment: dict[str, Any], playback_time_seconds: float | None) -> bool:
        if playback_time_seconds is None:
            return True
        window = moment.get("interaction_window")
        if not isinstance(window, dict):
            return True
        start = _as_float(window.get("notice_at_seconds"), _as_float(window.get("start_seconds"), 0.0))
        end = _as_float(window.get("end_seconds"), start)
        return start <= playback_time_seconds <= end

    def _notice_marker(self, request: RuntimeEventRequest) -> str:
        if not request.moment_id:
            return "!"
        try:
            moment = self.store.get_moment(request.drama_id, request.moment_id)
        except PackStoreError:
            return "!"
        marker = moment.get("companion_surface", {}).get("notice_marker")
        return "?" if marker == "?" else "!"

    def _hook(self, request: RuntimeEventRequest) -> str:
        if not request.moment_id:
            return ""
        try:
            return self._hook_from_moment(self.store.get_moment(request.drama_id, request.moment_id))
        except PackStoreError:
            return ""

    def _hook_from_moment(self, moment: dict[str, Any]) -> str:
        hook = moment.get("companion_surface", {}).get("hook")
        return str(hook or "要不要换你来一手？")

    def _safe_to_reference(self, session: ViewerSession) -> bool:
        return bool(session.last_action and session.last_action.summary_for_next_moment)

    def _notice_key(self, request: RuntimeEventRequest) -> str:
        if not request.moment_id:
            return ""
        return f"{request.drama_id}:{request.episode_id or ''}:{request.moment_id}"

    def _ok(
        self,
        request: RuntimeEventRequest,
        session: ViewerSession,
        *,
        companion: CompanionPayload,
        moment: RuntimeMomentPayload | None = None,
        judgment: Any = None,
        result_surface: ResultSurface | None = None,
        session_memory: RuntimeSessionMemoryPayload | None = None,
    ) -> RuntimeEventResponse:
        return RuntimeEventResponse(
            viewer_session_id=request.viewer_session_id,
            event_id=request.event_id,
            status="ok",
            companion=companion,
            moment=moment or RuntimeMomentPayload(),
            judgment=judgment,
            result_surface=result_surface,
            session_memory=session_memory or self._session_memory_payload(session),
            engine=RuntimeEnginePayload(mode="host_policy", cab_session_id=session.cab_session_id),
        )

    def _error(
        self,
        request: RuntimeEventRequest,
        *,
        code: str,
        message: str,
        retryable: bool,
        next_state: str,
    ) -> RuntimeEventResponse:
        session = self.sessions.get(request.viewer_session_id)
        cab_session_id = session.cab_session_id if session else f"deadman-viewer-{request.viewer_session_id}"
        return RuntimeEventResponse(
            viewer_session_id=request.viewer_session_id,
            event_id=request.event_id,
            status="error",
            companion=CompanionPayload(next_state=next_state, utterance="这次我卡住了，刚才那手先收一下。"),
            moment=self._moment_payload(request),
            session_memory=self._session_memory_payload(session) if session else RuntimeSessionMemoryPayload(),
            engine=RuntimeEnginePayload(mode="host_policy", cab_session_id=cab_session_id),
            error=ErrorPayload(code=code, message=message, retryable=retryable),
        )

    def _session_memory_payload(self, session: ViewerSession) -> RuntimeSessionMemoryPayload:
        if not session.last_action:
            return RuntimeSessionMemoryPayload()
        return RuntimeSessionMemoryPayload(
            last_choice_summary=session.last_action.summary_for_next_moment,
            safe_to_reference=True,
        )


def _default_options(moment: dict[str, Any]) -> list[str]:
    action_space = moment.get("action_space")
    if not isinstance(action_space, dict):
        return []
    return [str(item) for item in action_space.get("default_options", []) if str(item).strip()]


def _as_float(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number
