"""Standalone FastAPI app factory for the Deadman API experiment."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from .companion_runtime import CompanionRuntime
from .judgment import CabRuntimeJudgmentService, DeterministicJudgmentService
from .models import (
    DramaCatalogItem,
    DramaDetailResponse,
    ErrorPayload,
    ErrorResponse,
    HealthResponse,
    JudgmentRequest,
    JudgmentResponse,
    MomentSummary,
)
from .pack_store import DeadmanPackStore, PackStoreError
from .runtime_client import CabRuntimeWorkerConfig, RuntimeClientError
from .runtime_models import RuntimeEventRequest, RuntimeEventResponse

LOCAL_VITE_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1):51\d{2}$"
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MEDIA_ROOT = REPO_ROOT / "tmp"
DEFAULT_JUDGMENT_ENGINE = "cab_runtime"


def _get_store(app: FastAPI) -> DeadmanPackStore:
    return cast(DeadmanPackStore, app.state.deadman_store)


def _get_judgment_service(app: FastAPI) -> Any:
    return app.state.deadman_judgment_service


def _get_companion_runtime(app: FastAPI) -> CompanionRuntime:
    return cast(CompanionRuntime, app.state.deadman_companion_runtime)


def create_app(store: DeadmanPackStore | None = None, judgment_service: Any | None = None) -> FastAPI:
    app = FastAPI(title="Deadman Companion API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "capacitor://localhost",
            "https://localhost",
            "http://localhost",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ],
        allow_origin_regex=LOCAL_VITE_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.deadman_store = store or DeadmanPackStore()
    app.state.deadman_judgment_service = judgment_service or _default_judgment_service(_get_store(app))
    app.state.deadman_companion_runtime = CompanionRuntime(
        store=_get_store(app),
        judgment_service=_get_judgment_service(app),
    )

    @app.exception_handler(PackStoreError)
    async def handle_pack_error(_: Request, exc: PackStoreError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorPayload(code=exc.code, message=exc.message, retryable=exc.retryable)
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else None
        detail = "Invalid request payload."
        if first_error is not None:
            location = ".".join(str(part) for part in first_error.get("loc", []) if part != "body")
            message = str(first_error.get("msg", "Invalid request payload."))
            detail = f"{location}: {message}" if location else message
        payload = ErrorResponse(
            error=ErrorPayload(code="validation_error", message=detail, retryable=False)
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.get("/api/deadman/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        store = _get_store(app)
        return HealthResponse(
            data_root=str(store.data_root),
            drama_count=len(store.list_drama_ids()),
            dramas=store.list_drama_ids(),
            media=_media_readiness(store),
            judgment=_judgment_readiness(_get_judgment_service(app)),
        )

    @app.get("/api/deadman/dramas", response_model=list[DramaCatalogItem])
    async def list_dramas() -> list[dict[str, object]]:
        return _get_store(app).list_dramas()

    @app.get("/api/deadman/dramas/{drama_id}", response_model=DramaDetailResponse)
    async def get_drama(drama_id: str) -> DramaDetailResponse:
        pack = _get_store(app).get_drama(drama_id)
        manifest = pack.manifest
        return DramaDetailResponse(
            drama_id=pack.drama_id,
            title=pack.title,
            manifest_summary={
                "schema_version": manifest.get("schema_version"),
                "pack_type": manifest.get("pack_type"),
                "context_pack": manifest.get("context_pack"),
                "moment_packs": manifest.get("moment_packs"),
                "runtime_priority": manifest.get("runtime_priority"),
                "ingestion_status": manifest.get("ingestion_status"),
            },
            context=pack.context,
        )

    @app.get("/api/deadman/dramas/{drama_id}/moments", response_model=list[MomentSummary])
    async def list_moments(drama_id: str) -> list[MomentSummary]:
        pack = _get_store(app).get_drama(drama_id)
        return [_moment_summary(_public_moment(moment, drama_id)) for moment in pack.moments_by_id.values()]

    @app.get("/api/deadman/dramas/{drama_id}/moments/{moment_id}")
    async def get_moment(drama_id: str, moment_id: str) -> dict[str, object]:
        return cast(dict[str, object], _public_moment(_get_store(app).get_moment(drama_id, moment_id), drama_id))

    @app.get("/api/deadman/dramas/{drama_id}/media-registry")
    async def get_media_registry(drama_id: str) -> dict[str, object]:
        pack = _get_store(app).get_drama(drama_id)
        return cast(dict[str, object], _public_media_registry(pack.media_registry, drama_id))

    @app.get("/api/deadman/media/{drama_id}/{episode_id}")
    async def get_episode_media(drama_id: str, episode_id: str) -> FileResponse:
        pack = _get_store(app).get_drama(drama_id)
        episode = _registry_episode(pack.media_registry, episode_id)
        if episode is None:
            raise PackStoreError(
                "media_episode_not_found",
                f"Media episode '{episode_id}' is not registered for drama '{drama_id}'.",
                status_code=404,
            )
        producer_media = episode.get("producer_media", {})
        if not isinstance(producer_media, dict):
            producer_media = {}
        local_media_path = str(producer_media.get("local_media_path") or "")
        media_path = _safe_local_media_path(local_media_path)
        if media_path is None or not media_path.exists():
            raise PackStoreError(
                "media_not_available",
                "Local media is not available on this server. Configure DEADMAN_MEDIA_BASE_URL or provide local tmp media for recording.",
                status_code=404,
            )
        return FileResponse(media_path, media_type=_media_type(media_path))

    @app.post("/api/deadman/judgment", response_model=JudgmentResponse)
    async def create_judgment(request: JudgmentRequest) -> JudgmentResponse:
        return _get_judgment_service(app).judge(request)

    @app.post("/api/deadman/runtime/session/event", response_model=RuntimeEventResponse)
    async def handle_runtime_event(request: RuntimeEventRequest) -> RuntimeEventResponse:
        return _get_companion_runtime(app).handle_event(request)

    return app


def _default_judgment_service(store: DeadmanPackStore) -> Any:
    engine = _configured_judgment_engine()
    if engine == "cab_runtime":
        return CabRuntimeJudgmentService(store)
    return DeterministicJudgmentService(store)


def _configured_judgment_engine() -> str:
    return os.environ.get("DEADMAN_JUDGMENT_ENGINE", DEFAULT_JUDGMENT_ENGINE).strip() or DEFAULT_JUDGMENT_ENGINE


app = create_app()


def _public_moment(moment: dict[str, Any], drama_id: str) -> dict[str, Any]:
    next_moment = copy.deepcopy(moment)
    next_moment.pop("producer_refs", None)
    source_drama = next_moment.get("source_drama")
    if isinstance(source_drama, dict):
        episode_id = str(source_drama.get("episode_id") or "")
        if episode_id:
            source_drama["runtime_video_url"] = _runtime_video_url(drama_id, episode_id)
    return next_moment


def _public_media_registry(registry: dict[str, Any], drama_id: str) -> dict[str, Any]:
    next_registry = copy.deepcopy(registry)
    media_policy = next_registry.get("media_policy")
    if isinstance(media_policy, dict):
        media_policy.pop("producer_media", None)
        media_policy["local_metadata"] = "redacted_from_public_api"
    episodes = next_registry.get("episodes")
    if isinstance(episodes, list):
        for episode in episodes:
            if not isinstance(episode, dict):
                continue
            episode.pop("producer_media", None)
            episode_id = str(episode.get("episode_id") or "")
            if episode_id:
                episode["runtime_video_url"] = _runtime_video_url(drama_id, episode_id)
    return next_registry


def _runtime_video_url(drama_id: str, episode_id: str) -> str:
    media_base_url = os.environ.get("DEADMAN_MEDIA_BASE_URL", "").strip().rstrip("/")
    if media_base_url:
        return f"{media_base_url}/{drama_id}/{episode_id}.mp4"
    return f"/api/deadman/media/{drama_id}/{episode_id}"


def _registry_episode(registry: dict[str, Any], episode_id: str) -> dict[str, Any] | None:
    for episode in registry.get("episodes", []):
        if isinstance(episode, dict) and episode.get("episode_id") == episode_id:
            return episode
    return None


def _safe_local_media_path(local_media_path: str) -> Path | None:
    if not local_media_path:
        return None
    candidate = Path(local_media_path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(LOCAL_MEDIA_ROOT):
        return None
    if resolved.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
        return None
    return resolved


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".mov":
        return "video/quicktime"
    return "video/mp4"


def _media_readiness(store: DeadmanPackStore) -> dict[str, Any]:
    media_base_url = os.environ.get("DEADMAN_MEDIA_BASE_URL", "").strip()
    total_episodes = 0
    local_available = 0
    for drama_id in store.list_drama_ids():
        pack = store.get_drama(drama_id)
        for episode in pack.media_registry.get("episodes", []):
            if not isinstance(episode, dict):
                continue
            total_episodes += 1
            producer_media = episode.get("producer_media", {})
            if not isinstance(producer_media, dict):
                producer_media = {}
            media_path = _safe_local_media_path(str(producer_media.get("local_media_path") or ""))
            if media_path is not None and media_path.exists():
                local_available += 1
    return {
        "mode": "external_base_url" if media_base_url else "registered_local_files",
        "external_base_url_configured": bool(media_base_url),
        "total_registered_episodes": total_episodes,
        "local_available_episodes": local_available,
        "deployment_ready": bool(media_base_url) or (total_episodes > 0 and local_available == total_episodes),
        "requirement": "Set DEADMAN_MEDIA_BASE_URL for clean git deployments, or provide registered local tmp media on the server.",
    }


def _judgment_readiness(judgment_service: Any) -> dict[str, Any]:
    if isinstance(judgment_service, CabRuntimeJudgmentService):
        engine = "cab_runtime"
    elif isinstance(judgment_service, DeterministicJudgmentService):
        engine = "demo_deterministic"
    else:
        engine = _configured_judgment_engine()
    payload: dict[str, Any] = {
        "engine": engine,
        "service": type(judgment_service).__name__,
        "formal_runtime_enabled": engine == "cab_runtime",
        "demo_deterministic_enabled": engine != "cab_runtime",
    }
    if engine != "cab_runtime":
        payload["requirement"] = "Set DEADMAN_JUDGMENT_ENGINE=cab_runtime to run the formal CABRuntime-backed judgment path."
        return payload
    try:
        config = CabRuntimeWorkerConfig.from_env()
    except RuntimeClientError as exc:
        payload.update(
            {
                "cab_runtime_config_valid": False,
                "cab_runtime_error": {
                    "code": exc.code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                },
            }
        )
        return payload
    payload.update(
        {
            "cab_runtime_config_valid": True,
            "cab_runtime_root": str(config.cab_runtime_root),
            "cab_runtime_root_exists": config.cab_runtime_root.exists(),
            "cab_project": str(config.cab_project),
            "cab_project_exists": config.cab_project.exists(),
            "timeout_seconds": config.timeout_seconds,
            "requirement": "CABRuntime formal path is selected; readiness must run a cab_runtime judgment loop.",
        }
    )
    return payload


def _moment_summary(moment: dict[str, object]) -> MomentSummary:
    companion = moment.get("companion_surface", {})
    if not isinstance(companion, dict):
        companion = {}
    action_space = moment.get("action_space", {})
    if not isinstance(action_space, dict):
        action_space = {}
    review_state = moment.get("review_state", {})
    if not isinstance(review_state, dict):
        review_state = {}
    optional_modules = moment.get("optional_modules", {})
    if not isinstance(optional_modules, dict):
        optional_modules = {}
    companion_exchange = _companion_exchange(moment)
    reply_candidates = _reply_candidates(moment, action_space, companion_exchange)
    return MomentSummary(
        moment_id=str(moment.get("moment_id") or moment.get("pack_id") or ""),
        drama_id=str(moment.get("drama_id", "")),
        title=cast(str | None, moment.get("title")),
        source_drama=cast(dict[str, object], moment.get("source_drama", {}) or {}),
        interaction_window=cast(dict[str, object], moment.get("interaction_window", {}) or {}),
        notice_marker=cast(str | None, companion.get("notice_marker")),
        hook=cast(str | None, companion.get("hook")),
        companion_lead=cast(str | None, companion.get("companion_lead")),
        viewer_impulse=cast(str | None, companion.get("viewer_impulse")),
        action_type=cast(str | None, action_space.get("action_type")),
        default_options=[str(option) for option in action_space.get("default_options", [])],
        companion_exchange=cast(Any, companion_exchange),
        mouthpiece_candidates_schema_version=cast(
            str | None,
            action_space.get("mouthpiece_candidates_schema_version") or ("mouthpiece_candidates.v0.1" if reply_candidates else None),
        ),
        mouthpiece_candidates=cast(list[Any], reply_candidates),
        result_media=cast(dict[str, object], moment.get("result_media", {}) or {}),
        original_plot_note=cast(str | None, moment.get("original_plot_note")),
        evidence_grade=cast(str | None, review_state.get("evidence_grade")),
        score_axes=cast(dict[str, object], moment.get("score_axes", {}) or {}),
        optional_module_keys=sorted(str(key) for key in optional_modules.keys()),
    )


def _companion_exchange(moment: dict[str, object]) -> dict[str, Any] | None:
    exchange = moment.get("companion_exchange")
    return cast(dict[str, Any], exchange) if isinstance(exchange, dict) else None


def _reply_candidates(
    moment: dict[str, object],
    action_space: dict[str, Any],
    companion_exchange: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if companion_exchange and isinstance(companion_exchange.get("reply_candidates"), list):
        return [item for item in companion_exchange["reply_candidates"] if isinstance(item, dict)]
    candidates = action_space.get("mouthpiece_candidates")
    if isinstance(candidates, list):
        return [item for item in candidates if isinstance(item, dict)]
    return []
