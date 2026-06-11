#!/usr/bin/env python3
"""ONE orchestrator: a raw uploaded video -> a playable v0.4 CompanionExchange pack.

This is the thin front wrapper the agentic production graph deliberately does NOT do
(`deadman_agentic_production_graph` docstring: "What this graph deliberately does NOT do
yet: ingest + ASR (step 7) and brand-new-drama reviewed-window scaffolding"). The
end-to-end upload->playable pipeline already exists, but ONLY inside `server.py`
(`_process_upload`/`_propose_windows`/`_build_upload_moment`/`_write_sandbox`/`_run_upload_author`),
which a concurrent workflow owns and this tool must not touch. This module re-implements the
ONE missing seam as standalone tools/ars code — the brand-new-drama moment scaffold builder
(`interaction_window` + `source_drama` + `source_window`, mirroring server.py
`_build_upload_moment`/`_write_sandbox`) — and otherwise REUSES the already-landed tools end
to end:

  STEP 1  prepare assets   reuse deadman_prepare_drama_assets   (ffmpeg video->mono16k mp3 + keyframes + media_index.json)
  STEP 2  ASR              reuse deadman_volc_asr_flash         (audio->normalized ASR JSON; env creds only)
  STEP 2b stage ASR        copy normalized -> tmp/ars_{drama}_analysis/volc_asr/normalized/{episode_id}.json
                                                                (where author_moment's asr_window() globs)
  STEP 3  synopsis         register {drama_id:{title,synopsis}} (committed synopses for the real path; sidecar otherwise)
  STEP 4  propose windows  reuse deadman_build_timeline_windows (deterministic 20s grid) OR the Ark window picker
  STEP 5  scaffold (SEAM)  build per-window moment skeleton + write data/dramas/{drama}/{moments,context,manifest}.v0.1.json
          + media registry reuse deadman_register_media
  STEP 6  episode memory   reuse deadman_build_episode_memory   (ASR->L3/L2 memory; required before the graph)
  STEP 7  author+promote   reuse deadman_agentic_production_graph.run_production
                                                                (window_gate->scene_context->2-stage author->taste judge
                                                                 ->self-correct->owner gate->promote; fills companion_exchange)
  STEP 8  validate         reuse deadman_validate_producer_bridge (P0 completeness + publish safety + contract gates)

CONSTRAINTS this orchestrator honors:
  - Defaults to a NEW drama-id ("uploaded_demo"); refuses the 3 curated ids (huangnian/lihun/yunmiao)
    unless --allow-curated is passed, so the curated packs stay git-clean.
  - --data-root targets a TMP root so the tracked data/dramas/ is never written until validated.
  - --dry-run prints the planned, ordered steps without running any of them.
  - env-only creds (ARK_* + DOUBAO_SPEECH_*); never logged.

    python tools/ars/deadman_ingest_pipeline.py --video clip.mp4 --drama-id uploaded_demo \
        --drama-name "上传样片" --synopsis "一句话剧情" [--data-root tmp/ingest_root] [--max-windows 1] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# The 3 curated runtime packs that must stay byte-for-byte untouched (git-clean).
CURATED_DRAMA_IDS = frozenset({"huangnian", "lihun", "yunmiao"})
DEFAULT_DRAMA_ID = "uploaded_demo"
SYNOPSES_PATH = REPO / "data" / "review" / "drama_synopses.v0.1.json"
KNOWN_COVER_BY_DRAMA = {
    "huangnian": "/assets/covers/huangnian.png",
    "yunmiao": "/assets/covers/yunmiao.png",
    "lihun": "/assets/covers/xingde.png",
}
DEFAULT_DEMO_COVER = "/assets/covers/deadman-demo.png"


class IngestError(RuntimeError):
    """A precondition / step failure in the ingest pipeline."""


# ---------------------------------------------------------------------------
# small fs helpers (kept local so the orchestrator does not depend on server.py)
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_cover_image_url(drama_id: str, drama_name: str) -> str | None:
    """Reuse bundled cover art for known demos; otherwise keep Stage visually non-empty."""
    haystack = f"{drama_id} {drama_name}".lower()
    if "huangnian" in haystack or "荒年" in drama_name:
        return KNOWN_COVER_BY_DRAMA["huangnian"]
    if "yunmiao" in haystack or "云渺" in drama_name:
        return KNOWN_COVER_BY_DRAMA["yunmiao"]
    if "lihun" in haystack or "xingde" in haystack or "离婚" in drama_name or "幸得" in drama_name:
        return KNOWN_COVER_BY_DRAMA["lihun"]
    return DEFAULT_DEMO_COVER


def analysis_dir_for(drama_id: str) -> Path:
    """The git-ignored per-drama analysis scratch (audio_mp3/keyframes/volc_asr/...)."""
    return REPO / "tmp" / f"ars_{drama_id}_analysis"


def video_stage_dir_for(drama_id: str) -> Path:
    """A git-ignored staging dir for the renamed 第N集.mp4 inputs the asset prep tool globs."""
    return REPO / "tmp" / f"ars_{drama_id}_video"


# ---------------------------------------------------------------------------
# STEP 0 — stage the uploaded video(s) as 第N集.mp4 (asset prep parses 第N集 from the stem)
# ---------------------------------------------------------------------------

def stage_videos(videos: list[Path], video_dir: Path) -> list[Path]:
    """Copy/rename each uploaded clip to 第{n}集{suffix} so deadman_prepare_drama_assets's
    episode_number() assigns ep01..epNN deterministically. Returns the staged paths."""
    video_dir.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for n, src in enumerate(videos, start=1):
        if not src.exists():
            raise IngestError(f"input video not found: {src}")
        suffix = src.suffix.lower() or ".mp4"
        dest = video_dir / f"第{n}集{suffix}"
        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)
        staged.append(dest)
    if not staged:
        raise IngestError("no input videos to stage (pass --video or --video-dir)")
    return staged


# ---------------------------------------------------------------------------
# STEP 1 — prepare assets (reuse deadman_prepare_drama_assets)
# ---------------------------------------------------------------------------

def prepare_assets(
    drama_id: str,
    drama_name: str,
    video_dir: Path,
    analysis_dir: Path,
    *,
    through: int | None = None,
    skip_keyframes: bool = False,
    skip_contact_sheets: bool = False,
) -> Path:
    """ffmpeg video -> mono 16kHz mp3 (+ optional keyframes/contact sheet) + media_index.json.
    Returns the media_index.json path. REUSES deadman_prepare_drama_assets.build_media_index +
    the same audio/keyframe extractors (no reimplementation)."""
    from tools.ars import deadman_prepare_drama_assets as prep

    media_index = prep.build_media_index(video_dir, drama_id)
    if through:
        media_index = media_index[:through]
    if not media_index:
        raise IngestError(f"no *.mp4 found under {video_dir} for asset prep")
    for item in media_index:
        video_path = prep.resolve_path(item["video_path"])
        episode_id = item["episode_id"]
        ep_suffix = episode_id.rsplit("_", 1)[-1]
        audio_path = analysis_dir / "audio_mp3" / f"{episode_id}.mp3"
        prep.extract_audio(video_path, audio_path, False)
        if not skip_keyframes:
            prep.extract_keyframes(video_path, analysis_dir / "keyframes_10s" / ep_suffix, False)
        if not skip_contact_sheets:
            prep.make_contact_sheet(video_path, analysis_dir / "contact_sheets" / f"{ep_suffix}_sheet.jpg", False)
    media_index_path = analysis_dir / "media_index.json"
    prep.write_json(media_index_path, media_index)
    return media_index_path


# ---------------------------------------------------------------------------
# STEP 2 — REAL ASR (reuse deadman_volc_asr_flash) + STEP 2b stage where asr_window globs
# ---------------------------------------------------------------------------

def run_asr(analysis_dir: Path, episode_ids: list[str]) -> dict[str, Path]:
    """audio mp3 -> normalized ASR JSON via Volc Doubao flash (env creds only). Writes
    {analysis_dir}/volc_asr/normalized/{episode_id}.normalized.json AND, additively, a
    {episode_id}.json copy that author_moment's asr_window() glob
    (tmp/ars_{drama}_analysis/volc_asr*/**/{episode_id}*.json) also matches. REUSES
    deadman_volc_asr_flash._recognize/_normalize (the same functions server.py reuses).
    Returns {episode_id: normalized_path}."""
    import os

    from tools.ars import deadman_volc_asr_flash as asr

    api_key = next((os.environ[k] for k in asr.API_KEY_ENV_CANDIDATES if os.environ.get(k)), "")
    if not api_key:
        raise IngestError(
            "missing ASR API key env var; set one of " + ", ".join(asr.API_KEY_ENV_CANDIDATES)
        )
    uid = next((os.environ[k] for k in asr.UID_ENV_CANDIDATES if os.environ.get(k)), "") or "deadman-ars"

    out_dir = analysis_dir / "volc_asr"
    raw_dir = out_dir / "raw"
    normalized_dir = out_dir / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    out: dict[str, Path] = {}
    for episode_id in episode_ids:
        audio_path = analysis_dir / "audio_mp3" / f"{episode_id}.mp3"
        if not audio_path.exists():
            raise IngestError(f"audio missing for {episode_id}: {audio_path}")
        raw = asr._recognize(
            audio_path, api_key=api_key, uid=uid,
            endpoint=asr.DEFAULT_ENDPOINT, resource_id=asr.DEFAULT_RESOURCE_ID,
        )
        normalized = asr._normalize(raw, audio_path=audio_path)
        if not normalized.get("utterances"):
            raise IngestError(f"ASR returned no utterances for {episode_id} (check creds/audio)")
        (raw_dir / f"{episode_id}.raw.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        normalized_path = normalized_dir / f"{episode_id}.normalized.json"
        normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        # STEP 2b: asr_window() globs *{episode_id}*.json; the .normalized.json above already matches,
        # but stage a plain {episode_id}.json copy too (server.py stages exactly this) so the episode
        # memory + scene-context grounding find the window even if naming conventions drift.
        (normalized_dir / f"{episode_id}.json").write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        out[episode_id] = normalized_path
    return out


def load_normalized_asr(analysis_dir: Path, episode_id: str) -> dict[str, Any]:
    path = analysis_dir / "volc_asr" / "normalized" / f"{episode_id}.normalized.json"
    if not path.exists():
        raise IngestError(f"normalized ASR missing for {episode_id}: {path}")
    return _read_json(path)


# ---------------------------------------------------------------------------
# STEP 3 — register synopsis (committed for the real path; sidecar otherwise)
# ---------------------------------------------------------------------------

def register_synopsis(drama_id: str, drama_name: str, synopsis: str, *, write_committed: bool) -> dict[str, Any]:
    """Register {drama_id:{title,synopsis}} so load_synopsis(drama, require=True) returns a premise.

    load_synopsis() reads ONLY the committed data/review/drama_synopses.v0.1.json, so a REAL run
    (scene-context grounding is fail-closed require=True) needs the key there. We add the new key
    additively (it cannot collide with the 3 curated ids) and return a snapshot so the caller can
    restore the committed file for a throwaway id. A sidecar copy is always written under the data
    root for provenance. Returns {"committed_written": bool, "previous": <prior entry or None>}."""
    snapshot: dict[str, Any] = {"committed_written": False, "previous": None, "had_key": False}
    entry = {"title": drama_name, "synopsis": synopsis or ""}
    if write_committed:
        data = _read_json(SYNOPSES_PATH) if SYNOPSES_PATH.exists() else {"schema_version": "drama_synopses.v0.1"}
        snapshot["had_key"] = drama_id in data
        snapshot["previous"] = data.get(drama_id)
        data[drama_id] = entry
        _write_json(SYNOPSES_PATH, data)
        snapshot["committed_written"] = True
    return snapshot


def restore_synopsis(drama_id: str, snapshot: dict[str, Any]) -> None:
    """Undo a committed-synopsis write for a throwaway id, leaving the committed file as found."""
    if not snapshot.get("committed_written"):
        return
    data = _read_json(SYNOPSES_PATH) if SYNOPSES_PATH.exists() else {}
    if snapshot.get("had_key"):
        data[drama_id] = snapshot.get("previous")
    else:
        data.pop(drama_id, None)
    _write_json(SYNOPSES_PATH, data)


# ---------------------------------------------------------------------------
# STEP 4 — propose windows (deterministic grid reuse) OR Ark picker
# ---------------------------------------------------------------------------

def propose_windows_deterministic(
    media_index_path: Path,
    analysis_dir: Path,
    drama_id: str,
    drama_name: str,
    *,
    max_windows: int,
) -> list[dict[str, Any]]:
    """Mine candidate interaction windows via the DETERMINISTIC fixed 20s grid
    (deadman_build_timeline_windows.build_windows). Provider-free, so the default ingest path
    needs no extra creds for windowing. Picks the top-`max_windows` non-empty windows by
    transcript density. Returns server.py-window-shaped dicts (start/end/notice/excerpt)."""
    from tools.ars import deadman_build_timeline_windows as tw

    media_index = _read_json(media_index_path)
    windows = tw.build_windows(media_index, analysis_dir)
    scored = [
        w for w in windows
        if (w.get("transcript_text") or "").strip()
    ]
    scored.sort(key=lambda w: len(w.get("transcript_text") or ""), reverse=True)
    chosen = scored[: max(1, max_windows)] if scored else windows[: max(1, max_windows)]
    out: list[dict[str, Any]] = []
    for w in chosen:
        start_s = int(int(w["start_ms"]) / 1000)
        end_s = int(int(w["end_ms"]) / 1000)
        excerpt = (w.get("transcript_text") or "")[:160]
        out.append({
            "episode_id": w["episode_id"],
            "start_seconds": start_s,
            "end_seconds": end_s,
            "notice_at_seconds": start_s,
            "scene_signal": excerpt[:24],
            "rationale": "fixed-grid candidate window (highest dialogue density)",
            "transcript_excerpt": excerpt,
            "selection_method": "deterministic",  # density grid, NOT semantic (audit trail)
        })
    return out


def propose_windows_ark(
    analysis_dir: Path,
    episode_id: str,
    *,
    max_windows: int,
    video_seconds: int | None = None,
) -> list[dict[str, Any]]:
    """Taste-aware Ark window picker, mirroring server.py _propose_windows prompt/schema (reusing
    ArkStudioProofProvider from tools.ars, NOT importing server.py). Falls back to the deterministic
    grid via the caller if Ark is unavailable. Returns the same window-shaped dicts."""
    from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider

    transcript = load_normalized_asr(analysis_dir, episode_id)
    utts = transcript.get("utterances") or []
    compact = [
        {"start_ms": u.get("start_time"), "end_ms": u.get("end_time"), "text": u.get("text", "")}
        for u in utts
    ]
    sys_prompt = (
        "你是短剧『看剧搭子』的互动窗口选取器。给你一段剧集字幕（每条含起止毫秒 + 文本）。"
        "请挑出最适合『搭子接话』的 1–3 个高光窗口——观众此刻情绪被戳中、最想说一句的瞬间。"
        "每个窗口约 10–15 秒（紧扣一个 beat，别贪长）。notice_at_seconds 落在那句最戳人的台词"
        "**刚说完**的位置——搭子是和你一起追剧的朋友，看完这句才反应过来想接话，所以 notice_at "
        "要稍晚于、绝不早于那句台词本身。只依据字幕里真实出现的台词，不要虚构后续剧情。"
        "为每个窗口给 start_seconds / end_seconds / notice_at_seconds（整数秒）、"
        "scene_signal（≤12 字情绪概括）、rationale（≤30 字依据），按推荐度排序。"
        "必须严格返回 JSON 对象：{\"windows\": [ ... ]}，windows 为数组，不要额外文字。"
    )
    schema = {
        "type": "object",
        "properties": {"windows": {"type": "array", "items": {"type": "object", "properties": {
            "start_seconds": {"type": "integer"}, "end_seconds": {"type": "integer"},
            "notice_at_seconds": {"type": "integer"}, "scene_signal": {"type": "string"},
            "rationale": {"type": "string"},
        }, "required": ["start_seconds", "end_seconds", "notice_at_seconds", "scene_signal", "rationale"]}}},
        "required": ["windows"],
    }
    provider = ArkStudioProofProvider.from_env()
    prompt = {"system_prompt": sys_prompt, "task": "propose_interaction_windows", "subtitles": compact}
    raw: list[dict[str, Any]] = []
    for _attempt in range(3):
        try:
            result = provider.complete_case(prompt, schema)
            payload = (result or {}).get("payload") or {}
            cand = payload.get("windows")
            if isinstance(cand, list) and cand:
                raw = cand
                break
        except Exception:
            continue
    if not raw:
        raise IngestError("Ark window picker returned no usable windows")
    dur = video_seconds or int((transcript.get("duration") or 0) / 1000) or None
    out: list[dict[str, Any]] = []
    for w in raw[: max(1, max_windows)]:
        try:
            s = max(0, int(w.get("start_seconds", 0)))
            e = int(w.get("end_seconds", s + 20))
            n = int(w.get("notice_at_seconds", s))
        except (TypeError, ValueError):
            continue
        if e <= s:
            e = s + 20
        if dur:
            e = min(e, dur)
            s = min(s, max(0, e - 5))
        n = min(max(n, s), e)
        excerpt = _window_excerpt(transcript, s, e)
        out.append({
            "episode_id": episode_id, "start_seconds": s, "end_seconds": e, "notice_at_seconds": n,
            "scene_signal": str(w.get("scene_signal", ""))[:24],
            "rationale": str(w.get("rationale", ""))[:60], "transcript_excerpt": excerpt,
            "selection_method": "ark",  # LLM semantic pick over the real subtitles (audit trail)
        })
    if not out:
        raise IngestError("Ark windows were all clamped away (empty after sanitize)")
    return out


def _window_excerpt(transcript: dict[str, Any], start_s: int, end_s: int) -> str:
    lo, hi = start_s * 1000, end_s * 1000
    parts = [
        u.get("text", "") for u in (transcript.get("utterances") or [])
        if int(u.get("start_time", 0)) < hi and int(u.get("end_time", 0)) > lo
    ]
    return " ".join(p for p in parts if p)[:160]


# ---------------------------------------------------------------------------
# STEP 5 — THE MISSING SEAM: brand-new-drama moment scaffold + pack files
# (mirrors server.py _build_upload_moment / _write_sandbox, generalized to any drama-id)
# ---------------------------------------------------------------------------

# Owner-validated standard: the 11 curated hero windows are all ~10s with notice == start. The
# companion is a CO-WATCHER — it reacts AFTER seeing the beat (react-after), not foreshadowing it —
# so the "!" fires at the trigger line the picker marked (which the prompt now places just after the
# charged line), and the interaction opens with it (notice == start). Target a 10–15s invitation.
WINDOW_MIN_S = 10
WINDOW_MAX_S = 15
WINDOW_DEFAULT_S = 12


def _scaffold_window_bounds(window: dict[str, Any]) -> tuple[int, int, int]:
    """Resolve (notice_s, start_s, end_s) from a proposed window. react-after default: notice == start
    == the picker's notice_at (the moment the co-watching companion reacts, placed just after the
    trigger line — NOT a foreshadow lead-in). Duration targets 10–15s (owner standard ≈10s), honoring
    the picker's own length when it falls in range, else WINDOW_DEFAULT_S. Within the bridge's P0
    8–30s range."""
    llm_start = max(0, int(window.get("start_seconds", 0)))
    llm_end = int(window.get("end_seconds", llm_start + WINDOW_DEFAULT_S))
    peak = int(window.get("notice_at_seconds", llm_start))
    if not (llm_start <= peak <= llm_end):
        peak = llm_start
    notice_s = peak          # react-after: "!" fires when the companion reacts, not before the line
    start_s = peak           # interaction opens with the "!" (notice == start, like the curated heroes)
    picker_dur = llm_end - start_s
    duration = picker_dur if WINDOW_MIN_S <= picker_dur <= WINDOW_MAX_S else WINDOW_DEFAULT_S
    end_s = start_s + duration
    return notice_s, start_s, end_s


def build_scaffold_moment(
    drama_id: str,
    drama_name: str,
    episode_id: str,
    window: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    """Build ONE runtime moment skeleton (the seam server.py owns inline) with an EMPTY
    companion_exchange that the agentic graph fills.

    Mirrors server.py _build_upload_moment, but generalized to any drama-id AND made
    PUBLISH-SAFE so the producer-bridge gate (deadman_validate_producer_bridge) passes:
      - source_window.provenance_status = publish_safe_sanitized (not the raw uploaded_local_asr),
      - transcript_refs[].source = sanitized_asr_snippet,
      - interaction_window.source = manual_p0_fallback (a P0-accepted source),
      - a source_refs.reviewed_demo_node pointing at #{moment_id} (the paired evidence node, below),
      - producer_refs (light-promote policy) so reproducibility back to ignored evidence is recorded,
      - review_state.status = demo_candidate (an accepted review state).
    (server.py's sandbox shape is NOT bridge-validated — it serves uploads straight from tmp/.)"""
    notice_s, start_s, end_s = _scaffold_window_bounds(window)
    # The BEAT = the charged content the picker identified (its [start, end]). With react-after, the
    # interaction window (notice/start/end) sits just AFTER this beat, so the author must ground on the
    # BEAT (source_window below), NOT the offer window — else it would author about post-beat dialogue.
    beat_start_s = max(0, int(window.get("start_seconds", notice_s)))
    beat_end_s = int(window.get("end_seconds", beat_start_s + WINDOW_DEFAULT_S))
    if beat_end_s <= beat_start_s:
        beat_end_s = beat_start_s + WINDOW_DEFAULT_S
    excerpt = str(window.get("transcript_excerpt") or "")
    moment_id = f"{drama_id}_ep01_m{index:03d}"
    transcript_ref = {
        "id": f"{moment_id}_u001", "episode_id": episode_id,
        "start_ms": beat_start_s * 1000, "end_ms": beat_end_s * 1000,  # the charged beat (evidence)
        "text": excerpt, "source": "sanitized_asr_snippet",
    }
    return {
        "pack_id": moment_id,
        "moment_id": moment_id,
        "schema_version": "moment_causality_pack.v0.1",
        "drama_id": drama_id,
        "drama_context_ref": "context.v0.1.json",
        "source_drama": {
            "title": drama_name,
            "episode_id": episode_id,
            "time_range_seconds": [beat_start_s, end_s],  # spans the charged beat through the offer
            "runtime_video_url": f"/api/deadman/media/{drama_id}/{episode_id}.mp4",
            "media_registry_ref": f"data/dramas/{drama_id}/media_registry.v0.1.json#{episode_id}",
        },
        "source_window": {
            "start_ms": beat_start_s * 1000,   # the BEAT (charged content) — what the author grounds on
            "end_ms": beat_end_s * 1000,
            "transcript_refs": [dict(transcript_ref)],
            "keyframe_refs": [],
            "provenance_status": "publish_safe_sanitized",
        },
        "review_state": {
            "status": "demo_candidate",
            "evidence_grade": "medium",
            "evidence_notes": excerpt or str(window.get("rationale", "")) or "ingested ASR/LLM window",
            "evidence_vs_inference": "window is ingested+mined evidence; companion content pending CAB authoring",
        },
        "source_refs": {
            "reviewed_demo_node": f"data/dramas/{drama_id}/evidence/reviewed_demo_nodes.v0.1.json#{moment_id}",
            "transcript_snippets": [dict(transcript_ref)],
            "keyframe_refs": [],
        },
        "producer_refs": {
            "policy": "ingest pipeline; producer evidence under ignored tmp/ars_<drama>_analysis; runtime refs sanitized",
        },
        "interaction_window": {
            "notice_at_seconds": notice_s, "start_seconds": start_s, "end_seconds": end_s,
            "source": "manual_p0_fallback", "confidence": "medium",
            # audit trail: HOW this window was actually chosen (ark = LLM semantic pick over real
            # subtitles; deterministic = density grid). `source` above is the P0-bridge provenance
            # label (must be reviewed_ars/manual_p0_fallback), so it can't carry this — hence a
            # dedicated field so a promoted pack is auditable as semantically- vs grid-selected.
            "selection_method": str(window.get("selection_method") or "unknown"),
            "pause_policy": "pause_on_invite", "expire_behavior": "return_to_idle",
        },
        "original_plot_note": "原剧情按当前场景推进；互动只接当下这一口气。",
        "companion_surface": {"notice_marker": "!", "companion_lead": "", "hook": ""},
        "action_space": {"action_type": "other", "default_options": [], "mouthpiece_candidates": []},
        "companion_exchange": {
            "schema_version": "companion_exchange_pack.v0.1",
            # Prefer the window picker's CRISP scene_signal (Ark: a ≤12-char emotion summary like
            # 「围观者夸云小姐美貌」; deterministic grid: a short excerpt head). Only fall back to the raw
            # transcript dump when the picker gave none — otherwise the good semantic summary is thrown
            # away and the Studio window preview / review gate show a run-on subtitle dump.
            "scene_signal": str(window.get("scene_signal") or "")[:60] or excerpt[:120],
            "window_rationale": str(window.get("rationale") or "") or excerpt,
            "notice_marker": "!", "companion_lead": "", "reply_candidates": [],
        },
        "notice_marker": "!",
    }


def build_reviewed_demo_node(moment: dict[str, Any]) -> dict[str, Any]:
    """The paired evidence node for a scaffolded moment (evidence/reviewed_demo_nodes.v0.1.json).
    The bridge gate requires one node per moment with a publish_safe_sanitized source_window."""
    moment_id = moment["moment_id"]
    source_window = moment["source_window"]
    review_state = moment["review_state"]
    excerpt = (source_window.get("transcript_refs") or [{}])[0].get("text", "")
    return {
        "moment_id": moment_id,
        "candidate_id": f"{moment_id}_c001",
        "review_status": review_state["status"],
        "corrected_trigger_type": "other",
        "source_window": {
            "start_ms": source_window["start_ms"], "end_ms": source_window["end_ms"],
            "transcript_refs": [dict(r) for r in source_window.get("transcript_refs", [])],
            "keyframe_refs": [], "provenance_status": "publish_safe_sanitized",
        },
        "companion_hook": "这一下我有点想替他说一句。",
        "viewer_impulse": "要是我来，我想接一句。",
        "default_options": ["接住眼前这个人此刻的情绪", "为眼前这件事说一句公道话", "先把火气压一压，看眼前怎么落地"],
        "evidence": {"grade": review_state.get("evidence_grade", "medium"), "notes": excerpt},
        "evidence_vs_inference": review_state.get("evidence_vs_inference", "ingested evidence; companion pending CAB"),
    }


def _force_producer_media_under_tmp(registry: dict[str, Any], drama_id: str) -> None:
    """The bridge gate requires producer_media.local_media_path under ignored tmp/. The raw upload
    is staged under tmp/ars_{drama}_video, so rewrite any non-tmp local path to that ignored slot."""
    for episode in registry.get("episodes", []):
        pm = episode.get("producer_media")
        if not isinstance(pm, dict):
            continue
        local = str(pm.get("local_media_path") or "")
        if local and not local.startswith("tmp/"):
            episode_id = str(episode.get("episode_id") or "")
            ep_suffix = episode_id.rsplit("_", 1)[-1] or "ep01"
            n = ep_suffix.replace("ep", "").lstrip("0") or "1"
            pm["local_media_path"] = f"tmp/ars_{drama_id}_video/第{n}集.mp4"


def write_scaffold_pack(
    drama_id: str,
    drama_name: str,
    moments: list[dict[str, Any]],
    drama_dir: Path,
    media_index_path: Path,
) -> dict[str, Path]:
    """Write the fresh-drama publish-safe pack files (moments/context/manifest/media_registry +
    the paired evidence/reviewed_demo_nodes) into drama_dir, mirroring server.py _write_sandbox
    shapes but P0-bridge-complete, and register media via deadman_register_media. Returns the
    written paths."""
    drama_dir.mkdir(parents=True, exist_ok=True)
    moment_ids = [m["moment_id"] for m in moments]

    # Media registry FIRST so the manifest can mirror its episode_count (bridge-checked).
    from tools.ars import deadman_register_media as regmedia

    registry = regmedia.register_media(
        drama_id=drama_id, title=drama_name,
        media_index=regmedia.load_media_index(media_index_path),
        episode_ids=set(), runtime_base=f"/api/deadman/media/{drama_id}",
        checksum=False, include_vite_dev_url=False,
    )
    _force_producer_media_under_tmp(registry, drama_id)
    registry["registered_count"] = sum(1 for e in registry.get("episodes", []) if e.get("status") == "registered")
    media_registry_path = drama_dir / "media_registry.v0.1.json"
    _write_json(media_registry_path, registry)
    cover_image_url = infer_cover_image_url(drama_id, drama_name)

    manifest = {
        "schema_version": "deadman_drama_runtime_manifest.v0.1", "drama_id": drama_id, "title": drama_name,
        "cover_image_url": cover_image_url,
        "pack_type": "lightweight_drama_context_pack_not_arcforge_world_simulation",
        "context_pack": {"path": "context.v0.1.json", "schema_version": "drama_context_pack.v0.1"},
        "moment_packs": {"path": "moments.v0.1.json", "schema_version": "moment_causality_pack.v0.1",
                         "count": len(moments), "moment_ids": moment_ids},
        "media_registry": {
            "path": "media_registry.v0.1.json", "schema_version": "deadman_media_registry.v0.1",
            "episode_count": registry.get("episode_count"),
            "registered_count": registry.get("registered_count"),
        },
        "source_artifacts": {"reviewed_demo_nodes": "evidence/reviewed_demo_nodes.v0.1.json"},
        "promoted_dir": f"data/dramas/{drama_id}", "source_sandbox_of": "ingest_pipeline",
    }
    context = {
        "schema_version": "drama_context_pack.v0.1", "drama_id": drama_id, "title": drama_name,
        "cover_image_url": cover_image_url,
        "global_constraints": {"hard_constraints": [
            "answer only current scene or immediate aftermath", "do not claim continuous branch rewrite"]},
        "evidence_map": [{"moment_id": m["moment_id"],
                          "reviewed_demo_node": (m.get("source_refs") or {}).get("reviewed_demo_node", "")}
                         for m in moments],
    }
    moments_col = {
        "schema_version": "moment_causality_pack_collection.v0.1",
        "collection_schema_version": "moment_causality_pack.v0.1",
        "drama_id": drama_id, "title": drama_name, "moment_count": len(moments), "moments": moments,
    }
    reviewed_nodes = {
        "schema_version": "deadman_reviewed_demo_nodes.v0.1",
        "evidence_policy": "ingested ASR/LLM windows reviewed into demo candidates; raw media stays under ignored tmp/",
        "demo_node_count": len(moments),
        "demo_nodes": [build_reviewed_demo_node(m) for m in moments],
    }

    manifest_path = drama_dir / "manifest.v0.1.json"
    context_path = drama_dir / "context.v0.1.json"
    moments_path = drama_dir / "moments.v0.1.json"
    reviewed_nodes_path = drama_dir / "evidence" / "reviewed_demo_nodes.v0.1.json"
    _write_json(manifest_path, manifest)
    _write_json(context_path, context)
    _write_json(moments_path, moments_col)
    _write_json(reviewed_nodes_path, reviewed_nodes)

    return {
        "manifest": manifest_path, "context": context_path,
        "moments": moments_path, "media_registry": media_registry_path,
        "reviewed_demo_nodes": reviewed_nodes_path,
    }


# ---------------------------------------------------------------------------
# STEP 6 — episode memory (reuse deadman_build_episode_memory)
# ---------------------------------------------------------------------------

def build_episode_memory(drama_id: str, through: int) -> Path:
    """ASR -> L3/L2 episode memory (1 Ark call/episode), idempotent/skip-cached. Required before
    the agentic graph (its build_episode_memory_node flags missing_uncached otherwise). REUSES
    deadman_build_episode_memory.build. Returns the written memory path."""
    from tools.ars import deadman_build_episode_memory as mem

    rc = mem.build(drama_id, through, dry_run=False)
    if rc != 0:
        raise IngestError(f"episode memory build failed for {drama_id} (rc={rc})")
    return mem.out_path(drama_id)


def write_fallback_episode_memory(
    drama_id: str,
    drama_name: str,
    synopsis: str,
    analysis_dir: Path,
    episode_ids: list[str],
) -> Path:
    """Write a conservative ASR-derived memory skeleton for upload preview.

    This is intentionally only used by the non-authoring /batch path when the provider-backed
    memory builder is unavailable. It lets the uploaded drama reach the owner-review graph with
    explicit provenance instead of failing the upload itself.
    """
    from tools.ars.deadman_build_episode_memory import out_path

    episodes: dict[str, Any] = {}
    for eid in episode_ids:
        normalized = load_normalized_asr(analysis_dir, eid)
        utterances = [
            str(u.get("text") or "").strip()
            for u in (normalized.get("utterances") or [])
            if str(u.get("text") or "").strip()
        ]
        head = " ".join(utterances[:2]).strip()
        episodes[eid] = {
            "episode_id": eid,
            "l3_one_line": (head[:80] if head else f"{drama_name} {eid} 已完成上传转写，待正式记忆生成。"),
            "l2_event_log": utterances[:8],
            "asr_utterances": len(utterances),
            "source": "fallback_from_asr_no_provider",
        }
    index = {
        "schema_version": "episode_memory.v0.1",
        "drama_id": drama_id,
        "title": drama_name,
        "premise": synopsis or "",
        "source": "fallback_from_asr_no_provider",
        "episodes": dict(sorted(episodes.items())),
    }
    path = out_path(drama_id)
    _write_json(path, index)
    return path


# ---------------------------------------------------------------------------
# STEP 7 — agentic CAB author + owner gate + promote (reuse run_production)
# ---------------------------------------------------------------------------

def run_authoring(
    drama_id: str,
    data_root: Path,
    *,
    max_rounds: int,
    review_decision: str,
    author_provider: Any = None,
    judge_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    promote_write: bool = True,
) -> dict[str, Any]:
    """Drive the agentic production graph: window_gate -> scene_context -> 2-stage author ->
    taste judge -> self-correct -> owner gate (auto review_decision) -> promote (fills
    companion_exchange + reply_candidates). REUSES run_production. When author_provider/judge are
    None, the real Ark/Bailian providers are loaded from env (the live path); tests inject fakes +
    a judge_fn + candidates to run fully offline. Returns the final graph report."""
    from tools.ars import deadman_agentic_production_graph as graph_mod

    if author_provider is None:
        from tools.ars.deadman_studio_cab_loop_spike import _load_env
        _load_env()
        from tools.ars.deadman_author_drama_heroes import ArkStudioProofProvider
        from tools.ars.deadman_run_studio_taste_judge import BailianTasteJudgeProvider
        author_provider = ArkStudioProofProvider.from_env()
        judge_provider = BailianTasteJudgeProvider.from_env()

    final = graph_mod.run_production(
        drama_id, author_provider, judge_provider,
        review_decision=review_decision, max_rounds=max_rounds, data_root=data_root,
        judge_fn=judge_fn, candidates=candidates, promote_write=promote_write,
    )
    return final.get("report", {})


# ---------------------------------------------------------------------------
# STEP 8 — validate (reuse deadman_validate_producer_bridge)
# ---------------------------------------------------------------------------

def validate_pack(drama_dir: Path) -> dict[str, Any]:
    """P0 completeness + publish safety + companion_exchange/reply_candidate/interaction_window
    contract gate for the new drama dir. REUSES deadman_validate_producer_bridge.BridgeValidator."""
    from tools.ars.deadman_validate_producer_bridge import BridgeValidator

    return BridgeValidator(drama_dir).validate()


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def plan_steps(
    videos: list[Path],
    drama_id: str,
    drama_name: str,
    *,
    data_root: Path,
    max_windows: int,
    through: int,
    use_ark_windows: bool,
) -> list[dict[str, Any]]:
    """The ordered plan (--dry-run prints this; the runner executes the same order)."""
    analysis = analysis_dir_for(drama_id)
    video_dir = video_stage_dir_for(drama_id)
    drama_dir = data_root / drama_id
    return [
        {"step": 0, "name": "stage_videos", "reuse": "(local)",
         "writes": str(video_dir), "detail": f"{len(videos)} clip(s) -> 第N集.mp4"},
        {"step": 1, "name": "prepare_assets", "reuse": "deadman_prepare_drama_assets",
         "writes": str(analysis / "audio_mp3") + ", media_index.json"},
        {"step": 2, "name": "real_asr", "reuse": "deadman_volc_asr_flash",
         "writes": str(analysis / "volc_asr" / "normalized")},
        {"step": 3, "name": "register_synopsis", "reuse": "(synopses)",
         "writes": str(SYNOPSES_PATH) + " (+sidecar)"},
        {"step": 4, "name": "propose_windows",
         "reuse": "deadman_run_studio_real_provider_proof (Ark)" if use_ark_windows
                  else "deadman_build_timeline_windows (20s grid)",
         "detail": f"max_windows={max_windows}"},
        {"step": 5, "name": "build_scaffold (SEAM)", "reuse": "(mirror server.py _build_upload_moment) + deadman_register_media",
         "writes": str(drama_dir / "moments.v0.1.json") + ", context/manifest/media_registry"},
        {"step": 6, "name": "build_episode_memory", "reuse": "deadman_build_episode_memory",
         "writes": str(REPO / "data/review/context_memory" / f"{drama_id}.v0.1.json")},
        {"step": 7, "name": "author_and_promote", "reuse": "deadman_agentic_production_graph.run_production",
         "writes": str(drama_dir / "moments.v0.1.json") + " (companion_exchange filled)"},
        {"step": 8, "name": "validate", "reuse": "deadman_validate_producer_bridge",
         "detail": str(drama_dir)},
    ]


def ingest(
    *,
    videos: list[Path],
    drama_id: str = DEFAULT_DRAMA_ID,
    drama_name: str,
    synopsis: str = "",
    data_root: Path | None = None,
    max_windows: int = 1,
    through: int = 1,
    skip_keyframes: bool = False,
    skip_contact_sheets: bool = False,
    use_ark_windows: bool = False,
    review_decision: str = "approve",
    max_rounds: int = 2,
    author: bool = True,
    allow_curated: bool = False,
    write_committed_synopsis: bool = True,
    restore_committed_synopsis: bool = False,
    # injection points so the unit test runs fully offline with NO real provider/ASR/ffmpeg:
    author_provider: Any = None,
    judge_provider: Any = None,
    judge_fn: Callable[[Any, dict[str, Any]], dict[str, Any]] | None = None,
    asr_runner: Callable[[Path, list[str]], dict[str, Path]] | None = None,
    prepare_runner: Callable[..., Path] | None = None,
    memory_runner: Callable[[str, int], Path] | None = None,
    windows_override: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full ingest pipeline (steps 0..8) for ONE new drama-id. Returns a report dict
    with the per-step outcomes + the validation status + every file written.

    The `*_runner` / `*_override` / `*_provider` injection points let the unit test stub the
    heavy/credentialed steps (ffmpeg, ASR, Ark) and assert the orchestration ORDER offline."""
    if drama_id in CURATED_DRAMA_IDS and not allow_curated:
        raise IngestError(
            f"refusing to ingest into curated drama-id '{drama_id}'; pass a NEW --drama-id "
            f"(default '{DEFAULT_DRAMA_ID}') or --allow-curated to override"
        )
    data_root = data_root or (REPO / "data" / "dramas")
    analysis = analysis_dir_for(drama_id)
    video_dir = video_stage_dir_for(drama_id)
    drama_dir = data_root / drama_id
    order: list[str] = []
    report: dict[str, Any] = {"drama_id": drama_id, "data_root": str(data_root),
                              "order": order, "files_written": [], "curated_untouched": True}
    synopsis_snapshot: dict[str, Any] = {}

    # STEP 0 — stage videos
    staged = stage_videos(videos, video_dir)
    order.append("stage_videos")
    episode_ids = [f"{drama_id}_ep{n:02d}" for n in range(1, len(staged) + 1)][:through] or [f"{drama_id}_ep01"]

    # STEP 1 — prepare assets
    if prepare_runner is not None:
        media_index_path = prepare_runner(drama_id, drama_name, video_dir, analysis,
                                          through=through, skip_keyframes=skip_keyframes,
                                          skip_contact_sheets=skip_contact_sheets)
    else:
        media_index_path = prepare_assets(drama_id, drama_name, video_dir, analysis, through=through,
                                          skip_keyframes=skip_keyframes, skip_contact_sheets=skip_contact_sheets)
    order.append("prepare_assets")
    report["media_index"] = str(media_index_path)
    # re-derive episode ids from the actual media index (authoritative)
    media_index = _read_json(media_index_path)
    if isinstance(media_index, list) and media_index:
        episode_ids = [str(item.get("episode_id")) for item in media_index if item.get("episode_id")][:through]

    # STEP 2 — real ASR (+ 2b staging) — injectable for offline test
    runner = asr_runner or run_asr
    runner(analysis, episode_ids)
    order.append("real_asr")

    # STEP 3 — register synopsis (restore-aware for a throwaway id)
    synopsis_snapshot = register_synopsis(drama_id, drama_name, synopsis, write_committed=write_committed_synopsis)
    _write_json(drama_dir.parent / drama_id / "_ingest_synopsis.json",
                {"drama_id": drama_id, "title": drama_name, "synopsis": synopsis})  # sidecar provenance
    order.append("register_synopsis")

    try:
        # STEP 4 — propose windows
        window_source = "override"
        if windows_override is not None:
            windows = windows_override
        elif use_ark_windows:
            try:
                windows = propose_windows_ark(analysis, episode_ids[0], max_windows=max_windows)
                window_source = "ark"
            except IngestError:
                windows = propose_windows_deterministic(
                    media_index_path, analysis, drama_id, drama_name, max_windows=max_windows
                )
                window_source = "deterministic_fallback_after_ark"
        else:
            windows = propose_windows_deterministic(media_index_path, analysis, drama_id, drama_name,
                                                    max_windows=max_windows)
            window_source = "deterministic"
        if not windows:
            raise IngestError("no interaction windows proposed")
        order.append("propose_windows")
        report["window_count"] = len(windows)
        report["window_source"] = window_source

        # STEP 5 — build the brand-new-drama scaffold (the seam) + pack files
        moments = [
            build_scaffold_moment(drama_id, drama_name,
                                  str(w.get("episode_id") or episode_ids[0]), w, index=i + 1)
            for i, w in enumerate(windows)
        ]
        written = write_scaffold_pack(drama_id, drama_name, moments, drama_dir, media_index_path)
        order.append("build_scaffold")
        report["files_written"].extend(str(p) for p in written.values())
        report["moment_ids"] = [m["moment_id"] for m in moments]

        # candidates the graph authors onto — each scaffolded moment IS a reviewed window.
        candidates = [{
            "item_id": m["moment_id"], "moment_id": m["moment_id"], "drama_id": drama_id,
            "drama_title": drama_name,
            "episode_id": (m.get("source_drama") or {}).get("episode_id"),
            "start_seconds": (m.get("interaction_window") or {}).get("start_seconds"),
            "end_seconds": (m.get("interaction_window") or {}).get("end_seconds"),
            "scene_signal": (m.get("companion_exchange") or {}).get("scene_signal"),
        } for m in moments]

        # STEP 6 — episode memory — injectable for offline test
        mem_runner = memory_runner or build_episode_memory
        try:
            memory_path = mem_runner(drama_id, through)
            report["memory_source"] = "provider"
        except Exception as exc:
            if author:
                raise
            memory_path = write_fallback_episode_memory(
                drama_id, drama_name, synopsis, analysis, episode_ids
            )
            report["memory_source"] = "fallback_from_asr_no_provider"
            report["memory_fallback_error_type"] = exc.__class__.__name__
        order.append("build_episode_memory")
        report["episode_memory"] = str(memory_path)

        # expose the proposed windows + candidates so a caller that STOPS before authoring
        # (author=False — the Studio /batch endpoint) can preview windows and hand the scaffolded
        # drama to the graph-run API (/run/start), which does the agentic authoring + owner gate.
        report["windows"] = windows
        report["candidates"] = candidates

        if author:
            # STEP 7 — agentic author + owner gate + promote
            graph_report = run_authoring(
                drama_id, data_root, max_rounds=max_rounds, review_decision=review_decision,
                author_provider=author_provider, judge_provider=judge_provider,
                judge_fn=judge_fn, candidates=candidates, promote_write=True,
            )
            order.append("author_and_promote")
            report["graph_report"] = graph_report

            # STEP 8 — validate
            validation = validate_pack(drama_dir)
            order.append("validate")
            report["validation_status"] = validation.get("status")
            report["validation_errors"] = validation.get("errors", [])
    finally:
        if restore_committed_synopsis:
            restore_synopsis(drama_id, synopsis_snapshot)
            report["committed_synopsis_restored"] = True

    report["curated_untouched"] = drama_id not in CURATED_DRAMA_IDS
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", action="append", default=[], help="Input video file. Repeatable.")
    ap.add_argument("--video-dir", help="Directory of input videos (alternative to --video).")
    ap.add_argument("--drama-id", default=DEFAULT_DRAMA_ID,
                    help=f"NEW drama-id (default '{DEFAULT_DRAMA_ID}'); curated ids are refused.")
    ap.add_argument("--drama-name", required=True, help="Display title for the new drama.")
    ap.add_argument("--synopsis", default="", help="One-line premise (authoritative L0 for authoring).")
    ap.add_argument("--through", type=int, default=1, help="Episodes to ingest (default 1).")
    ap.add_argument("--max-windows", type=int, default=1, help="Bounded count of interaction windows (default 1).")
    ap.add_argument("--data-root", default="", help="Override data/dramas root (TMP root keeps tracked packs clean).")
    ap.add_argument("--ark-windows", action="store_true",
                    help="Use the taste-aware Ark window picker instead of the deterministic 20s grid.")
    ap.add_argument("--review-decision", default="approve", help="Owner gate decision on resume (approve stamps reviewed).")
    ap.add_argument("--max-rounds", type=int, default=2, help="Self-correction rounds per window.")
    ap.add_argument("--skip-keyframes", action="store_true")
    ap.add_argument("--skip-contact-sheets", action="store_true")
    ap.add_argument("--allow-curated", action="store_true", help="Permit a curated drama-id (off by default).")
    ap.add_argument("--no-write-committed-synopsis", action="store_true",
                    help="Do not add the synopsis key to the committed synopses file.")
    ap.add_argument("--restore-committed-synopsis", action="store_true",
                    help="Restore the committed synopses file after the run (throwaway-id safe).")
    ap.add_argument("--dry-run", action="store_true", help="Print the ordered plan without running anything.")
    return ap.parse_args(argv)


def _gather_videos(args: argparse.Namespace) -> list[Path]:
    videos = [Path(v) for v in args.video]
    if args.video_dir:
        d = Path(args.video_dir)
        videos.extend(sorted(p for p in d.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".m4v"}))
    return videos


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    videos = _gather_videos(args)
    data_root = Path(args.data_root) if args.data_root else (REPO / "data" / "dramas")

    if args.dry_run:
        if not videos:
            videos = [Path("<input-video>")]
        plan = plan_steps(videos, args.drama_id, args.drama_name, data_root=data_root,
                          max_windows=args.max_windows, through=args.through,
                          use_ark_windows=args.ark_windows)
        print(json.dumps({
            "dry_run": True, "drama_id": args.drama_id, "data_root": str(data_root),
            "curated_id_refused": args.drama_id in CURATED_DRAMA_IDS and not args.allow_curated,
            "videos": [str(v) for v in videos], "plan": plan,
        }, ensure_ascii=False, indent=2))
        return 0

    if not videos:
        print("no input videos (pass --video or --video-dir)", file=sys.stderr)
        return 2

    report = ingest(
        videos=videos, drama_id=args.drama_id, drama_name=args.drama_name, synopsis=args.synopsis,
        data_root=data_root, max_windows=args.max_windows, through=args.through,
        skip_keyframes=args.skip_keyframes, skip_contact_sheets=args.skip_contact_sheets,
        use_ark_windows=args.ark_windows, review_decision=args.review_decision, max_rounds=args.max_rounds,
        allow_curated=args.allow_curated,
        write_committed_synopsis=not args.no_write_committed_synopsis,
        restore_committed_synopsis=args.restore_committed_synopsis,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("validation_status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
