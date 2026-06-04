"""Deadman-owned thin client for the CAB host adapter."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RuntimeClientError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


@dataclass(frozen=True)
class CabRuntimeResult:
    adapter_output: dict[str, Any]
    worker_response: dict[str, Any]
    session_payload: dict[str, Any]
    host_should_persist: bool = True
    persisted_by_cab: bool = False


@dataclass(frozen=True)
class CabRuntimeWorkerConfig:
    cab_runtime_root: Path
    cab_project: Path
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "CabRuntimeWorkerConfig":
        cab_root = _cab_runtime_root_from_env()
        timeout_value = os.environ.get("DEADMAN_CAB_RUNTIME_TIMEOUT_SECONDS") or "30"
        try:
            timeout = int(timeout_value)
        except ValueError as exc:
            raise RuntimeClientError(
                "cab_runtime_config_invalid",
                "DEADMAN_CAB_RUNTIME_TIMEOUT_SECONDS must be an integer.",
                retryable=False,
                details={"env": "DEADMAN_CAB_RUNTIME_TIMEOUT_SECONDS", "value": timeout_value},
            ) from exc
        project = Path(
            os.environ.get("DEADMAN_CAB_RUNTIME_PROJECT")
            or cab_root / "examples" / "v041-deadman-moment-judgment"
        ).expanduser()
        return cls(cab_runtime_root=cab_root, cab_project=project.resolve(), timeout_seconds=timeout)

    def to_host_adapter_config(self) -> Any:
        _, host_adapter_config, _ = _load_host_adapter(self.cab_runtime_root)
        return host_adapter_config(
            cab_project=self.cab_project,
            cab_runtime_root=self.cab_runtime_root,
            timeout_seconds=self.timeout_seconds,
        )


class CabRuntimeWorkerClient:
    """Calls a compiled CAB runtime while keeping Deadman mapping local."""

    def __init__(self, config: CabRuntimeWorkerConfig | None = None) -> None:
        self.config = config

    def judge(
        self,
        adapter_input: dict[str, Any],
        *,
        viewer_session_id: str | None = None,
        event_id: str | None = None,
        host_state: dict[str, Any] | None = None,
    ) -> CabRuntimeResult:
        config = self.config or CabRuntimeWorkerConfig.from_env()
        host_adapter_client, _, host_adapter_error = _load_host_adapter(config.cab_runtime_root)
        client = host_adapter_client(config.to_host_adapter_config())
        request_id = str(event_id or adapter_input.get("request_id") or "deadman-cab-runtime")
        session_id = (
            _safe_session_id(f"deadman-viewer-{viewer_session_id}")
            if viewer_session_id
            else _safe_session_id(f"deadman-{request_id}")
        )
        next_host_state = {
            "deadman_drama_id": adapter_input.get("drama_id"),
            "adapter_schema": "deadman_judgment_adapter_input.v0.1",
        }
        if host_state:
            next_host_state.update(host_state)
        message = {
            "event_type": "user_action" if viewer_session_id else "judgment",
            "adapter_input": adapter_input,
        }
        if viewer_session_id:
            message["session_context"] = {
                "viewer_session_id": viewer_session_id,
                "event_id": event_id,
            }
        try:
            result = client.run(
                session_id=session_id,
                message=json.dumps(message, ensure_ascii=False, separators=(",", ":")),
                host_state=next_host_state,
                request_id=request_id,
                require_structured_output=True,
            )
        except host_adapter_error as exc:
            raise RuntimeClientError(
                exc.code,
                exc.message,
                retryable=exc.retryable,
                details=exc.details,
            ) from exc
        return CabRuntimeResult(
            adapter_output=result.output_structured or {},
            worker_response=result.worker_response,
            session_payload=result.session_payload,
            host_should_persist=result.host_should_persist,
            persisted_by_cab=result.persisted_by_cab,
        )


def _default_cab_runtime_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "CABRuntime"
        if (candidate / "cab" / "host_adapter.py").exists():
            return candidate
    return current.parents[2] / "CABRuntime"


def _cab_runtime_root_from_env() -> Path:
    return Path(os.environ.get("DEADMAN_CAB_RUNTIME_ROOT") or _default_cab_runtime_root()).expanduser().resolve()


def _load_host_adapter(cab_runtime_root: Path) -> tuple[type[Any], type[Any], type[BaseException]]:
    root = cab_runtime_root.expanduser().resolve()
    host_adapter_path = root / "cab" / "host_adapter.py"
    if not host_adapter_path.exists():
        raise RuntimeClientError(
            "cab_runtime_root_invalid",
            "DEADMAN_CAB_RUNTIME_ROOT does not point to a CABRuntime checkout.",
            retryable=False,
            details={"cab_runtime_root": str(root)},
        )
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        from cab.host_adapter import HostAdapterClient, HostAdapterConfig, HostAdapterError
    except Exception as exc:
        raise RuntimeClientError(
            "cab_runtime_import_failed",
            "Could not import cab.host_adapter from DEADMAN_CAB_RUNTIME_ROOT.",
            retryable=False,
            details={"cab_runtime_root": str(root), "error": f"{type(exc).__name__}: {exc}"},
        ) from exc
    return HostAdapterClient, HostAdapterConfig, HostAdapterError


def _safe_session_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value).strip(".:-")
    return (cleaned or "deadman-cab-runtime")[:96]
