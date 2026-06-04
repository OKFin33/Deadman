# Huangnian Runtime Pack

Runtime-readable P0 drama pack for:

```text
荒年全村啃树皮，我有系统满仓肉
```

Tracked files:

- `context.v0.1.json`: lightweight Drama Context Pack;
- `moments.v0.1.json`: reviewed Moment Causality Packs;
- `manifest.v0.1.json`: pack manifest and source refs;
- `evidence/reviewed_demo_nodes.v0.1.json`: sanitized reviewed-node evidence;
- `media_registry.v0.1.json`: producer media registry metadata.

`media_registry.v0.1.json` intentionally keeps producer-only relative local
media metadata under `producer_media` for recording and local development.
Machine-specific Vite `@fs` paths are not tracked. The backend redacts
producer-only fields in public API responses; runtime clients should use
`runtime_video_url`.

Validate before runtime handoff:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian
```
