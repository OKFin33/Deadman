# Deadman Data

Reserved for Branch 3 data artifacts that are safe to keep in the repo:

- Moment Causality Pack examples
- lightweight Drama Context Packs
- source-window ledgers
- sanitized transcript snippets
- small deterministic fixtures for tests

Raw MP4/MOV drama files, raw ASR provider responses with request identifiers,
API keys, and local secrets do not belong here.

`dramas/` contains promoted runtime-readable packs only. Generated drafts,
provider/raw outputs, media files, and local review scratch stay under ignored
`tmp/` paths.

`evals/deadman_v0.4_authoring_proof.v0.1.json` is a tracked deterministic
fixture for the v0.4 Studio authoring proof gate. It contains only sanitized
input-window refs, generated draft summaries, validation results, and review
notes; it is not a raw provider trace.
