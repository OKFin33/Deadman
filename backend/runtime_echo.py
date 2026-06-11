"""Runtime custom-input echo — bounded runtime adaptation for a viewer's typed line.

The v0.4 product is "我想说一句". For a *preset* reply the echo (搭子接话) is pre-authored
backstage (Stage B). For a *custom* typed line there was no real-time echo; the companion
fell back to a bounded template. This module builds the real-time echo by **re-running Stage B
for this window with `target.display_text` swapped to the viewer's typed line** — same
generator, same v0.3 echo taste, same archived L0–L3 scene context as backstage. Only the text
changes (see docs/context/runtime-custom-echo-contract.md).

Hard fail-safe guarantee: this module NEVER raises into the request path. Any
missing-context / timeout / provider-error / policy-violation degrades to ``None`` so the
caller renders the existing bounded template. The companion is never blocked, the request
never 500s.

Stage-B authoring + provider are imported lazily via the ``Deadman`` namespace shim so the
backend never hard-depends on langgraph/tools at import time, and a missing overlay or import
error degrades to ``None`` rather than crashing the backend.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Any


def _env_off(name: str) -> bool:
    """True only when the gate is *explicitly* turned off."""
    return os.environ.get(name, "").strip().lower() in {"0", "false", "no", "off"}


def _ark_creds_present() -> bool:
    """Mirror ArkCandidateJudgeProvider.from_env() requirements without importing it.

    Default policy per contract: echo is on when an Ark provider is configured, else template.
    Checking here lets us short-circuit (and stay quiet in CI/test) before any tools import.
    """
    api_key = os.environ.get("ARK_API_KEY", "").strip()
    model = (os.environ.get("ARK_MODEL") or os.environ.get("ARK_ENDPOINT_ID") or "").strip()
    return bool(api_key and model)


def runtime_custom_echo(moment: dict[str, Any], custom_say: str) -> str | None:
    """Re-run Stage B for this window with the viewer's typed line; return the echo or ``None``.

    Returns ``None`` (caller falls back to the existing template) when:
      - the env gate ``DEADMAN_RUNTIME_ECHO`` is explicitly off, or no Ark creds are configured;
      - the window has no archived ``companion_exchange.scene_context`` (Part-A backfill absent);
      - the viewer line is low-signal / unsupported / disallowed by ``custom_reply_policy``;
      - the provider times out / errors;
      - the generated echo fails the safety post-check (future-plot / unsupported leakage).

    Never raises: the whole body is wrapped so a viewer request can never 500 or block.
    """
    try:
        return _runtime_custom_echo(moment, custom_say)
    except Exception:  # noqa: BLE001 — fail-safe: any error degrades to the template
        return None


def _runtime_custom_echo(moment: dict[str, Any], custom_say: str) -> str | None:
    # 1. ENV GATE — explicitly off, or no Ark provider configured -> template.
    if _env_off("DEADMAN_RUNTIME_ECHO"):
        return None
    if not _ark_creds_present():
        return None

    # 2. ARCHIVED SCENE CONTEXT — the window's L0–L3 card. Absent -> degrade to template.
    exchange = moment.get("companion_exchange")
    if not isinstance(exchange, dict):
        return None
    scene_context = exchange.get("scene_context")
    if not isinstance(scene_context, dict) or not scene_context:
        return None

    # 3. WINDOW INPUTS from the SAME pack moment (additive read; nothing mutated).
    lead = str(exchange.get("companion_lead") or "").strip()
    reply_candidates = [c for c in exchange.get("reply_candidates", []) if isinstance(c, dict)]
    siblings = [str(c.get("display_text") or "").strip() for c in reply_candidates if c.get("display_text")]
    prior = [str(c.get("selected_echo") or "").strip() for c in reply_candidates if c.get("selected_echo")]

    # 4. PRE-CHECK the viewer line with the SAME helpers friend_voice uses, so the echo only
    #    fires on the supported+groundable path (mirrors the template-fallback branches).
    from .friend_voice import (
        _custom_reply_policy,
        _groundable_custom_input,
        _normalize_custom_input,
    )

    norm = _normalize_custom_input(custom_say)
    # No CONTENT rejection AND no low-signal rejection: a "what happens later?" question, a 改剧情
    # riff, even a casual "哈哈哈" all reach the model — a friend laughs / riffs / speculates along,
    # never says "I didn't get it". The echo is prompt-bounded (never assert future plot as fact)
    # and context-bounded to this window's L0–L3, so it cannot spoil. Only TRULY EMPTY input (after
    # normalization) and an explicit policy opt-out gate out → caller renders the neutral line.
    if not norm:
        return None
    if _custom_reply_policy(moment).get("allowed") is False:
        return None

    # 5. PROVIDER with a per-call ~10s timeout (the in-request judgment runs first + Ark varies under
    #    load, so 4s was too tight and timed out into the template; the FSM "thinking" state covers it).
    #    Reuse Stage-B authoring via the Deadman shim.
    #    Lazy import so a missing overlay / langgraph dep degrades to the template, not a crash.
    from Deadman.tools.ars.deadman_author_drama_heroes import stage_b_prompt
    from Deadman.tools.ars.deadman_run_studio_real_provider_proof import (
        ArkStudioProofProvider,
        stage_b_output_schema,
    )

    try:
        base = ArkStudioProofProvider.from_env()
    except Exception:  # noqa: BLE001 — no creds / config error -> template
        return None
    # Clone the frozen inner with a short timeout and re-wrap (do NOT mutate the frozen dataclass).
    fast = ArkStudioProofProvider(inner=dataclasses.replace(base.inner, timeout_seconds=10.0))

    # 6. Thinking OFF for latency (Doubao-seed-2.0-lite + ARK_DISABLE_THINKING). Read at build time.
    os.environ.setdefault("ARK_DISABLE_THINKING", "1")

    # 7. BUILD the Stage-B prompt by REUSING stage_b_prompt — only target.display_text is swapped.
    moment_id = str(moment.get("moment_id") or moment.get("pack_id") or "")
    scene = {"case_id": f"runtime:{moment_id}", "scene_context": scene_context}
    target = {"display_text": norm, "emotion_role": "", "semantic_role": "", "viewer_motivation": ""}
    prompt = stage_b_prompt(
        scene=scene,
        lead=lead,
        target=target,
        siblings=siblings,
        prior=prior,
        echoes=[],  # cross-drama style few-shot optional; in-scene reviewed echoes are the real anchor
        feedback=None,
    )
    # Runtime-only rule (injected into the returned prompt, NOT stage_b_prompt's source): this
    # viewer typed their own line and may ask what happens later. React like a co-watching friend —
    # it may guess or say it doesn't know, but must NEVER assert later plot as fact.
    prompt["echo_rules"] = [
        ("这位是自己打字的观众，可能问之后会怎样。你只看到这一刻、不知道后面——像一起追剧的朋友："
         "可以瞎猜或说不知道（我也不晓得／我猜可能／谁说得准呢），但绝不把后续剧情当事实断言"
         "（不说死「他会」「一定」「不会」）。聊到「要是我来改剧情」就打趣岔开，别真编后续。"),
        *prompt.get("echo_rules", []),
    ]

    # 8. ONE Ark call (NOT call_json — that retries 3x and would triple the 4s budget).
    try:
        out = fast.complete_case(prompt, stage_b_output_schema())
    except Exception:  # noqa: BLE001 — timeout / network / parse error -> template
        return None
    payload = out.get("payload") if isinstance(out, dict) else None
    echo = str((payload or {}).get("selected_echo") or "").strip()
    if not echo:
        return None

    # 9. SAFETY POST-CHECK on the generated echo (reuse the same helpers + sanitizer).
    from .friend_voice import _compact_result_text, sanitize_viewer_copy

    clean = sanitize_viewer_copy(echo)  # general viewer-copy cleaner (no content rejection — the
    # prompt keeps the friend from asserting future plot; speculation/uncertainty is allowed).
    if not clean:
        return None
    clean = _compact_result_text(clean, "")
    if not clean:
        return None
    return clean
