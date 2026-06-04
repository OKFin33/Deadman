# Deadman ARS Tools

Provider adapters and local scripts for Branch 3 ARS node-mining dogfood.

Current adapters:

- `deadman_volc_asr_flash.py`
- `deadman_volc_asr_standard.py`

Both adapters read credentials from environment variables only. Keep raw outputs
in ignored local artifact paths unless they have been sanitized.

Local deterministic bridge scripts:

- `deadman_prepare_drama_assets.py`
- `deadman_register_media.py`
- `deadman_build_timeline_windows.py`
- `deadman_mine_candidates.py`
- `deadman_cluster_candidates.py`
- `deadman_review_candidates.py`
- `deadman_induce_moment_fields.py`
- `deadman_build_drama_context.py`
- `deadman_publish_p0_bridge.py`
- `deadman_validate_producer_bridge.py`
- `deadman_print_recording_urls.py`
- `deadman_check_submission_readiness.py`

`deadman_build_drama_context.py` promotes reviewed ARS artifacts into
runtime-readable Drama Context Pack and Moment Causality Pack JSON. It does not
call providers or read secrets.

`deadman_validate_producer_bridge.py` is the post-publish gate. It checks that
tracked manifest/context/moments/media-registry/reviewed-node files agree, that
runtime-facing fields do not dereference ignored `tmp/` artifacts, that promoted
moments point back to reviewed nodes, and that tracked drama data does not
contain raw media or env files.

`deadman_print_recording_urls.py` prints local Vite URLs for demo recording from
producer-only media registry metadata. It keeps the local `@fs` video URL in
the query string and does not write it into runtime-facing pack fields.

`deadman_check_submission_readiness.py` is the final local submission gate. It
imports `server:app`, verifies deployed Deadman routes, media readiness, public
redaction, media serving, judgment output, and tracked secret/media hygiene.

`deadman_prepare_drama_assets.py`, `deadman_review_candidates.py`, and
`deadman_induce_moment_fields.py` are the v0.2 multi-drama field-induction
helpers. They keep raw media, audio, keyframes, ASR outputs, and review scratch
under ignored `tmp/` paths; only the induced docs/schema should be promoted.

## Huangnian P0 Producer Bridge

The current reproducible Huangnian path is:

```bash
python3 tools/ars/deadman_prepare_drama_assets.py \
  --drama-id huangnian \
  --drama-title "荒年全村啃树皮，我有系统满仓肉" \
  --video-dir "tmp/视频素材/荒年" \
  --analysis-dir tmp/ars_huangnian_analysis

python3 tools/ars/deadman_register_media.py \
  --media-index tmp/ars_huangnian_analysis/media_index.json \
  --episode-ids huangnian_ep03,huangnian_ep04,huangnian_ep06,huangnian_ep07,huangnian_ep12

python3 tools/ars/deadman_build_timeline_windows.py
python3 tools/ars/deadman_mine_candidates.py --max-candidates <candidate_recall_budget>
python3 tools/ars/deadman_cluster_candidates.py

# Human review edits tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json.

python3 tools/ars/deadman_build_drama_context.py \
  --drama-id huangnian \
  --reviewed-demo-nodes tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json \
  --reviewed-candidates tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json \
  --summaries docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md \
  --out-dir tmp/ars_huangnian_analysis/drama_context \
  --promote \
  --promote-dir data/dramas/huangnian

python3 tools/ars/deadman_publish_p0_bridge.py

python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian \
  --report tmp/ars_huangnian_analysis/producer_bridge_validation_report.md

python3 tools/ars/deadman_print_recording_urls.py \
  --episode-id huangnian_ep12
```

The validator is the handoff checkpoint. If it fails, do not claim the runtime
pack is reproducible.
