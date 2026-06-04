# Branch 3 Companion Avatar Asset Pack

Asset: `半像素番茄睡袍女孩`

Purpose: lightweight Codex-avatar-like state assets for OSeria Branch 3
`要是我来`. These are static transparent images intended for the P0 video-player
companion trigger layer. No Live2D or avatar runtime is required.

## States

- `idle`
- `notice_question`
- `notice_exclaim`
- `runout`
- `stand_bubble`
- `thinking`
- `verdict`

Each state is exported as:

- `png/<state>.png`
- `webp/<state>.webp`

The optional uniform-frame spritesheet is exported as:

- `spritesheet/tomato_companion_spritesheet.png`
- `spritesheet/tomato_companion_spritesheet.webp`

Frame metadata and recommended anchors live in `manifest.json`.

## UI Notes

- Use `idle` on the left edge, lower-middle safe area.
- Use `notice_question` / `notice_exclaim` at highlight moments.
- Use `runout` for the slide/run transition into the invite state.
- Use `stand_bubble` for the bitmap `要是我来` prompt state.
- Use `thinking` while the Moment Causality Engine judges the action.
- Use `verdict` for a blank placard; render verdict copy in UI when needed.

The individual images are tight-cropped. The spritesheet uses `640x512` frames
to prevent layout shift during state switches.

## Runtime Motion Contract

Use the asset pack through a lightweight finite state machine:

```text
idle
  -> notice_question / notice_exclaim
  -> runout
  -> stand_bubble
  -> thinking
  -> verdict
  -> dismissed
  -> idle
```

- Stable states keep a tiny CSS breathing loop until an event moves them.
- `runout` and `dismissed` are one-shot transition states.
- Timeline notices are ignored while the companion is already in
  `stand_bubble`, `thinking`, or `verdict`.
- The frontend implementation lives in
  `frontend/src/companion/TomatoCompanion.tsx` and
  `frontend/src/companion/tomatoCompanionMachine.ts`.
- P0 still does not require Live2D, APNG/GIF, or a full avatar runtime.

## Source

`source/tomato_companion_chroma_sheet.png` is the generated source sheet.
`source/tomato_companion_transparent_sheet.png` is the chroma-keyed transparent
sheet used for the exports.
