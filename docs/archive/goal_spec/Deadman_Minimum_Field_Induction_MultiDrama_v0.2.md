# Deadman Minimum Field Induction Multi-Drama v0.2 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24  

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Minimum_Field_Induction_MultiDrama_v0.2.md.

Run the Deadman minimum-field induction pass across three local short-drama genres: 荒年, 云渺, and 幸得相遇离婚时. Build or reuse per-drama ARS artifacts, mine candidate “要是我来” moments, cluster by judgment mechanism, compare field requirements across genres, and produce Moment Causality Pack v0.2 plus Field Evidence Matrix v0.2. Keep raw media, audio, keyframes, ASR/provider outputs, and review scratch artifacts in ignored tmp paths. Do not commit MP4/MOV files, API keys, raw provider outputs, or local .env files. Treat non-reviewed migration outputs as evidence for field induction, not final pack truth.

Before editing or running provider calls, read the contract file and treat it as the source of truth.
```

## Why This Goal Exists

The current Deadman P0 works for one drama (`荒年`), but the product claim is not
“we hard-coded five moments.” The claim is:

```text
short-drama materials -> bridge analysis -> minimal moment fields -> viewer-side credible consequence
```

This goal tests whether the current `Moment Causality Pack` fields generalize
across at least three short-drama mechanisms:

- famine / system / family survival pressure (`荒年`);
- cultivation / hidden power / supernatural rule pressure (`云渺`);
- divorce / revenge / humiliation / relationship reversal (`幸得相遇离婚时`).

The output is a schema and evidence decision, not a polished demo UI.

## Source Materials

All raw video files are local and ignored:

```text
tmp/视频素材/荒年/第1集.mp4 ... 第20集.mp4
tmp/视频素材/云渺/第1集.mp4 ... 第20集.mp4
tmp/视频素材/离婚/第1集.mp4 ... 第20集.mp4
```

Material inventory observed on 2026-05-24:

| Drama ID | Folder | Episodes | Duration | Format |
|---|---|---:|---:|---|
| `huangnian` | `tmp/视频素材/荒年` | 20 | ~41.6 min | 1080x1920 mp4 + AAC |
| `yunmiao` | `tmp/视频素材/云渺` | 20 | ~43.0 min | 1080x1920 mp4 + AAC |
| `lihun` | `tmp/视频素材/离婚` | 20 | ~47.8 min | 1080x1920 mp4 + AAC |

Use `lihun` internally for the folder named `离婚`, but label reports as
`幸得相遇离婚时` where user-facing title is needed.

## Current Baseline

Already implemented for `huangnian`:

- media / audio / keyframe / contact-sheet artifacts under
  `tmp/ars_huangnian_analysis/`;
- Doubao Speech ASR success for 20 / 20 episodes;
- 135 timeline windows;
- 64 first-pass candidates;
- 8 mechanism buckets;
- 5 reviewed P0 demo moments promoted into
  `data/dramas/huangnian/`;
- `Moment_Causality_Pack_v0.1_Draft.md`;
- `Field_Evidence_Matrix_v0.1.md`;
- backend and frontend consumption of the promoted pack.

Known gap:

- existing ARS scripts still contain `huangnian` defaults and output names;
- prior migration probe was summary-based because local media was missing;
- now local media exists, so migration must be rerun from source materials.

## Objective

Produce a multi-drama, evidence-grounded minimum field induction package:

```text
three local short-drama media sets
  -> per-drama media index / audio / ASR / windows
  -> per-drama candidate moments
  -> per-drama mechanism buckets
  -> cross-drama field evidence matrix
  -> Moment Causality Pack v0.2
  -> ARS miner field-output requirements
```

## Required Outputs

Tracked outputs:

```text
docs/Moment_Causality_Pack_v0.2.md
docs/Field_Evidence_Matrix_v0.2.md
docs/MultiDrama_Field_Induction_Report_v0.2.md
data/schemas/moment_causality_pack.v0.2.json
```

Ignored scratch outputs:

```text
tmp/ars_yunmiao_analysis/
tmp/ars_lihun_analysis/
tmp/ars_multidrama_field_induction/
```

Each per-drama scratch directory should mirror the useful `huangnian` layout
where possible:

```text
media_index.json
audio_mp3/
volc_asr/
keyframes_10s/
contact_sheets/
candidates/
review/
```

## Phase 1 - Generalize ARS Inputs

Patch or add scripts so `huangnian` is not the only first-class target.

Minimum capability:

- build `media_index.json` from a local drama folder;
- extract audio mp3;
- extract keyframes every 10 seconds;
- generate contact sheets;
- run or reuse Doubao Speech ASR artifacts;
- build windows from a configurable analysis dir;
- mine candidates with configurable drama id / title / output prefix;
- bucket mechanisms with configurable source drama metadata.

Do not break existing `huangnian` commands.

Recommended helper script:

```text
tools/ars/deadman_prepare_drama_assets.py
```

Recommended optional batch wrapper:

```text
tools/ars/deadman_run_ars_batch.py
```

If scripts are not added, the run report must include exact commands for each
manual step. But prefer scripts; manual command chains are harder to reproduce.

## Phase 2 - Run Per-Drama ARS

Run `yunmiao` and `lihun` from local materials.

Use ignored outputs:

```text
tmp/ars_yunmiao_analysis/candidates/yunmiao_candidates.v0.2.json
tmp/ars_yunmiao_analysis/candidates/yunmiao_candidates.v0.2.md
tmp/ars_yunmiao_analysis/candidates/yunmiao_mechanism_buckets.v0.2.json
tmp/ars_yunmiao_analysis/candidates/yunmiao_field_hypotheses.v0.2.md

tmp/ars_lihun_analysis/candidates/lihun_candidates.v0.2.json
tmp/ars_lihun_analysis/candidates/lihun_candidates.v0.2.md
tmp/ars_lihun_analysis/candidates/lihun_mechanism_buckets.v0.2.json
tmp/ars_lihun_analysis/candidates/lihun_field_hypotheses.v0.2.md
```

Provider policy:

- read credentials from environment only;
- do not print secrets;
- keep provider outputs under ignored `tmp`;
- if provider calls fail, stop and write a gap report rather than faking
  transcripts.

## Phase 3 - Candidate Review Sample

This goal does not need full human review of all migration candidates.

Required minimum:

- review at least top 12 `yunmiao` candidates;
- review at least top 12 `lihun` candidates;
- review enough lower-ranked candidates to cover mechanism diversity if top
  candidates are repetitive.

Review labels:

```text
reject
keep
schema_evidence
demo_candidate
```

For `schema_evidence` and `demo_candidate`, record:

- field pressure observed;
- what field would be missing if current v0.1 schema is used;
- whether the evidence is transcript-based, visual-reference-based, or inferred;
- whether the candidate should influence core fields or optional modules.

Ignored review outputs:

```text
tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json
tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json
```

## Phase 4 - Cross-Drama Field Induction

Build a cross-drama matrix with rows as fields and columns as evidence.

Required tracked output:

```text
docs/Field_Evidence_Matrix_v0.2.md
```

The matrix must distinguish:

- `CoreEnvelope`
  - required for every Deadman moment;
  - absence would make backend judgment or frontend rendering ambiguous.
- `OptionalCausalityModules`
  - required only for specific mechanism families.
- `GenreExtensions`
  - needed by migration genres but not necessarily by P0 core.
- `ProducerReviewFields`
  - needed for evidence hygiene and human review.
- `NonP0Fields`
  - should stay out because they imply continuous branch simulation.

Do not promote a field to core just because it appears in one genre.

## Phase 5 - Moment Causality Pack v0.2

Write:

```text
docs/Moment_Causality_Pack_v0.2.md
data/schemas/moment_causality_pack.v0.2.json
```

The schema must preserve P0 semantics:

```text
local credible consequence, not continuous alternate timeline
```

The v0.2 schema should specify:

- required fields;
- optional fields;
- field types;
- producer/consumer responsibility;
- evidence requirement;
- whether field is front-end visible, backend-only, or producer-only;
- how an LLM judgment adapter should consume it.

## Phase 6 - ARS Miner Output Requirements

Write:

```text
docs/MultiDrama_Field_Induction_Report_v0.2.md
```

This report must answer:

- which v0.1 fields survived unchanged;
- which fields were renamed or split;
- which fields must be added for `yunmiao`;
- which fields must be added for `lihun`;
- which fields should remain optional;
- what ARS miner must emit before a node can be promoted;
- what still requires human review;
- what is safe to feed into backend judgment immediately.

## Acceptance Criteria

The goal is complete only if:

- all three drama material sets are inventoried;
- `yunmiao` and `lihun` have source-based ARS candidate outputs or explicit
  provider/blocker reports;
- at least 24 migration candidates total are reviewed or marked as schema
  evidence;
- `Field_Evidence_Matrix_v0.2.md` exists and references all three dramas;
- `Moment_Causality_Pack_v0.2.md` exists and separates core vs optional fields;
- `moment_causality_pack.v0.2.json` exists and is machine-readable;
- `.agent/dev-log.md` receives a `[Deadman]` entry;
- no MP4/MOV, `.env`, literal API keys, or raw provider outputs are committed;
- existing Deadman backend/frontend tests still pass if code is touched.

## Verification

Run at minimum:

```bash
python3 -m py_compile tools/ars/*.py backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
find Deadman Runtime/frontend docs/goal_spec -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '.env' \) -print
rg -n --glob '!Runtime/frontend/dist/**' --glob '!frontend/dist/**' 'ark-[A-Za-z0-9-]{20,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}' Deadman Runtime/frontend docs/goal_spec 2>/dev/null || true
```

If frontend/backend code is not touched, frontend tests may be reported as
unchanged but still run if time permits.
