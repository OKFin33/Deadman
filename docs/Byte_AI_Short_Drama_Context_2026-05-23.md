# Byte AI Full-Stack Short-Drama Context

Date: 2026-05-23
Primary brief: `${LOCAL_DOWNLOADS}/AI全栈项目--基于短剧剧情的即时互动激发（宣讲）.docx`
Target deadline: 2026-06-11

## 1. Competition Task

The task is to build a full-stack project for short-drama instant interaction.

Core problem:

- Short dramas contain emotional peaks, reversals, famous scenes, cliffhangers, and finale moments.
- Current interaction is mostly comments and bullet chats, which require text input and interrupt watching.
- The product should provide lower-friction, richer interaction during or immediately after watching.

Required closed loop:

1. Mark and store drama highlight points.
2. During playback, deliver highlight-point metadata to the client.
3. Render interaction components or branching content on the client.
4. Provide a backend service and storage path.

## 2. MVP Requirements

Required:

- Short-drama list page.
- Short-drama playback page.
- Basic playback controls: play/pause, progress bar.
- Backend service and storage.
- At least one content interaction mode:
  - highlight-point interaction, or
  - story branch / expansion.

Optional but useful:

- User interaction aggregation, such as viewing other users' interaction counts.
- Likes/comments on generated branch content.
- Model-based short-drama understanding to identify conflict, reversal, famous-scene, and sweet moments.

Submission:

- Frontend presentation can be Android, iOS, or HarmonyOS for team submissions.
- Considering overall difficulty, a solo participant may choose Web frontend + backend.
- GitHub project managed by Git.
- Demo recording and final artifact.
- Feishu technical document with module breakdown, technical choices, main flowchart, work breakdown, schedule, and AI usage disclosure.

## 3. Scoring

| Dimension | Weight |
|---|---:|
| Overall functional completeness | 40% |
| Technical choices and implementation | 30% |
| Innovation and free exploration | 20% |
| Documentation and presentation | 10% |

## 4. Timeline

| Date | Milestone |
|---|---|
| 2026-05-21 | Topic release and kickoff |
| 2026-05-22 to 2026-06-10 | Core development |
| 2026-06-11 | Final delivery deadline |
| 2026-06-11 to 2026-06-19 | Online defense and selection |
| After 2026-06-19 | Green interview channel for strong projects |

As of 2026-05-23, there are 19 calendar days until the final delivery deadline.

## 5. Security Note

The organizer brief includes a model endpoint credential. Treat it as a secret.

Rules:

- Do not commit it.
- Do not paste it into docs, frontend code, screenshots, or public logs.
- Use server-side environment variables only.
- If it has already been exposed outside the private team context, rotate or request replacement.

## 6. OSeria Fit

OSeria / ArcForge already fits the high-value half of the task: story branch and expansion.

The competition does not require a full IP world simulation. For short drama, the right abstraction is:

```text
Short Drama Episode
  -> highlight moments
  -> Moment Pack / World Pack Lite
  -> client playback trigger
  -> 2-5 turn interaction
  -> branch summary / shareable result
```

Use pack depth by drama type:

| Drama type | Pack depth |
|---|---|
| urban revenge, romance misunderstanding, family conflict | Moment Pack |
| summoner, apocalypse survival, cultivation, infinite loop | World Pack Lite + Moment Pack |
| mature long-form IP | Full World Pack |

## 7. Current Repo Reality

Current OSeria-Alter role:

- ArcForge competition and deployment branch.
- Runtime shell with FastAPI backend and React/Vite frontend.
- Existing Qing Yu Nian demo world.
- Existing story runtime loop with session, streaming response, state snapshot, choices, lorebook, and world list.

Current implementation gap against Byte task:

- No short-drama list/player flow yet.
- No video playback timeline trigger model yet.
- No highlight-point storage schema yet.
- No short-drama asset pack format yet.
- No client-side highlight interaction overlay yet.
- Existing runtime is story-first, not video-player-first.

## 8. Recommended Product Direction

Position the submission as:

```text
OSeria SnapScene
World-aware short-drama instant interaction engine.
```

Claim:

- It turns short-drama highlight moments into playable interactive moments.
- It preserves OSeria's world-state discipline, but downshifts from full World Pack to Moment Pack / World Pack Lite.
- It is stronger than simple emoji/button interaction because user choices can create personalized branches.

Demo shape:

1. User opens short-drama list.
2. User plays selected drama.
3. At a marked highlight timestamp, an interaction component appears.
4. User selects an action or enters custom intent.
5. Backend uses highlight context + Moment Pack to generate a short branch.
6. Client displays branch result and optional A/B/C follow-up.
7. Interaction result is stored and can be shown as aggregate user response.

## 9. Development Priority

P0 must optimize for scoring, not platform purity.

Build order:

1. Backend schema and seed data for dramas, episodes, highlight moments, and moment packs.
2. Frontend short-drama list and player shell.
3. Timestamp-triggered overlay interaction.
4. Branch generation endpoint using existing runtime/LLM client where possible.
5. Interaction persistence and lightweight aggregate display.
6. Demo content and recording path.
7. Feishu technical document.

Defer:

- Full multi-IP compiler.
- Full FactRepository.
- Full mobile native app unless required by team strategy.
- Android APK wrapper unless core Web + backend functionality is already complete.
- iOS installable IPA / TestFlight delivery for this sprint.
- Multi-user real-time sync.
- Long-term memory beyond the demo interaction window.

## 10. Candidate Architecture

```text
React/Vite client
  -> short-drama list
  -> video player
  -> highlight overlay
  -> branch result panel

FastAPI backend
  -> drama catalog API
  -> highlight metadata API
  -> interaction API
  -> branch generation API
  -> local JSON/SQLite storage

OSeria runtime layer
  -> Moment Pack / World Pack Lite
  -> LLM branch generation
  -> state_patch / choice output
```

## 11. Next Engineering Gate

Before writing code:

1. Decide whether this submission lives in `OSeria-Alter/Runtime` or a new `SnapScene/` module.
2. Pick one allowed drama material from the organizer list.
3. Create a minimal seed dataset with:
   - drama metadata,
   - one episode/video asset placeholder,
   - 3-5 highlight moments,
   - one Moment Pack.
4. Implement the local player and interaction loop end to end before model-heavy extraction.
