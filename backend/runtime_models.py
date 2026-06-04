"""Pydantic models for the Deadman companion runtime API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .models import ErrorPayload, JudgmentResponse, UserAction, ViewerProfile


RuntimeEventType = Literal[
    "session_start",
    "player_tick",
    "moment_notice",
    "companion_tap",
    "user_action",
    "continue_watching",
    "runtime_retry",
]


class RuntimeEventRequest(BaseModel):
    viewer_session_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,96}$")
    event_id: str = Field(min_length=1, max_length=128)
    event_type: RuntimeEventType
    drama_id: str
    episode_id: str | None = None
    playback_time_seconds: float | None = None
    moment_id: str | None = None
    companion_state: str = "idle"
    action: UserAction | None = None
    viewer_profile: ViewerProfile = Field(default_factory=ViewerProfile)

    @model_validator(mode="after")
    def action_required_for_user_action(self) -> "RuntimeEventRequest":
        if self.event_type == "user_action" and self.action is None:
            raise ValueError("action is required for user_action events")
        return self


class CompanionPayload(BaseModel):
    next_state: str
    marker: str | None = None
    utterance: str = ""
    should_interrupt: bool = False


class RuntimeMomentPayload(BaseModel):
    moment_id: str | None = None
    interaction_window_active: bool = False
    default_options: list[str] = Field(default_factory=list)
    hook: str | None = None


class RuntimeMicroCue(BaseModel):
    kind: Literal["aggregate_hint", "cost_hint", "visual_fallback_hint"]
    text: str


class ResultSurface(BaseModel):
    mode: Literal["single_narrative"] = "single_narrative"
    text: str
    micro_cue: RuntimeMicroCue | None = None
    continue_label: str = "继续看"


class RuntimeSessionMemoryPayload(BaseModel):
    last_choice_summary: str = ""
    safe_to_reference: bool = False


class RuntimeEnginePayload(BaseModel):
    mode: str
    cab_session_id: str | None = None


class RuntimeEventResponse(BaseModel):
    viewer_session_id: str
    event_id: str
    status: Literal["ok", "error"]
    companion: CompanionPayload
    moment: RuntimeMomentPayload = Field(default_factory=RuntimeMomentPayload)
    judgment: JudgmentResponse | None = None
    result_surface: ResultSurface | None = None
    session_memory: RuntimeSessionMemoryPayload = Field(default_factory=RuntimeSessionMemoryPayload)
    engine: RuntimeEnginePayload
    error: ErrorPayload | None = None
