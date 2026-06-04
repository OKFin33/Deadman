# Branch 3 ARS Node Mining Dogfood v0.1

> Product: 要是我来 / Deadman  
> Demo source: `荒年全村啃树皮，我有系统满仓肉` first 20 episodes  
> Goal: use ARS as the bridge-system dogfood path from raw short-drama material to candidate Moment Causality Packs.

## 1. One-Line Decision

Yes: use ARS to find possible intervention nodes.

For P0, ARS should not be treated as a perfect fully automatic video-understanding system. It should be a semi-automatic bridge pass:

```text
20 episodes
  -> transcript / OCR / keyframes / timeline windows
  -> candidate intervention nodes
  -> cluster by judgment mechanism
  -> field hypotheses
  -> ranked node table
  -> Field Evidence Matrix
  -> Moment Causality Pack drafts
  -> human selection of 3-5 demo nodes
```

This is good dogfood because it tests the exact bridge claim: source materials can be converted into runtime-ready interactive foundations.

Deadman does not branch the drama into a continuous alternate plot for P0. Each mined node answers a local question:

```text
要是你在这一刻这么做，当前局面里可信后果是什么？
```

The viewer can then return to the original episode flow without the system pretending later episodes truly changed.

It is also the schema-induction path for `Moment Causality Pack v0.1`. The first pack contract should not be frozen from intuition. ARS should first extract real candidate nodes, cluster them by the kind of causal judgment they require, and reveal which fields are stable across genres.

## 2. Why ARS Fits This Stage

Manual node picking is fast but does not prove the bridge system.

ARS node mining can prove:

- the system can ingest real organizer material;
- the system can identify high-emotion timestamps;
- the system can extract scene facts and constraints;
- the system can propose A/B/C actions;
- the system can draft Moment Causality Packs;
- the runtime can consume generated highlight metadata.

The important product proof is not "AI found every perfect node." It is:

```text
Given real short-drama episodes, our bridge can produce usable interactive moment candidates faster than manual authoring from scratch.
```

## 3. Input Assumptions

The 20 downloaded episodes may have any of:

- embedded subtitles;
- burned-in subtitles;
- clear dialogue audio;
- no machine-readable transcript;
- short vertical video format.

P0 should support a fallback ladder:

| Input availability | Preferred extraction |
|---|---|
| subtitle file exists | parse subtitle timestamps directly |
| online ASR allowed | Volcano Engine / Doubao Speech ASR with drama-specific hotwords and timestamps |
| burned-in subtitles | OCR sampled frames |
| clear dialogue but online ASR not allowed | local Whisper fallback with candidate-clip refinement |
| no reliable text | keyframe + short human notes |

Local probe result on 2026-05-24:

- local Whisper `base` is fast but too noisy for this short-drama mix;
- local Whisper `small` is noticeably better on candidate clips, but too slow for blind full-batch transcription;
- no local OCR tool is currently installed in the OSeria-Alter workspace environment;
- therefore the preferred P0 bridge path should be Volcano Engine online ASR if external upload is allowed, plus keyframe/contact-sheet review.

Roco reference:

- Roco uses a Bailian hotword ASR fallback path through `bl speech recognize`;
- the transferable pattern is provider adapter + hotword vocabulary + transcript quality ledger + explicit unresolved-ASR downgrade;
- for this Byte challenge, Volcano Engine should be the primary provider; Bailian remains only an optional fallback/reference implementation;
- Deadman should not promote ASR-derived facts directly into Moment Packs without source-window provenance or human review.

## 4. ARS Pipeline

### 4.1 Media Index

For each episode:

- file path;
- duration;
- resolution / aspect ratio;
- frame rate;
- whether subtitle text can be extracted;
- sample keyframes every N seconds;
- shot / scene boundary guesses if available.

Output:

```json
{
  "episode_id": "huangnian_ep01",
  "video_path": "/path/to/ep01.mp4",
  "duration_ms": 90000,
  "has_subtitle_file": false,
  "has_burned_subtitle": true,
  "keyframe_dir": "analysis/huangnian_ep01/keyframes"
}
```

### 4.2 Transcript / Timeline Windows

Create short timestamped windows:

```json
{
  "window_id": "ep01_w012",
  "start_ms": 32000,
  "end_ms": 47000,
  "dialogue": "孩子喊饿，外面亲戚打听家里有没有吃的。",
  "visual_notes": ["破旧院子", "孩子围着锅", "主角犹豫"],
  "detected_emotions": ["饥饿", "护崽", "警惕"]
}
```

Window length target:

- 10-20 seconds for fast short-drama beats;
- merge adjacent windows if a conflict spans multiple cuts.

Recommended transcription providers:

| Provider path | Use | Notes |
|---|---|---|
| `online_volcengine_seedasr_standard` | Preferred batch path if audio URLs are available | Byte/Volcano-native standard submit/query path. Use model 2.0 resource `volc.seedasr.auc` for 20-episode transcription if upload/URL hosting is ready. |
| `online_volcengine_bigasr_flash` | Preferred local probe path | One request returns result and supports local audio base64. Use resource `volc.bigasr.auc_turbo` for quick 1-2 episode tests. |
| `online_bailian_fun_asr` | Optional fallback/reference | Roco-proven pattern via `bl speech recognize`; useful if Volcano credentials are not ready. |
| `local_whisper_base` | Fast rough fallback | Useful for broad timing hints, not reliable as factual source. |
| `local_whisper_small_clip` | Candidate refinement fallback | Better quality on short clips; use after visual/keyframe candidate selection. |
| `manual_notes` | Human correction | Required for final promoted demo nodes. |

Volcano Engine target API:

- product path: Doubao Speech / speech recognition large model;
- standard API endpoint: submit `POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit`, query `POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/query`;
- standard API resource ids: model 1.0 `volc.bigasr.auc`, model 2.0 `volc.seedasr.auc`;
- flash API endpoint: `POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash`;
- flash API resource id: `volc.bigasr.auc_turbo`;
- expected output: full text plus utterance / word timestamps where enabled;
- expected input prep: extract episode audio to MP3 or WAV before upload, because the API is designed for audio files rather than raw MP4 video;
- practical decision: use standard 2.0 for batch quality if we can provide audio URLs; use flash for local-file probes because it supports direct base64 audio upload.

Credential rules:

- read API key from environment only. The local adapter checks `DOUBAO_SPEECH_API_KEY` first, then `VOLC_ASR_API_KEY`, then `VOLC_API_KEY`;
- read uid from `DOUBAO_SPEECH_UID` first, then `VOLC_ASR_UID`, then `VOLC_UID`; if none exists, use `deadman-ars`;
- never commit keys, request headers, or raw provider logs containing credentials;
- raw ASR JSON may include request identifiers and should stay in local `tmp/` artifacts unless sanitized.

Local adapter:

```bash
python3 tools/ars/deadman_volc_asr_flash.py \
  --audio-dir tmp/ars_huangnian_analysis/audio_mp3 \
  --limit 1 \
  --dry-run
```

Credential probe on 2026-05-24:

- an `ark-...` key from Volcano Ark / Doubao Seed was rejected by the Doubao Speech ASR endpoint;
- provider response: HTTP 401, `45000010 Invalid X-Api-Key`;
- conclusion: Seed / Ark API keys are for LLM calls, not for Doubao Speech ASR;
- next ASR run needs a Speech console `X-Api-Key` with the required ASR resource enabled.
- a Speech console `X-Api-Key` was then validated against the official standard API sample URL;
- provider response: submit `20000000 OK`, query `20000000 OK`;
- standard API returns full text plus utterance/word timestamps when `show_utterances` is enabled;
- remaining production issue: standard API requires `audio.url`, so local episode MP3 files need temporary public/object-storage URLs before batch transcription.

Standard API adapter:

```bash
python3 tools/ars/deadman_volc_asr_standard.py \
  --audio-url "https://example.com/audio.mp3" \
  --show-utterances \
  --poll
```

Prepared audio artifacts:

- source videos: `tmp/视频素材/荒年/*.mp4`;
- extracted ASR inputs: `tmp/ars_huangnian_analysis/audio_mp3/*.mp3`;
- default ASR outputs: `tmp/ars_huangnian_analysis/volc_asr/`.

First-pass run result on 2026-05-24:

- Doubao Speech flash ASR completed for 20 / 20 local episode MP3 files.
- Raw and normalized provider artifacts stayed under ignored `tmp/ars_huangnian_analysis/volc_asr/`.
- Generated ARS bridge artifacts live under ignored `tmp/ars_huangnian_analysis/candidates/`:
  - `huangnian_windows.v0.1.json`;
  - `huangnian_candidates.v0.1.json`;
  - `huangnian_candidates.v0.1.md`;
  - `huangnian_mechanism_clusters.v0.1.json`;
  - `huangnian_mechanism_clusters.v0.1.md`;
  - `huangnian_field_hypotheses.v0.1.md`;
  - `run_report.md`.
- Output counts: 135 windows, 64 candidate nodes, 8 mechanism clusters, 39 candidates with rank score >= 70.
- These outputs are semi-automatic bridge evidence only; promoted Moment Packs still require source-window human review.

Drama hotwords should include:

- title and protagonist names: `荒年全村啃树皮`, `程弯弯`;
- genre/world terms: `荒年`, `系统`, `商城`, `积分`, `粮食`, `野菜`, `肉`, `露富`;
- family/role terms: `娘`, `大哥`, `二弟`, `三弟`, `四弟`, `孩子`, `亲戚`, `村里`;
- recurring risk terms discovered from the first pass.

### 4.3 Candidate Node Mining

ARS should score each window against intervention value.

Core scores:

| Score | Meaning |
|---|---|
| `emotion_heat` | viewer impulse to react now |
| `choice_leverage` | whether a choice could plausibly change the local outcome |
| `causal_clarity` | whether scene facts are clear enough to judge consequences |
| `world_constraint_value` | whether the scene tests resources, system secrecy, village pressure, kinship, or survival rules |
| `watch_flow_fit` | whether the interaction can finish and return the viewer to the original episode without making the drama feel broken |
| `visual_result_fit` | whether a result image/card can be generated clearly |

For `荒年`, special detectors:

- child hunger / family protection;
- food or meat appearance;
- villagers / relatives watching or asking questions;
- system resource use;
- risk of露富;
- moral pressure to share food;
- conflict between immediate survival and long-term safety.

### 4.4 Candidate Output

For each candidate:

```json
{
  "candidate_id": "ep01_c003",
  "episode_id": "huangnian_ep01",
  "start_ms": 41200,
  "end_ms": 49300,
  "trigger_type": "resource_crisis",
  "notice_marker": "!",
  "hook": "这口肉要不要拿出来？",
  "why_now": "孩子已经饿到撑不住，但外人正在盯着家里有没有吃的。",
  "scores": {
    "emotion_heat": 82,
    "choice_leverage": 88,
    "causal_clarity": 76,
    "world_constraint_value": 94,
    "watch_flow_fit": 81,
    "visual_result_fit": 70
  },
  "default_options": [
    "直接把肉端出来，先让孩子吃饱",
    "少量拿出来，编个能糊弄过去的来源",
    "先藏住肉，用野菜粥撑过这一顿"
  ],
  "pack_draft_ready": true
}
```

### 4.5 Moment Pack Drafting

For top candidates, ARS drafts:

- `moment_id`;
- timestamp;
- scene summary;
- current known facts;
- hidden facts;
- role goals;
- world rules;
- canon anchors;
- default options;
- likely action types;
- image prompt seed;
- result tone hints.

The draft does not need to be perfect. It should be good enough for a human pass and runtime test.

### 4.6 Schema Induction And Field Evidence Matrix

Before freezing `Moment Causality Pack v0.1`, run ARS as a field-discovery pass.

Process:

1. collect all candidate nodes from `荒年`;
2. cluster by judgment mechanism, not by plot summary;
3. list which variables are needed to judge each cluster;
4. repeat on two migration dramas:
   - one revenge / humiliation / relationship-conflict drama;
   - one cultivation / supernatural / hidden-power drama;
5. build a Field Evidence Matrix;
6. promote cross-genre fields into the core envelope;
7. demote genre-specific fields into optional modules.

Initial cluster labels:

| Cluster | Example judgment question |
|---|---|
| resource crisis | Should the protagonist release scarce food / money / power now? |
| exposure risk | Does the action reveal system, identity, wealth, or hidden power too early? |
| social pressure | How do relatives, villagers, classmates, or bystanders react? |
| humiliation revenge | Does a public confrontation create leverage or only escalate backlash? |
| evidence / trap | Does collecting proof or setting a trap beat immediate confrontation? |
| hidden power / genre rule | Does the action respect power level, cooldown, sect/world rules, or identity concealment? |
| nonsense / overpowered break | Is the input outside the scene contract and only worth a light response? |

Field Evidence Matrix format:

```json
{
  "field": "exposure_risk",
  "huangnian": {"strength": "strong", "examples": ["food stockpile exposure", "system source suspicion"]},
  "revenge": {"strength": "medium", "examples": ["identity or evidence exposure"]},
  "cultivation": {"strength": "strong", "examples": ["hidden power and identity exposure"]},
  "decision": "core_axis"
}
```

Expected schema shape:

```text
MomentCausalityPack v0.1
  = CoreEnvelope
  + OptionalCausalityModules
```

Core candidates:

- `source_window`;
- `hook`;
- `scene_pressure`;
- `viewer_impulse`;
- `canon_baseline`;
- `actors`;
- `constraints`;
- `action_space`;
- `score_axes`;
- `output_policy`.

Likely optional modules:

- `resource`;
- `exposure`;
- `evidence`;
- `relationship`;
- `genre_rules`;
- `power_boundary`.

## 5. Human Review Loop

Review should be fast:

1. sort candidates by weighted score;
2. watch top 10 clips;
3. choose 3-5 P0 nodes;
4. edit pack constraints;
5. run red-team actions;
6. load into player.

Suggested weighted score:

```text
0.25 emotion_heat
+ 0.25 choice_leverage
+ 0.20 world_constraint_value
+ 0.15 causal_clarity
+ 0.10 watch_flow_fit
+ 0.05 visual_result_fit
```

## 6. Bridge Dogfood Success Criteria

The dogfood pass is successful when:

- 20 episodes can be indexed without manual timestamp bookkeeping;
- ARS outputs at least 20 candidate nodes;
- at least 5 candidates are good enough after quick human review;
- at least 3 candidates can become valid Moment Causality Packs;
- runtime player can show those timestamps as highlight markers;
- companion trigger can use ARS-produced hook and options;
- interaction endpoint can evaluate at least one ARS-produced pack.

## 7. Implementation Shape

Recommended local artifacts:

```text
materials/huangnian/
  videos/
    ep01.mp4
    ep02.mp4
  analysis/
    ep01/
      media_index.json
      transcript.json
      windows.json
      candidates.json
      keyframes/
  packs/
    moment_ep01_c003.json
    moment_ep02_c001.json
```

Runtime seed import:

```text
materials/huangnian/packs/*.json
  -> Runtime seed store
  -> GET /api/short-drama/episodes/{episode_id}/highlights
```

## 8. Risk Controls

| Risk | Control |
|---|---|
| ASR/OCR misses important plot | Let candidate miner accept human notes and manual timestamp patches. |
| Online ASR uploads organizer material | Require explicit operator approval and keep API keys/server credentials out of repo artifacts. |
| ASR hallucinates or mishears core facts | Keep raw transcript, provider, timestamp, and quality flags; never promote unresolved ASR into pack facts. |
| ARS over-selects loud scenes | Score `choice_leverage` and `watch_flow_fit`, not only emotion. |
| Generated packs hallucinate facts | Store source window and transcript snippets for every pack field. |
| Result nodes make the original episode feel stupid | Require canon anchors, a short original-plot note when needed, and `watch_flow_fit`. |
| Pipeline becomes too heavy for deadline | Start with transcript/OCR + keyframe sampling; add shot detection only if needed. |

## 9. Next Step

After the 2026-05-24 first pass, the next step is human review of the generated top candidates:

1. open `tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.md`;
2. watch the top 10 source windows against their keyframes/contact sheets;
3. choose 3-5 P0 nodes;
4. edit constraints and canon notes;
5. convert one reviewed candidate into a real Moment Pack.

## 10. Review + v0.2 Patch Result

Follow-up review on 2026-05-24 covered 25 first-pass candidates: the top 20
plus lower-ranked mechanism-diversity candidates. The reviewed demo candidates
are:

- `huangnian_ep12_c001`: rabbit / Fourdan resource visibility and family trust.
- `huangnian_ep07_c001`: daughter-in-law meal-table humiliation reversal.
- `huangnian_ep03_c001`: first system panel use.
- `huangnian_ep04_c001`: public false accusation / evidence reversal.
- `huangnian_ep06_c001`: white-rice source exposure risk.

First-pass assumptions that failed:

- `resource_crisis` was too broad. Bare mentions of `吃` pulled in scenes that
  were really humiliation, relationship repair, or ordinary meal aftermath.
- Hooks were too templated. `这口吃的要不要现在拿出来？` repeated across unrelated
  rabbit, rice, rotten grain, and family-table scenes.
- `visual_evidence: high` overstated what the script knew. Keyframe refs prove
  nearby visual material exists; they do not prove the described object or
  action unless reviewed.
- `--max-candidates` was not a hard cap because episode-coverage backfill could
  append extra rows.
- The mechanism output was label-bucket aggregation, not emergent clustering.

What v0.2 fixed:

- `resource_crisis` now requires co-occurrence between food/hunger/scarcity and
  distribution, exposure, family, or village pressure. `吃` alone is not enough.
- Hooks and default options now include concrete objects, relationships, or
  decision pressure from the source window when available.
- Reliability now uses `keyframe_ref_quality`; deterministic visual evidence is
  capped at `medium` unless a reviewed or machine-interpreted visual claim
  exists.
- Candidate limiting is now explicit hard-cap behavior. Coverage backfill only
  runs while still under `--max-candidates`.
- The aggregation output is named `mechanism_buckets` and reports that it is not
  emergent semantic clustering.

What still requires human review:

- Correct trigger type, especially resource-vs-humiliation and
  resource-vs-exposure boundaries.
- Original plot note quality: this is product judgment, not ASR output.
- Whether a keyframe/contact sheet actually supports the source claim or only
  provides timestamp context.
- Pack promotion. ARS can draft candidates; it cannot certify demo nodes without
  the reviewed evidence layer.
