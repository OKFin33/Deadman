#!/usr/bin/env python3
"""Backfill judgment fields into slim promoted moment packs.

The light promote tool (deadman_promote_light_drama.py) emitted *slim* moments that
carry list/play/companion_exchange but lack the judgment fields the runtime adapter
needs (outcome_response_contract, canon_baseline, score_axes, local_constraints,
actor_context, result_media, ...). Without them, tapping a preset fails closed with
``adapter_mapping_nonlocal_time_horizon`` (the adapter hits the first missing field).

The viewer surface for a preset tap is the *authored echo* — friend_voice returns the
candidate's ``selected_echo`` for ``preset_candidate`` actions — so the deterministic
verdict/consequence is computed but never surfaced. This backfill therefore only needs
to make the judge *run cleanly* on neutral-but-valid values; it deliberately does NOT
inherit huangnian's drama-specific optional_modules / actors so no huangnian content
leaks into the (internal) verdict.

Structural contracts (outcome_response_contract / judgment_policy / visual_result_policy)
are copied from the huangnian template moment because they are drama-agnostic policy
blocks. Everything drama-specific is derived from the target moment's own data.

Usage:
    python tools/ars/deadman_backfill_judgment_fields.py --drama-id yunmiao
    python tools/ars/deadman_backfill_judgment_fields.py --drama-id lihun --dry-run
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

TEMPLATE_DRAMA = "huangnian"
MOMENTS_FILENAME = "moments.v0.1.json"

# Drama-agnostic policy/contract blocks: safe to copy verbatim from the template.
VERBATIM_FIELDS = ("outcome_response_contract", "judgment_policy", "visual_result_policy")


def _known_facts(moment: dict[str, Any]) -> list[str]:
    evidence = moment.get("evidence") or {}
    facts: list[str] = []
    if isinstance(evidence, dict):
        for key in ("excerpt", "notes"):
            value = evidence.get(key)
            if isinstance(value, str) and value.strip():
                facts.append(value.strip())
    if not facts:
        scene = (moment.get("companion_exchange") or {}).get("scene_signal")
        if scene:
            facts.append(str(scene))
    return facts or ["scene-local evidence only"]


def _result_media(moment: dict[str, Any]) -> dict[str, Any]:
    candidates = (moment.get("companion_exchange") or {}).get("reply_candidates") or []
    slots = [
        {
            "option_index": index,
            "status": "placeholder",
            "image_url": "",
            "prompt": f"{moment.get('moment_id')} option {index}: {candidate.get('display_text', '')}",
            "source": "manual_placeholder",
            "fallback_text": "P0 result image slot reserved; render text consequence when no image is available.",
        }
        for index, candidate in enumerate(candidates)
        if isinstance(candidate, dict)
    ]
    return {
        "preset_options": slots,
        "custom_action": {
            "status": "not_requested",
            "mode": "realtime_generate_or_text_only_fallback",
            "timeout_ms": 8000,
        },
    }


def backfill_moment(moment: dict[str, Any], template: dict[str, Any]) -> list[str]:
    """Add missing judgment fields in-place; return the list of fields added."""
    added: list[str] = []
    exchange = moment.get("companion_exchange") or {}

    for field in VERBATIM_FIELDS:
        if field not in moment and field in template:
            moment[field] = copy.deepcopy(template[field])
            added.append(field)

    if "optional_modules" not in moment:
        # Empty: keeps the (unsurfaced) verdict generic; no huangnian resource framing.
        moment["optional_modules"] = {}
        added.append("optional_modules")

    if "canon_baseline" not in moment:
        own_plot = moment.get("original_plot_note") or "原剧情按当前场景推进；互动只接当下这一口气。"
        moment["canon_baseline"] = {
            "original_action": "原剧情按当前场景自然推进，没有替观众把话说满。",
            "original_rationale": "这一拍的张力靠场面本身，不需要额外动作改写。",
            "audience_tension": str(exchange.get("scene_signal") or "观众想接住这口气"),
            "original_plot_note": str(own_plot),
        }
        added.append("canon_baseline")

    if "actor_context" not in moment:
        moment["actor_context"] = {
            "pov_actor": "主角",
            "directly_affected_actors": [],
            "relationship_context": str(exchange.get("scene_signal") or ""),
            "local_emotional_pressure": str(exchange.get("companion_lead") or exchange.get("scene_signal") or ""),
        }
        added.append("actor_context")

    if "local_constraints" not in moment:
        moment["local_constraints"] = {
            "known_facts": _known_facts(moment),
            "unknown_or_hidden_facts": ["later-episode branch outcomes", "facts outside this window"],
            "risk_notes": [],
            "hard_constraints": ["current_scene_only"],
        }
        added.append("local_constraints")

    if "score_axes" not in moment:
        moment["score_axes"] = {
            "emotion_heat": 80,
            "choice_leverage": 58,
            "causal_clarity": 70,
            "world_constraint_value": 68,
            "watch_flow_fit": 80,
            "visual_result_fit": 50,
        }
        added.append("score_axes")

    if "result_media" not in moment:
        moment["result_media"] = _result_media(moment)
        added.append("result_media")

    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drama-id", required=True, help="target drama (e.g. yunmiao, lihun)")
    parser.add_argument("--root", default="data/dramas", help="dramas root directory")
    parser.add_argument("--dry-run", action="store_true", help="print the first backfilled moment, do not write")
    args = parser.parse_args()

    root = Path(args.root)
    template = json.loads((root / TEMPLATE_DRAMA / MOMENTS_FILENAME).read_text(encoding="utf-8"))["moments"][0]
    path = root / args.drama_id / MOMENTS_FILENAME
    data = json.loads(path.read_text(encoding="utf-8"))
    moments = data["moments"] if isinstance(data, dict) else data

    fields_added: set[str] = set()
    for moment in moments:
        fields_added.update(backfill_moment(moment, template))

    if args.dry_run:
        print(json.dumps(moments[0], ensure_ascii=False, indent=2))
        print(f"\n# would backfill {len(moments)} moments; fields touched: {sorted(fields_added)}")
        return 0

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"backfilled {len(moments)} moments in {path} (fields: {sorted(fields_added)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
