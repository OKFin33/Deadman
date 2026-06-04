# Deadman Backend

Branch 3 / Deadman API for `要是我来`.

This backend reads promoted runtime packs from:

```text
data/dramas/
```

In local development it can run standalone. The deployment entrypoint
`server.py` mounts these `/api/deadman` routes.

The public API does not expose producer-only local paths. Local MP4 files can
be served only through registered `/api/deadman/media/{drama_id}/{episode_id}`
URLs; the raw registry paths remain in tracked producer metadata and are
redacted from public `media-registry` responses.

## Run Locally

From the repo root:

```bash
uvicorn server:app --reload --port 7860
```

Health check:

```bash
curl http://127.0.0.1:7860/api/deadman/health
```

The health response includes media readiness. A clean git/ModelScope deployment
must either:

- configure `DEADMAN_MEDIA_BASE_URL` to an external media host; or
- run on a server that also has the registered ignored `tmp/` media files.

If neither is true, `/api/deadman/media/{drama_id}/{episode_id}` returns a
structured `media_not_available` error instead of leaking local paths.

## Endpoints

Base prefix:

```text
/api/deadman
```

Available endpoints:

```text
GET  /api/deadman/health
GET  /api/deadman/dramas
GET  /api/deadman/dramas/{drama_id}
GET  /api/deadman/dramas/{drama_id}/moments
GET  /api/deadman/dramas/{drama_id}/moments/{moment_id}
GET  /api/deadman/media/{drama_id}/{episode_id}
POST /api/deadman/judgment
```

## Judgment Example

```bash
curl -X POST http://127.0.0.1:7860/api/deadman/judgment \
  -H 'Content-Type: application/json' \
  -d '{
    "drama_id": "huangnian",
    "moment_id": "huangnian_ep12_m001",
    "action": {
      "source": "preset",
      "text": "今晚分兔肉，先让四蛋确认自己也有份",
      "option_index": 0
    },
    "viewer_profile": {
      "tone": "friend",
      "risk_preference": "balanced"
    }
  }'
```

The response is a stable frontend-ingestion shape with `verdict`,
`consequence`, `canon_anchor`, Chinese score axes, `result_card`,
`aggregate_stats`, `judgment_basis`, and engine metadata.

## Judgment Engine Boundary

Default local/deploy startup uses `cab_runtime`. Set
`DEADMAN_JUDGMENT_ENGINE=demo_deterministic` only for deterministic demo/unit
testing or emergency fallback in an environment without a usable CABRuntime
checkout. Claim the default path only after
`deadman_check_submission_readiness.py` or
`deadman_check_submission_readiness.py --require-cab-runtime` passes.

Formal CABRuntime failure returns a structured error. It must not fall back to
`demo_deterministic`.

## Demo Deterministic Boundary

The v0.1 judgment path is intentionally deterministic for the demo. It uses the promoted
Drama Context Pack, Moment Pack, selected action, original plot note, local
constraints, guardrails, and evidence notes to produce a bounded result.

Overpowered custom actions such as unlimited resources, public system reveals,
or later-episode rewrites are accepted as viewer impulses but softened back into
local credible consequences.

## Adapter Mapping Layer

`adapter_mapping.py` validates each promoted v0.1 moment against the typed
adapter boundary before judgment returns. It maps current
Huangnian runtime packs into `moment_causality_pack.v0.3.draft` and wraps them
as `deadman_judgment_adapter_input.v0.1`.

This layer is fail-closed: missing source windows, missing action options,
non-local time horizons, ungrounded stakes, visual proof leakage, or
viewer-facing `score_axes` leakage stop the request with a structured backend
error. Product consequence: a future LLM/hybrid adapter gets typed facts instead
of being asked to infer stake, proof, capability, and watch-flow rules from
loose prose.

The current public response shape is shared by both the demo deterministic path
and the CABRuntime-backed path. ASR and image-generation providers are not
connected here.

## CABRuntime Adapter

`CabRuntimeJudgmentService` sits behind the same request/response models. It
uses `backend/runtime_client.py` and the CABRuntime host adapter when
`DEADMAN_JUDGMENT_ENGINE=cab_runtime` is set.
