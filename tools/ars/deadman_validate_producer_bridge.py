#!/usr/bin/env python3
"""Validate tracked Deadman producer-bridge runtime data.

This is a post-publish gate for the CLI producer flow. It checks that reviewed
local evidence was promoted into tracked, runtime-readable pack data without
making viewer/backend fields depend on ignored tmp artifacts.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_DRAMA_DIR = REPO_ROOT / "data/dramas/huangnian"
RAW_MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v"}
ACCEPTED_REVIEW_STATES = {"demo_candidate", "pack_draft", "reviewed", "promoted"}
PRODUCER_ONLY_SEGMENTS = {"producer_refs", "producer_media", "producer_ref"}
RUNTIME_LOCAL_FIELDS = {"local_media_path", "vite_dev_video_url"}
SECRET_KEYS = {
    "api_key",
    "x-api-key",
    "authorization",
    "access_token",
    "secret_key",
    "client_secret",
    "private_key",
}
NARRATION_TONE_BLOCKLIST = {
    "主角",
    "剧情",
    "原剧情",
    "原剧",
    "本集",
    "接下来",
    "观众",
    "玩家",
    "角色",
    "互动",
    "分支",
    "选择支",
    "系统将",
    "请你",
}
HOOK_MAX_CHARS = 36
OPTION_MAX_CHARS = 42


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: str | Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class BridgeValidator:
    def __init__(self, drama_dir: Path) -> None:
        self.drama_dir = drama_dir
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stats: dict[str, Any] = {}
        self.files: dict[str, Path] = {
            "manifest": drama_dir / "manifest.v0.1.json",
            "context": drama_dir / "context.v0.1.json",
            "moments": drama_dir / "moments.v0.1.json",
            "media_registry": drama_dir / "media_registry.v0.1.json",
            "reviewed_demo_nodes": drama_dir / "evidence/reviewed_demo_nodes.v0.1.json",
        }

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def load_required_json(self, label: str) -> Any:
        path = self.files[label]
        if not path.exists():
            self.error(f"Missing required {label}: {repo_relative(path)}")
            return {}
        try:
            return read_json(path)
        except json.JSONDecodeError as exc:
            self.error(f"Invalid JSON in {repo_relative(path)}: {exc.msg}")
            return {}

    def validate(self) -> dict[str, Any]:
        manifest = self.load_required_json("manifest")
        context = self.load_required_json("context")
        moments = self.load_required_json("moments")
        registry = self.load_required_json("media_registry")
        reviewed_nodes = self.load_required_json("reviewed_demo_nodes")

        self.validate_tracked_files()
        self.validate_safety("manifest", manifest)
        self.validate_safety("context", context)
        self.validate_safety("moments", moments)
        self.validate_safety("media_registry", registry)
        self.validate_safety("reviewed_demo_nodes", reviewed_nodes)

        moment_ids = self.validate_moments(moments)
        episode_ids = self.validate_media_registry(registry, moment_ids, moments)
        self.validate_manifest(manifest, moments, registry, moment_ids)
        self.validate_reviewed_nodes(reviewed_nodes, moment_ids)
        self.validate_context(context)

        self.stats.update(
            {
                "drama_dir": repo_relative(self.drama_dir),
                "moment_count": len(moment_ids),
                "episode_count": len(episode_ids),
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
            }
        )
        return {
            "status": "pass" if not self.errors else "fail",
            "stats": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def validate_tracked_files(self) -> None:
        if not self.drama_dir.exists():
            self.error(f"Drama directory does not exist: {repo_relative(self.drama_dir)}")
            return
        for path in self.drama_dir.rglob("*"):
            if not path.is_file():
                continue
            lower_name = path.name.lower()
            if lower_name == ".env" or lower_name.endswith(".env"):
                self.error(f"Tracked drama data contains env file: {repo_relative(path)}")
            if path.suffix.lower() in RAW_MEDIA_SUFFIXES:
                self.error(f"Tracked drama data contains raw media file: {repo_relative(path)}")

    def validate_safety(self, label: str, data: Any) -> None:
        def walk(value: Any, path: tuple[str, ...]) -> None:
            producer_only = any(segment in PRODUCER_ONLY_SEGMENTS for segment in path)
            if isinstance(value, dict):
                for key, child in value.items():
                    key_text = str(key)
                    next_path = (*path, key_text)
                    if key_text in RUNTIME_LOCAL_FIELDS and not producer_only:
                        self.error(f"{label}.{'.'.join(next_path)} is producer-local but not under producer_media")
                    if key_text.lower() in SECRET_KEYS and child:
                        self.error(f"{label}.{'.'.join(next_path)} looks like a secret-bearing field")
                    walk(child, next_path)
                return
            if isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, (*path, str(index)))
                return
            if not isinstance(value, str):
                return

            if ".env" in value:
                self.error(f"{label}.{'.'.join(path)} references an env file: {value}")
            if producer_only:
                return
            if value.startswith("tmp/") or "/tmp/" in value:
                self.error(f"{label}.{'.'.join(path)} depends on ignored tmp data: {value}")
            if value.startswith(str(REPO_ROOT)) or value.startswith("/Users/"):
                self.error(f"{label}.{'.'.join(path)} contains an absolute local path: {value}")

        walk(data, ())

    def validate_manifest(
        self,
        manifest: dict[str, Any],
        moments: dict[str, Any],
        registry: dict[str, Any],
        moment_ids: set[str],
    ) -> None:
        if manifest.get("schema_version") != "deadman_drama_runtime_manifest.v0.1":
            self.error("manifest.schema_version is not deadman_drama_runtime_manifest.v0.1")

        manifest_count = ((manifest.get("moment_packs") or {}).get("count"))
        if manifest_count != len(moment_ids):
            self.error(f"manifest moment count {manifest_count} does not match moments {len(moment_ids)}")

        manifest_ids = set((manifest.get("moment_packs") or {}).get("moment_ids") or [])
        if manifest_ids != moment_ids:
            self.error("manifest moment_ids do not match moments.v0.1.json")

        registry_summary = manifest.get("media_registry") or {}
        if registry_summary.get("episode_count") != registry.get("episode_count"):
            self.error("manifest media_registry.episode_count does not match media_registry.v0.1.json")

        for ref in (
            (manifest.get("context_pack") or {}).get("path"),
            (manifest.get("moment_packs") or {}).get("path"),
            (manifest.get("media_registry") or {}).get("path"),
            (manifest.get("source_artifacts") or {}).get("reviewed_demo_nodes"),
            (manifest.get("source_artifacts") or {}).get("allowed_summary"),
        ):
            if ref:
                self.require_ref_exists("manifest", str(ref))

    def validate_context(self, context: dict[str, Any]) -> None:
        if context.get("schema_version") != "drama_context_pack.v0.1":
            self.error("context.schema_version is not drama_context_pack.v0.1")
        evidence_map = context.get("evidence_map") or []
        if not evidence_map:
            self.warn("context.evidence_map is empty; runtime can load, but provenance is thin")

    def validate_moments(self, moments: dict[str, Any]) -> set[str]:
        moment_list = moments.get("moments")
        if not isinstance(moment_list, list):
            self.error("moments.moments must be a list")
            return set()

        ids: set[str] = set()
        for index, moment in enumerate(moment_list):
            if not isinstance(moment, dict):
                self.error(f"moments[{index}] is not an object")
                continue
            moment_id = str(moment.get("moment_id") or moment.get("pack_id") or "")
            if not moment_id:
                self.error(f"moments[{index}] is missing moment_id")
                continue
            if moment_id in ids:
                self.error(f"Duplicate moment_id: {moment_id}")
            ids.add(moment_id)

            review_state = moment.get("review_state") or {}
            status = str(review_state.get("status") or "")
            if status not in ACCEPTED_REVIEW_STATES:
                self.error(f"{moment_id} has unaccepted review_state.status: {status or '<missing>'}")

            source_window = moment.get("source_window") or {}
            if source_window.get("provenance_status") != "publish_safe_sanitized":
                self.error(f"{moment_id} source_window is not marked publish_safe_sanitized")

            source_refs = moment.get("source_refs") or {}
            reviewed_ref = str(source_refs.get("reviewed_demo_node") or "")
            if f"#{moment_id}" not in reviewed_ref:
                self.error(f"{moment_id} source_refs.reviewed_demo_node does not point to the same moment id")
            if not moment.get("producer_refs"):
                self.warn(f"{moment_id} has no producer_refs; reproducibility back to ignored evidence is weaker")

            source_drama = moment.get("source_drama") or {}
            if not source_drama.get("episode_id"):
                self.error(f"{moment_id} missing source_drama.episode_id")
            if not source_drama.get("runtime_video_url"):
                self.error(f"{moment_id} missing source_drama.runtime_video_url")
            if not source_drama.get("media_registry_ref"):
                self.error(f"{moment_id} missing source_drama.media_registry_ref")

            self.validate_interaction_window(moment_id, moment.get("interaction_window") or {})
            options = ((moment.get("action_space") or {}).get("default_options") or [])
            if len(options) < 2:
                self.error(f"{moment_id} has fewer than two default options")
            self.validate_companion_tone(moment_id, moment.get("companion_surface") or {}, options)

        declared = moments.get("moment_count")
        if declared != len(ids):
            self.error(f"moments.moment_count {declared} does not match actual {len(ids)}")
        return ids

    def validate_companion_tone(self, moment_id: str, companion_surface: dict[str, Any], options: Any) -> None:
        hook = str(companion_surface.get("hook") or "").strip()
        self.validate_friend_voice_text(moment_id, "companion_surface.hook", hook, max_chars=HOOK_MAX_CHARS)
        if hook and "?" not in hook and "？" not in hook:
            self.error(f"{moment_id} companion_surface.hook is not question-shaped")
        if hook and not any(marker in hook for marker in ("要不要", "该不该", "能不能", "现在")):
            self.warn(f"{moment_id} companion_surface.hook may not read like an immediate friend prompt")

        if not isinstance(options, list):
            self.error(f"{moment_id} action_space.default_options must be a list")
            return
        for index, option in enumerate(options):
            self.validate_friend_voice_text(
                moment_id,
                f"action_space.default_options[{index}]",
                str(option or "").strip(),
                max_chars=OPTION_MAX_CHARS,
            )

    def validate_friend_voice_text(self, moment_id: str, field: str, text: str, *, max_chars: int) -> None:
        if not text:
            self.error(f"{moment_id} {field} is empty")
            return
        if len(text) > max_chars:
            self.error(f"{moment_id} {field} is too long for companion surface: {len(text)} > {max_chars}")
        blocked = sorted(term for term in NARRATION_TONE_BLOCKLIST if term in text)
        if blocked:
            self.error(f"{moment_id} {field} uses narration/product wording: {', '.join(blocked)}")

    def validate_interaction_window(self, moment_id: str, window: dict[str, Any]) -> None:
        try:
            notice = int(window.get("notice_at_seconds"))
            start = int(window.get("start_seconds"))
            end = int(window.get("end_seconds"))
        except (TypeError, ValueError):
            self.error(f"{moment_id} interaction_window has non-integer timing")
            return
        if notice > start:
            self.error(f"{moment_id} notice_at_seconds is after start_seconds")
        if start >= end:
            self.error(f"{moment_id} interaction_window start is not before end")
        duration = end - start
        if duration < 8 or duration > 30:
            self.error(f"{moment_id} interaction_window duration {duration}s is outside P0 range 8-30s")
        if window.get("source") not in {"reviewed_ars", "manual_p0_fallback"}:
            self.error(f"{moment_id} interaction_window.source is not reviewed_ars/manual_p0_fallback")

    def validate_media_registry(
        self,
        registry: dict[str, Any],
        moment_ids: set[str],
        moments: dict[str, Any],
    ) -> set[str]:
        if registry.get("schema_version") != "deadman_media_registry.v0.1":
            self.error("media_registry.schema_version is not deadman_media_registry.v0.1")
        episodes = registry.get("episodes")
        if not isinstance(episodes, list):
            self.error("media_registry.episodes must be a list")
            return set()

        episode_ids: set[str] = set()
        for episode in episodes:
            if not isinstance(episode, dict):
                self.error("media_registry.episodes contains a non-object entry")
                continue
            episode_id = str(episode.get("episode_id") or "")
            if not episode_id:
                self.error("media_registry episode missing episode_id")
                continue
            episode_ids.add(episode_id)
            if not episode.get("runtime_video_url"):
                self.error(f"{episode_id} missing runtime_video_url")
            if "local_media_path" in episode or "vite_dev_video_url" in episode:
                self.error(f"{episode_id} has producer-local media fields at the episode top level")
            producer_media = episode.get("producer_media")
            if not isinstance(producer_media, dict):
                self.warn(f"{episode_id} has no producer_media block for local audit metadata")
            elif producer_media.get("local_media_path") and not str(producer_media["local_media_path"]).startswith("tmp/"):
                self.error(f"{episode_id} producer_media.local_media_path is not under ignored tmp/")

        declared = registry.get("episode_count")
        if declared != len(episode_ids):
            self.error(f"media_registry.episode_count {declared} does not match actual {len(episode_ids)}")

        moment_episode_ids = {
            str((moment.get("source_drama") or {}).get("episode_id"))
            for moment in moments.get("moments", [])
            if isinstance(moment, dict) and (moment.get("source_drama") or {}).get("episode_id")
        }
        missing = sorted(moment_episode_ids - episode_ids)
        if missing:
            self.error(f"media_registry is missing moment episode ids: {', '.join(missing)}")

        self.stats["moment_ids"] = sorted(moment_ids)
        self.stats["episode_ids"] = sorted(episode_ids)
        return episode_ids

    def validate_reviewed_nodes(self, reviewed_nodes: dict[str, Any], moment_ids: set[str]) -> None:
        nodes = reviewed_nodes.get("demo_nodes")
        if not isinstance(nodes, list):
            self.error("reviewed_demo_nodes.demo_nodes must be a list")
            return
        by_id = {str(node.get("moment_id")): node for node in nodes if isinstance(node, dict)}
        if set(by_id) != moment_ids:
            self.error("reviewed_demo_nodes moment ids do not match promoted moments")
        declared = reviewed_nodes.get("demo_node_count")
        if declared != len(nodes):
            self.error(f"reviewed_demo_nodes.demo_node_count {declared} does not match actual {len(nodes)}")
        for moment_id, node in by_id.items():
            status = str(node.get("review_status") or "")
            if status not in ACCEPTED_REVIEW_STATES:
                self.error(f"{moment_id} reviewed_demo_nodes review_status is not accepted: {status or '<missing>'}")
            if not node.get("evidence_vs_inference"):
                self.error(f"{moment_id} missing evidence_vs_inference in reviewed evidence")
            source_window = node.get("source_window") or {}
            if source_window.get("provenance_status") != "publish_safe_sanitized":
                self.error(f"{moment_id} reviewed source_window is not publish_safe_sanitized")

    def require_ref_exists(self, source_label: str, ref: str) -> None:
        path_text = ref.split("#", 1)[0]
        path = Path(path_text)
        if not path_text:
            return
        if path.is_absolute():
            resolved = path
        elif path.parts and path.parts[0] == "Deadman":
            resolved = REPO_ROOT / Path(*path.parts[1:])
        elif path.parts and path.parts[0] in {"assets", "backend", "data", "docs", "frontend", "tools"}:
            resolved = REPO_ROOT / path
        else:
            resolved = self.drama_dir / path
        if not resolved.exists():
            self.error(f"{source_label} reference does not exist: {ref}")


def build_report(result: dict[str, Any]) -> str:
    stats = result["stats"]
    lines = [
        "# Deadman Producer Bridge Validation Report",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Status: `{result['status']}`",
        f"- Drama dir: `{stats.get('drama_dir')}`",
        f"- Moments: {stats.get('moment_count', 0)}",
        f"- Episodes in media registry: {stats.get('episode_count', 0)}",
        f"- Errors: {len(result['errors'])}",
        f"- Warnings: {len(result['warnings'])}",
        "",
        "## Checks",
        "",
        "- Required manifest/context/moments/media registry/reviewed-node files exist and parse as JSON.",
        "- Manifest counts match promoted moments and media registry.",
        "- Promoted moments point back to reviewed demo-node evidence.",
        "- Companion hooks and quick replies avoid narration/product wording and stay short enough for friend-tone UI.",
        "- Runtime-facing fields do not depend on ignored `tmp/` files or absolute local paths.",
        "- Producer-only local refs stay under `producer_refs`, `producer_media`, or `producer_ref`.",
        "- No raw MP4/MOV/M4V or env file exists in the tracked drama data directory.",
        "",
    ]
    if result["errors"]:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {item}" for item in result["errors"])
        lines.append("")
    if result["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {item}" for item in result["warnings"])
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--drama-dir", default=str(DEFAULT_DRAMA_DIR))
    parser.add_argument("--report", help="Optional Markdown report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validator = BridgeValidator(resolve_path(args.drama_dir))
    result = validator.validate()
    if args.report:
        write_text(resolve_path(args.report), build_report(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
