"""Pydantic models for the Deadman judgment API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorPayload


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_root: str
    drama_count: int
    dramas: list[str]
    media: dict[str, Any] = Field(default_factory=dict)
    judgment: dict[str, Any] = Field(default_factory=dict)


class DramaCatalogItem(BaseModel):
    drama_id: str
    title: str
    schema_version: str
    manifest_schema_version: str
    moment_count: int
    promoted_dir: str


class DramaDetailResponse(BaseModel):
    drama_id: str
    title: str
    manifest_summary: dict[str, Any]
    context: dict[str, Any]


class MouthpieceCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidate_id: str
    display_text: str
    action_payload: dict[str, Any]
    selected_echo: str | None = None
    emotion_role: str
    semantic_role: str
    distinctness_rationale: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    constraint_refs: list[str] = Field(default_factory=list)
    friend_voice_seed: str | None = None
    requires_review: bool = False


class CompanionExchangePack(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "companion_exchange_pack.v0.1"
    scene_signal: str = ""
    window_rationale: str = ""
    notice_marker: str = "!"
    companion_lead: str = ""
    reply_candidates: list[MouthpieceCandidate] = Field(default_factory=list)
    custom_reply_policy: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    constraint_refs: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    review_status: str = "draft"


class MomentSummary(BaseModel):
    moment_id: str
    drama_id: str
    title: str | None = None
    source_drama: dict[str, Any] = Field(default_factory=dict)
    interaction_window: dict[str, Any] = Field(default_factory=dict)
    notice_marker: str | None = None
    hook: str | None = None
    companion_lead: str | None = None
    viewer_impulse: str | None = None
    action_type: str | None = None
    default_options: list[str] = Field(default_factory=list)
    companion_exchange: CompanionExchangePack | None = None
    mouthpiece_candidates_schema_version: str | None = None
    mouthpiece_candidates: list[MouthpieceCandidate] = Field(default_factory=list)
    result_media: dict[str, Any] = Field(default_factory=dict)
    original_plot_note: str | None = None
    evidence_grade: str | None = None
    score_axes: dict[str, Any] = Field(default_factory=dict)
    optional_module_keys: list[str] = Field(default_factory=list)

class UserAction(BaseModel):
    source: Literal["preset_candidate", "preset", "custom"]
    text: str
    option_index: int | None = None
    candidate_id: str | None = None
    action_payload: dict[str, Any] | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("action.text cannot be empty")
        return stripped

    @model_validator(mode="after")
    def preset_candidate_requires_id_and_payload(self) -> "UserAction":
        if self.source == "preset_candidate":
            if not self.candidate_id or not self.candidate_id.strip():
                raise ValueError("preset_candidate actions require candidate_id")
            if not isinstance(self.action_payload, dict) or not self.action_payload:
                raise ValueError("preset_candidate actions require action_payload")
        return self


class ViewerProfile(BaseModel):
    tone: str = "friend"
    risk_preference: str = "balanced"


class JudgmentRequest(BaseModel):
    drama_id: str
    moment_id: str
    action: UserAction
    viewer_profile: ViewerProfile = Field(default_factory=ViewerProfile)


class Verdict(BaseModel):
    label: str
    stance: Literal["support", "caution", "reject_softly"]
    summary: str


class Consequence(BaseModel):
    text: str
    time_horizon: Literal["current_scene_or_immediate_aftermath"]
    watch_flow_fit: Literal["high", "medium", "low"]


class CanonAnchor(BaseModel):
    original_plot_note: str
    safe_to_continue: bool


class ResultCard(BaseModel):
    mode: Literal["fallback_card"]
    title: str
    prompt: str


class JudgmentMedia(BaseModel):
    type: Literal["image"] = "image"
    status: Literal[
        "placeholder",
        "pregenerated",
        "not_available",
        "generation_pending",
        "generation_failed",
    ]
    image_url: str = ""
    prompt: str = ""
    source: str = ""
    fallback_text: str | None = None


class JudgmentBasis(BaseModel):
    evidence_refs: list[str]
    applied_constraints: list[str]
    inference_notes: list[str]
    warnings: list[str]


class EngineMetadata(BaseModel):
    mode: Literal["demo_deterministic", "cab_runtime"] = "demo_deterministic"
    schema_version: Literal[
        "deadman_judgment_result.v0.1",
        "deadman_judgment_adapter_output.v0.1",
    ] = "deadman_judgment_result.v0.1"


class ChoiceShare(BaseModel):
    label: str
    percent: int
    selected: bool = False


class AggregateStats(BaseModel):
    mode: Literal["demo_static"] = "demo_static"
    total_count: int
    choices: list[ChoiceShare]
    note: str


class JudgmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    drama_id: str
    moment_id: str
    action: UserAction
    verdict: Verdict
    consequence: Consequence
    canon_anchor: CanonAnchor
    scores: dict[str, int]
    result_card: ResultCard
    media: JudgmentMedia | None = None
    aggregate_stats: AggregateStats | None = None
    judgment_basis: JudgmentBasis
    engine: EngineMetadata = Field(default_factory=EngineMetadata)
