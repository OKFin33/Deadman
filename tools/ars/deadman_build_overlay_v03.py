#!/usr/bin/env python3
"""Step3 of the v0.3 rebuild: coherent re-clustering of the全量 taste labels into a self-consistent
overlay v0.3 PROPOSAL (方案①: LLM proposes -> owner edits -> finalize).

Input  : data/review/taste_labels_full.v0.1.json (checkpoint① output) + overlay v2 (prior taxonomy/gold).
Output : data/datasets/studio_guidance/studio_cab_taste_overlay.v0.3.json  (status=proposed_awaiting_owner).
         --dry-run instead writes data/review/overlay_v03_dryrun.v0.1.json (prompt + deterministic parts,
         NO provider call) so the assembly can be verified before spending a live call.

owner checkpoint① rulings (binding — see docs/context/dataset-rebuild-v03-contract.md):
  1. v0.3 true gold = ONLY owner-confirmed (~65). Provisional (draft/phase2_repair/runtime) NOT gold.
  2. The 7 owner-rejected echoes (verbatim v1 runtime_reviewed "gold") + runtime provisional -> fed as
     named-negative material. (They are already verdict=reject in the全量, so they ride the reject pool.)
  3. dedup key was (layer, text) -> cross-source taste flips surface as conflicts (kept in the全量).

口径: method professional + self-consistent; N small/medium fine; NEVER claim data volume. The LLM only
PROPOSES the taxonomy; the owner is the taste authority and edits before this becomes real.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

FULL = REPO / "data/review/taste_labels_full.v0.1.json"
OVERLAY_V2 = REPO / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.2.json"
OUT_V03 = REPO / "data/datasets/studio_guidance/studio_cab_taste_overlay.v0.3.json"
DRYRUN = REPO / "data/review/overlay_v03_dryrun.v0.1.json"

# ruling #1: owner-confirmed provenances only count as true gold.
OWNER_PROV = {"owner_confirmed", "inplayer_element", "owner_tray"}

# --- mechanical cleanup spec (owner: "I do mechanical, you taste-review") -----------------------
# moment-layer patterns the model mislabeled -> their true layer (kept; they fill real gaps).
RELABEL = {
    "echo_verbatim_paraphrase": "echo",                 # fills echo's missing pure-paraphrase pattern
    "lead_explicit_scene_topic_naming": "companion_lead",
    "display_text_break_audience_knowledge_state": "display_text",
}
# (drop_this, into_this) — exact-duplicate failures fold together.
MERGE = [("echo_catch_overused_template", "echo_formulaic_template_overuse")]
# author the when/corrected_direction the model left blank (display layer), matching the layer's style.
FILL = {
    "rpg_action_menu_rewrite_plot": {
        "when": "The line tells a character what to do or proposes a plot tactic (先护住她 / 证据先上桌) instead of voicing the viewer's own reaction.",
        "corrected_direction": "Rewrite as the viewer's spontaneous feeling about the scene (吐槽/心疼/期待) — never an instruction or plan for the characters."},
    "producer_meta_analysis_not_viewer_speech": {
        "when": "The line evaluates the show's writing/pacing or labels a plot function (点出原主偏心后果 / 别太煽) — a creator/analyst voice.",
        "corrected_direction": "Drop the production framing; react to the characters in-the-moment the way an ordinary viewer would."},
    "emotional_axis_label_no_viewer_voice": {
        "when": "The output is a bare stance/emotion tag (吐槽原主吃独食 / 骂赖账太欠) — authoring metadata, not a spoken line.",
        "corrected_direction": "Expand the tag into a complete, casual line the viewer would actually choose to send."},
    "duplicate_or_paraphrase_of_lead_or_other_candidates": {
        "when": "The display text restates the companion lead, or repeats a stance another candidate in the same set already covers.",
        "corrected_direction": "Give this slot a distinct viewer angle (different emotion/target) so the three candidates stay non-overlapping."},
    "flat_low_emotion_unnatural_wording": {
        "when": "The line reads as a flat, abstract summary (孩子太容易满足 / 他这反应有点戳人) with little spoken feel or stance.",
        "corrected_direction": "Re-voice it as a warm, casual line with visible feeling, the way one mutters it to a friend."},
    "exaggerated_or_misaligned_tone": {
        "when": "The line is overdramatic for the beat or tacks on a redundant commentary tail (…太让人心软了).",
        "corrected_direction": "Dial the tone back to the restrained level the beat calls for; cut the trailing commentary."},
    "ambiguous_or_factual_error_subject": {
        "when": "The line's referent is unclear or misnames the on-screen subject/item versus the current scene.",
        "corrected_direction": "Pin the line to the exact on-screen subject so it maps cleanly to what they're watching."},
}
# taste calls left to the owner (flagged, NOT auto-applied).
MERGE_CANDIDATES = [
    {"layer": "companion_lead", "consider": ["lead_uses_question_form_as_opener (soft)",
     "lead_uses_explicit_questionnaire_or_ui_label (hard)"],
     "note": "都在拒『问句/答题式』lead——一条还是两条由你定（severity 也不同 soft vs hard）"},
    {"layer": "companion_lead", "consider": ["lead_misaligned_to_short_drama_viewer_rhythm (soft)"],
     "note": "pattern 偏虚、单例低信号——看是否删，或并入别的 lead 模式"},
    {"layer": "companion_lead", "consider": ["lead_uses_overly_harsh_high_risk_language (soft)"],
     "note": "更像内容安全约束而非口味失败——看是否留在 taste 集"},
]


def _load_env():
    for v in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        os.environ.pop(v, None)
    env = REPO / ".env"
    if env.exists() and not os.environ.get("ARK_API_KEY"):
        for raw in env.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, val = s.partition("=")
                os.environ.setdefault(k.strip(), val.strip())
    # Doubao-seed spends output tokens on "thinking" -> long taxonomies truncate. Disable it so the
    # whole output budget goes to the JSON (clustering is well-specified; owner edits the result anyway).
    os.environ.setdefault("ARK_DISABLE_THINKING", "1")


def _is_owner_gold(r: dict) -> bool:
    p = r.get("provenance", "")
    return r.get("verdict") == "gold" and (p in OWNER_PROV or p.startswith("owner"))


def partition(full: dict) -> tuple[dict, list, list]:
    """-> (rejects_by_layer, owner_gold_records, dropped_provisional_gold)."""
    rejects_by_layer: dict = {}
    owner_gold, provisional = [], []
    for r in full.get("records", []):
        if r.get("verdict") == "reject":
            rejects_by_layer.setdefault(r.get("layer", "?"), []).append(r)
        elif r.get("verdict") == "gold":
            (owner_gold if _is_owner_gold(r) else provisional).append(r)
    return rejects_by_layer, owner_gold, provisional


LAYER_CN = {
    "companion_lead": "搭子开场引子（搭子先开口的一句，邀请观众接话）",
    "display_text": "观众自己想说的一句（观众点选的、代他说出口的话）",
    "echo": "搭子对某条观众选择的回应（接住观众那句、再延伸）",
    "moment": "整段方向（owner 在 moment 粒度记的备注，多与 echo 复述/腔调有关）",
}


def _instances(instances: list) -> list:
    """Compact, verbatim reject instances for ONE layer's clustering prompt."""
    return [{
        "id": f"{r.get('source')}:{r.get('item_id', '')}:{r.get('element', '')}",
        "text": r.get("text", ""),
        "owner_note": r.get("note", ""),
        "existing_tag": r.get("pattern") or "",
        "scene": (r.get("scene") or "")[:120],
    } for r in instances]


def build_prompt(layer: str, instances: list, prior_negatives: list, addenda: dict) -> dict:
    """Per-layer prompt (keeps each output small enough to not truncate)."""
    return {
        "system_prompt": (
            "You curate a self-consistent taste FAILURE-PATTERN taxonomy for ONE layer of 看剧搭子 (a short-drama "
            "watching-companion). Product thesis: the viewer says the line the scene made them want to say "
            "(我想说一句) — NOT choosing a plot branch / 改剧情 (an archived anti-pattern; RPG/action-menu phrasing "
            "like 先护住她/证据先上桌/别让她白挨 is a HARD breach). Given the owner's FULL history of rejected lines "
            "for THIS layer (v1+v2+new in-player) plus the prior taxonomy for this layer, produce a mutually-"
            "exclusive set of named_negatives that folds duplicates together (e.g. the many one-off exaggeration / "
            "paraphrase / meta-commentary variants -> single well-named patterns). Return ONE strict JSON object, "
            "no prose."),
        "task": f"recluster_owner_rejections_for_layer::{layer}",
        "layer": layer,
        "layer_meaning": LAYER_CN.get(layer, layer),
        "binding_constraints": [
            "Each named_negative = a generalizable failure SITUATION for THIS layer, never a verbatim string.",
            "MUTUALLY EXCLUSIVE within this layer: merge semantic duplicates; cite merges_from.",
            "severity='hard' if it breaks the core thesis (RPG/action-menu/改剧情/overclaim/meta-commentary on the "
            "show); else 'soft_preference'.",
            "illustrative_examples: copy AT MOST 3 verbatim from the instances (do not invent).",
            "source_provenance: at most 4 instance ids you grouped. merges_from: prior negative_type names folded in.",
            "Prefer ~4-8 strong patterns; do not pad with singletons.",
        ],
        "prior_taxonomy_for_this_layer": prior_negatives,
        "prior_rules_addenda": addenda,
        "owner_rejected_instances": _instances(instances),
        "output_contract": {"named_negatives": [{
            "negative_type": "echo_rpg_or_action_menu", "severity": "hard",
            "when": "...", "pattern": "...", "why_bad": "...", "corrected_direction": "...",
            "illustrative_examples": ["..."], "source_provenance": ["source:item:element"],
            "merges_from": ["old_negative_type"]}]},
    }


def build_schema() -> dict:
    props = {k: {"type": "string"} for k in
             ("negative_type", "severity", "when", "pattern", "why_bad", "corrected_direction")}
    props["illustrative_examples"] = {"type": "array", "items": {"type": "string"}}
    props["source_provenance"] = {"type": "array", "items": {"type": "string"}}
    props["merges_from"] = {"type": "array", "items": {"type": "string"}}
    item = {"type": "object", "properties": props,  # layer is injected by us, not required from the model
            "required": ["negative_type", "severity", "when", "pattern", "why_bad", "corrected_direction"]}
    return {"type": "object", "properties": {"named_negatives": {"type": "array", "items": item}},
            "required": ["named_negatives"]}


def _norm(t: str) -> str:
    return re.sub(r"\s+", "", t or "").rstrip("。.!！?？，,、")


def guard_gold(v: dict, full: dict) -> list:
    """Cross-check: no gold COPY (examples or exemplars) may reuse an owner-rejected line.
    This is the gap that let the lihun gold_examples slip through (carried gold not decomposed into records)."""
    rej: dict = {}
    for r in full.get("records", []):
        if r.get("verdict") == "reject" and r.get("layer") in ("companion_lead", "display_text", "echo"):
            rej.setdefault(r["layer"], {})[_norm(r.get("text", ""))] = {
                "item_id": r.get("item_id"), "note": r.get("note", "")}
    col: list = []

    def check(layer, text, where):
        k = _norm(text)
        if k and k in rej.get(layer, {}):
            col.append({"where": where, "layer": layer, "text": text, "rejected_as": rej[layer][k]})

    for g in v.get("gold_examples", []):
        mid = g.get("moment_id")
        check("companion_lead", g.get("companion_lead", ""), f"gold_example:{mid}:lead")
        for i, c in enumerate(g.get("reply_candidates", []), 1):
            check("display_text", c.get("display_text", ""), f"gold_example:{mid}:say{i}")
            check("echo", c.get("selected_echo", ""), f"gold_example:{mid}:echo{i}")
    for e in v.get("gold_exemplars", []):
        check(e.get("layer"), e.get("text", ""), f"gold_exemplar:{e.get('item_id')}")
    return col


def _gold_exemplars(owner_gold: list) -> list:
    """Element-level owner-confirmed positives (lighter than full-moment gold_examples)."""
    seen, out = set(), []
    for r in owner_gold:
        key = (r.get("layer"), r.get("text"))
        if r.get("text") and key not in seen:
            seen.add(key)
            out.append({"layer": r.get("layer"), "text": r.get("text"),
                        "note": r.get("note", ""), "provenance": r.get("provenance", ""),
                        "item_id": r.get("item_id", "")})
    return out


def _window_negatives(window_rejects: list) -> list:
    return [{"text": r.get("text", ""), "pattern": r.get("pattern") or "",
             "note": r.get("note", ""), "scene": (r.get("scene") or "")[:140],
             "source": r.get("source", ""), "item_id": r.get("item_id", "")} for r in window_rejects]


def assemble_v03(named_negatives: list, overlay_v2: dict, owner_gold: list,
                 rejects_by_layer: dict, provisional_n: int, window_rejects: list | None = None) -> dict:
    window_rejects = window_rejects or []
    addenda = {k: overlay_v2.get(k) for k in overlay_v2 if k.endswith("_rules_addendum")}
    return {
        "schema_version": "studio_cab_taste_overlay.v0.3",
        "status": "proposed_awaiting_owner_review",
        "method": "方案①: LLM re-clustered the FULL owner-rejection history into one self-consistent taxonomy; "
                  "OWNER edits before this is finalized. Method-professional + self-consistent; N small/medium; "
                  "NOT a data-volume claim.",
        "base_frozen": "studio_cab_guidance_dataset.v0.1.json (owner_reviewed_v1_frozen — do NOT mutate)",
        "supersedes": "studio_cab_taste_overlay.v0.2.json",
        "owner_rulings_applied": {
            "gold": "true gold = owner-confirmed only",
            "rejected_v1_gold": "owner-flipped lines fed as named-negative material",
            "dedup_key": "(layer, text)",
        },
        "build_meta": {
            "copy_reject_instances_clustered": sum(len(v) for v in rejects_by_layer.values()),
            "copy_reject_by_layer": {k: len(v) for k, v in rejects_by_layer.items()},
            "window_negatives_carried": len(window_rejects),
            "owner_gold_kept": len(owner_gold),
            "provisional_gold_excluded": provisional_n,
            "named_negatives_count": len(named_negatives),
        },
        "reflow_mechanism": overlay_v2.get("reflow_mechanism", ""),
        **addenda,
        "named_negatives": named_negatives,
        "gold_examples": overlay_v2.get("gold_examples", []),  # 4 owner-confirmed full moments, carried
        "gold_exemplars": _gold_exemplars(owner_gold),         # element-level owner-confirmed positives
        # window/direction taste kept SEPARATE from the copy taxonomy (not LLM-clustered this round)
        "window_negatives": _window_negatives(window_rejects),
    }


def run(dry_run: bool) -> int:
    if not FULL.exists():
        print(f"missing {FULL} — run deadman_harvest_taste_labels.py first")
        return 1
    full = json.loads(FULL.read_text(encoding="utf-8"))
    overlay_v2 = json.loads(OVERLAY_V2.read_text(encoding="utf-8")) if OVERLAY_V2.exists() else {}
    rejects_by_layer, owner_gold, provisional = partition(full)
    # window-selection negatives are a different KIND (when NOT to open) — keep them OUT of the copy
    # taxonomy and carry separately, per contract「window/direction 另列」.
    copy_rejects = {l: r for l, r in rejects_by_layer.items() if l != "window"}
    window_rejects = rejects_by_layer.get("window", [])
    prior = overlay_v2.get("named_negatives", [])
    addenda = {k: overlay_v2.get(k) for k in overlay_v2 if k.endswith("_rules_addendum")}
    # ONE prompt per copy layer (small outputs that won't truncate); each reconciles that layer's priors.
    prompts = {layer: build_prompt(layer, recs, [n for n in prior if n.get("layer") == layer], addenda)
               for layer, recs in copy_rejects.items()}

    n_copy = sum(len(v) for v in copy_rejects.values())
    print(f"copy rejects to cluster: {n_copy}  by layer: {{ {', '.join(f'{k}:{len(v)}' for k, v in copy_rejects.items())} }}")
    print(f"window rejects (carried separately): {len(window_rejects)}")
    print(f"owner gold kept: {len(owner_gold)}   provisional gold excluded: {len(provisional)}")
    print(f"prior taxonomy to reconcile: {len(prior)} named_negatives")

    if dry_run:
        DRYRUN.parent.mkdir(parents=True, exist_ok=True)
        DRYRUN.write_text(json.dumps({
            "note": "DRY RUN — no provider call. Verify the per-layer prompts + deterministic gold before --live.",
            "prompts_by_layer": prompts, "schema": build_schema(),
            "owner_gold_exemplars_preview": _gold_exemplars(owner_gold)[:8],
            "gold_examples_carried": len(overlay_v2.get("gold_examples", [])),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDRY RUN -> {DRYRUN.relative_to(REPO)}  (inspect, then re-run --live)")
        return 0

    _load_env()
    from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider
    from tools.ars.deadman_author_drama_heroes import call_json
    provider = ArkStudioProofProvider.from_env()
    named: list = []
    for layer, recs in copy_rejects.items():
        out = call_json(provider, prompts[layer], build_schema())
        layer_negs = out.get("named_negatives", []) if isinstance(out, dict) else []
        for n in layer_negs:
            n.setdefault("layer", layer)
        named += layer_negs
        print(f"  {layer}: {len(recs)} rejects -> {len(layer_negs)} patterns")
    if not named:
        print("LLM returned no named_negatives — aborting (not writing v0.3).")
        return 1
    v03 = assemble_v03(named, overlay_v2, owner_gold, copy_rejects, len(provisional), window_rejects)
    OUT_V03.write_text(json.dumps(v03, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_V03.relative_to(REPO)}  ({len(named)} named_negatives, "
          f"{len(v03['gold_examples'])} gold_examples, {len(v03['gold_exemplars'])} gold_exemplars)")
    print("status=proposed_awaiting_owner_review — STOP. Owner edits (方案①) before finalize. v1 frozen untouched.")
    return 0


def cmd_cleanup() -> int:
    """Apply the mechanical cleanup spec to the v0.3 proposal (relabel / merge dup / fill blanks)."""
    if not OUT_V03.exists():
        print(f"missing {OUT_V03} — run --live first")
        return 1
    v = json.loads(OUT_V03.read_text(encoding="utf-8"))
    negs = v.get("named_negatives", [])
    by_type = {n.get("negative_type"): n for n in negs}

    merged = []
    for drop, into in MERGE:
        if drop in by_type and into in by_type:
            src, dst = by_type[drop], by_type[into]
            exs = dst.setdefault("illustrative_examples", [])
            exs.extend(e for e in src.get("illustrative_examples", []) if e not in exs)
            dst.setdefault("merges_from", []).extend(src.get("merges_from", []) + [drop])
            merged.append(f"{drop} -> {into}")
    drop_set = {d for d, _ in MERGE}
    negs = [n for n in negs if n.get("negative_type") not in drop_set]

    relabeled, filled = [], []
    for n in negs:
        nt = n.get("negative_type")
        if nt in RELABEL:
            n["layer"] = RELABEL[nt]
            relabeled.append(f"{nt} -> {RELABEL[nt]}")
        f = FILL.get(nt)
        if f:
            if not n.get("when"):
                n["when"] = f["when"]
            if not n.get("corrected_direction"):
                n["corrected_direction"] = f["corrected_direction"]
            filled.append(nt)

    v["named_negatives"] = negs
    v["status"] = "proposed_cleaned_awaiting_owner_taste"
    v["cleanup_log"] = {"merged": merged, "relabeled": relabeled, "filled_when_fix": filled,
                        "note": "mechanical only (non-taste). Owner does the taste pass next; see merge_candidates_for_owner."}
    v["merge_candidates_for_owner"] = MERGE_CANDIDATES
    v.get("build_meta", {})["named_negatives_count"] = len(negs)
    OUT_V03.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    bl = {}
    for n in negs:
        bl[n.get("layer")] = bl.get(n.get("layer"), 0) + 1
    print(f"cleaned -> {OUT_V03.relative_to(REPO)}  ({len(negs)} named_negatives, by layer: {bl})")
    print(f"  merged: {merged}")
    print(f"  relabeled: {relabeled}")
    print(f"  filled when/fix: {filled}")
    print(f"  merge_candidates flagged for owner: {len(MERGE_CANDIDATES)}")
    print("status=proposed_cleaned_awaiting_owner_taste — owner taste pass next (方案①).")
    return 0


REVIEW_MD = REPO / "data/review/overlay_v03_review.v0.1.md"
_LAYER_TITLE = {"companion_lead": "LEAD（搭子引子）", "display_text": "SAY（我想说的一句）", "echo": "ECHO（搭子回应）"}


def render_md(v: dict) -> str:
    L = []
    L.append(f"# v0.3 味觉数据集 — 人审稿（{v.get('status')}）")
    L.append("> 全文无截断，从头读到尾即可。这是给 owner 做 方案① taste 审的。\n")
    L.append("## 怎么读")
    L.append("- **档位**：🔴 `hard` = 一票挡稿（作者必避 / judge 直接否）；🟡 `soft_preference` = 偏好提示（尽量避 / judge 扣分不否）。")
    L.append("- **例句全是你自己标过的 reject**。你判的是「我归纳的模式对不对、组织得对不对」，不是「这句好不好」。")
    mc = v.get("build_meta", {})
    L.append(f"- 规模：{mc.get('named_negatives_count','?')} 失败模式 · {len(v.get('gold_examples',[]))} 整段 gold · "
             f"{len(v.get('gold_exemplars',[]))} 单句 gold · {mc.get('window_negatives_carried','?')} window 负例（另列）。\n")

    negs = v.get("named_negatives", [])
    bylayer: dict = {}
    for n in negs:
        bylayer.setdefault(n.get("layer"), []).append(n)
    L.append(f"## 一、失败模式 named_negatives（{len(negs)} 条）")
    for layer in ("companion_lead", "display_text", "echo"):
        arr = bylayer.get(layer, [])
        L.append(f"\n### {_LAYER_TITLE.get(layer, layer)} — {len(arr)} 条")
        for n in arr:
            sev = "🔴 hard" if n.get("severity") == "hard" else "🟡 soft"
            L.append(f"\n#### {sev} · `{n.get('negative_type')}`")
            L.append(f"- **说它不行**：{n.get('pattern','')}")
            if n.get("when"):
                L.append(f"- **何时出现**：{n.get('when')}")
            if n.get("why_bad"):
                L.append(f"- **为什么坏**：{n.get('why_bad')}")
            if n.get("corrected_direction"):
                L.append(f"- **该怎么写**：{n.get('corrected_direction')}")
            eg = n.get("illustrative_examples") or []
            if eg:
                L.append("- **你标过的例句**：")
                L.extend(f"    - {e}" for e in eg)
            if n.get("merges_from"):
                L.append(f"- *合并自*：{', '.join(n['merges_from'])}")

    pos = v.get("named_positives", [])
    posl: dict = {}
    for n in pos:
        posl.setdefault(n.get("layer"), []).append(n)
    L.append(f"\n## 二、✅ 正例模式 named_positives（{len(pos)} 条 — 该往哪写，对称负例）")
    for layer in ("companion_lead", "display_text", "echo"):
        arr = posl.get(layer, [])
        L.append(f"\n### {_LAYER_TITLE.get(layer, layer)} — {len(arr)} 条")
        for n in arr:
            L.append(f"\n#### ✓ `{n.get('positive_type')}`")
            L.append(f"- **做对了什么**：{n.get('pattern','')}")
            if n.get("when"):
                L.append(f"- **什么情况**：{n.get('when')}")
            if n.get("why_good"):
                L.append(f"- **为什么好**：{n.get('why_good')}")
            eg = n.get("illustrative_examples") or []
            if eg:
                L.append("- **好例句**：")
                L.extend(f"    - {e}" for e in eg)

    L.append(f"\n## 三、整段参考 gold_examples（{len(v.get('gold_examples',[]))} 个 — 完整交换的形）")
    for g in v.get("gold_examples", []):
        ws = f"  ⚠️ window_status={g['window_status']}" if g.get("window_status") else ""
        L.append(f"\n**{g.get('moment_id')}**{ws}  ·  lead: 「{g.get('companion_lead','')}」")
        for i, c in enumerate(g.get("reply_candidates", []), 1):
            L.append(f"  {i}. 说「{c.get('display_text','')}」 → 搭子接「{c.get('selected_echo','')}」")
    csn = v.get("content_safety_notes", [])
    if csn:
        L.append(f"\n### 内容安全注记（{len(csn)} 条 — 移出 taste 集，属内容安全非口味失败）")
        for c in csn:
            L.append(f"- [{c.get('layer')}] `{c.get('negative_type')}`: {c.get('pattern','')[:80]}")

    wn = v.get("window_negatives", [])
    L.append(f"\n## 四、window/direction 负例（另列，{len(wn)} 条 — 不进 copy taxonomy）")
    for w in wn[:60]:
        tag = f"[{w['pattern']}] " if w.get("pattern") else ""
        note = f" — {w['note']}" if w.get("note") else ""
        L.append(f"- {tag}{w.get('item_id','')}{note}")

    L.append("\n## 五、★ taste 合并候选（已拍：留 question/questionnaire 两条 · 删 misaligned · 移出 harsh）")
    for c in v.get("merge_candidates_for_owner", []):
        L.append(f"- **[{c['layer']}]** {c['consider']}")
        L.append(f"    - {c['note']}")

    cl = v.get("cleanup_log", {})
    L.append(f"\n---\n*机械清理记录*：merged={cl.get('merged')} · relabeled={cl.get('relabeled')} · filled={cl.get('filled_when_fix')}")
    return "\n".join(L)


def cmd_render() -> int:
    if not OUT_V03.exists():
        print(f"missing {OUT_V03} — run --live first")
        return 1
    v = json.loads(OUT_V03.read_text(encoding="utf-8"))
    REVIEW_MD.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_MD.write_text(render_md(v), encoding="utf-8")
    print(f"wrote readable review -> {REVIEW_MD.relative_to(REPO)}  (open this; 全文无截断)")
    return 0


def build_positive_prompt(layer: str, gold_lines: list, do_instead: list, rules) -> dict:
    """Per-layer: cluster owner gold lines into generalizable POSITIVE patterns (symmetric to negatives)."""
    return {
        "system_prompt": (
            "You curate the POSITIVE half of a taste spec for ONE layer of 看剧搭子 (a short-drama watching-"
            "companion). Product thesis: the viewer says the line the scene made them want to say (我想说一句). "
            "Owner labeling only captured good/bad on individual lines, so good lines are raw cases — your job is "
            "to lift them into a few GENERALIZABLE positive patterns (a SITUATION + what the good line does right), "
            "so an author can aim for them. Use three signals: the owner's good lines, the 'do instead' directions "
            "distilled from failures, and the positive rules. Return ONE strict JSON object, no prose."),
        "task": f"cluster_owner_gold_into_positive_patterns::{layer}",
        "layer": layer,
        "layer_meaning": LAYER_CN.get(layer, layer),
        "binding_constraints": [
            "Each named_positive = a generalizable SITUATION + what the good line DOES right, never a verbatim string.",
            "MUTUALLY EXCLUSIVE; prefer ~3-6 strong patterns; do not pad.",
            "illustrative_examples: copy AT MOST 3 verbatim from owner_gold_lines (do not invent).",
            "Tie each pattern to the 我想说一句 thesis; positives are the inverse of the failures, grounded in real good lines.",
        ],
        "owner_gold_lines": gold_lines,
        "do_instead_signals_from_failures": do_instead,
        "positive_rules": rules,
        "output_contract": {"named_positives": [{
            "positive_type": "echo_catches_then_adds_one_detail", "when": "...", "pattern": "...",
            "why_good": "...", "illustrative_examples": ["..."]}]},
    }


def build_positive_schema() -> dict:
    props = {k: {"type": "string"} for k in ("positive_type", "when", "pattern", "why_good")}
    props["illustrative_examples"] = {"type": "array", "items": {"type": "string"}}
    item = {"type": "object", "properties": props,
            "required": ["positive_type", "when", "pattern", "why_good"]}
    return {"type": "object", "properties": {"named_positives": {"type": "array", "items": item}},
            "required": ["named_positives"]}


def cmd_positives() -> int:
    """Cluster owner gold into named_positives (symmetric to negatives); drop the raw gold_exemplars bloat."""
    if not OUT_V03.exists():
        print(f"missing {OUT_V03}")
        return 1
    v = json.loads(OUT_V03.read_text(encoding="utf-8"))
    LAYERS = ("companion_lead", "display_text", "echo")
    gold_by: dict = {l: [] for l in LAYERS}
    for e in v.get("gold_exemplars", []):
        if e.get("layer") in LAYERS and e.get("text") and not str(e["text"]).startswith("taste_"):
            gold_by[e["layer"]].append(e["text"])
    cdir_by: dict = {l: [] for l in LAYERS}
    for n in v.get("named_negatives", []):
        if n.get("layer") in LAYERS and n.get("corrected_direction"):
            cdir_by[n["layer"]].append(n["corrected_direction"])

    _load_env()
    from tools.ars.deadman_run_studio_real_provider_proof import ArkStudioProofProvider
    from tools.ars.deadman_author_drama_heroes import call_json
    provider = ArkStudioProofProvider.from_env()
    positives: list = []
    for layer in LAYERS:
        rules = v.get(f"{layer.replace('companion_lead','lead')}_rules_addendum") or v.get(f"{layer}_rules_addendum")
        prompt = build_positive_prompt(layer, gold_by[layer], cdir_by[layer], rules)
        out = call_json(provider, prompt, build_positive_schema())
        pos = out.get("named_positives", []) if isinstance(out, dict) else []
        for p in pos:
            p.setdefault("layer", layer)
        positives += pos
        print(f"  {layer}: {len(gold_by[layer])} gold + {len(cdir_by[layer])} do-instead -> {len(pos)} positive patterns")
    if not positives:
        print("LLM returned no named_positives — aborting (not modifying v0.3).")
        return 1
    removed = len(v.get("gold_exemplars", []))
    v["named_positives"] = positives
    v.pop("gold_exemplars", None)  # distilled into named_positives; raw lines still in the harvest全量 + v1
    v.setdefault("build_meta", {})["named_positives_count"] = len(positives)
    v["build_meta"]["gold_exemplars_distilled_and_dropped"] = removed
    v.setdefault("taste_deltas", []).append({"by": "owner", "date": "2026-06-10",
        "change": f"正例聚类：{removed} 条 gold_exemplars 蒸馏成 {len(positives)} 条 named_positives（对称负例）；删原始死句。"})
    OUT_V03.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {len(positives)} named_positives, dropped {removed} gold_exemplars -> {OUT_V03.relative_to(REPO)}")
    return 0


def cmd_guard() -> int:
    """Gate: fail if any gold COPY reuses an owner-rejected line."""
    if not OUT_V03.exists() or not FULL.exists():
        print("missing v0.3 or全量 — run --live / harvest first")
        return 1
    v = json.loads(OUT_V03.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))
    col = guard_gold(v, full)
    if not col:
        print("✓ guard pass — no gold element reuses an owner-rejected line.")
        return 0
    print(f"✗ guard FAIL — {len(col)} gold element(s) match owner rejects:")
    for c in col:
        ra = c["rejected_as"]
        print(f"  {c['where']} [{c['layer']}] 「{c['text'][:42]}」 ← rejected ({ra.get('item_id')}: {(ra.get('note') or '')[:34]})")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="assemble + emit prompt, NO provider call")
    ap.add_argument("--live", action="store_true", help="call the provider and write the v0.3 proposal")
    ap.add_argument("--cleanup", action="store_true", help="apply mechanical cleanup spec to the proposal")
    ap.add_argument("--render", action="store_true", help="render a readable markdown review doc (no truncation)")
    ap.add_argument("--guard", action="store_true", help="gate: fail if any gold copy reuses an owner-rejected line")
    ap.add_argument("--positives", action="store_true", help="cluster owner gold into named_positives (live provider)")
    args = ap.parse_args()
    if args.positives:
        return cmd_positives()
    if args.guard:
        return cmd_guard()
    if args.render:
        return cmd_render()
    if args.cleanup:
        return cmd_cleanup()
    if not args.live and not args.dry_run:
        print("specify --dry-run (verify) or --live (call provider). Defaulting to --dry-run.")
        return run(dry_run=True)
    return run(dry_run=not args.live)


if __name__ == "__main__":
    raise SystemExit(main())
