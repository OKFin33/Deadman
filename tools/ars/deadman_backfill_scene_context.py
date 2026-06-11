#!/usr/bin/env python3
"""Backfill the layered SCENE CONTEXT card for the 3 reviewed dramas — into a SIDECAR.

The agentic production graph computes a layered SCENE CONTEXT card (build_scene_context:
l0_canon premise/protagonist + l1 this-beat + l3_series_spine + l2_recent_events) for every
window during authoring. The 11 ALREADY-reviewed moments in
data/dramas/{huangnian,lihun,yunmiao} were promoted BEFORE that card was persisted anywhere, so
they carry a reviewed companion_exchange with NO scene_context.

This one-shot backfill recomputes the card ONCE per reviewed moment (the SAME build_scene_context
the graph uses — real Ark for the L1 beat synthesis, static committed canon/memory for L0/L2/L3,
require_grounding=True to match the graph's candidate bridge) and writes it to a per-drama SIDECAR
file ``data/dramas/{id}/scene_context.v0.1.json``:

    {"schema_version": "scene_context.v0.1",
     "drama_id": "{id}",
     "scene_context": {"<moment_id>": <reshaped L0/L1/L2/L3 card>, ...}}

It NEVER mutates ``moments.v0.1.json`` — the reviewed moment packs stay byte-stable. The runtime
(pack_store.get_moment) re-attaches the sidecar card to companion_exchange.scene_context in memory
for the single-moment fetch; the public list/summary path never sees it.

Honest degrade: if the Ark provider is unavailable (no creds), the card still carries the static
L0/L2/L3 layers with an EMPTY l1, instead of crashing — never a fabricated beat.

Idempotent: a moment whose id already has an entry in the sidecar is skipped (re-run is a no-op)
unless --force is passed.

Provider creds come from the environment ONLY (set -a; . ./.env; set +a). Run --dry-run first to
preview which moments would gain a card without writing anything.

  # preview (no provider needed; l1 will be empty without Ark):
  python3 tools/ars/deadman_backfill_scene_context.py --dry-run
  # write the sidecar, with Ark for the l1 beat:
  set -a; . ./.env; set +a
  python3 tools/ars/deadman_backfill_scene_context.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# The 3 reviewed dramas whose moments were promoted before scene_context persistence landed.
DEFAULT_DRAMAS = ("huangnian", "lihun", "yunmiao")

# Sidecar schema/filename shared with promote + pack_store.
SIDECAR_SCHEMA_VERSION = "scene_context.v0.1"
SIDECAR_FILENAME = "scene_context.v0.1.json"


class _NoProvider:
    """Stand-in author provider when Ark creds are absent. Its complete_case raises, which
    build_scene_context catches internally for the L1 beat call — so the card still carries the
    static L0/L2/L3 layers and an EMPTY l1, instead of crashing. (Degraded but honest: we never
    fabricate the this-beat synthesis without the provider.)"""

    name = "no_provider"
    model = "none"

    def complete_case(self, prompt: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("no Ark provider configured (env creds absent); l1 left empty")


def _author_provider(force_no_provider: bool = False):
    """The real Ark provider if creds are present, else a _NoProvider that degrades l1 to empty.

    Returns (provider, available: bool). Never raises on missing creds — the backfill degrades
    rather than failing the whole run."""
    if force_no_provider:
        return _NoProvider(), False
    try:
        from tools.ars.deadman_studio_cab_loop_spike import _load_env

        _load_env()
        from tools.ars.deadman_author_drama_heroes import ArkStudioProofProvider

        return ArkStudioProofProvider.from_env(), True
    except Exception as exc:  # noqa: BLE001 - missing creds / import -> degrade to static-only card
        print(f"[warn] Ark provider unavailable ({type(exc).__name__}: {exc}); "
              "l1 (this-beat) will be left empty, L0/L2/L3 still written.", file=sys.stderr)
        return _NoProvider(), False


def _moment_window_ms(moment: dict[str, Any]) -> tuple[str, int, int]:
    iw = moment.get("interaction_window") or {}
    ep = (moment.get("source_drama") or {}).get("episode_id") or ""
    start_ms = int(float(iw.get("start_seconds") or 0)) * 1000
    end_ms = int(float(iw.get("end_seconds") or 0)) * 1000
    return ep, start_ms, end_ms


def sidecar_path_for(drama_id: str, *, data_root: Path | None = None) -> Path:
    """Path to the per-drama scene_context sidecar, alongside moments.v0.1.json."""
    root = data_root or (REPO / "data" / "dramas")
    return root / drama_id / SIDECAR_FILENAME


def load_sidecar(path: Path, drama_id: str) -> dict[str, Any]:
    """Load an existing sidecar, or return a fresh empty one. Never raises on a missing/corrupt
    file — a fresh sidecar lets the run proceed (the corrupt one is simply overwritten on write)."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("scene_context"), dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "drama_id": drama_id,
        "scene_context": {},
    }


def backfill_drama(
    drama_id: str,
    provider: Any,
    *,
    data_root: Path | None = None,
    write: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Recompute scene_context for one drama's moments and write it to the per-drama SIDECAR.

    Returns a per-drama summary. With write=False (dry-run) the cards are recomputed but the
    sidecar is never persisted. A moment already present in the sidecar is left untouched unless
    force=True (so a re-run is a no-op). It NEVER reads or writes moments.v0.1.json's contents —
    moments.v0.1.json is only read to enumerate moments and is never modified.
    """
    from tools.ars.deadman_author_drama_heroes import build_scene_context
    from tools.ars.deadman_promote_companion_pack import reshape_scene_context

    root = data_root or (REPO / "data" / "dramas")
    path = root / drama_id / "moments.v0.1.json"
    if not path.exists():
        raise FileNotFoundError(f"moments pack not found for drama '{drama_id}': {path}")
    pack = json.loads(path.read_text(encoding="utf-8"))
    title = pack.get("title", "")
    moments = pack.get("moments")
    if not isinstance(moments, list):
        raise ValueError(f"{path} has no moments list")

    sidecar_path = sidecar_path_for(drama_id, data_root=data_root)
    sidecar = load_sidecar(sidecar_path, drama_id)
    cards: dict[str, Any] = sidecar["scene_context"]

    backfilled: list[str] = []
    skipped_existing: list[str] = []
    empty_l1: list[str] = []
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        moment_id = str(moment.get("moment_id") or "")
        if not moment_id:
            continue
        exchange = moment.get("companion_exchange")
        if not isinstance(exchange, dict):
            continue  # no exchange to ground onto; emit-only node never invents one
        if moment_id in cards and not force:
            skipped_existing.append(moment_id)
            continue

        ep, start_ms, end_ms = _moment_window_ms(moment)
        # SAME card the production graph builds (require_grounding=True matches candidate_scene_context).
        card = build_scene_context(provider, drama_id, ep, start_ms, end_ms, title, require_grounding=True)
        shaped = reshape_scene_context(card)
        if not shaped:
            continue
        if not shaped.get("l1"):
            empty_l1.append(moment_id)
        # Write ONLY into the sidecar map keyed by moment_id. moments.v0.1.json is never touched.
        cards[moment_id] = shaped
        backfilled.append(moment_id)

    if write and backfilled:
        sidecar_path.write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {
        "drama_id": drama_id,
        "pack_path": str(path),
        "sidecar_path": str(sidecar_path),
        "backfilled_moment_ids": backfilled,
        "skipped_existing": skipped_existing,
        "empty_l1_moment_ids": empty_l1,
        "written": bool(write and backfilled),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--drama-id", action="append", default=None,
                    help="Limit to specific drama id(s) (repeatable). Default: all 3 reviewed dramas.")
    ap.add_argument("--data-root", default="", help="Override the data/dramas root (e.g. a TMP copy).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Recompute + report what would be written, but do not write the sidecar.")
    ap.add_argument("--force", action="store_true",
                    help="Recompute even when a moment already has a sidecar card (default: skip it).")
    ap.add_argument("--no-provider", action="store_true",
                    help="Skip the Ark provider entirely (write only the static L0/L2/L3 layers).")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    dramas = tuple(args.drama_id) if args.drama_id else DEFAULT_DRAMAS
    data_root = Path(args.data_root) if args.data_root else None
    provider, available = _author_provider(force_no_provider=args.no_provider)

    summaries = []
    for drama_id in dramas:
        summary = backfill_drama(
            drama_id, provider, data_root=data_root, write=not args.dry_run, force=args.force,
        )
        summaries.append(summary)
    out = {
        "dry_run": args.dry_run,
        "provider_available": available,
        "dramas": summaries,
        "total_backfilled": sum(len(s["backfilled_moment_ids"]) for s in summaries),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
