"""Runtime loader for promoted Deadman drama packs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PackStoreError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 404,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True)
class DramaPack:
    drama_id: str
    title: str
    root: Path
    manifest: dict[str, Any]
    context: dict[str, Any]
    moments_collection: dict[str, Any]
    moments_by_id: dict[str, dict[str, Any]]
    media_registry: dict[str, Any]


class DeadmanPackStore:
    """Loads tracked runtime packs from data/dramas only."""

    def __init__(self, data_root: str | Path | None = None) -> None:
        if data_root is None:
            data_root = os.environ.get("DEADMAN_DRAMA_DATA_ROOT")
        self.data_root = Path(data_root) if data_root else Path(__file__).resolve().parents[1] / "data" / "dramas"
        self._packs: dict[str, DramaPack] | None = None

    def load(self) -> dict[str, DramaPack]:
        if self._packs is None:
            self._packs = self._load_all()
        return self._packs

    def reset(self) -> None:
        """Drop the in-memory cache so a newly written/promoted drama dir is picked up
        on the next request (used by the Studio console's live promote-to-sandbox)."""
        self._packs = None

    def list_drama_ids(self) -> list[str]:
        return sorted(self.load().keys())

    def list_dramas(self) -> list[dict[str, Any]]:
        return [self._catalog_item(pack) for pack in self.load().values()]

    def get_drama(self, drama_id: str) -> DramaPack:
        pack = self.load().get(drama_id)
        if pack is None:
            raise PackStoreError(
                "drama_not_found",
                f"Drama pack '{drama_id}' is not available.",
                status_code=404,
            )
        return pack

    def get_moment(self, drama_id: str, moment_id: str) -> dict[str, Any]:
        pack = self.get_drama(drama_id)
        moment = pack.moments_by_id.get(moment_id)
        if moment is None:
            raise PackStoreError(
                "moment_not_found",
                f"Moment '{moment_id}' is not available for drama '{drama_id}'.",
                status_code=404,
            )
        return moment

    def _load_all(self) -> dict[str, DramaPack]:
        if not self.data_root.exists():
            return {}

        packs: dict[str, DramaPack] = {}
        for drama_dir in sorted(path for path in self.data_root.iterdir() if path.is_dir()):
            manifest_path = drama_dir / "manifest.v0.1.json"
            context_path = drama_dir / "context.v0.1.json"
            moments_path = drama_dir / "moments.v0.1.json"
            media_registry_path = drama_dir / "media_registry.v0.1.json"
            if not (manifest_path.exists() and context_path.exists() and moments_path.exists()):
                continue

            manifest = self._read_json(manifest_path)
            context = self._read_json(context_path)
            moments_collection = self._read_json(moments_path)
            media_registry = self._read_json(media_registry_path) if media_registry_path.exists() else {}
            drama_id = str(manifest.get("drama_id") or context.get("drama_id") or drama_dir.name)
            moments = moments_collection.get("moments", [])
            moments_by_id = {
                str(moment.get("moment_id") or moment.get("pack_id")): moment
                for moment in moments
                if isinstance(moment, dict) and (moment.get("moment_id") or moment.get("pack_id"))
                # placeholder moments are not yet CAB-authored/reviewed — never serve them at runtime
                and (moment.get("companion_exchange") or {}).get("content_status") != "placeholder_pending_cab"
            }
            packs[drama_id] = DramaPack(
                drama_id=drama_id,
                title=str(manifest.get("title") or context.get("title") or drama_id),
                root=drama_dir,
                manifest=manifest,
                context=context,
                moments_collection=moments_collection,
                moments_by_id=moments_by_id,
                media_registry=media_registry,
            )
        return packs

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PackStoreError(
                "pack_json_invalid",
                f"Failed to parse promoted pack file '{path.name}': {exc.msg}",
                status_code=500,
                retryable=False,
            ) from exc

    def _catalog_item(self, pack: DramaPack) -> dict[str, Any]:
        cover = pack.manifest.get("cover_image_url") or pack.context.get("cover_image_url")
        return {
            "drama_id": pack.drama_id,
            "title": pack.title,
            "cover_image_url": cover,
            "schema_version": str(pack.context.get("schema_version", "")),
            "manifest_schema_version": str(pack.manifest.get("schema_version", "")),
            "moment_count": len(pack.moments_by_id),
            "promoted_dir": str(pack.root.relative_to(Path.cwd())) if pack.root.is_relative_to(Path.cwd()) else str(pack.root),
        }
