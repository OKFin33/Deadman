# Deadman Frontend Standalone Package Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Turn frontend into a real standalone mobile-first Vite frontend package, instead of only being source modules imported by Runtime/frontend. Preserve the current Branch 3 player demo behavior, keep Runtime/frontend as a temporary compatibility host bridge, do not move ArcForge legacy code, do not copy MP4s, do not touch secrets, and verify tests/build for both the new Deadman frontend package and the existing Runtime frontend host.
```

## Current State

- `frontend/src` already contains Branch 3 UI source:
  - `frontend/src/player/Branch3PlayerDemo.tsx`
  - `frontend/src/player/Branch3PlayerDemo.css`
  - `frontend/src/companion/TomatoCompanion.tsx`
  - `frontend/src/companion/TomatoCompanion.css`
  - `frontend/src/companion/tomatoCompanionMachine.ts`
  - `frontend/src/companion/tomatoCompanionMachine.test.ts`
- `Deadman/assets/public` contains Branch 3 public assets.
- `Runtime/frontend` currently builds the demo by importing `../../../frontend/src/...`.
- `Runtime/frontend` currently serves `Deadman/assets/public` through Vite `publicDir`.
- This is acceptable as a temporary host bridge, but `frontend` is not yet a real frontend package.

## Task

Make `frontend` a standalone Vite React package that can run, test, and build the Branch 3 player demo by itself.

The standalone app should render the mobile-first Branch 3 player as the first screen.

## Implementation Requirements

1. Add `frontend/package.json` with scripts:
   - `dev`
   - `build`
   - `preview`
   - `test`
2. Use React 18, Vite, TypeScript, Vitest, and Testing Library versions compatible with `Runtime/frontend` unless there is a clear reason not to.
3. Add `frontend/tsconfig*.json`.
4. Add `frontend/vite.config.ts`.
5. Add `frontend/index.html`.
6. Add `frontend/src/main.tsx`.
7. Add `frontend/src/App.tsx` or an equivalent minimal app shell.
8. The app shell should render `Branch3PlayerDemo` directly.
9. Configure Vite public asset handling so companion assets resolve correctly from `Deadman/assets/public`.
10. Preferred asset handling:
    - from `frontend`, configure `publicDir` to `../assets/public`;
    - preserve URLs like `/assets/branch3/companion/tomato-robes/...`.
11. Keep the existing `Runtime/frontend` bridge working:
    - `Runtime/frontend` with `?branch3_player=1` should still work;
    - `Runtime/frontend` may continue importing Deadman modules during this sprint;
    - do not remove the bridge unless tests/build prove a safe replacement and docs are updated.
12. Update docs to state the new boundary:
    - `frontend` is now the canonical Deadman frontend package;
    - `Runtime/frontend` is only a compatibility host bridge for legacy demo URLs.
13. Add a `.agent/dev-log.md` entry with prefix `[Deadman]`.

## Constraints

- Do not move ArcForge legacy files into an `ArcForge/` directory.
- Do not move or rewrite unrelated ArcForge docs.
- Do not copy or commit MP4/MOV files.
- Do not print, move, or commit API keys.
- Do not rewrite old dev-log history.
- Do not change Branch 3 product logic unless required to make the standalone package work.
- Keep the migration mechanical and reversible.

## Verification Required

Run from `frontend`:

```bash
npm install
npm test
npm run build
```

Run from `Runtime/frontend`:

```bash
npm test
npm run build
```

If Playwright is available, smoke test both entry points:

- Deadman standalone app at its dev URL.
- Runtime bridge at `/demo/?branch3_player=1`.

Required viewports:

- `390x844`
- `393x852`
- `430x932`

Smoke checks:

- Branch 3 player renders as the first screen.
- Companion image loads.
- Highlight hook renders.
- Two seeded highlight markers render.
- Tapping companion opens the `要是我来` bubble.
- The player accepts a `videoUrl` query parameter in standalone mode.

## Acceptance Criteria

- `frontend` has its own `package.json` and can build independently.
- `frontend` can run tests independently.
- Deadman standalone frontend shows the mobile-first Branch 3 player as first screen.
- Existing `Runtime/frontend` bridge still builds and tests.
- Docs clearly distinguish canonical Deadman frontend package from Runtime host bridge.
- No large video files or secrets are added.
- Remaining known debt is reported explicitly.

## Expected Final Report

The execution thread should report:

- files added/changed;
- verification commands and results;
- dev URL(s);
- whether Runtime bridge still works;
- whether `videoUrl` works in standalone mode;
- remaining debt.
