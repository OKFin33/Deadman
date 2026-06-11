# Deadman · 看剧搭子

A short-drama watching **companion**. While you watch, the moment a scene makes
you want to say something, the companion catches that beat: one friend-style
opener, three "things I want to say", and a reply that catches your feeling back.

```text
我想说一句。
```

The viewer is not choosing a story branch — they are saying the line the scene
made them want to say. **No typing required, and it never interrupts playback.**

## 一键启动 / Quick start

**Requirements:** Python 3 and Node.js (npm). The demo runs at
`http://127.0.0.1:7861`.

**Easiest:** double-click `start.command` (macOS), or run `bash start.command`.
It installs deps, builds the frontend, starts the Local Server, and opens Stage.

Or run the three commands yourself:

```bash
python3 -m pip install -r requirements.txt
( cd frontend && npm install && npm run build )
python3 -m uvicorn server:app --host 127.0.0.1 --port 7861
```

**Keys & 模型（可自选）:** the **Stage 观众端 demo needs none** — preset echoes are baked
into the reviewed packs. For **live Studio authoring** (custom echo / ASR upload),
copy `.env.example → .env` and fill the three providers — **每一类都可换 key / 换模型**：

| 用途 | 变量 | 自选模型 |
|---|---|---|
| 创作 + 语义选窗 (author) | `ARK_API_KEY` / `ARK_ENDPOINT_ID` / `ARK_BASE_URL` | `ARK_ENDPOINT_ID` 指向任意 Ark/Doubao endpoint |
| ASR 语音转写 | `DOUBAO_SPEECH_API_KEY` / `DOUBAO_SPEECH_UID` | 火山/豆包语音 |
| 味觉评审 (judge) | Bailian `bl` CLI + `BAILIAN_JUDGE_MODEL` | `qwen-flash`(快) / `qwen-turbo` / `qwen3.6-plus`(更稳) |

```bash
cp .env.example .env   # 填三类 provider 的 key/模型
```

> ⚠ **创作模型 (author) 与评审模型 (judge) 建议用【不同】模型** —— 跨模型评审才可信；让一个模型
> 评它自己写的稿会自我偏袒 (self-grading)，判别力归零。这也是本项目「Ark 创作 + Qwen 评审」的设计。
> judge 想更快可设 `BAILIAN_JUDGE_MODEL=qwen-flash`（人审 gate 兜底最终判别力）。

**Media:** raw video is gitignored (公开仓库不含短剧素材)。两种方式拿到可播内容：

- **上传你自己的短剧（fresh clone 推荐）**：填好 `.env` 的三个 key → 打开制作端
  `http://127.0.0.1:7861/studio/` → 上传一段短剧片段 → 生产图（ASR → 语义选窗 →
  搭子创作 / 跨模型评审 → 人审闸门）把它产成一条可播的互动 pack → 回观众端 Stage 观看。
  这条 = 「填 key + 上传视频即可用」的标准路径。
- **或** 把素材放到 `tmp/视频素材/<剧名>/第N集.mp4`（runtime 通过每部剧的
  `media_local.v0.1.json` 把 `episode_id` 映射到该路径），或设 `DEADMAN_MEDIA_BASE_URL`
  指向外部媒体地址。

**Open:**

- 观众端 Stage  → `http://127.0.0.1:7861/Stage/`
- 制作端 Studio → `http://127.0.0.1:7861/studio/`

## Architecture

```text
agentic authoring backstage · deterministic frontstage · bounded runtime adaptation
```

- **Studio (backstage)** — agentic authoring (LangGraph + CAB) turns reviewed
  drama moments into audited companion-exchange packs.
- **Stage (frontstage)** — a light, deterministic mobile-first player renders the
  reviewed packs; runtime model use is bounded and only after the viewer opts in.

The primary runtime contract is `companion_exchange.reply_candidates`: a
friend-style lead, three reviewed reply candidates, and a selected echo.

## Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Mobile-first React/Vite player + tomato companion |
| `backend/` | FastAPI APIs, viewer runtime, judgment adapter, CAB client |
| `studio/` | Producer-side Studio prototype |
| `tools/` | Producer/authoring pipeline, validation, publication checks |
| `data/` | Reviewed drama packs, schemas, and the taste dataset |
| `assets/` | Static companion assets |
| `server.py` | Deployable FastAPI entrypoint |
| `ms_deploy.json` | Deployment env template (secrets omitted) |

## Run locally

Backend:

```bash
python3 -m pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 7861
```

Frontend:

```bash
cd frontend
npm install
VITE_DEADMAN_API_PROXY_TARGET=http://127.0.0.1:7861 npm run dev -- --host 127.0.0.1 --port 5175
```

Open `http://127.0.0.1:5175/?branch3_player=1`.

## Runtime modes

```bash
DEADMAN_JUDGMENT_ENGINE=cab_runtime         # formal judgment via sibling CABRuntime
DEADMAN_JUDGMENT_ENGINE=demo_deterministic  # tests / demo fallback only
```

Formal runtime failure fails closed with a structured error — it never silently
returns deterministic/template judgment as formal judgment.

## Media & secrets

Raw media (`*.mp4`), provider keys, `.env`, caches and build outputs are never
committed. Public deployment either configures an external media base URL
(`DEADMAN_MEDIA_BASE_URL`) or serves registered local media outside git.
**Provider credentials are environment variables only** (`ARK_API_KEY`, …).

## Checks

```bash
python3 -m unittest discover -s backend/tests
python3 tools/ars/deadman_validate_producer_bridge.py --drama-dir data/dramas/huangnian
python3 tools/check_publication_safety.py
cd frontend && npm test && npm run build
```
