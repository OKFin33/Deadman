"""Standalone Deadman deployment entrypoint."""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

_log = logging.getLogger("deadman.studio")

from backend.api import create_app as create_deadman_app

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STUDIO_STATIC = BASE_DIR / "studio"

app = FastAPI(title="Deadman")
deadman_app = create_deadman_app()

for exception_type, handler in deadman_app.exception_handlers.items():
    app.add_exception_handler(exception_type, handler)
app.include_router(deadman_app.router)


# Demo launcher — frames the two-product architecture (Studio authors → CompanionExchangePack
# → Stage plays) and routes to either side. Stage = /demo (viewer), Studio = /studio (producer).
_LANDING_HTML = """<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>看剧搭子 · Deadman</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&family=Noto+Serif+SC:wght@600;700;900&display=swap" rel="stylesheet">
<style>
  :root{--cream:#f3ece2;--dim:#b9ac9c;--coral:#ff6a45;--line:rgba(255,255,255,.09);--card:rgba(255,255,255,.035)}
  *{margin:0;padding:0;box-sizing:border-box}
  body{min-height:100vh;background:radial-gradient(1100px 680px at 50% -8%,#2a1f17,#17120f 62%);color:var(--cream);
    font-family:"Noto Sans SC",-apple-system,BlinkMacSystemFont,sans-serif;display:grid;place-items:center;padding:48px 20px}
  .wrap{width:100%;max-width:760px;text-align:center}
  .logo{font-size:46px;line-height:1}
  h1{font-family:"Noto Serif SC",serif;font-weight:900;font-size:38px;letter-spacing:1px;margin:14px 0 8px}
  .sub{color:var(--dim);font-size:15px;margin-bottom:38px;letter-spacing:.5px}
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}
  @media(max-width:560px){.cards{grid-template-columns:1fr}}
  .card{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);
    border-radius:18px;padding:26px 24px;text-align:left;transition:.16s ease}
  .card:hover{border-color:var(--coral);transform:translateY(-3px);background:rgba(255,106,69,.06)}
  .card .ico{font-size:30px;line-height:1}
  .card h2{font-family:"Noto Serif SC",serif;font-size:21px;font-weight:700;margin:12px 0 5px}
  .card .one{color:var(--dim);font-size:13.5px;line-height:1.65}
  .card .go{margin-top:18px;color:var(--coral);font-weight:700;font-size:14px}
  .bridge{margin-top:36px;color:var(--dim);font-size:12.5px;line-height:2.1}
  .bridge b{color:var(--cream)} .bridge .pack{color:var(--coral);font-weight:600}
  .foot{margin-top:30px;color:#6f6557;font-size:11.5px;line-height:1.7}
</style></head><body>
  <div class="wrap">
    <div class="logo">🍅</div>
    <h1>看剧搭子</h1>
    <p class="sub">短剧即时互动陪看 · 两端一桥</p>
    <div class="cards">
      <a class="card" href="/demo/">
        <div class="ico">👀</div>
        <h2>观众端 · Stage</h2>
        <p class="one">看短剧，高光点搭子接住你「想说的那句」——不打字、不打断。</p>
        <div class="go">进入 →</div>
      </a>
      <a class="card" href="/studio/">
        <div class="ico">🎬</div>
        <h2>制作端 · Studio</h2>
        <p class="one">把一个剧情瞬间授权成搭子对话，过 owner 风味评审再发布。</p>
        <div class="go">进入 →</div>
      </a>
    </div>
    <p class="bridge"><b>制作端</b> 授权 <span class="pack">─ CompanionExchangePack →</span> <b>观众端</b> 播放<br>
      （后台 · 重 · LLM 在环）&nbsp;&nbsp;（前台 · 轻 · 确定）</p>
    <p class="foot">单人参赛 · Web + Local Server · 制作端是后台 producer 控制台（演示用）。</p>
  </div>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    if not FRONTEND_DIST.exists():
        return (
            "<h1>Deadman</h1>"
            "<p>Run the frontend dev server or build frontend/dist to enable the demo shell.</p>"
        )
    return _LANDING_HTML


if STUDIO_STATIC.exists():
    @app.get("/studio")
    async def studio_redirect():
        return RedirectResponse(url="/studio/")

    app.mount("/studio", StaticFiles(directory=str(STUDIO_STATIC), html=True), name="deadman-studio")


if FRONTEND_DIST.exists():
    # The built SPA references its JS/CSS bundle + public assets at absolute /assets/... (vite
    # base "/"). Serve dist/assets at root so the app works under /demo/ AND the Studio→Stage
    # deep-link resolves — without this, /demo/ loads index.html but the bundle 404s → blank page.
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets"), html=False), name="frontend-assets")

    @app.get("/demo/{path:path}")
    async def demo_static(path: str):
        fp = FRONTEND_DIST / path
        if fp.exists() and fp.is_file():
            return FileResponse(str(fp))
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")

    @app.get("/demo")
    async def demo_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")


# ---- Studio producer API (L1: live CAB authoring from the console) ----------------
def _ensure_provider_env() -> None:
    """Lazy-load `.env` so the (launchd) backend can reach the Ark provider for live
    authoring. Local-demo only; `.env` is gitignored. Also strips any inherited SOCKS/HTTP
    proxy — Ark is a direct domestic API and the launchd env may carry a system proxy."""
    for _var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(_var, None)
    if os.environ.get("ARK_API_KEY"):
        return
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Lead copy must not be question-shaped (contract: validators must not encourage 要不要/该不该).
_QUESTION_LEAD_MARKERS = ("要不要", "该不该", "要不要紧")


def _safe_id(value: object, field: str) -> str:
    """Allowlist-validate an id used to build filesystem paths — blocks `../` traversal."""
    text = str(value or "")
    if not _SAFE_ID.match(text):
        raise ValueError(f"invalid {field}")
    return text


def _studio_error(code: str, exc: Exception, status_code: int = 502) -> JSONResponse:
    """Stable code + generic message to the client; full detail to the server log only."""
    _log.warning("studio endpoint failed [%s]: %s", code, exc)
    return JSONResponse({"error": {"code": code, "message": "Studio operation failed."}}, status_code=status_code)


def _review_violations(draft: dict) -> list[str]:
    """Backend publish gate: enforce the lead-shape + non-empty contract (mirrors the console lint's
    hard rules) so promote can't be driven past review by a direct POST."""
    violations: list[str] = []
    lead = str(draft.get("companion_lead") or "").strip()
    if not lead:
        violations.append("empty_lead")
    if any(marker in lead for marker in _QUESTION_LEAD_MARKERS) or lead.endswith(("吗？", "吗?")):
        violations.append("question_shaped_lead")
    replies = draft.get("replies") or []
    if not isinstance(replies, list) or not replies:
        violations.append("no_replies")
    else:
        for reply in replies:
            if not str((reply or {}).get("display_text") or "").strip():
                violations.append("empty_display_text")
                break
    return violations


def _run_author_prepared(drama_id: str, moment_id: str) -> dict:
    """Blocking: real 2-stage CAB authoring of a prepared moment (runs in a threadpool)."""
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from tools.ars.deadman_author_drama_heroes import author_moment, ArkStudioProofProvider, load as _load
    guidance = _load(BASE_DIR / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")
    pack = _load(BASE_DIR / f"data/dramas/{drama_id}/moments.v0.1.json")
    moment = next((m for m in pack["moments"] if m["moment_id"] == moment_id), pack["moments"][0])
    provider = ArkStudioProofProvider.from_env()
    _scene, lead, rcs = author_moment(provider, guidance, drama_id, pack, moment)
    return {
        "drama_id": drama_id,
        "moment_id": moment["moment_id"],
        "episode_id": moment["source_drama"]["episode_id"],
        "companion_lead": lead,
        "replies": [
            {"display_text": r.get("display_text"), "echo": r.get("selected_echo"),
             "motivation": r.get("viewer_motivation"),
             "coverage": ["core_direction_a", "core_direction_b", "fallback"][i] if i < 3 else "fallback"}
            for i, r in enumerate(rcs)
        ],
    }


@app.post("/api/studio/author")
async def studio_author(request: Request):
    """Live-author one prepared moment via the real 2-stage CAB path (Doubao/Ark).
    Body: {drama_id, moment_id}. Returns the fresh draft (lead + 3 replies + echoes)."""
    payload = await request.json()
    try:
        drama_id = _safe_id(payload.get("drama_id") or "yunmiao", "drama_id")
        moment_id = str(payload.get("moment_id") or "")
        if moment_id and not _SAFE_ID.match(moment_id):
            raise ValueError("invalid moment_id")
    except ValueError as exc:
        return JSONResponse({"error": {"code": "studio_bad_request", "message": str(exc)}}, status_code=400)
    _ensure_provider_env()
    try:  # blocking CAB off the event loop so it can't freeze concurrent viewer requests
        return await run_in_threadpool(_run_author_prepared, drama_id, moment_id)
    except Exception as exc:  # provider/env/data failure → structured error, never silent 500
        return _studio_error("studio_author_failed", exc)


# ---- Studio producer API (L2: promote a reviewed exchange to a live sandbox drama) ----
# The console publishes into ONE rolling sandbox drama (studio_sandbox), never the 3 curated
# demo dramas. It clones the source drama's pack (manifest/context/moments/media_registry),
# swaps in the published exchange, and reuses the source episode media + cover — so Stage lists
# and plays it immediately. New-video upload + ASR-driven windows are Phase C, not here.
SANDBOX_DRAMA_ID = "studio_sandbox"
_DRAMA_SHORT = {"yunmiao": "云渺", "lihun": "离婚", "huangnian": "荒年"}
_COVER_BY_DRAMA = {
    "yunmiao": "/assets/covers/yunmiao.png",
    "lihun": "/assets/covers/xingde.png",
    "huangnian": "/assets/covers/huangnian.png",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_draft_to_moment(moment: dict, draft: dict) -> dict:
    """Overwrite a cloned moment's authored content (lead + 3 replies + echoes) from the
    reviewed console draft, keeping its judgment/window/scaffold fields intact."""
    lead = str(draft.get("companion_lead") or moment.get("companion_exchange", {}).get("companion_lead", ""))
    replies = draft.get("replies") or []
    exchange = moment.setdefault("companion_exchange", {})
    exchange["companion_lead"] = lead
    cands = exchange.get("reply_candidates") or []
    for i, reply in enumerate(replies):
        cand = cands[i] if i < len(cands) else (copy.deepcopy(cands[-1]) if cands else {})
        if i >= len(cands):
            cands.append(cand)
        display = str(reply.get("display_text") or "")
        echo = str(reply.get("echo") or "")
        cand["display_text"] = display
        # fill scaffold defaults so a from-scratch (uploaded) candidate is runtime-valid; clones keep theirs
        payload = cand.setdefault("action_payload", {})
        payload["text"] = display
        payload.setdefault("action_type", "other")
        payload.setdefault("intent", "stance")  # neutral viewer-stance; don't leak the coverage label here
        payload.setdefault("target_actors", ["scene_focus"])
        payload.setdefault("risk_posture", "balanced")
        cand["candidate_id"] = f"preset_{i}"  # per-index, never inherit the deep-copied scaffold's id
        cand.setdefault("emotion_role", "")
        cand.setdefault("semantic_role", "stance")
        cand.setdefault("evidence_refs", ["current_scene_window"])
        cand.setdefault("constraint_refs", ["current_scene_only", "no_branch_rewrite", "source_window_grounding"])
        cand["selected_echo"] = echo
        cand["friend_voice_seed"] = echo
        if reply.get("motivation"):
            cand["viewer_motivation"] = str(reply["motivation"])
        if reply.get("coverage"):
            cand["distinctness_rationale"] = f"coverage:{reply['coverage']}; Studio-console published"
    exchange["reply_candidates"] = cands[: len(replies)] if replies else cands
    surface = moment.setdefault("companion_surface", {})
    surface["companion_lead"] = lead
    surface["hook"] = lead
    action_space = moment.setdefault("action_space", {})
    action_space["default_options"] = [c.get("display_text", "") for c in exchange["reply_candidates"]]
    action_space["mouthpiece_candidates"] = copy.deepcopy(exchange["reply_candidates"])
    return moment


def _promote_to_sandbox(source_drama_id: str, source_moment_id: str, draft: dict) -> dict:
    source_drama_id = _safe_id(source_drama_id, "drama_id")
    src_dir = BASE_DIR / "data" / "dramas" / source_drama_id
    if not src_dir.exists():
        raise ValueError(f"source drama '{source_drama_id}' not found")
    manifest = _read_json(src_dir / "manifest.v0.1.json")
    context = _read_json(src_dir / "context.v0.1.json")
    moments_col = _read_json(src_dir / "moments.v0.1.json")
    reg_path = src_dir / "media_registry.v0.1.json"
    media_reg = _read_json(reg_path) if reg_path.exists() else {}

    moments = moments_col.get("moments", [])
    src_moment = next((m for m in moments if m.get("moment_id") == source_moment_id), moments[0] if moments else None)
    if src_moment is None:
        raise ValueError(f"no moment '{source_moment_id}' in '{source_drama_id}'")

    moment = _apply_draft_to_moment(copy.deepcopy(src_moment), draft)
    moment["drama_id"] = SANDBOX_DRAMA_ID
    episode_id = str(moment.get("source_drama", {}).get("episode_id", ""))
    short = _DRAMA_SHORT.get(source_drama_id, source_drama_id)
    title = f"📝 控制台样片 · {short}"
    cover = _COVER_BY_DRAMA.get(source_drama_id)

    # rewrite the sandbox identity; KEEP episode_ids + local_media_path so source media is reused.
    manifest.update({"drama_id": SANDBOX_DRAMA_ID, "title": title, "cover_image_url": cover,
                     "promoted_dir": f"data/dramas/{SANDBOX_DRAMA_ID}", "source_sandbox_of": source_drama_id})
    if isinstance(manifest.get("moment_packs"), dict):
        manifest["moment_packs"] = {**manifest["moment_packs"], "count": 1, "moment_ids": [moment.get("moment_id")]}
    context.update({"drama_id": SANDBOX_DRAMA_ID, "title": title, "cover_image_url": cover})
    moments_col.update({"drama_id": SANDBOX_DRAMA_ID, "title": title, "moment_count": 1, "moments": [moment]})
    if media_reg:
        media_reg.update({"drama_id": SANDBOX_DRAMA_ID, "title": title})

    out_dir = BASE_DIR / "data" / "dramas" / SANDBOX_DRAMA_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "manifest.v0.1.json", manifest)
    _write_json(out_dir / "context.v0.1.json", context)
    _write_json(out_dir / "moments.v0.1.json", moments_col)
    if media_reg:
        _write_json(out_dir / "media_registry.v0.1.json", media_reg)

    seek = moment.get("interaction_window", {}).get("notice_at_seconds", 0)
    return {
        "drama_id": SANDBOX_DRAMA_ID,
        "title": title,
        "moment_id": moment.get("moment_id"),
        "episode_id": episode_id,
        "stage_url": f"/demo/?branch3_player=1&dramaId={SANDBOX_DRAMA_ID}&episodeId={episode_id}&seek={seek}",
    }


@app.post("/api/studio/promote")
async def studio_promote(request: Request):
    """Publish a reviewed exchange into the live sandbox drama, then invalidate the runtime
    pack cache so Stage serves it immediately. Body: {drama_id, moment_id, draft:{companion_lead, replies}}."""
    payload = await request.json()
    draft = payload.get("draft") or {}
    try:
        drama_id = _safe_id(payload.get("drama_id") or "yunmiao", "drama_id")
        moment_id = str(payload.get("moment_id") or "")
        if moment_id and not _SAFE_ID.match(moment_id):
            raise ValueError("invalid moment_id")
    except ValueError as exc:
        return JSONResponse({"error": {"code": "studio_bad_request", "message": str(exc)}}, status_code=400)
    violations = _review_violations(draft)
    if violations:  # backend publish gate — a direct POST can't bypass the lead-shape contract
        return JSONResponse(
            {"error": {"code": "promote_review_failed", "message": "Draft failed the publish review gate.",
                       "violations": violations}}, status_code=400)
    try:
        result = await run_in_threadpool(_promote_to_sandbox, drama_id, moment_id, draft)
        deadman_app.state.deadman_store.reset()  # runtime picks up the new drama on next request
    except Exception as exc:  # data/write failure → structured error, never silent 500
        return _studio_error("studio_promote_failed", exc)
    return result


# ---- Studio producer API (L3/C.1: upload video -> audio -> ASR -> LLM window proposal) ----
# Full bring-your-own-video ingest. Audio extract + window-LLM + (downstream) CAB author + promote
# are all genuinely live via Ark; only the ASR transcript falls back to a bundled sample when no
# Volc speech creds are configured (DOUBAO_SPEECH_API_KEY / VOLC_ASR_API_KEY). Uploads land under
# tmp/ (git-ignored) — never the tracked demo dramas.
STUDIO_UPLOAD_ROOT = BASE_DIR / "tmp" / "studio_uploads"
_ASR_KEY_ENVS = ("DOUBAO_SPEECH_API_KEY", "VOLC_ASR_API_KEY", "VOLC_API_KEY")
_ASR_UID_ENVS = ("DOUBAO_SPEECH_UID", "VOLC_ASR_UID", "VOLC_UID")
_WINDOW_SYS_PROMPT = (
    "你是短剧『看剧搭子』的互动窗口选取器。给你一段剧集字幕（每条含起止毫秒 + 文本）。"
    "请挑出最适合『搭子接话』的 1–3 个高光窗口——观众此刻情绪被戳中、最想说一句的瞬间。"
    "每个窗口约 18–24 秒，notice_at 落在情绪顶点那句台词附近。只依据字幕里真实出现的台词，"
    "不要虚构后续剧情。为每个窗口给 start_seconds / end_seconds / notice_at_seconds（整数秒）、"
    "scene_signal（≤12 字情绪概括）、rationale（≤30 字依据），按推荐度排序。"
    "必须严格返回 JSON 对象：{\"windows\": [ ... ]}，windows 为数组，不要额外文字。"
)
_WINDOW_SCHEMA = {
    "type": "object",
    "properties": {
        "windows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_seconds": {"type": "integer"},
                    "end_seconds": {"type": "integer"},
                    "notice_at_seconds": {"type": "integer"},
                    "scene_signal": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["start_seconds", "end_seconds", "notice_at_seconds", "scene_signal", "rationale"],
            },
        }
    },
    "required": ["windows"],
}
_EMO_MARKERS = ("！", "!", "？", "?", "站住", "对不起", "难道", "怎么", "居然", "竟然", "凭什么", "心心念念", "孝心")


def _extract_audio(video_path: Path, job_dir: Path) -> Path:
    audio_path = job_dir / "audio.mp3"
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio_path)],
        capture_output=True, timeout=180,
    )
    if proc.returncode != 0 or not audio_path.exists():
        raise RuntimeError("ffmpeg audio extraction failed: " + proc.stderr.decode("utf-8", "ignore")[-300:])
    return audio_path


def _video_duration_seconds(video_path: Path) -> int | None:
    """Real playable length via ffprobe — used to clamp proposed windows to the uploaded clip."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
            capture_output=True, timeout=30,
        )
        dur = float(proc.stdout.decode("utf-8", "ignore").strip() or 0)
        return int(dur) if dur > 0 else None
    except Exception:
        return None


def _run_asr(audio_path: Path) -> tuple[dict, str]:
    """Cloud ASR via Volcengine 豆包/Seed-ASR 录音文件识别 (flash) when speech creds are set;
    else the bundled demo sample transcript. Cloud-only so the product ships without per-host deps."""
    api_key = next((os.environ[k] for k in _ASR_KEY_ENVS if os.environ.get(k)), "")
    if api_key:
        try:
            import sys
            sys.path.insert(0, str(BASE_DIR))
            from tools.ars.deadman_volc_asr_flash import (
                _recognize, _normalize, DEFAULT_ENDPOINT, DEFAULT_RESOURCE_ID,
            )
            uid = next((os.environ[k] for k in _ASR_UID_ENVS if os.environ.get(k)), "deadman-ars")
            raw = _recognize(audio_path, api_key=api_key, uid=uid, endpoint=DEFAULT_ENDPOINT, resource_id=DEFAULT_RESOURCE_ID)
            norm = _normalize(raw, audio_path=audio_path)
            if norm.get("utterances"):
                return norm, "live_volc_flash"
        except Exception:
            pass  # fall through to the bundled sample
    return _read_json(BASE_DIR / "data/studio_samples/sample_transcript.v0.1.json"), "sample_fallback"


def _window_excerpt(transcript: dict, start_s: int, end_s: int) -> str:
    lo, hi = start_s * 1000, end_s * 1000
    parts = [
        u.get("text", "") for u in (transcript.get("utterances") or [])
        if int(u.get("start_time", 0)) < hi and int(u.get("end_time", 0)) > lo
    ]
    return " ".join(p for p in parts if p)[:160]


def _sanitize_windows(windows: list, transcript: dict, max_seconds: int | None = None) -> list[dict]:
    t_dur = int((transcript.get("duration") or 0) / 1000) or None
    caps = [d for d in (max_seconds, t_dur) if d]  # clamp to the tighter of real video + transcript length
    dur_s = min(caps) if caps else None
    out: list[dict] = []
    for w in (windows or [])[:3]:
        try:
            s = max(0, int(w.get("start_seconds", 0)))
            e = int(w.get("end_seconds", s + 20))
            n = int(w.get("notice_at_seconds", s))
        except (TypeError, ValueError):
            continue
        if e <= s:
            e = s + 20
        if dur_s:
            e = min(e, dur_s)
            s = min(s, max(0, e - 5))
        n = min(max(n, s), e)
        out.append({
            "start_seconds": s, "end_seconds": e, "notice_at_seconds": n,
            "scene_signal": str(w.get("scene_signal", ""))[:24],
            "rationale": str(w.get("rationale", ""))[:60],
            "transcript_excerpt": _window_excerpt(transcript, s, e),
        })
    return out


def _heuristic_windows(transcript: dict, max_seconds: int | None = None) -> list[dict]:
    utts = transcript.get("utterances") or []
    best = None
    for u in utts:
        start_s = int(int(u.get("start_time", 0)) / 1000)
        if start_s < 8:  # skip the cold open — climax is rarely the first line
            continue
        if max_seconds and start_s > max_seconds - 4:  # peak must fit inside the real clip
            continue
        text = u.get("text", "")
        score = sum(text.count(m) for m in _EMO_MARKERS) + len(text) / 40.0
        if best is None or score > best[0]:
            best = (score, start_s)
    if best is None:
        return []
    _, peak = best
    s = max(0, peak - 5)
    return _sanitize_windows(
        [{"start_seconds": s, "end_seconds": s + 20, "notice_at_seconds": peak,
          "scene_signal": "情绪高点（启发式）", "rationale": "字幕情绪标记密度最高处"}],
        transcript, max_seconds,
    )


def _extract_windows_from_payload(payload: object) -> list:
    """Tolerant: prefer payload['windows']; else the first list-of-objects value the model returned."""
    if not isinstance(payload, dict):
        return []
    wins = payload.get("windows")
    if isinstance(wins, list):
        return wins
    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


def _propose_windows(transcript: dict, max_seconds: int | None = None) -> tuple[list[dict], str]:
    """LLM (Ark) window proposal over the ASR transcript, retried for reliability; deterministic
    emotional-density heuristic only if every Ark attempt fails or returns nothing usable."""
    utts = transcript.get("utterances") or []
    compact = [
        {"start_ms": u.get("start_time"), "end_ms": u.get("end_time"), "text": u.get("text", "")}
        for u in utts
    ]
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider
        provider = ArkStudioProofProvider.from_env()
        prompt = {"system_prompt": _WINDOW_SYS_PROMPT, "task": "propose_interaction_windows", "subtitles": compact}
        for _attempt in range(3):
            try:
                result = provider.complete_case(prompt, _WINDOW_SCHEMA)
                raw = _extract_windows_from_payload((result or {}).get("payload"))
                windows = _sanitize_windows(raw, transcript, max_seconds)
                if windows:
                    return windows, "llm_ark"
            except Exception:
                continue
    except Exception:
        pass
    return _heuristic_windows(transcript, max_seconds), "heuristic_fallback"


def _process_upload(job_id: str, job_dir: Path, video_path: Path) -> dict:
    """Blocking: ffmpeg audio extract + remux + ASR + window-LLM (runs in a threadpool)."""
    audio_path = _extract_audio(video_path, job_dir)
    served = _servable_video(video_path, job_dir)  # Stage media route needs .mp4/.mov/.m4v
    video_dur = _video_duration_seconds(served)
    transcript, asr_source = _run_asr(audio_path)
    windows, window_source = _propose_windows(transcript, max_seconds=video_dur)
    if not windows:
        raise RuntimeError("no interaction windows could be proposed from the transcript")
    _write_json(job_dir / "transcript.json", transcript)
    _write_json(job_dir / "meta.json", {
        "video": served.name, "asr_source": asr_source,
        "window_source": window_source, "windows": windows,
    })
    return {
        "job_id": job_id,
        "video": served.name,
        "asr_source": asr_source,
        "window_source": window_source,
        "duration_seconds": video_dur or int((transcript.get("duration") or 0) / 1000),
        "transcript_excerpt": (transcript.get("text") or "")[:240],
        "proposed_windows": windows,
    }


@app.post("/api/studio/upload")
async def studio_upload(file: UploadFile = File(...)):
    """Ingest an uploaded video: extract audio, run ASR (live or sample), and propose interaction
    windows via the window-LLM. Returns {job_id, asr_source, window_source, proposed_windows}."""
    _ensure_provider_env()
    job_id = "up_" + uuid4().hex[:10]  # server-generated; never client-controlled
    job_dir = STUDIO_UPLOAD_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    suffix = (Path(file.filename or "video.mp4").suffix or ".mp4").lower()
    video_path = job_dir / ("source" + suffix)
    try:  # all heavy work off the event loop so a Studio upload can't freeze concurrent viewer requests
        data = await file.read()
        await run_in_threadpool(video_path.write_bytes, data)
        return await run_in_threadpool(_process_upload, job_id, job_dir, video_path)
    except Exception as exc:  # ffmpeg/ASR/provider/data failure → structured error, never silent 500
        return _studio_error("studio_upload_failed", exc)


# ---- Studio producer API (L3/C.3 + C.4: author + promote an UPLOADED-video window) ----------
def _servable_video(video_path: Path, job_dir: Path) -> Path:
    """The Stage media route only serves .mp4/.mov/.m4v under tmp/. Remux anything else to .mp4."""
    if video_path.suffix.lower() in {".mp4", ".mov", ".m4v"}:
        return video_path
    mp4 = job_dir / "source.mp4"
    proc = subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-c", "copy", str(mp4)],
                          capture_output=True, timeout=180)
    if proc.returncode != 0 or not mp4.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(video_path), str(mp4)], capture_output=True, timeout=300)
    if not mp4.exists():
        raise RuntimeError("could not produce a playable mp4 from the upload")
    return mp4


def _build_upload_moment(job_id: str, window: dict) -> tuple[dict, dict, dict, str, str]:
    """Construct a runtime moment skeleton from an uploaded job + a chosen window (no draft yet)."""
    job_id = _safe_id(job_id, "job_id")
    job_dir = STUDIO_UPLOAD_ROOT / job_id
    if not (job_dir / "transcript.json").exists():
        raise ValueError(f"upload job '{job_id}' not found")
    transcript = _read_json(job_dir / "transcript.json")
    meta = _read_json(job_dir / "meta.json") if (job_dir / "meta.json").exists() else {}
    video = str(meta.get("video") or "source.mp4")
    llm_start = max(0, int(window.get("start_seconds", 0)))
    llm_end = int(window.get("end_seconds", llm_start + 20))
    peak = int(window.get("notice_at_seconds", llm_start))
    if not (llm_start <= peak <= llm_end):
        peak = llm_start
    # Player requires notice_at <= start <= end (Branch3PlayerDemo.readInteractionWindow). The LLM
    # puts notice_at at the emotional peak (mid-window), so open the interaction there and let the
    # "!" marker sit just before it — otherwise the player rejects the window and mistimes the companion.
    start_s = peak
    notice_s = max(0, min(llm_start, peak - 1))
    end_s = max(peak + 6, llm_end)
    excerpt = str(window.get("transcript_excerpt") or _window_excerpt(transcript, notice_s, end_s))
    episode_id = f"{job_id}_ep"
    moment = {
        "pack_id": f"{job_id}_m001", "moment_id": f"{job_id}_m001",
        "schema_version": "moment_causality_pack.v0.1",
        "drama_id": SANDBOX_DRAMA_ID, "drama_context_ref": "context.v0.1.json",
        "source_drama": {
            "title": "控制台上传样片", "episode_id": episode_id, "time_range_seconds": [start_s, end_s],
            "runtime_video_url": f"/api/deadman/media/{SANDBOX_DRAMA_ID}/{episode_id}",
            "media_registry_ref": f"data/dramas/{SANDBOX_DRAMA_ID}/media_registry.v0.1.json#{episode_id}",
        },
        "source_window": {
            # evidence span = the marker span [notice_s, end_s], matching the excerpt text below
            "start_ms": notice_s * 1000, "end_ms": end_s * 1000,
            "transcript_refs": [{
                "id": f"{job_id}_m001_u001", "episode_id": episode_id,
                "start_ms": notice_s * 1000, "end_ms": end_s * 1000,
                "text": excerpt, "source": "uploaded_local_asr_snippet",
            }],
            "keyframe_refs": [], "provenance_status": "uploaded_local_asr",
        },
        "interaction_window": {
            "notice_at_seconds": notice_s, "start_seconds": start_s, "end_seconds": end_s,
            "source": "uploaded_asr_llm_window", "confidence": "medium",
            "pause_policy": "pause_on_invite", "expire_behavior": "return_to_idle",
        },
        "original_plot_note": "原剧情按当前场景推进；互动只接当下这一口气。",
        "companion_surface": {"notice_marker": "!", "companion_lead": "", "hook": ""},
        "action_space": {"action_type": "other", "default_options": [], "mouthpiece_candidates": []},
        "companion_exchange": {
            "schema_version": "companion_exchange_pack.v0.1",
            "scene_signal": excerpt[:120] or str(window.get("scene_signal", "")),
            "window_rationale": excerpt, "notice_marker": "!", "companion_lead": "", "reply_candidates": [],
        },
        "notice_marker": "!",
    }
    return moment, transcript, meta, episode_id, video


def _write_sandbox(moment: dict, *, title: str, cover: str | None, episode_id: str,
                   local_media_path: str, episode_title: str = "样片") -> None:
    """Write a fresh single-moment sandbox drama whose media is the given local path (uploaded video)."""
    out_dir = BASE_DIR / "data" / "dramas" / SANDBOX_DRAMA_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    moment["drama_id"] = SANDBOX_DRAMA_ID
    manifest = {
        "schema_version": "deadman_drama_runtime_manifest.v0.1", "drama_id": SANDBOX_DRAMA_ID, "title": title,
        "cover_image_url": cover,
        "pack_type": "lightweight_drama_context_pack_not_arcforge_world_simulation",
        "moment_packs": {"path": "moments.v0.1.json", "schema_version": "moment_causality_pack.v0.1",
                         "count": 1, "moment_ids": [moment.get("moment_id")]},
        "promoted_dir": f"data/dramas/{SANDBOX_DRAMA_ID}", "source_sandbox_of": "studio_upload",
    }
    context = {
        "schema_version": "drama_context_pack.v0.1", "drama_id": SANDBOX_DRAMA_ID, "title": title,
        "cover_image_url": cover,
        "global_constraints": {"hard_constraints": [
            "answer only current scene or immediate aftermath", "do not claim continuous branch rewrite"]},
    }
    moments_col = {
        "schema_version": "moment_causality_pack_collection.v0.1",
        "collection_schema_version": "moment_causality_pack.v0.1",
        "drama_id": SANDBOX_DRAMA_ID, "title": title, "moment_count": 1, "moments": [moment],
    }
    media_reg = {
        "schema_version": "deadman_media_registry.v0.1", "drama_id": SANDBOX_DRAMA_ID, "title": title,
        "media_policy": "local producer media; runtime serves via runtime_video_url; raw mp4 not committed",
        "episode_count": 1, "registered_count": 1,
        "episodes": [{
            "episode_id": episode_id, "title": episode_title,
            "runtime_video_url": f"/api/deadman/media/{SANDBOX_DRAMA_ID}/{episode_id}", "status": "registered",
            "producer_media": {"local_media_path": local_media_path, "policy": "producer-only local metadata"},
        }],
    }
    _write_json(out_dir / "manifest.v0.1.json", manifest)
    _write_json(out_dir / "context.v0.1.json", context)
    _write_json(out_dir / "moments.v0.1.json", moments_col)
    _write_json(out_dir / "media_registry.v0.1.json", media_reg)


def _run_upload_author(job_id: str, window: dict) -> dict:
    """Blocking: author an uploaded-video window via real 2-stage CAB (runs in a threadpool)."""
    job_id = _safe_id(job_id, "job_id")
    moment, transcript, _meta, episode_id, _video = _build_upload_moment(job_id, window)
    # stage the transcript where author_moment's asr_window() looks, so it authors from the real window
    asr_dir = BASE_DIR / "tmp" / f"ars_{job_id}_analysis" / "volc_asr" / "normalized"
    asr_dir.mkdir(parents=True, exist_ok=True)
    _write_json(asr_dir / f"{episode_id}.json", transcript)
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from tools.ars.deadman_author_drama_heroes import author_moment, ArkStudioProofProvider, load as _load
    guidance = _load(BASE_DIR / "data/datasets/studio_guidance/studio_cab_guidance_dataset.v0.1.json")
    pack = {"title": "控制台上传样片", "moments": [moment]}
    provider = ArkStudioProofProvider.from_env()
    _scene, lead, rcs = author_moment(provider, guidance, job_id, pack, moment)
    return {
        "job_id": job_id, "episode_id": episode_id, "companion_lead": lead,
        "replies": [
            {"display_text": r.get("display_text"), "echo": r.get("selected_echo"),
             "motivation": r.get("viewer_motivation"),
             "coverage": ["core_direction_a", "core_direction_b", "fallback"][i] if i < 3 else "fallback"}
            for i, r in enumerate(rcs)
        ],
    }


@app.post("/api/studio/upload/author")
async def studio_upload_author(request: Request):
    """Author one uploaded-video window via real 2-stage CAB. Body: {job_id, window}."""
    payload = await request.json()
    window = payload.get("window") or {}
    try:
        job_id = _safe_id(payload.get("job_id"), "job_id")
    except ValueError as exc:
        return JSONResponse({"error": {"code": "studio_bad_request", "message": str(exc)}}, status_code=400)
    _ensure_provider_env()
    try:
        return await run_in_threadpool(_run_upload_author, job_id, window)
    except Exception as exc:
        return _studio_error("studio_upload_author_failed", exc)


def _run_upload_promote(job_id: str, window: dict, draft: dict) -> dict:
    """Blocking: build + backfill + write the uploaded-video sandbox drama (runs in a threadpool)."""
    job_id = _safe_id(job_id, "job_id")
    moment, _transcript, _meta, episode_id, video = _build_upload_moment(job_id, window)
    _apply_draft_to_moment(moment, draft)
    moment["companion_exchange"]["scene_signal"] = (
        str(window.get("scene_signal") or moment["companion_exchange"].get("scene_signal", ""))[:24]
    )
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from tools.ars.deadman_backfill_judgment_fields import backfill_moment
    template = _read_json(BASE_DIR / "data/dramas/yunmiao/moments.v0.1.json")["moments"][0]
    backfill_moment(moment, template)
    _write_sandbox(
        moment, title="📝 控制台样片 · 上传", cover=None, episode_id=episode_id,
        local_media_path=f"tmp/studio_uploads/{job_id}/{video}", episode_title="上传样片",
    )
    seek = int(moment["interaction_window"]["start_seconds"])  # land at the peak (= remapped start, in-window)
    return {
        "drama_id": SANDBOX_DRAMA_ID, "title": "📝 控制台样片 · 上传", "moment_id": moment["moment_id"],
        "episode_id": episode_id,
        "stage_url": f"/demo/?branch3_player=1&dramaId={SANDBOX_DRAMA_ID}&episodeId={episode_id}&seek={seek}",
    }


@app.post("/api/studio/upload/promote")
async def studio_upload_promote(request: Request):
    """Promote a reviewed uploaded-video exchange into the sandbox drama, media = the uploaded video.
    Body: {job_id, window, draft:{companion_lead, replies}}."""
    payload = await request.json()
    window = payload.get("window") or {}
    draft = payload.get("draft") or {}
    try:
        job_id = _safe_id(payload.get("job_id"), "job_id")
    except ValueError as exc:
        return JSONResponse({"error": {"code": "studio_bad_request", "message": str(exc)}}, status_code=400)
    violations = _review_violations(draft)
    if violations:  # backend publish gate
        return JSONResponse(
            {"error": {"code": "promote_review_failed", "message": "Draft failed the publish review gate.",
                       "violations": violations}}, status_code=400)
    try:
        result = await run_in_threadpool(_run_upload_promote, job_id, window, draft)
        deadman_app.state.deadman_store.reset()
    except Exception as exc:
        return _studio_error("studio_upload_promote_failed", exc)
    return result


if __name__ == "__main__":
    # Default to loopback — the producer /api/studio/* surface is unauthenticated; opt into a
    # public bind explicitly (e.g. HOST=0.0.0.0) only behind a trusted network.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=port, reload=False)

