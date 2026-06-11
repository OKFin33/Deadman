# 看剧搭子 · Deadman

> 短剧即时互动陪看 · 两端一桥 —— 把观众情绪高点的「我想说一句」接住，**不用打字、不打断观看**。

看短剧时，某个镜头让你突然想说点什么——搭子就在那一刻接住这口气：一句朋友式的开场、三句「我想说的话」、再用一句回声接住你的感受。

```text
我想说一句。
```

观众**不是在选剧情分支**，而是说出此刻这场戏让自己想说的那句话。三句候选都不够时，可以主动输入自己的话，搭子在**当前场景边界内**接一句——不开放闲聊、不剧透、不改写后续剧情。

**链接**：录屏 [【待填公开视频链接】] · 技术文档 [【待填飞书链接】] · 在线演示（本地 Local Server）观众端 `http://127.0.0.1:7861/Stage/` · 制作端 `http://127.0.0.1:7861/studio/`

---

## 亮点 / 创新

**前台轻确定性 · 后台 agentic 生产图 · 人审是图里的真实 gate · 跨模型味觉评审收敛对味。**
把模型生成的不确定性全部拦在制作侧：后台 **Studio** 用 LangGraph 把「上传 → ASR → 语义选窗 → 分层上下文 → 搭子创作（author）→ 跨模型味觉评审（judge）→ 定向修订 → 人审 gate → 发布」串成一条可恢复的生产图；人审不是页面上的假步骤，而是图里的 interrupt/resume 节点——**只有过审的 pack 才会 promote 到 Stage**。前台 **Stage** 保持轻、稳、确定：观看过程默认只消费已审核 pack，不在播放时实时生成剧情内容。

---

## 快速开始 / Quick start

**前置**：Python 3 与 Node.js（含 npm）。服务跑在 `http://127.0.0.1:7861`。

**最简单**：双击 `start.command`（macOS），或运行 `bash start.command`。它会装依赖、构建前端、启动 Local Server，并自动打开观众端 Stage。

或自己跑这三条命令：

```bash
python3 -m pip install -r requirements.txt
( cd frontend && npm install && npm run build )
python3 -m uvicorn server:app --host 127.0.0.1 --port 7861
```

启动后打开：

- 观众端 **Stage** → `http://127.0.0.1:7861/Stage/`
- 制作端 **Studio** → `http://127.0.0.1:7861/studio/`
- 健康检查 → `http://127.0.0.1:7861/api/deadman/health`

> **开发模式（可选）**：前端 Vite 热更新可单独跑 `cd frontend && VITE_DEADMAN_API_PROXY_TARGET=http://127.0.0.1:7861 npm run dev`。日常演示与评审请走上面构建好的 `/Stage/`，无需此步。

---

## 模型与 key

观众端的**默认互动**——开场 + 三句「我想说」+ 回声——来自已审核 pack，**开箱即用、播放时不调模型**。两处会**实时调模型、需要 provider 凭据**：观众端的**自定义输入**（观众说出自己的话 → 搭子在当前场景边界内接一句，这是观众体验的**一等能力**，不是附属）和**制作端 Studio 实时创作**。`cp .env.example .env` 后填三类——**已给预设，开箱即用，也可替换**：

| 用途 | 预设模型 |
|---|---|
| 创作 + 语义选窗 (author) | Ark · Doubao-Seed-2.0-lite |
| ASR 语音转写 (speech) | 火山 / 豆包语音 |
| 味觉评审 (judge) | Qwen via Bailian `bl`（默认 `qwen-flash`） |

```bash
cp .env.example .env   # 填三类 provider 的 key（自定义输入 / Studio 创作需要）
```

> 创作 (author) 与评审 (judge) 建议用**不同**模型——跨模型评审才可信，同模型自评会自我偏袒；最终判别力由**人审 gate** 兜底。

---

## 媒体 · 上传你自己的短剧

原始视频不进公开仓库（`*.mp4` 等 gitignored）。两种方式拿到可播内容：

- **上传你自己的短剧（fresh clone 推荐）**：填好 `.env` → 打开制作端 `http://127.0.0.1:7861/studio/` → 上传一段短剧片段 → 生产图（ASR → 语义选窗 → 搭子创作 / 跨模型评审 → 人审 gate）把它产成一条可播的互动 pack → 回观众端 Stage 观看。这条 = 「填 key + 上传视频即可用」的标准路径。
- **或** 把素材放到本机本地路径（每部剧的 gitignored sidecar `media_local.v0.1.json` 把 `episode_id` 映射到该路径），或设 `DEADMAN_MEDIA_BASE_URL` 指向外部媒体地址。

> 诚实边界：当前主路径是高光点即时表达；自定义输入是**有界 runtime echo**（仅在用户主动输入后触发、只围绕当前场景接话），不声称剧情分支、无限聊天或画面级高光检测。ASR 凭据缺失时落入内置样片转写，窗口提议失败时落入确定性启发式兜底。搭子文案不保证每句都精准贴脸——保留人审 gate 与味觉 loop 作为质量收敛机制。

---

## 架构 / Architecture

```text
agentic authoring backstage · deterministic frontstage · bounded runtime adaptation
```

- **Studio（后台）** —— agentic 创作（LangGraph + CAB）把已审核的剧情瞬间产成审计过的 companion-exchange pack。
- **Stage（前台）** —— 轻量、确定性的移动端播放器渲染已审核 pack；runtime 模型使用是**有界的**，且仅在观众主动 opt-in 后才发生。
- **桥**：制作端产出版本化 `CompanionExchangePack`，观众端只消费该契约，两端不强耦合。

主 runtime 契约是 `companion_exchange.reply_candidates`：一句朋友式 lead、三个已审核的 reply candidate、和一个 selected echo。

---

## 目录 / Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | 移动端 React/Vite 观众端 Stage + 番茄搭子 + Studio 控制台 |
| `backend/` | FastAPI API、viewer runtime、judgment adapter、pack store |
| `studio/` | 制作端 Studio（legacy 静态控制台，`/studio-legacy`） |
| `tools/ars/` | 生产图、ASR/ingest、taste overlay、promote、校验脚本 |
| `data/dramas/` | 可公开的 runtime pack、manifest、context、moments、media registry |
| `assets/` | 番茄搭子状态素材、短剧封面 |
| `server.py` | Local Server 入口，统一服务前端页面与后端 API |
| `ms_deploy.json` | 部署环境模板（密钥不写入仓库） |

## 测试 / Checks

```bash
python3 -m unittest discover -s backend/tests
cd frontend && npm test && npm run build
cd ..
python3 tools/check_publication_safety.py
```

> 发布安全：密钥仅在 `.env`，不进入代码、文档、截图或 `ms_deploy.json`；本地视频路径移入 gitignored sidecar；提交前用 safety script 扫描。Provider 凭据**只通过环境变量**读取。
