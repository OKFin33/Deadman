# Axis Navigator Skill PRD v0.1

> Chinese name: 开发罗盘  
> Product type: independent Codex skill  
> First reference case: Deadman / `要是我来`  
> Date: 2026-05-25  
> Status: zero-context PRD draft

## One Sentence

Axis Navigator is a Codex skill that lets a human owner and a main agent recover
where a project currently is on its development axis, what layer is active, what
just happened, what should happen next, and what must not be done.

## Zero-Context Assumption

Assume the reader has:

- no access to the originating chat thread;
- no memory of previous subagent runs;
- no confidence that the latest answer in chat is still current;
- a repo with scattered docs, dev logs, goal specs, source code, and possibly
  stale handoff notes;
- a human product owner who cannot audit the code deeply;
- multiple agents that may resume from different context windows.

The skill must make the project recoverable from repo evidence alone.

## Problem

Agent collaboration fails in a specific way: not because agents cannot execute a
task, but because they often execute the right kind of task at the wrong layer.

Examples:

- A subagent builds runtime code while the current project state says "wait for
  external SDK; harden non-runtime surfaces".
- A main agent continues a stale plan after a later dev-log entry changed the
  axis.
- A human sees many artifacts but cannot tell whether the project is before or
  after a key boundary.
- A side branch such as image generation or avatar design starts looking like
  the main line.

Product consequence: the team spends tokens and time moving sideways, then pays
cleanup cost because no one had a compact, trusted map of "where we are".

## Product Goal

Create a repo-owned reorientation layer with two outputs:

1. Main-agent view: compact, deterministic, text-first recovery card.
2. Human view: visual, browser-openable project axis page.

Both outputs must be generated from the same underlying state contract, or at
minimum kept mutually checkable, so they do not drift.

## Non-Goals

- Not a full project management system.
- Not a replacement for `.agent/dev-log.md`.
- Not a replacement for ADRs, goal specs, or wiki writeback.
- Not a timeline of every commit or test run.
- Not an autonomous decision maker that changes project direction.
- Not a general chat summarizer.
- Not a dashboard that requires a server to understand the current state.

## Primary Users

| User | Need |
| --- | --- |
| Human product owner | Open one visual artifact and know current position, next decision, and side branches. |
| Main agent | Recover current station and constraints before planning or spawning work. |
| Subagent | Receive a short prompt seed and avoid wrong-layer execution. |
| Reviewer | Check whether a completed task moved the axis or only changed local implementation. |

## Core User Stories

1. As a human owner, I can open a local HTML page and know in under one minute:
   where the project is, what is done, what is current, what is next, and what
   is explicitly deferred.
2. As a main agent, I can read one Markdown file before a task and avoid stale
   or contradictory plans.
3. As a subagent, I can receive a prompt seed that includes current station,
   allowed scope, forbidden work, and required logs.
4. As a reviewer, I can tell whether a subagent changed the axis, and if yes
   which files must be updated.
5. As a future project, I can install the skill without inheriting Deadman
   product assumptions.

## Product Principles

- Repo evidence beats chat memory.
- Current station must be visible without reading the whole changelog.
- Macro axis and micro slice must be separate.
- Side branches must not masquerade as the main line.
- "Do not do" is as important as "next".
- Human view should be visual; agent view should be terse and machine-useful.
- The skill should prefer stale-state warnings over confident fabrication.

## Required Outputs

### 1. Agent Recovery Card

Recommended filename:

```text
.axis/AXIS_FOR_AGENT.md
```

Minimum sections:

- current station;
- current micro slice: previous / current / next;
- active recommendation;
- do-not-do list;
- last reliable validation;
- files to inspect first;
- prompt seed for next subagent;
- update rules.

This file should fit in one to two screens. It is not a full PRD.

### 2. Human Axis View

Recommended filename:

```text
.axis/AXIS_VIEW.html
```

Minimum visual blocks:

- macro phase axis;
- highlighted current phase;
- current station card;
- previous / current / next micro panel;
- side branches and rejoin condition;
- next decision;
- forbidden work;
- last validation summary;
- key files.

This must be a static HTML file with no build step and no remote dependency.

### 3. Optional Canonical State File

Recommended filename:

```text
.axis/axis_state.v0.1.json
```

Purpose: make Markdown and HTML renderable from one source.

Minimum shape:

```json
{
  "project": {
    "name": "string",
    "repo_path": "string",
    "updated_at": "YYYY-MM-DD",
    "owner": "string"
  },
  "current_station": {
    "label": "string",
    "plain_state": "string",
    "product_consequence": "string"
  },
  "macro_axis": [
    {
      "id": "string",
      "label": "string",
      "status": "done|current|next|later|blocked",
      "product_question": "string",
      "artifacts": ["string"],
      "notes": "string"
    }
  ],
  "micro_axis": {
    "previous": "string",
    "current": "string",
    "next": "string"
  },
  "active_recommendation": ["string"],
  "do_not_do": ["string"],
  "side_branches": [
    {
      "label": "string",
      "status": "string",
      "rejoin_condition": "string"
    }
  ],
  "last_reliable_validation": ["string"],
  "files_to_read_first": ["string"],
  "subagent_prompt_seed": "string"
}
```

P0 can skip the JSON file if the skill is still manual. P1 should introduce it
to reduce drift.

## Skill Behaviors

### Init

Creates the axis folder and first draft outputs.

Expected command shape:

```text
axis-navigator init --project <name> --repo <path>
```

Codex skill behavior:

- inspect repo docs and dev-log;
- identify likely main axis;
- ask only if current station cannot be inferred safely;
- create agent card and human view;
- append a dev-log entry if the repo has a dev-log convention.

### Update

Updates current station after a real change.

Expected command shape:

```text
axis-navigator update --station "<new station>"
```

Codex skill behavior:

- read current axis files;
- read latest dev-log and relevant goal spec;
- decide whether the macro phase changed or only micro slice changed;
- update both agent and human outputs;
- record why the station changed.

### Check

Detects drift.

Expected command shape:

```text
axis-navigator check
```

Checks:

- agent card and human view disagree on current station;
- current station contradicts latest dev-log;
- "next" points to a forbidden side branch;
- stale dates;
- missing required files;
- subagent prompt seed lacks do-not-do constraints.

### Render

Regenerates HTML from canonical state when JSON exists.

Expected command shape:

```text
axis-navigator render
```

P0 may render by direct template substitution. No server required.

## Input Sources

The skill should inspect, in this order:

1. existing axis files;
2. `.agent/dev-log.md` tail or project-specific dev log;
3. current goal spec or active task contract;
4. workspace map / README / AGENTS instructions;
5. relevant implementation files only if the station depends on code truth.

It should not summarize the whole repo by default.

## Decision Rules

The skill may update:

- phrasing;
- current micro slice;
- recent validation;
- files to inspect;
- subagent prompt seed;
- side branch status when evidence is clear.

The skill should warn before changing:

- macro phase names;
- project strategy;
- primary product goal;
- ownership boundaries;
- "do not do" constraints;
- canonical artifact locations.

The skill must not:

- hide uncertainty;
- convert a side branch into main line without evidence;
- treat chat-only claims as current truth if repo evidence disagrees;
- record secrets, raw provider outputs, or local-only media paths in public
  human artifacts.

## MVP Scope

P0 should be a Codex skill with templates and instructions, not a full app.

P0 includes:

- `SKILL.md` workflow;
- Markdown agent-card template;
- HTML human-view template;
- optional small validation script;
- examples from Deadman as reference fixtures;
- clear update rules.

P0 does not require:

- server;
- database;
- web framework;
- cross-repo sync;
- automatic graph extraction;
- browser automation;
- LLM-powered full repo summarization.

## P1 Scope

P1 adds:

- canonical `axis_state.v0.1.json`;
- renderer script from JSON to Markdown and HTML;
- drift checker;
- command shortcuts for init/update/check/render;
- project-specific adapters for common files such as `.agent/dev-log.md` and
  `docs/goal_spec/`.

## P2 Scope

P2 may become a richer plugin:

- local browser preview;
- diff view between previous and new axis;
- multi-project index;
- export to wiki;
- handoff packet generator;
- integration with `/goal` contracts.

Only do this after P0 proves it reduces agent drift.

## UX Requirements

### Agent View

- Dense and boring on purpose.
- No decorative prose.
- Current station visible in the first 10 lines.
- Contains a pasteable subagent prompt seed.
- Explicitly names forbidden work.
- Names exact files to inspect first.

### Human View

- Visual, scannable, and static.
- Current station must be visually dominant.
- Macro axis should show done/current/next/later.
- Side branches should be visually separate from the main line.
- Use plain project consequences instead of implementation jargon.
- Avoid requiring the human to understand code structure.

## Acceptance Criteria

The PRD is satisfied when a new project can install the skill and produce:

- one agent recovery card;
- one human visual axis page;
- one documented update protocol;
- one check that catches stale or contradictory state.

Deadman-specific acceptance:

- a new main agent can read the agent card and correctly answer:
  - what is the current station?
  - what should be done next?
  - what must not be done?
  - which files are first-read files?
  - what prompt should be given to a subagent?
- the human can open the HTML page and identify the current phase without
  reading the dev-log.

## Metrics

Useful early metrics:

- time for a new agent to produce a correct next-step plan;
- number of repeated "where are we?" questions per project week;
- number of subagent tasks rejected for wrong-layer work;
- number of stale-doc contradictions caught by `axis-navigator check`;
- human owner confidence that the current station is understandable.

## Risks

| Risk | Consequence | Mitigation |
| --- | --- | --- |
| Axis becomes stale | Agents trust wrong map | `check` command and update rules tied to dev-log. |
| HTML becomes pretty but untrusted | Human sees a dashboard that lies | Render from canonical state in P1. |
| Skill becomes a project manager | Scope balloons | Keep it to orientation, not scheduling. |
| Skill over-infers from repo text | False certainty | Prefer warning state over confident state. |
| Deadman assumptions leak into other projects | Skill is not reusable | Keep templates generic and examples separate. |

## First Implementation Recommendation

Build P0 as a local Codex skill named:

```text
axis-navigator
```

Suggested install path:

```text
/Users/okfin3/.codex/skills/axis-navigator/
```

Suggested files:

```text
SKILL.md
templates/AXIS_FOR_AGENT.md
templates/AXIS_VIEW.html
examples/deadman/
scripts/check_axis.py
```

Deadman can remain the first worked example, but the skill must not depend on
Deadman paths.

## Open Questions

1. Should the canonical state file be required in P0, or introduced only after
   one more manual trial?
2. Should project repos store axis files under `.axis/`, `docs/axis/`, or a
   project-specific docs folder?
3. Should the skill update `.agent/dev-log.md` automatically, or only produce
   a suggested log entry?
4. Should the human HTML include a mini changelog, or only current-state
   orientation?
5. Should this later integrate with `/goal` so a goal can declare which axis
   phase it intends to move?

## Current Recommendation On Open Questions

- Use `.axis/` as the default location for new projects.
- Keep Deadman compatibility by linking existing `docs/Axis_*` files
  until migration is useful.
- Make canonical JSON optional in P0 but mandatory in P1.
- Let the skill suggest a dev-log entry in P0; automate it only after the
  update behavior is stable.
- Keep the human HTML current-state first. Changelog belongs in dev-log.
