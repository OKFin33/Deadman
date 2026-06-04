# P0 Mobile UX Acceptance Checklist v0.1

> Product: Deadman / `要是我来`  
> Status: v0.1 checklist; acceptable to revise after UI review  
> Date: 2026-05-25

## Purpose

This checklist decides whether the viewer-facing Deadman P0 surface is shippable
for demo recording.

P0 is a mobile short-drama product surface. Desktop is only a phone preview
shell.

## Required Viewports

Every accepted user flow must pass:

```text
390x844
393x852
430x932
```

Acceptance means no clipped primary controls, no text overflow in buttons, no
blocked input, and no companion/bubble state that prevents returning to video.

## Core User Flow

P0 viewer flow must complete:

1. Open drama catalog.
2. Enter a demo drama/episode.
3. Play vertical video.
4. Reach a published interaction window.
5. See companion idle-to-notice state.
6. Tap companion.
7. See companion invite/bubble state.
8. Choose preset A/B/C.
9. Receive consequence result.
10. Close bubble and keep watching.
11. Reopen bubble or trigger another published moment.
12. Submit custom text.
13. Receive result or structured error state.

## Screen-Level Checklist

### Catalog

- Drama title and poster/thumbnail are visible.
- Demo drama can be entered with one clear tap.
- Page does not look like a desktop admin list.
- Touch target for entering a drama is at least `44px`.

### Player

- Video is vertical and primary.
- Desktop wraps the phone shell; it does not stretch the player into a desktop
  layout.
- Play/pause is reachable.
- Progress/timestamp is visible but not dominant.
- Highlight markers are visible without becoming the main product.
- Safe-area insets are respected for future WebView wrappers.

### Companion

Required states:

| State | Acceptance |
| --- | --- |
| `idle` | half-hidden, low interference, still noticeable |
| `notice_question` | visible `?`, does not block subtitles/controls |
| `notice_exclamation` | visible `!`, used for high-emotion trigger |
| `invite` | companion comes out enough to feel active |
| `bubble_open` | bubble reads as companion speech, not modal admin UI |
| `judging` | user sees work is happening and cannot double-submit accidentally |
| `result` | verdict, consequence, evidence, visual slot/fallback visible |
| `error` | explains failure without pretending judgment happened |
| `dismissed` | companion returns to non-blocking edge state |

### Bubble

- Opens from companion position.
- Does not cover essential playback controls permanently.
- Has one obvious close/dismiss control.
- Preset options are readable and tappable.
- Custom input uses native `textarea` or `input`.
- Submit button remains reachable with mobile keyboard open.
- Bubble content can scroll internally if needed.

### Result

Must show:

- companion verdict line;
- local consequence prose;
- why this happens, in compact viewer-safe language;
- one-line watch-flow rationale or canon anchor;
- image slot, placeholder, or text-only fallback;
- aggregate choice hint if available.

Must not show:

- `score_axes`;
- raw source paths;
- raw runtime trace;
- producer-only debug fields;
- claim that future episodes now follow the branch.
- tell the viewer that their choice does not affect the plot.
- use disclaimer-like copy such as `原剧情还能继续`, `不改写主线`, `不影响剧情`,
  `只改变眼前`, or `先别把这步当剧情结论`.

### Error State

Formal judgment failure must show an error state, not deterministic fallback.

Required copy properties:

- short;
- does not blame the user;
- says the result should not be treated as a story conclusion;
- lets the user retry or close.

Example:

```text
这次我卡住了，刚才那手先收一下。可以重试，或者继续看。
```

## Interaction Timing

For each published moment:

- before `notice_at_seconds`: companion is idle;
- within `interaction_window.start_seconds` and `end_seconds`: notice is
  available;
- after the window: notice expires unless bubble is already open;
- opening the bubble should not seek or restart the video unless explicitly
  designed later.

## Recording Acceptance

Demo recording must show:

- one complete preset action result;
- one complete custom action result or structured error;
- the user returning to video after the bubble;
- at least one visible timestamp-based notice;
- no desktop-only controls required for the flow.

## Test/Smoke Suggestions

Manual or Playwright smoke should verify:

```text
catalog visible
player visible
companion visible
moment markers loaded
notice appears inside interaction window
tap companion opens bubble
preset submit returns result
custom submit returns result or structured error
close returns to player
390x844 / 393x852 / 430x932 no overflow
```

## P0 Non-Goals

- full companion chat;
- voice input/output;
- native Android/iOS wrapper;
- realtime video generation;
- proof-grade generated images;
- producer/admin UI polish inside the viewer surface.
