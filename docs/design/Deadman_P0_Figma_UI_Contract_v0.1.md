# Deadman P0 Figma UI Contract v0.1

> Product: Deadman / 要是我来  
> Surface: user-side mobile player  
> Purpose: first Figma review board source  
> Primary frame: 390x844  
> Validation frames: 393x852, 430x932  
> Date: 2026-06-01

## 0. Board Goal

Create a Figma board named:

```text
Deadman P0 Mobile UI States v0.1
```

This board is a UI contract, not a product-logic source of truth. It exists so
Zab can adjust the look, spacing, hierarchy, and copy before Codex applies the
changes back to `frontend/`.

Figma owns visual state layout, phone safe areas, companion position and scale,
bubble shape, typography hierarchy, color and spacing tokens, and review notes.

Code/PRD owns state machine transitions, runtime event timing, viewer session,
CABRuntime/judgment API, data contracts, and retry/error semantics.

## 1. Product Framing

Deadman is a mobile-first short-drama interaction layer. At a high-emotion
moment, a tomato-robed watching companion notices the same beat, lets the viewer
choose or type "要是我来", and replies in a friend-like way grounded in the
moment.

Design tone:

```text
short-drama tension + warm watching friend + sharp mild roast
```

Do not make it look like a SaaS dashboard, modal survey, script-analysis report,
generic chatbot, or desktop product shrunk into mobile.

## 2. Required 390x844 Frames

### 00 Contract

- title: `Deadman P0 Mobile UI States`
- subtitle: `要是我来 / 390x844 primary`
- note: `Figma = visual contract; code = runtime truth`
- state flow:

```text
catalog -> idle -> notice -> bubble -> thinking -> result/error -> dismissed
```

### 01 Catalog

Layout:

- full phone viewport, dark warm background;
- top title: `要是我来`;
- section label: `短剧高光`;
- one drama card for `荒年全村啃树皮，我有系统满仓肉`;
- thumbnail area can use the tomato companion contact sheet;
- title: `第 12 集 · 兔子肉要不要下锅`;
- metadata: `5 个已发布介入点`;
- primary button: `进入`.

Acceptance:

- `进入` touch target is at least 44px;
- card does not look like an admin list;
- first screen already feels like a vertical drama product.

### 02 Player Idle

Layout:

- 9:16 vertical video fills the phone;
- topbar left label: `要是我来`;
- title: `荒年全村啃树皮，我有系统满仓肉`;
- right pill: `Branch 3`;
- hook label: `高光钩子`;
- hook text: `四蛋抓到兔子，兔子肉今晚要不要真的下锅？`;
- companion half-hidden at left edge, lower-middle;
- bottom player controls: progress bar, highlight dots, play button, timestamp.

Acceptance:

- companion is visible but low-interference;
- subtitle/video center remains dominant;
- controls remain reachable.

### 03 Notice Exclaim

Same as idle, but companion state is `notice_exclaim`.

Behavior note:

- use `!` for high-emotion trigger;
- `notice_question` exists, but v0.1 does not need a separate full frame unless
  spacing differs.

Acceptance:

- notice marker does not cover hook, subtitles, or bottom controls;
- companion still reads as a watching friend, not an ad pop-up.

### 04 Runout Invite

This is a motion keyframe, not a stable screen.

Show:

- companion running/sliding out from left;
- robe trailing;
- video still visible behind;
- no bubble yet or only a faint pending anchor.

Motion annotation:

```text
notice tap: direct bubble open; runout art remains an unused optional asset
```

### 05 Bubble Choice

Layout:

- companion stands small at the left side;
- bubble opens from companion toward center/right, but stays compact;
- bubble left edge starts around `126-150px` depending viewport;
- bubble bottom sits above player controls;
- single companion line, marker pill plus sentence: `四蛋这一下太戳了。肉能救急，但孩子不能又被晾在一边。`;
- close action: `继续看`;
- strip 1: `先让四蛋吃第一口，别让孩子白懂事`;
- strip 2: `肉可以救急，来路先别当众说破`;
- strip 3: `这功劳算四蛋的，别又被大人吞掉`;
- custom input placeholder: `不爽就回一句，搭子接着`;
- submit affordance: compact `送` button attached to the input.

Acceptance:

- bubble reads as companion speech, not modal admin UI;
- bubble must not read like a branch-choice questionnaire;
- all buttons are at least 44px high;
- content can scroll internally if needed;
- close/continue is always reachable.

### 06 Custom Input

Same bubble with textarea filled:

```text
先把兔肉切碎熬进粥里，让四蛋先吃第一口，但别让外人知道肉从哪来。
```

Design note:

- include a keyboard-safe annotation, not necessarily the full keyboard;
- submit button must stay reachable when keyboard appears.

### 07 Thinking

State:

- companion state `thinking`;
- submit disabled;
- submit label: `搭子判断中`;
- optional microcopy: `搭子判断中`.

Acceptance:

- user understands work is happening;
- no double-submit path;
- no fake verdict yet.

### 08 Result

Result surface principle:

```text
one natural companion response + at most one contextual micro-cue
```

Recommended content:

```text
这手稳，先让四蛋吃第一口，情绪就不会炸到全家身上。
```

Micro-cue:

```text
兔肉能救急，但暴露来源会把后面风险提前引爆。
```

Continue button:

```text
继续看
```

Optional aggregate hint if space allows:

```text
更多人选了 A：先稳住孩子，再处理全家分配。
```

Do not expose score axes, raw source paths, producer debug fields, long canon
explanation, or `不改写主线 / 不影响剧情 / 原剧情还能继续` style disclaimers.

### 09 Structured Error

Error copy:

```text
这次我卡住了，刚才那手先收一下。可以重试，或者继续看。
```

Actions:

- primary: `重试`;
- secondary: `继续看`.

Acceptance:

- does not pretend judgment succeeded;
- does not blame the user;
- still lets user return to video.

### 10 Dismissed

Show:

- companion returning to half-hidden idle;
- bubble gone;
- player controls visible;
- video remains primary.

Motion annotation:

```text
dismissed: 260ms, then idle
```

## 3. Component Sheet

Frame name:

```text
11 Components + Tokens
```

Components:

- `Phone Shell`
- `Video Scrim`
- `Topbar`
- `Hook Block`
- `Companion Safe Area`
- `Bubble`
- `Option Button`
- `Custom Textarea`
- `Submit Button`
- `Continue Button`
- `Result Micro Cue`
- `Error Actions`
- `Timeline Marker`

Color tokens from current implementation:

```text
ink/dark-video       #0F0B0A
page/deep-warm       #1B1210
surface/bubble       #FFF6E8
surface/option       #FFFAF2
text/on-dark         #FFF7EE
text/bubble          #2B1812
accent/tomato        #FF6B35
accent/warm          #FFB25D
accent/leaf          #2F6C4F
danger/result        #BD3C20
line/warm            rgba(255,226,192,0.28)
shadow/bubble        0 18 48 rgba(12,7,5,0.32)
```

Typography:

```text
Font family: Noto Serif SC / Source Han Serif SC
Topbar title: 16px, line-height 1.28
Hook label: 12px
Hook text: 15px, line-height 1.35
Bubble hook: 15-16px, line-height 1.35
Option text: 14-15px, line-height 1.36
Body/result: 14px, line-height 1.55
Small note: 12px, line-height 1.42
```

Radius:

```text
Bubble: 8px
Option button: 8px
Small pill: 8px or 999px for circular marker
Phone shell desktop preview: 32px
```

Spacing:

```text
Outer phone padding: 16px
Bubble padding: 10px
Internal bubble gap: 8-10px
Option gap: 7px
Bottom controls gap: 8px
Minimum touch target: 44px
```

## 4. Validation Frames

Create lightweight derived checks, not full duplicate designs:

```text
12 Check 393x852
13 Check 430x932
```

For each, duplicate only:

- `05 Bubble Choice`;
- `08 Result`;
- `09 Structured Error`.

Check:

- no clipped controls;
- no text overflow in option buttons;
- close/continue reachable;
- textarea and submit reachable under keyboard-safe assumption;
- companion does not cover critical video/control area;
- larger screen does not make bubble look sparse or disconnected.

## 5. Figma Generation Prompt

Paste this into Figma AI / Figma Slides if direct MCP generation is unavailable:

```text
Create an editable Figma review board titled "Deadman P0 Mobile UI States v0.1".
The product is a mobile-first short-drama interaction layer named "要是我来".
Primary design frame is 390x844. Validation frames are 393x852 and 430x932.

Build a UI contract board, not a marketing presentation. Use a warm dark
short-drama video background, tomato red and leaf green accents, cream speech
bubbles, and compact mobile UI. The tone is a sharp watching friend, not a
chatbot or SaaS dashboard.

Create complete 390x844 frames for:
00 Contract, 01 Catalog, 02 Player Idle, 03 Notice Exclaim, 04 Runout Invite,
05 Bubble Choice, 06 Custom Input, 07 Thinking, 08 Result, 09 Structured Error,
10 Dismissed, 11 Components + Tokens.

Create lightweight validation frames for 393x852 and 430x932 using Bubble
Choice, Result, and Structured Error only.

Important copy:
Product label: 要是我来
Drama title: 荒年全村啃树皮，我有系统满仓肉
Hook: 四蛋抓到兔子那一眼，懂事得让人难受。
Companion line: 四蛋这一下太戳了。肉能救急，但孩子不能又被晾在一边。
Options:
1 先让四蛋吃第一口，别让孩子白懂事
2 肉可以救急，来路先别当众说破
3 这功劳算四蛋的，别又被大人吞掉
Input placeholder: 不爽就回一句，搭子接着
Submit: 送
Thinking submit: 判
Continue: 继续看
Result line: 这手稳。先让四蛋被看见，孩子那股委屈就不至于炸到全家身上。
Micro-cue: 有52%其他观众也这么想。
Error: 这次我卡住了，刚才那手先收一下。可以重试，或者继续看。
Error actions: 重试 / 继续看

Do not include score axes, raw source paths, producer debug fields, dashboard
tables, or disclaimers like 不改写主线 / 不影响剧情 / 原剧情还能继续.

Use these colors:
#0F0B0A dark video, #1B1210 page, #FFF6E8 bubble, #FFFAF2 option,
#FFF7EE text on dark, #2B1812 bubble text, #FF6B35 tomato accent,
#FFB25D warm accent, #2F6C4F leaf green, #BD3C20 result/danger.

Minimum touch target is 44px. Bubble radius is 8px. The companion should be
represented as a tomato-hood robe girl asset placeholder at the left edge:
half-hidden in idle/notice, standing beside the bubble in bubble/result/error.
```

## 6. Return-To-Code Notes

When reading the finished Figma board back into code, map frames to:

```text
frontend/src/App.tsx
frontend/src/player/Branch3PlayerDemo.tsx
frontend/src/player/Branch3PlayerDemo.css
frontend/src/companion/TomatoCompanion.tsx
frontend/src/companion/TomatoCompanion.css
frontend/src/companion/tomatoCompanionMachine.ts
```

Do not change runtime semantics from Figma alone. If a Figma edit implies a
different event or state transition, update the PRD/runtime contract first.
