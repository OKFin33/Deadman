"""Small in-memory viewer session store for the Deadman companion runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .runtime_models import RuntimeEventResponse


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")


class ViewerSessionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class LastActionMemory:
    moment_id: str
    text: str
    source: str
    summary_for_next_moment: str


@dataclass
class ViewerSession:
    viewer_session_id: str
    created_at: str
    updated_at: str
    drama_id: str = ""
    episode_id: str = ""
    current_moment_id: str = ""
    companion_state: str = "idle"
    cab_session_id: str = ""
    last_action: LastActionMemory | None = None
    notified_moment_ids: set[str] = field(default_factory=set)
    completed_event_responses: dict[str, RuntimeEventResponse] = field(default_factory=dict)
    retryable_user_action: object | None = None


class ViewerSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ViewerSession] = {}

    def get_or_create(self, viewer_session_id: str) -> ViewerSession:
        self._validate_session_id(viewer_session_id)
        session = self._sessions.get(viewer_session_id)
        if session is not None:
            return session
        now = _now()
        session = ViewerSession(
            viewer_session_id=viewer_session_id,
            created_at=now,
            updated_at=now,
            cab_session_id=f"deadman-viewer-{viewer_session_id}",
        )
        self._sessions[viewer_session_id] = session
        return session

    def get(self, viewer_session_id: str) -> ViewerSession | None:
        self._validate_session_id(viewer_session_id)
        return self._sessions.get(viewer_session_id)

    def touch(
        self,
        session: ViewerSession,
        *,
        drama_id: str | None = None,
        episode_id: str | None = None,
        moment_id: str | None = None,
        companion_state: str | None = None,
    ) -> None:
        if drama_id:
            session.drama_id = drama_id
        if episode_id:
            session.episode_id = episode_id
        if moment_id:
            session.current_moment_id = moment_id
        if companion_state:
            session.companion_state = companion_state
        session.updated_at = _now()

    def _validate_session_id(self, viewer_session_id: str) -> None:
        if not SESSION_ID_PATTERN.fullmatch(viewer_session_id):
            raise ViewerSessionError(
                "viewer_session_invalid",
                "viewer_session_id must be 1-96 chars using letters, numbers, underscore, dot, colon, or dash.",
            )


def _now() -> str:
    return datetime.now(UTC).isoformat()
