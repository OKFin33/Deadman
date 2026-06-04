# Deadman Publication Review

> Status: public-source gate checkpoint  
> Created: 2026-06-03  
> Scope: final hygiene review before any public GitHub push

## Extraction Boundary

Included:

- `frontend/`
- `backend/`
- `data/`
- `tools/ars/`
- `assets/`
- `docs/`
- root `server.py`
- root `requirements.txt`
- root `ms_deploy.json`

Excluded mechanically during extraction:

- `node_modules/`
- `dist/`
- `build/`
- `.gradle/`
- `.DS_Store`
- `.env`
- `*.tsbuildinfo`
- MP4/MOV/M4V files
- `tmp/`
- `__pycache__/`
- `.pytest_cache/`

## Review Before Publicizing

Required checks:

- [x] No obvious secrets or provider keys in token-pattern scan.
- [x] No local OAuth/token URLs in token-pattern scan.
- [x] No local media files found.
- [x] No dependency directories, build outputs, `.DS_Store`, `.env`,
      `.tsbuildinfo`, or Android local build files found.
- [x] v0.3 baseline is complete enough for local review.
- [x] Local development artifacts are available under ignored paths.
- [x] Current public entry docs do not expose machine-specific absolute paths.
- [x] Historical specs and archive candidates have been explicitly selected,
      archived, or generalized for public release.
- [x] README backend/frontend verification commands work after dependency
      install.
- [x] CABRuntime dependency is described as optional/formal mode, not bundled.
- [x] ModelScope deployment env values are sanitized.
- [x] Competition claims do not overstate image generation, multi-drama
      promotion, real aggregate stats, or autonomous ingestion.
- [x] Tracked media registry no longer exposes machine-specific Vite `@fs`
      local paths.

## Extraction Check Results

Last local checks:

- initial extracted size before verification cleanup: about 11 MB;
- current cleaned size after v0.3 verification: about 9.6 MB;
- current cleaned file count: 264;
- Python compile: passed for `server.py`, `backend/*.py`, and `tools/ars/*.py`;
- backend API import: passed;
- backend unit tests: 40 run, 40 passed, 2 CABRuntime integration tests skipped
  by explicit env gate;
- producer bridge validation: passed for 5 Huangnian promoted moments with 0
  errors / 0 warnings when run from the extracted `Deadman` directory;
- frontend test/build: 21 tests passed and production build passed after
  `npm ci`;
- standalone v0.3 review: `docs/V0_3_Completeness_Review_v0.1.md`.
- local artifact policy: `docs/Local_Development_Artifact_Policy_v0.1.md`;
- publicization decision log: `docs/Publicization_Decision_Log_v0.1.md`;
- local-only copied artifacts: `tmp/`, `.agent/`, and `local_artifacts/` are
  present for local development and ignored for GitHub publication;
- local artifact size: `tmp/` about 2.2 GB, `.agent/` about 88 KB,
  `local_artifacts/` about 4.0 MB;
- repo-wide structure map added: `REPO_STRUCTURE.md` separates public
  candidate tree, local-only tree, boundary rules, and remaining blockers;
- documentation map added: `docs/README.md` separates current entry points,
  historical goal specs, submission docs, and ignored local artifacts;
- historical goal spec disclaimer added: `docs/goal_spec/README.md`;
- historical sprint goal specs archived under `docs/archive/goal_spec/`; current
  `docs/goal_spec/` keeps only selected LangGraph producer specs;
- key directory READMEs added or updated for `Deadman/`, `tools/`, `studio/`,
  `data/schemas/`, `data/dramas/huangnian/`, and `frontend/android/`;
- generated local leftovers removed: TypeScript build-info files, compiled
  Vite config outputs, and Python `__pycache__`;
- standalone path normalization applied to current repo-facing code, Studio
  prototype command surfaces, runtime data refs, and current submission maps
  (`tools/ars/...`, `data/...`, `docs/...`, `frontend/...`);
- producer graph dry-run command verification passed with root-relative
  standalone paths;
- backend unit tests after repo organization: 40 passed, 2 CABRuntime worker
  dogfood tests skipped by explicit env gate;
- submission readiness check in `demo_deterministic` mode passed ms_deploy,
  media/env scan, literal secret scan, public redaction, viewer judgment loop,
  and resident runtime loop; it still failed media readiness and media route
  because no external media host or server-local registered media is configured;
- producer graph unit tests require `langgraph`; `requirements.txt` declares it,
  but installing missing dependencies in the current Python environment stalled
  and was terminated before completion;
- baseline commit/tag created locally:
  `a709b13 baseline: v0.3 before v0.4 pivot` tagged
  `baseline/v0.3-pre-v0.4-local`;
- publication safety check: `python3 tools/check_publication_safety.py` passed
  with tracked-file candidates checked;
- public claim audit applied: image generation, multi-drama promotion, real
  aggregate stats, arbitrary ingestion, and CABRuntime formal success are now
  described as absent, evidence-only, fictional/static demo copy, human-reviewed
  only, or readiness-gated as appropriate;
- high-confidence local secret scan: passed over 1163 text files. No Doubao /
  Volc / Ark key literal was found in the local Deadman package.
- media registry publicization fix applied: tracked registry keeps relative
  `tmp/...` producer-local media metadata, checksum, and size for local
  development, but no longer tracks machine-specific Vite dev URLs.

Known blockers before public upload:

- Run final leak scan immediately before any push.
- No open-source license is attached yet; this is intentional until IP/media
  boundaries are cleared.

## Resolved Pre-Publication Decisions

Resolved owner decisions:

1. Local checkout is the private baseline; remote push should be public only
   after final leak/public-claim scan.
2. Keep useful historical docs, but archive/generalize noisy specs before
   public release.
3. Keep sanitized deployment config tracked if it contains no real secrets or
   private URLs.
4. Keep local videos and local media metadata for development/recording; raw
   videos remain ignored.
5. First visible project state should be the v0.3 pre-v0.4 baseline; v0.4
   becomes a later iteration.
