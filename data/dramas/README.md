# Deadman Drama Runtime Data

Tracked runtime-readable drama packs for Branch 3 / `要是我来`.

These packs are lightweight runtime context, not ArcForge world simulation
packs. A `Drama Context Pack` gives the judgment layer global genre, rule,
relationship, and tone constraints for one drama. A `Moment Causality Pack`
answers one timestamped intervention moment.

Runtime priority:

```text
Moment Causality Pack local facts
  > Drama Context Pack global constraints
  > LLM common sense
```

Current packs:

| Drama ID | Context | Moments | Status |
|---|---|---|---|
| `huangnian` | `huangnian/context.v0.1.json` | `huangnian/moments.v0.1.json` | reviewed P0 bridge artifact |

Do not add raw MP4/MOV files, raw provider payloads, `.env` files, or secrets
to this directory.

Before handing a promoted pack to runtime/backend work, run:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian
```
