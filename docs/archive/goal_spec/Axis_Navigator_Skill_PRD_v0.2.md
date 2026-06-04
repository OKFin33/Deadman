# Axis Navigator Skill PRD v0.2

> Chinese name: 开发罗盘  
> Product type: independent Codex skill and optional LaunchPad orientation layer  
> First reference cases: Deadman, CABRuntime, LaunchPad-managed project work  
> Date: 2026-05-25  
> Status: zero-context PRD draft  
> Supersedes: `Axis_Navigator_Skill_PRD_v0.1.md`

## v0.2 Change Thesis

v0.1 defined Axis as a recovery card plus a human visual page. v0.2 changes the
center of gravity:

- the core object is no longer only "current station";
- the core object is **Project Position**;
- canonical state is mandatory in P0, not optional in P1;
- Axis must calibrate against a stack of moving documents, not just a dev-log;
- Axis may integrate with LaunchPad, but must not become LaunchPad.

Product consequence: a new human or agent should not merely know "what happened
last". They should know where the work is in absolute terms, where it is
relative to the current execution spec, which future roadmap items are still
illegal, and which document currently governs the next move.

## One Sentence

Axis Navigator is a repo-owned skill that keeps a human owner and agent team
oriented by continuously rendering the project's absolute and relative position
from PRDs, execution specs, roadmaps, logs, validations, and optional LaunchPad
runtime artifacts.

## Product Definition

Axis is a **positioning layer** for agentic development.

It is not a planner, scheduler, runtime, or project manager. Its job is to
answer:

1. Where are we in the product's absolute lifecycle?
2. Where are we relative to the active execution spec?
3. Where are we on the longer roadmap?
4. What evidence proves that position?
5. What document currently governs the next legal move?
6. What work is tempting but wrong-layer right now?

The skill maintains two dossiers generated from one canonical state:

- **Agent Position Dossier**: terse, structured, pasteable into an agent or
  subagent context.
- **Human Position Dossier**: static browser-openable HTML that visualizes the
  project axis and the current decision surface.

## Zero-Context Assumption

Assume the reader has:

- no access to the originating chat thread;
- no memory of previous agent runs;
- no confidence that the latest chat answer is still current;
- a repo with PRDs, execution specs, roadmaps, goal specs, dev logs, reviews,
  tests, and possibly stale handoff notes;
- a human product owner who cannot audit code deeply;
- multiple agents that may resume from different context windows;
- specs that are themselves changing over time.

The skill must make the project recoverable from repo evidence alone.

## Problem

Agent collaboration fails when people and agents lose position.

The common failure is not "no one can do work". The failure is that someone does
the right-looking work at the wrong layer:

- implementing roadmap work before the active execution spec allows it;
- following an old PRD after a newer spec narrowed the scope;
- continuing a local fix when the absolute project phase is actually "replan";
- treating a side branch as mainline because the latest artifact is visually
  prominent;
- handing a subagent an impressive but stale prompt.

Product consequence: execution feels busy but not convergent. The owner cannot
judge whether the work moved the product, the agent cannot tell whether it is
inside the allowed lane, and later cleanup costs more than the original work.

## Product Goal

Create a lightweight, repo-owned orientation layer that:

- computes and records Project Position;
- keeps human and agent views synchronized;
- warns when specs, logs, code evidence, or LaunchPad state contradict each
  other;
- names the next legal move and the tempting illegal moves;
- produces a subagent-ready prompt seed with governing documents and boundaries.

Axis should let a project survive context loss without turning every new agent
into an archaeology session.

## Core Concept: Project Position

Project Position is a structured answer to "where are we?"

It has six required dimensions.

| Dimension | Meaning | Product consequence |
| --- | --- | --- |
| `absolute_position` | Position against the product north star and lifecycle. | Tells whether the project is in discovery, design, build, review, release, or repair. |
| `relative_position` | Position inside the active execution spec or slice. | Tells what step is current and what is not yet allowed. |
| `roadmap_position` | Position against the long-range roadmap. | Separates current work from later ambition. |
| `evidence_position` | What repo evidence actually proves. | Prevents docs from claiming work that code/tests do not prove. |
| `drift_position` | Known contradiction or staleness. | Surfaces when the map is unsafe to trust. |
| `next_legal_move` | The next action permitted by the current governing doc stack. | Prevents agents from picking useful-looking but wrong-layer tasks. |

## Document Stack

Axis absorbs the status architecture of PRD, execution spec, roadmap, and
runtime logs. It does not absorb their product content.

| Document role | Example | Axis use |
| --- | --- | --- |
| `north_star_prd` | product PRD or mission doc | Defines absolute product intent and lifecycle target. |
| `active_execution_spec` | current implementation spec, slice plan, or launch charter | Defines current allowed work. |
| `strategic_roadmap` | v1.0 roadmap, long-horizon plan | Defines future sequencing and non-current ambition. |
| `goal_spec` | local goal spec or experiment spec | Defines local test or branch objective. |
| `runtime_state` | `.launchpad/runtime_state.yaml` when present | Defines control-plane state, not product truth. |
| `dev_log` | `.agent/dev-log.md` or equivalent | Records what changed and what was verified. |
| `validation_evidence` | tests, smoke logs, review docs | Proves whether claims are backed by execution. |
| `handoff_or_review` | Thread Packet, Return Packet, review finding | Records bounded transfer and independent judgment. |

Rules:

- PRD answers "why and what";
- execution spec answers "what is legal now";
- roadmap answers "what is later";
- logs and tests answer "what actually happened";
- LaunchPad state answers "what the control plane currently permits".

When these disagree, Axis must show the disagreement instead of selecting the
most convenient answer.

## Non-Goals

- Not a full project management system.
- Not a scheduler.
- Not a replacement for PRDs, execution specs, roadmaps, ADRs, or dev logs.
- Not a replacement for LaunchPad.
- Not a replacement for CABRuntime or any agent runtime.
- Not a task tracker that lists every commit or test.
- Not an autonomous decision maker that changes product direction.
- Not a general chat summarizer.
- Not a dashboard that requires a server.
- Not a full repo summarizer.

## Primary Users

| User | Need |
| --- | --- |
| Human product owner | Open one visual artifact and know current position, next decision, and wrong-layer traps. |
| Main agent | Recover governing documents, current position, and legal next action before planning. |
| Subagent | Receive a compact prompt seed with scope, forbidden work, files, and validation expectations. |
| Reviewer | Check whether a result changed position, contradicted the spec stack, or only completed local work. |
| LaunchPad operator | See whether launch state, charter, checkpoint, and thread packets agree with the project axis. |

## Core User Stories

1. As a human owner, I can open one static HTML file and know in under one
   minute where the project is, why that is the current position, what decision
   is next, and what work is explicitly premature.
2. As a main agent, I can read one Markdown dossier before planning and avoid
   stale, contradictory, or wrong-layer execution.
3. As a subagent, I can receive a prompt seed that includes current position,
   governing documents, allowed scope, forbidden scope, first-read files, and
   required validation.
4. As a reviewer, I can tell whether completed work moved the axis, only
   advanced the current slice, or created drift that needs a spec update.
5. As a LaunchPad-managed project, I can include Axis position in Launch Checks,
   checkpoints, and Thread Packets without letting Axis mutate LaunchPad state.

## Product Principles

- Position beats progress.
- Repo evidence beats chat memory.
- Absolute position and relative position must be separate.
- Current execution and future roadmap must be separate.
- A pretty map that lies is worse than no map.
- "Do not do" is as important as "next".
- Axis should warn when stale rather than fabricate certainty.
- Agent view should be terse and deterministic.
- Human view should be visual and consequence-first.
- Axis may read control-plane artifacts, but only the owning runtime mutates
  them.

## Required Artifacts

### 1. Canonical Position State

Recommended standalone path:

```text
.axis/axis_state.v0.2.json
```

Recommended LaunchPad-integrated path:

```text
.launchpad/axis/axis_state.v0.2.json
```

This file is mandatory in P0. Markdown and HTML are rendered from it.

Minimum shape:

```json
{
  "schema_version": "axis_state.v0.2",
  "project": {
    "name": "string",
    "repo_path": "string",
    "owner": "string",
    "updated_at": "YYYY-MM-DD",
    "axis_home": ".axis|.launchpad/axis"
  },
  "governing_stack": {
    "north_star_prd": {
      "path": "string",
      "version": "string",
      "status": "active|stale|unknown"
    },
    "active_execution_spec": {
      "path": "string",
      "version": "string",
      "status": "active|stale|unknown"
    },
    "strategic_roadmap": {
      "path": "string",
      "version": "string",
      "status": "active|stale|unknown"
    },
    "runtime_state": {
      "path": "string|null",
      "status": "active|absent|contradictory|unknown"
    }
  },
  "positioning": {
    "absolute_position": {
      "label": "string",
      "phase": "discovery|design|dev|e2e|review|qa|release|repair|handoff|paused|unknown",
      "plain_state": "string",
      "product_consequence": "string"
    },
    "relative_position": {
      "active_spec_step": "string",
      "previous": "string",
      "current": "string",
      "next": "string",
      "blocked_by": ["string"]
    },
    "roadmap_position": {
      "current_band": "string",
      "later_bands": ["string"],
      "premature_items": ["string"]
    },
    "evidence_position": {
      "last_reliable_validation": ["string"],
      "implementation_evidence": ["string"],
      "doc_evidence": ["string"],
      "unproven_claims": ["string"]
    },
    "drift_position": {
      "status": "none|warning|blocked",
      "types": [
        "evidence_conflict",
        "spec_obsolete",
        "implementation_ahead",
        "implementation_behind",
        "roadmap_premature",
        "wrong_layer_work",
        "human_decision_needed"
      ],
      "notes": ["string"]
    }
  },
  "next_legal_move": [
    {
      "action": "string",
      "why_now": "string",
      "governing_doc": "string",
      "required_evidence": ["string"],
      "forbidden_adjacent_moves": ["string"]
    }
  ],
  "side_branches": [
    {
      "label": "string",
      "status": "active|parked|done|blocked|unknown",
      "rejoin_condition": "string"
    }
  ],
  "dossiers": {
    "agent_path": "string",
    "human_path": "string"
  },
  "subagent_prompt_seed": {
    "summary": "string",
    "allowed_scope": ["string"],
    "forbidden_scope": ["string"],
    "first_read_files": ["string"],
    "return_contract": ["string"]
  }
}
```

### 2. Agent Position Dossier

Recommended standalone path:

```text
.axis/AXIS_FOR_AGENT.md
```

Recommended LaunchPad-integrated path:

```text
.launchpad/axis/AXIS_FOR_AGENT.md
```

Minimum sections:

- current position in the first 10 lines;
- governing document stack;
- absolute position;
- relative position;
- roadmap position and premature items;
- drift warnings;
- next legal move;
- do-not-do list;
- last reliable validation;
- files to inspect first;
- subagent prompt seed;
- update rules.

This file should fit in one to two screens. It is a recovery dossier, not a
full PRD.

### 3. Human Position Dossier

Recommended standalone path:

```text
.axis/AXIS_VIEW.html
```

Recommended LaunchPad-integrated path:

```text
.launchpad/axis/AXIS_VIEW.html
```

Minimum visual blocks:

- macro lifecycle axis;
- highlighted absolute position;
- active execution-spec slice;
- roadmap band with future items clearly separated;
- drift warning panel;
- next legal move panel;
- side branch map with rejoin conditions;
- evidence chips for latest validation;
- governing document stack;
- files to inspect or decide on.

This must be a static HTML file with no build step and no remote dependency.

### 4. Evidence Index

Recommended path:

```text
.axis/evidence_index.md
```

or:

```text
.launchpad/axis/evidence_index.md
```

P0 may keep this as a compact section in the canonical JSON. P1 should extract
it when projects have many validations, reviews, or handoffs.

Purpose:

- prevent Axis from becoming a claim-only dashboard;
- show which file or command supports each position claim;
- let reviewers trace stale or contradictory evidence quickly.

## Skill Behaviors

### Init

Creates the axis home and first draft dossiers.

Expected command shape:

```text
axis-navigator init --project <name> --repo <path>
```

Behavior:

- inspect repo docs, dev-log, goal specs, and optional LaunchPad state;
- identify likely governing document stack;
- ask only when current position cannot be inferred safely;
- create canonical state, agent dossier, and human dossier;
- suggest a dev-log entry if the repo has a dev-log convention.

### Calibrate

Core v0.2 behavior. Recomputes Project Position from current evidence.

Expected command shape:

```text
axis-navigator calibrate
```

Behavior:

- read canonical state;
- re-read governing stack;
- check latest dev-log and validation evidence;
- compare active execution spec against roadmap and PRD;
- compare optional LaunchPad state against Axis position;
- update position when evidence is clear;
- otherwise mark drift and name the missing decision or evidence.

### Update

Records a known position change after real work.

Expected command shape:

```text
axis-navigator update --position "<new position>" --evidence "<file-or-command>"
```

Behavior:

- decide whether the absolute position changed or only the relative slice moved;
- update canonical state first;
- render both dossiers from canonical state;
- record why the position changed.

### Check

Detects drift without changing the canonical state.

Expected command shape:

```text
axis-navigator check
```

Checks:

- canonical state, agent dossier, and human dossier disagree;
- active execution spec is older than a later accepted plan;
- next legal move points into a roadmap item marked later;
- dev-log says work happened but evidence position does not include it;
- LaunchPad state and Axis position contradict each other;
- subagent prompt seed lacks forbidden scope;
- stale dates or missing governing documents.

### Render

Regenerates Markdown and HTML from canonical state.

Expected command shape:

```text
axis-navigator render
```

No server is required.

### Thread Seed

Produces a subagent-ready seed from canonical state.

Expected command shape:

```text
axis-navigator thread-seed --objective "<bounded objective>"
```

Output includes:

- current position;
- governing documents;
- allowed scope;
- forbidden scope;
- first-read files;
- expected return contract;
- validation expectation.

### LaunchPad Sync

Optional behavior when `.launchpad/` exists.

Expected command shape:

```text
axis-navigator launchpad-sync
```

Behavior:

- read `.launchpad/runtime_state.yaml`;
- read active Launch Check, Launch Charter, checkpoint, or Thread Packet when
  present;
- render Axis artifacts under `.launchpad/axis/` if the project opts in;
- produce warnings when LaunchPad state and Axis position disagree;
- never mutate `.launchpad/runtime_state.yaml`.

## Input Source Priority

The skill should inspect, in this order:

1. existing Axis canonical state and dossiers;
2. active execution spec, Launch Charter, or current goal spec;
3. PRD or north-star document;
4. roadmap;
5. `.agent/dev-log.md` tail or project-specific dev log;
6. latest validation, smoke, review, or Return Packet;
7. `.launchpad/runtime_state.yaml` and related LaunchPad artifacts when present;
8. workspace map, README, AGENTS instructions;
9. implementation files only when position depends on implementation truth.

It must not summarize the whole repo by default.

## Decision Rules

Axis may update without human approval:

- phrasing;
- latest evidence;
- dossier rendering;
- relative slice when evidence is explicit;
- files to inspect first;
- subagent prompt seed;
- side branch status when evidence is unambiguous.

Axis should warn before changing:

- absolute phase;
- active execution spec;
- strategic roadmap interpretation;
- project strategy;
- ownership boundaries;
- "do not do" constraints;
- canonical artifact locations.

Axis must not:

- hide uncertainty;
- convert a side branch into mainline without evidence;
- treat chat-only claims as current truth when repo evidence disagrees;
- approve LaunchPad launch state;
- mutate external runtime state;
- record secrets, raw provider outputs, or local-only media paths in public
  human artifacts.

## LaunchPad Integration

Axis can become part of LaunchPad as an orientation and recovery surface.

It should not replace LaunchPad's control plane.

| LaunchPad owns | Axis owns |
| --- | --- |
| runtime state transitions | position interpretation |
| Launch Charter approval | governing-stack visibility |
| Launch Check surface | drift warning |
| checkpoint lifecycle | evidence-position rendering |
| Thread Packet creation | agent prompt seed content |
| Return Packet ingestion | whether returned work moved the axis |

Recommended integration:

- standalone projects use `.axis/`;
- LaunchPad-managed projects may use `.launchpad/axis/`;
- Launch Checks should link the human dossier when available;
- Thread Packets should include or reference the agent dossier;
- checkpoints should trigger `axis-navigator calibrate`;
- `prepare-launch` may require `axis-navigator check` to pass or explicitly log
  a waiver.

Product consequence: the owner sees not only "LaunchPad says launch_ready", but
also "this is the current project position and these roadmap items remain
illegal". That reduces false confidence from a clean control-plane state.

## MVP Scope

P0 should be a Codex skill with a mandatory canonical state file and static
rendering.

P0 includes:

- `SKILL.md` workflow;
- `axis_state.v0.2.json` template;
- `AXIS_FOR_AGENT.md` template;
- `AXIS_VIEW.html` template;
- renderer from JSON to Markdown and HTML;
- drift checker for the most common contradictions;
- examples from Deadman and one LaunchPad-managed project;
- clear update rules.

P0 does not require:

- server;
- database;
- web framework;
- automatic graph extraction;
- browser automation;
- LLM-powered full repo summarization;
- multi-project index;
- automatic LaunchPad mutation.

## P1 Scope

P1 adds:

- richer evidence index;
- diff view between previous and new position;
- adapter modules for common spec stacks;
- stronger stale-document detection;
- Thread Packet prompt-seed export;
- optional wiki export.

## P2 Scope

P2 may become a richer plugin:

- local browser preview;
- multi-project LaunchPad axis index;
- interactive filtering by document role, evidence, and drift type;
- integration with `/goal` contracts;
- position history replay.

Only do this after P0 proves it reduces wrong-layer agent work.

## UX Requirements

### Agent View

- Dense and boring on purpose.
- Current position visible in the first 10 lines.
- Names the governing document stack.
- Separates absolute, relative, and roadmap position.
- Contains a pasteable subagent prompt seed.
- Explicitly names forbidden work.
- Names exact files to inspect first.
- Shows drift before next action when drift is blocking.

### Human View

- Visual, scannable, and static.
- Current position must be visually dominant.
- Absolute lifecycle and active execution slice must both be visible.
- Future roadmap items must not look like current tasks.
- Side branches must be visually separate from the main line.
- Use plain product consequences instead of implementation jargon.
- Avoid requiring the human to understand code structure.

## Acceptance Criteria

The PRD is satisfied when a new project can install the skill and produce:

- one canonical position state;
- one agent position dossier;
- one human visual position dossier;
- one documented update protocol;
- one check that catches stale or contradictory position.

General acceptance:

- a new main agent can answer:
  - what is the absolute project position?
  - what is the relative position in the active execution spec?
  - what roadmap items are explicitly later?
  - what is the next legal move?
  - what must not be done?
  - which files prove the current position?
- the human can open the HTML page and identify current position and next
  decision without reading the dev-log.

LaunchPad acceptance:

- in a LaunchPad-managed repo, Axis can read runtime state and active surface;
- Axis can say whether LaunchPad state and Project Position agree;
- Axis can render `.launchpad/axis/AXIS_FOR_AGENT.md` and
  `.launchpad/axis/AXIS_VIEW.html`;
- Axis can provide a prompt seed suitable for inclusion in a Thread Packet;
- Axis never mutates `.launchpad/runtime_state.yaml`.

Drift acceptance:

- given a stale execution spec and newer dev-log evidence, `check` reports
  `spec_obsolete` or `evidence_conflict`;
- given a next action that belongs to a future roadmap band, `check` reports
  `roadmap_premature`;
- given a LaunchPad state that says launch-ready while Axis has blocking drift,
  `check` reports the conflict instead of hiding it.

## Metrics

Useful early metrics:

- time for a new agent to produce a correct next-step plan;
- number of repeated "where are we?" questions per project week;
- number of subagent tasks rejected for wrong-layer work;
- number of stale-doc contradictions caught by `axis-navigator check`;
- number of roadmap-premature tasks prevented;
- human owner confidence that the current position is understandable.

## Risks

| Risk | Consequence | Mitigation |
| --- | --- | --- |
| Axis becomes stale | Agents trust the wrong map | Mandatory `check`, dev-log evidence, stale-date warnings. |
| HTML becomes pretty but untrusted | Human sees a dashboard that lies | Render from canonical state only. |
| Axis becomes a project manager | Scope balloons and conflicts with LaunchPad | Keep it to position, drift, and next legal move. |
| Axis overfits LaunchPad | Standalone projects cannot use it | Keep `.axis/` as default and `.launchpad/axis/` as optional. |
| Axis over-infers from repo text | False certainty | Prefer warning state over confident state. |
| Spec stack is unclear | Next legal move is arbitrary | Require governing document roles and confidence. |
| Deadman assumptions leak into other projects | Skill is not reusable | Keep examples separate from templates. |

## First Implementation Recommendation

Build P0 as a local Codex skill named:

```text
axis-navigator
```

Suggested install path:

```text
/Users/okfin3/.codex/skills/axis-navigator/
```

Suggested skill files:

```text
SKILL.md
templates/axis_state.v0.2.json
templates/AXIS_FOR_AGENT.md
templates/AXIS_VIEW.html
scripts/render_axis.py
scripts/check_axis.py
scripts/calibrate_axis.py
examples/deadman/
examples/launchpad/
```

Suggested project output for standalone repos:

```text
.axis/axis_state.v0.2.json
.axis/AXIS_FOR_AGENT.md
.axis/AXIS_VIEW.html
.axis/evidence_index.md
```

Suggested project output for LaunchPad-integrated repos:

```text
.launchpad/axis/axis_state.v0.2.json
.launchpad/axis/AXIS_FOR_AGENT.md
.launchpad/axis/AXIS_VIEW.html
.launchpad/axis/evidence_index.md
```

## Open Questions

1. Should LaunchPad-integrated projects store Axis only under `.launchpad/axis/`,
   or mirror a short pointer under `.axis/`?
2. Should `axis-navigator check` be allowed to fail a Launch Check by default,
   or only produce a warning until the first real project trial?
3. Should Axis keep historical position snapshots, or should history remain in
   dev-log and checkpoints?
4. Should the human dossier include a mini changelog, or stay current-position
   only?
5. Should `/goal` or future CABRuntime packs reference Axis state directly?

## Current Recommendations On Open Questions

- Use `.axis/` as the standalone default.
- Use `.launchpad/axis/` when the project is explicitly LaunchPad-managed.
- Allow a `.axis/README.md` pointer to `.launchpad/axis/` if discoverability is
  useful.
- In early P0, `axis-navigator check` should warn before Launch Check. After
  one successful trial, it can become a blocking preflight with waiver support.
- Keep historical position in dev-log, checkpoints, and optional snapshots.
  The human dossier should stay current-position first.
- Let `/goal` and CABRuntime read Axis as context later, but do not make Axis
  depend on either one.
