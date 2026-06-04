# Branch 3 UX Core Pivot Log v0.1

> Product: Deadman / 要是我来  
> Date: 2026-06-03  
> Status: context log for product-direction pivot  
> Related PRD: `docs/Branch3_要是我来_PRD_v0.4_UX_Core.md`

## 0. Why This Log Exists

This file records the product turn from the previous "if-line / branch-choice"
shape toward the new UX core:

```text
我想说一句。
```

The pivot is not a cosmetic copy change. It changes what the user-side runtime
must protect, what Deadman Studio must produce, and what the CABRuntime
integration should mean inside the viewer experience.

## 1. Before The Pivot

The working product shape before this pivot was:

```text
short-drama highlight
  -> companion notice
  -> tap companion
  -> 3 options or custom action
  -> local judgment / friend response
  -> continue watching
```

This was already better than a full RPG branch client. `Branch3_要是我来_PRD_v0.3.md`
had correctly rejected:

- long-form RP;
- free companion chat;
- full alternate timeline simulation;
- visible plot-impact disclaimers;
- fixed field-table result surfaces.

The resident runtime plan also correctly established:

- Deadman owns viewer session, event protocol, companion policy, and product
  memory;
- CABRuntime is consumed as a governed runtime substrate;
- formal judgment failure must fail closed;
- CAB should not be called on every playback tick.

## 2. What Was Still Wrong

The remaining problem was not that the frontend needed nicer labels. The deeper
problem was that the system still treated the three presets as action options:

```json
"default_options": [
  "今晚分兔肉，先让四蛋确认自己也有份",
  "先留下兔子和皮毛，改用别的食物补这一顿",
  "把兔子当成四蛋的功劳，只少量处理给全家尝味"
]
```

That shape pushes the product back toward:

- "你要怎么做";
- branch/RPG choice;
- action-menu semantics;
- frontend-side copy patching to make options feel lighter.

The `Branch3_Companion_Product_Detail_Spec_v0.1.md` attempt to split "路过 /
吐槽 / if 线讨论" exposed the same tension. It correctly noticed that the
viewer mind should be lighter, but the two-level entry introduced new cognitive
load:

```text
light reaction first
  -> expand if-line discussion
```

That makes the user understand the feature as two modes. For P0, that is the
wrong mental model.

## 3. Product Correction

The new core is:

```text
用户不是来做剧情选择。
用户是想把话说出口。
```

The three presets are not three branch choices. They are three attempts by the
system to guess the user's "话在嘴边":

```text
This one?
Or this one?
Or actually this one?
```

The product promise becomes:

```text
搭子不是问你要怎么改剧情。
搭子是在这一刻接住你想说的那一句。
```

## 4. New User-Side Core

User-side UX must stay one-level and light:

```text
companion notices emotional moment
  -> user taps
  -> one compact bubble
  -> 3 short mouthpiece candidates + custom
  -> one friend-style response
  -> continue watching
```

No explicit "吐槽 vs if 线" mode split in P0.

The visible surface should feel like:

- "凭什么啊";
- "先护住她";
- "别让她白挨";
- "这口气得有人出";
- "我有不同想法".

It should not feel like:

- "请选择分支";
- "展开 if 线";
- "你会怎么做";
- "A/B/C 行动菜单";
- "系统正在计算局部后果".

## 5. New Producer-Side Core

The production side becomes heavier, not lighter.

Deadman Studio must produce scene-semantic `mouthpiece_candidates`, not plain
action strings. Each promoted moment should carry three reviewed candidates:

```text
display_text       -> what the viewer sees
action_payload     -> what judgment/CAB consumes
emotion_role       -> what emotional outlet this represents
semantic_role      -> why this option is distinct
evidence_refs      -> what scene evidence supports it
constraint_refs    -> what runtime constraints it must respect
```

This is the main product contract change.

## 6. CABRuntime Meaning After The Pivot

CABRuntime must not become a decorative backend hidden behind frontend labels.

The CAB-backed user-side loop matters because the viewer action is a runtime
event, not a fake UI click:

- it is submitted with stable `candidate_id`;
- it carries hidden semantic payload;
- it is checked against the moment pack and runtime constraints;
- it fails closed on provider/schema/runtime failure;
- it produces structured output for Deadman to translate into friend voice;
- it leaves traceable session/provenance evidence for product evaluation.

Ownership stays split:

| Layer | Owner | Product consequence |
| --- | --- | --- |
| UX copy, companion pacing, viewer session, mouthpiece semantics | Deadman | Product tone stays in the host. |
| Runtime execution, protocol safety, structured output/error, worker/session substrate | CABRuntime | The event is governed and auditable. |
| Scene-semantic candidate production and review | Deadman Studio | The three visible choices come from production judgment, not UI guesswork. |

## 7. What To Reuse

Reuse:

- vertical player shell;
- tomato companion states and assets;
- runtime event endpoint;
- viewer session store;
- CAB fail-closed path;
- promoted Huangnian moment packs as migration source material;
- producer graph / LangGraph direction;
- human review and validation gates;
- aggregate percentage cue as demo material.

Reference only:

- current `default_options`;
- current local `displayText` compaction;
- old friend-voice lead templates;
- "路过 / 吐槽 / if 线" detailed split.

Discard or rewrite for P0:

- two-level "展开 if 线" entry;
- user-facing "你要怎么做" framing;
- mode labels that make the user choose between light and serious interaction;
- result copy that explains evidence like a field table.

## 8. Consequence For Current Docs

`Branch3_要是我来_PRD_v0.3.md` remains useful background but is superseded by
v0.4 for:

- UX core;
- preset option semantics;
- user-side acceptance;
- Studio artifact contract;
- CABRuntime role inside the user-side loop.

`Branch3_Companion_Product_Detail_Spec_v0.1.md` should be treated as a prior
design attempt. Its friend-voice and active-companion observations are still
useful, but its "吐槽 vs if 线" two-level information architecture is not the
P0 direction.

`Branch3_Demo_Episode_Pack_Contract_v0.1.md` must be patched later so
`default_options` becomes legacy and `mouthpiece_candidates` becomes the primary
episode-pack field.

`Deadman_Studio_Implementation_Contract_v0.1.md` and the LangGraph LLM extension
must be patched later so the producer graph validates candidate distinctness and
payload grounding.

## 9. Open Questions

These are not blocking for the v0.4 PRD, but they affect implementation order:

1. Should `tap_reaction` exist at all in P0, or should every tap enter the same
   three-candidate mouthpiece surface?
2. Should `display_text` target 8, 10, 12, or 14 Chinese characters as the hard
   default limit?
3. Should custom input be visually equal to a fourth candidate, or slightly
   de-emphasized as "我有不同想法"?
4. Should production candidate review happen in the same human review gate as
   moment promotion, or as a second mouthpiece-specific review gate?
5. Should aggregate percentages be tied to candidate id immediately, or remain
   demo-static per result in v0.4 P0?

