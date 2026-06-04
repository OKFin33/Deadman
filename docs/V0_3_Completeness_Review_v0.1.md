# Deadman v0.3 Completeness Review v0.1

> Scope: standalone local extraction at the Deadman repo root  
> Date: 2026-06-03  
> Verdict: `pass_for_local_review`, not yet `public_ready`

## Definition

For this extraction, "complete v0.3" means the repo still carries the full
v0.3 baseline before any v0.4 UX-core publicization:

- PRD v0.3 and v0.3 external review framing are present;
- Moment Field Minimum Set v0.3 is present;
- Field Minimum Red Team result and typed-subkey patch evidence are present;
- Moment Causality Pack v0.3 draft schema is present;
- backend adapter mapping can map all promoted Huangnian v0.1 moments into the
  v0.3 typed adapter input;
- runtime data for the five reviewed Huangnian P0 moments is present and
  producer-bridge validation passes;
- frontend package still tests and builds in standalone form.

v0.4 UX-core docs may also exist in the repo, but they do not replace the
requirement that v0.3 remains inspectable and executable as a baseline.

## Required Artifacts

| Requirement | Artifact | Status |
| --- | --- | --- |
| v0.3 PRD | `docs/Branch3_要是我来_PRD_v0.3.md` | present |
| v0.3 review correction | `docs/external_review_v0.3_pivoted_lens.md` | present |
| field minimum set | `docs/Moment_Field_Minimum_Set_v0.3.md` | present |
| field demand evidence | `docs/Field_Demand_Cluster_Report_v0.3.md` | present |
| red-team result | `docs/Field_Minimum_Red_Team_v0.1.md` | present |
| red-team eval data | `data/evals/field_minimum_red_team.v0.1.json` | present |
| typed pack schema | `data/schemas/moment_causality_pack.v0.3.draft.json` | present |
| field minimum schema | `data/schemas/moment_field_minimum_set.v0.3.json` | present |
| adapter input/output schemas | `data/schemas/deadman_judgment_adapter_*.v0.1.json` | present |
| Huangnian runtime packs | `data/dramas/huangnian/` | present |
| backend mapper/tests | `backend/adapter_mapping.py`, `backend/tests/` | present |
| standalone frontend | `frontend/` | present |

## Verification

Commands run from repo root unless noted:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile server.py Deadman/__init__.py backend/*.py tools/ars/*.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s backend/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 tools/ars/deadman_validate_producer_bridge.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/ars/deadman_print_recording_urls.py --episode-id huangnian_ep07
cd frontend && npm ci && npm test && npm run build
```

Results:

- Python compile: passed.
- Backend tests: 40 passed, 2 CABRuntime integration tests skipped by explicit
  env gate.
- Producer bridge validation: passed for 5 Huangnian moments, 0 errors, 0
  warnings.
- Recording URL utility: ran successfully for `huangnian_ep07`.
- Frontend tests: 21 passed.
- Frontend build: passed.
- Post-check cleanup: `node_modules`, `dist`, `.pytest_cache`, and
  `__pycache__` removed.

## Fixes Applied During Review

- Added `tools/ars/deadman_paths.py` so ARS scripts can locate the Deadman root
  from both the original nested checkout and this standalone extraction.
- Replaced code-level `REPO_ROOT / "Deadman/..."` assumptions with direct
  repo-root-relative paths in v0.3-critical scripts.
- Updated `data/dramas/huangnian/manifest.v0.1.json` source artifact refs from
  old nested paths to standalone repo-relative paths.
- Updated frontend test expectations to match the current single-narrative
  companion result surface.
- Updated CABRuntime default root discovery to find a sibling `CABRuntime`
  checkout from either nested or standalone Deadman paths.

## Remaining Publicization Blockers

These did not block v0.3 completeness. The tracked-file cleanup has since
resolved the direct public repo blockers:

- `data/dramas/huangnian/media_registry.v0.1.json` keeps relative `tmp/...`
  producer media metadata, but no longer tracks machine-specific Vite
  `@fs/<local-user>/...` URLs;
- historical goal specs that mention the old source checkout path are archived
  under `docs/archive/goal_spec/`;
- docs still contain `tmp/...` provenance references for ignored producer
  artifacts. These are acceptable as historical/provenance notes and are
  explained in the repo boundary docs.

## Verdict

The extracted repo is now complete enough to serve as the local v0.3 baseline:
the v0.3 documents, schemas, reviewed Huangnian runtime data, backend adapter
contract, producer validation, and standalone frontend all verify.

It became public-source ready after the media registry and historical local-path
docs were sanitized and the final publication gate passed.
