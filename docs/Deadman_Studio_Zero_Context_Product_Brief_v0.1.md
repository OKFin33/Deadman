# Deadman Studio Zero-Context Product Brief v0.1

> Product: Deadman / `要是我来`
> Audience: external reviewer, competition judge, zero-context collaborator
> Date: 2026-05-25

## One-Sentence Definition

Deadman Studio is the producer-side tool that turns raw short-drama episodes
into reviewed Moment Packs that the user-side `要是我来` mobile player can
consume.

## Product Split

Deadman has two product surfaces with different users and logic.

| Surface | User | Core Job |
| --- | --- | --- |
| User-side player | Short-drama viewer | Watch an episode, notice the companion prompt, choose or type "what I would do", and receive a believable local consequence. |
| Deadman Studio | Producer / operator / creator | Ingest short-drama materials, understand the story locally, mine interaction moments, review them, and publish runtime-safe packs. |

This split matters because the user-side player is a real-time entertainment
experience, while the producer side is an offline or semi-offline content
production workflow.

## Why The Producer Side Exists

Without a producer side, every new drama would require manual work:

- manually watch episodes;
- manually find "要是我来" moments;
- manually summarize character, scene, and world constraints;
- manually write candidate options;
- manually connect the selected nodes to the player.

That does not scale across genres. It also makes the demo hard to reproduce.

Deadman Studio makes this repeatable: raw episodes become evidence, evidence
becomes candidate moments, reviewed moments become Moment Packs, and Moment
Packs become player-consumable runtime data.

## Why LangGraph Fits Here

The producer workflow is a multi-stage graph:

```text
local MP4s
  -> media registry
  -> ASR / timeline windows / keyframes
  -> candidate mining
  -> field clustering
  -> human review
  -> Drama Context Pack
  -> Moment Causality Packs
  -> validation
  -> mobile player consumption
```

This is a better fit for LangGraph than for a single prompt or a hand-written
script chain because it needs:

- named stages;
- resumable jobs;
- a human review gate;
- repeatable artifacts;
- audit-friendly reports;
- failure isolation.

LangGraph is used only for the producer-side workflow wrapper. It is not the
user-side judgment runtime, not the companion chat runtime, and not a
replacement for CABRuntime.

## What P0 Proves

P0 proves the smallest complete production loop:

1. Start from local downloaded short-drama episodes.
2. Produce structured source evidence.
3. Mine candidate "what if I did this" moments.
4. Cluster the causal field needs behind those moments.
5. Pause for human review.
6. Publish reviewed Moment Packs.
7. Validate that the player can consume the packs.

The first closed-loop target is `荒年全村啃树皮，我有系统满仓肉` because it already
has reviewed P0 moments and a working player bridge.

## What Reviewers Should Inspect

External review should focus on these questions:

- Can the workflow be rerun from local materials?
- Are the producer steps named and auditable?
- Is there a human review gate before publishing runtime packs?
- Are runtime-facing packs free of raw local paths, secrets, and ignored tmp refs?
- Can the mobile player consume the published moments?
- Does the same workflow direction plausibly transfer to other short-drama genres?

The goal is not to prove a polished creator SaaS. The goal is to prove an AI
full-stack pipeline from drama material to user-facing interaction.

## Boundaries

Deadman Studio v0.1 does not claim:

- a complete creator platform UI;
- automatic commercial-grade video understanding;
- fully automatic publication without human review;
- user-side real-time judgment runtime;
- CABRuntime SDK integration;
- image-generation provider integration;
- runtime promotion for every tested drama.

`云渺` and `幸得相遇离婚时` are currently migration and field-evidence materials.
They help validate the minimum field set, but they are not promoted runtime
packs in this P0 producer flow.

## Relationship To Existing Engineering Spec

The executable implementation contract is:

```text
docs/Deadman_Studio_Implementation_Contract_v0.1.md
```

The underlying goal specs remain:

```text
docs/goal_spec/Deadman_LangGraph_Producer_Pipeline_v0.1.md
docs/goal_spec/Deadman_LangGraph_Producer_LLM_Extension_v0.1.md
```

This brief explains why those engineering plans exist and how an external
reviewer should evaluate the producer-side product.
