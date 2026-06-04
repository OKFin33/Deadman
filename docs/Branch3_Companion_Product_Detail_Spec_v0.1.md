# 要是我来 · 搭子陪伴 产品细节方案 v0.1

> Branch: OSeria Branch 3 / Deadman / 要是我来  
> Date: 2026-06-03  
> Status: 落地实现规格（PRD 下游，不替代 PRD）  
> Upstream: `Branch3_要是我来_PRD_v0.3.md` §3 / §7 / §0 (v0.3.1 framing fix)  
> Upstream: `Resident_Companion_Runtime_Tech_Plan_v0.1.md` §1 First-Principles UX  
> Upstream-inputs: `external_review_v0.3_pivoted_lens.md` (5 个 gap) + 字段消费分层结论  
> Scope: 用户侧 player + companion + 后端 friend_voice，**不含** Studio / 多剧扩展 / 图像生成 / 持久化账户

---

## 0. 关系图

```
PRD v0.3 (What/Why)               ← 框架，已稳定
  └─ §3 first-principles
  └─ §7 UX requirements
  └─ §0 v0.3.1 framing fix
       │
       ▼
Resident_Companion_Runtime §1 (UX 原则)
       │
       ▼
本文件 v0.1 (How，落地规格)        ← 当前文档
  ├─ §2 总领翻译
  ├─ §3 入口分层（吐槽 vs if 线）
  ├─ §4-§7 搭子主动性 / 路过 / 再吐 / 还记得
  ├─ §8 结果回弹文案规范
  ├─ §9 字段消费分层表
  ├─ §10 catalog 软化
  ├─ §11 边界（不做清单）
  └─ §12 P0 / P0.5 / P1 范围
       │
       ▼
P0_Mobile_UX_Acceptance_Checklist v0.1 (验收)
```

PRD 不动正文，§18 加一条 link 指向本文件即可。

---

## 1. 当前发现的 5 个真问题（对照 v0.3 评测 + 字段分层）

| Gap | 性质 | 修在哪 |
|---|---|---|
| 搭子是 reactive 不是 alive | `companion.utterance` 字段后端在 `player_tick` 不填 | 后端 friend_voice |
| 路过通道缺失 | 用户不互动时搭子死等 | 前端 state machine |
| 再吐一句无入口 | 结果面板只有"继续看 / 分享" | 前端 ResultPanel |
| 吐槽 vs if 线没分层 | marker 命中默认弹完整选项面板 | 前端 + moment schema |
| LEAD_BANK 文案偏剧情研究员 | friend_voice 模板池太"分析" | 后端 friend_voice 文案池 |

这五项是本规格的主要工作内容。

---

## 2. 总领翻译：三句锚定 / 三个用户姿态

PRD §3 + §7.2 总领翻译成本规格遵循的三句话：

> 搭子始终在看剧旁边。  
> 用户偶尔想说一句时，搭子接得住、回得轻。  
> 想深入聊一聊 if 线时，路径在但不强求。

**对应三个用户姿态**（任何时刻用户都在其中一种）：

| 姿态 | 频次预期 | 用户动作 | 搭子动作 |
|---|---|---|---|
| **路过** | 最高频 | 不点任何东西 | 搭子偶尔自言一句 / notice 自动收手 |
| **吐槽** | 中频 | 1-tap 选一个轻反应 | 搭子轻回响（"啊就是" / "我懂" / "心疼"）|
| **if 线讨论** | 低频 | 展开完整面板、3 选项或自由输入 | 搭子认真接一句（仍单行，但语义更具体）|

**核心设计原则**：默认通往"吐槽"姿态，"if 线讨论"是用户主动展开的二级路径，"路过"是隐含的兜底。

---

## 3. 入口分层（吐槽 vs if 线）

### 3.1 当前状态

marker 命中后路径：
```
notice ! → tap companion → 弹出完整面板（hook + 3 选项 + 自由输入）
```
**问题**：所有交互冲动都走同一个面板，门槛高。

### 3.2 新设计

```
marker 命中 → companion notice (! / ?)
         │
         ├─ 5 秒无动作 → 路过姿态（§5）
         │
         └─ tap companion → 弹出【吐槽气泡】
                            ├─ 三个 1-tap 反应 + "我懂"
                            ├─ "展开 if 线..." 入口
                            └─ 自动收回（点击外部 / 3 秒不动）
                                       │
                                       └─ 点【展开】→ 弹出现有完整面板（hook + 3 选项 + 自由输入）
```

### 3.3 吐槽气泡规格

**视觉**：在搭子头顶或旁边浮起的轻量小气泡，**不全屏遮挡视频**。

**内容**：
- 3 个 1-tap 反应按钮（按 marker 类型不同），文案在 §3.4
- 1 个"展开 if 线..."文字链
- 不包含 hook 句、不包含自由输入

**交互**：
- 点反应按钮 → 立即触发结果回弹（§8），不阻塞视频
- 点"展开 if 线..." → 转入现有面板（hook + 3 选项 + 自由输入）
- 点气泡外 / 3 秒未点 → 气泡收回，搭子回 idle

### 3.4 1-tap 反应按钮文案库

按 marker 类型分：

| Marker 类型 | 三个反应 |
|---|---|
| `!` 火气点（emotion） | 🔥 就是啊 / 💔 心疼 / 😅 离谱 |
| `?` 憋住点（temptation） | 🤔 我也想 / 😬 别试 / 👀 看看再说 |

按 `action_type`（resource / humiliation / system_rule / evidence 等）可以做更精细的文案，**但 P0 先用 marker 二分**。

每个反应按钮点击后：
- 前端立即显示"懂你❤"小气泡 + 0.5 秒高亮
- 异步 POST 到 runtime/session/event（event_type=`user_action`, action.source="tap_reaction", action.text=反应文本）
- 后端 friend_voice 走精简路径生成短回响（≤ 20 字）
- 前端展示短回响 1.5 秒后自动消失 → 回 idle

### 3.5 后端 schema 扩展

`UserAction` 加一个 source：
```python
source: Literal["preset", "custom", "tap_reaction"]
```

friend_voice 加一个分支：对 `tap_reaction` 走"轻回响"模板池（不调用 LEAD_BANK，直接选 ≤ 20 字的搭子 echo）。

---

## 4. 搭子主动性升级（utterance 注入）

### 4.1 当前状态

- 前端：`runtimeResponse.companion.utterance` 已经接了（`Branch3PlayerDemo.tsx` line 1094）
- 后端：只在 `companion_tap` event 时填 hook；在 `player_tick` 总是空字符串
- 结果：搭子永远不会主动开口

### 4.2 新设计

后端在 `player_tick` event 时**有条件**填 utterance：

**触发条件**（满足其一）：
- 视频经过某个 `companion_utterance_anchor`（在 Moment Pack 里新增字段，标注时间戳 + 候选 utterance 池）
- session 累计观看 X 秒未发生 marker（避免长时间冷场）
- 用户刚完成一次互动后 30-60 秒（保持陪伴感连续）

**频次预算**：
- 每集每用户 ≤ 5 次 utterance（防过度打扰）
- 两次 utterance 间隔 ≥ 30 秒
- 不与 marker 通知重叠（如果即将命中 marker，跳过 utterance）

**utterance 内容池示例**（按场景分）：
- 角色情绪触发："这眼神看着难受" / "她不容易"
- 资源稀缺触发："这家一年没吃过肉啊"
- 关系紧张触发："这桌上没一个人说话"
- 节奏停顿触发："等下，这一段我想多看一会"

**utterance 不是 hook，不引发 marker 也不开互动面板**。它只是搭子的"自言自语"。

### 4.3 前端渲染

- utterance 气泡：搭子头顶飘起，2-3 秒淡出
- 不阻塞视频
- 不可点击响应（只是陪伴）
- 如果用户在 utterance 显示期间点搭子，按当前姿态处理（idle → 不响应或弹路过 hint）

### 4.4 后端实现

friend_voice 加 `compose_utterance(session, drama, moment_context, recent_history)` 方法：
- 优先从 Moment Pack 里查 `companion_utterance_anchor`
- 否则用通用兜底池（按 drama_id 提供）
- 自然语言不超过 18 字

---

## 5. 路过姿态

### 5.1 当前状态

`notice_question` / `notice_exclaim` 状态进入后，**只有用户 tap 才会换状态**。一直不点就一直举着。

### 5.2 新设计

`notice_question` / `notice_exclaim` 状态加超时转移：

```
notice_exclaim/notice_question
   ├─ tap → stand_bubble（现有路径）
   └─ 5-8 秒无动作 → notice_runout
                       └─ 自动飘一句 → idle
```

`notice_runout` 是新增中间状态：
- 视觉：搭子从"举手"姿势放下，旁边飘一句话 "算了，下次再有"（或类似）
- 持续 2 秒后自动转 idle
- 不影响 interaction_window（window 内重新触发 marker 仍会重新走 notice）

### 5.3 状态机 patch

`tomatoCompanionMachine.ts` 加：

```typescript
| { type: "NOTICE_TIMEOUT" }
| { type: "RUNOUT_COMPLETE" }
```

```typescript
case "NOTICE_TIMEOUT":
  if (state === "notice_question" || state === "notice_exclaim") {
    return "notice_runout";  // 新状态
  }
  return state;

case "RUNOUT_COMPLETE":
  return state === "notice_runout" ? "idle" : state;
```

新状态对应新 webp asset `notice_runout.webp`（或复用 `runout.webp` 但内含放手姿态）。

### 5.4 文案池（搭子放手时飘的话）

随机 / 按 stance 选：
- "算了，下次再有"
- "看你没接，那我先收一下"
- "你专心看"
- "（搭子收回了举着的手）"

---

## 6. "再吐一句"入口

### 6.1 当前状态

结果面板（ResultPanel）只有"继续看 / 分享"两个按钮。一次互动结束就关闭。

### 6.2 新设计

结果面板加第三个动作"还想说"，放在"继续看"和"分享"之间或下方：

```
[ 继续看 ▷ ]   [ 还想说 ]   [ 分享 ]
```

点"还想说"：
- 不关闭面板
- 视图切换到自由输入态（同"我有不同想法"展开后样子）
- 用户输入 → 提交 → 第二次 verdict → 第二次结果回弹
- 可重复（无次数限制，但每次都重新走 verdict）

### 6.3 后端不需要改

`POST /runtime/session/event` 已支持多次 `user_action`，每次都会走 judgment + friend_voice。**这是纯前端 ResultPanel 改造**。

### 6.4 第二次起的结果回弹文案要小心

第二次开始，friend_voice 的 `_compose_lead` 会因为 `previous_summary` 非空而加 "接着你上一手看" 前缀（line 109-111）。**这正好用作"再吐"的衔接感**。前端不用做事，自动有了。

---

## 7. "搭子还记得"（last_choice_summary 前端消费）

### 7.1 当前状态

后端 `session_memory.last_choice_summary` 已填充（如 "你上一手是想猛推一把，但搭子把尺度收住了"）。前端类型已声明但 **不读取这个字段**。

### 7.2 新设计

前端在以下时机消费 `last_choice_summary`：

**时机 A：同集 marker 再次命中时**
- 在 notice 状态进入时，如果 `last_choice_summary` 非空，搭子顶起一行小气泡："上次你说……"
- 持续 2 秒后自动消失，不影响 notice 行为

**时机 B：同剧切回时（用户切到其他集再切回）**
- 切回检测：通过 viewer_session_id + drama_id，session 中存在 last_choice_summary
- 搭子开口："上次你说……" 一句话 utterance（走 §4 的 utterance 通道）

**时机 C：跨 session 不做**（P0 不做持久化，session 关掉就丢，这是 PRD §10 明确的）

### 7.3 文案口吻

不是"已记录"或"上次操作"，而是**朋友式的"我还记得"**：
- "上次你说想护住孩子那一下"（朋友式）
- 不要："您上次的判定是 [stance=support]"（评委式）

后端 friend_voice 的 `_summary_for_next_moment` 已经走朋友式（line 127-131），文案 OK。前端直接用即可。

### 7.4 不暴露的部分

- `session_memory.safe_to_reference` 字段：governance，不暴露给 UI，用作后端 sanitize 时的 reference flag。如果是 false，前端不应该展示"上次你说"。
  - 前端逻辑：`if (session_memory.safe_to_reference && session_memory.last_choice_summary) { 显示 }`

---

## 8. 结果回弹文案规范（重点）

### 8.1 问题

现在 `_LEAD_BANK`（`friend_voice.py` line 157+）的模板偏"剧情研究员"：

> "这顿饭先别只看肉，{action}是在给家里立个能服众的分法。"  
> "这种羞辱不能干看着，{action}先把底线摆出来。"  
> "面板能救命，但得先知道它怎么收尾，{action}方向是对的。"

读起来像剧评人在分析。新总领下应该是"看剧时旁边朋友说一句"。

### 8.2 文案改写原则

| 原模板特征 | 新模板特征 |
|---|---|
| 解释性长句 | 短句、可省略主语 |
| "这种 / 这一步 / 这里" 等抽象指示 | 具体细节（"那个眼神 / 那一口" 等）|
| 完整剧情分析逻辑 | 朋友脱口而出的反应 |
| 评价用语（"得 / 应该 / 不能"）| 共情用语（"懂 / 太对了 / 心疼"）|

### 8.3 新文案样本（覆盖 9 类 = 3 action_type × 3 stance）

#### resource × support
```
这一下我也想这么干。
就是该让娃看见自己被放在心上。
这肉分对了，比怎么做都重要。
```

#### resource × caution
```
对是对，但这家底太薄。
分肉是稳的，就是别太张扬。
这步没错，留点话别说满。
```

#### resource × reject_softly
```
太满了，这家撑不住这么大动静。
心是好的，但这家底亮不得。
等等，先想想后面这顿怎么收。
```

#### humiliation × support
```
就是该有人这么说一句。
这桌上确实需要有人开口。
看到那个眼神我也忍不了。
```

#### humiliation × caution
```
该护，但这桌上的人都在看。
是该出口气，就别把火一下烧太满。
护得对，留个台阶。
```

#### humiliation × reject_softly
```
心疼，但这样掀桌她反而更难站。
冲动是真冲动，就是怕反伤了她。
缓一缓，这不是不能怼。
```

#### system_rule × support
```
对，先看清这东西怎么用。
这种事不能急着大手大脚。
节奏稳，比一次性梭哈强。
```

#### system_rule × caution
```
能试，就别在那么多眼睛底下试。
这东西扎眼，分寸自己拿。
看准时机再动。
```

#### system_rule × reject_softly
```
太招摇，留着等关键时候。
忍住，这种牌不能开局就打。
等等，这场合不对。
```

### 8.4 自由输入回响文案池

`{action}` 会被替换成用户输入。建议保留 friend_voice 现有逻辑，但**对自由输入文案换一组模板**：

```python
# 自由输入额外模板（line 109 后增加分支）
if action.source == "custom":
    if stance == "support":
        return f"懂，{action_text} 我也是这个想法。"
    if stance == "caution":
        return f"思路对，{action_text}——就是别一次给满。"
    if stance == "reject_softly":
        return f"听到你的意思了，{action_text}——但这家底撑不住这步。"
```

### 8.5 micro_cue 文案保留

`_select_micro_cue` 现有的两条：
- "这手爽是爽，搭子建议收一点"（watch_flow_fit=low）
- "有 X% 其他观众也这么想"（aggregate_stats）

**保留不动**——已经是朋友式语气。

---

## 9. 字段消费分层表（44 字段最终归属）

按"实际消费路径"分 7 层。后端工程师以此为准。

### Tier A：UI 直接显示（6 字段）

| 字段 | UI 位置 |
|---|---|
| `moment.hook` | "火气点 · 你是不是也想说" 下方 |
| `moment.default_options` | 3 个选项按钮 |
| `result_surface.text` | 结果面板正文（≤ 58 字） |
| `result_surface.micro_cue.text` | 结果面板下方小行（≤ 28 字） |
| `result_surface.continue_label` | "继续看" 按钮文字 |
| `result_surface.stamp` | 搭子举牌文字 |

### Tier B：前端逻辑消费（5 字段）

| 字段 | 用途 |
|---|---|
| `companion.next_state` | 驱动 state machine |
| `companion.marker` (`!` / `?`) | notice 子状态变体 |
| `companion.utterance` | §4 utterance 气泡 / 错误兜底文本 |
| `companion.should_interrupt` | 是否暂停视频 |
| `moment.interaction_window_active` | 决定 tap 是开 bubble 还是 idle |

### Tier C：后端 friend_voice 内部消费（10+ 字段）

这些**不暴露给 UI**，但 friend_voice 用它们生成 Tier A 的 6 字段内容：

- `verdict.label` / `verdict.stance` / `verdict.summary`
- `consequence.text` / `consequence.time_horizon` / `consequence.watch_flow_fit`
- `canon_anchor.original_plot_note` / `canon_anchor.safe_to_continue`
- `engine.mode` / `engine.schema_version`
- `aggregate_stats`（驱动 micro_cue）
- `action.source` / `action.text` / `action.option_index`

### Tier D：治理 / 防漂移（4 字段，绝不暴露）

- `judgment_basis.evidence_refs`
- `judgment_basis.applied_constraints`
- `judgment_basis.inference_notes`
- `judgment_basis.warnings`

这些是 AI 不说错话的证据链，由 sanitize 和合规层使用。

### Tier E：Axis 明文不暴露（1 字段）

- `judgment.scores`（6 维评分）

`Axis_For_Main_Agent.md`：`do not expose score_axes as viewer-facing evidence`。

### Tier F：Schema 预留 / 占位（3 字段）

- `result_card.mode` / `title` / `prompt`（fallback_card schema，未来扩展槽位）
- `judgment.media.*`（图像生成接入后用）

### Tier G：内部 metadata（5 字段）

- `viewer_session_id` / `event_id` / `cab_session_id` / `moment_id` / `drama_id`

### 真 Gap 字段（2 个）

- `companion.utterance`：前端已接，后端在 `player_tick` 不填 → §4 修
- `session_memory.last_choice_summary`：后端已填，前端不消费 → §7 修

**修完这 2 项，44 字段全部归位。**

---

## 10. Catalog 软化（v0.3 评测保留项）

### 10.1 文案

| 现状 | 改成 |
|---|---|
| 主标题 "要是我来" 无 tagline | 主标题下加："看剧也想说一句？搭子在听" |
| "Branch 3" 徽章 | 改成 "P0 体验" 或直接删除 |
| "5 个已发布介入点 · 当前高光 00:12" | "今天 5 个想吐的瞬间"（去 timing 误导）|
| "搭子已在场" 徽章 | 保留（这个对得上） |

### 10.2 Hero 占位

当前 hero 是手绘风半圆（兔子 + 锅）。换成：
- 一张高对比的"剧情触发瞬间"静帧（不是封面，是冲突一刻）
- 或加一句"灯光锁定 第 12 集"的副标题，让占位有戏剧感

### 10.3 不重写 catalog 数据结构

P0 不强求改成"集列表"。当前单卡形态 + 文案软化即可。**集列表是 P1 范围**（多剧多集时再做）。

---

## 11. 边界 / 不做清单

以下事项明文不做（与 PRD §5 / §7.4 / §11 一致）：

### 11.1 文案禁区（沿用 PRD §7.4）

viewer-facing 文案禁止出现：
- "原剧情还能继续"
- "不改写主线"
- "不影响剧情"
- "只改变眼前"
- "先别把这步当剧情结论"
- "未来分支"
- "后续主线"

`sanitize_viewer_copy`（`Branch3PlayerDemo.tsx` line 1178+）已经 enforce 这些，**不要在新文案中重新引入**。

### 11.2 UI 元素禁区

不做：
- consequence 长文展开按钮
- "原剧 vs 你" 对照视图
- verdict.label / stance 立场徽章
- 6 维评分可视化
- evidence_refs / applied_constraints / inference_notes / warnings 任何形式的展示
- 用户判定历史列表
- 跨集 / 跨剧的"我的"页面（P1）

### 11.3 搭子姿态禁区

搭子不可以：
- 主动质疑用户的选择（最多 caution / reject_softly 的轻劝）
- 输出超过 60 字的回复
- 引用具体集数 / 时间码 / 数据字段
- 解释自己"是 AI"或"我在分析"
- 让用户感觉被打分

---

## 12. P0 / P0.5 / P1 范围

### P0（8 天内，答辩前）

按边际效用排序，全部在新总领"放大陪伴温度"方向：

| # | 项 | 估时 | 章节 |
|---|---|---|---|
| 1 | utterance 注入（后端 friend_voice + Moment Pack 锚点）| 4-6h | §4 |
| 2 | 文案池重写（LEAD_BANK 9 类 + 自由输入 + 1-tap 反应）| 3-4h | §8 |
| 3 | 路过姿态（state machine + notice_runout asset）| 2-3h | §5 |
| 4 | 还想说入口（ResultPanel patch）| 1-2h | §6 |
| 5 | last_choice_summary 前端消费 | 2-3h | §7 |
| 6 | catalog 文案软化 | 1h | §10 |
| 7 | 分享按钮做"搭子聊了一句"卡片 | 3-4h | (v0.3 保留项) |
| 8 | 继续看自动恢复播放 / Branch 3 命名清理 | < 1h 合计 | (v0.3 保留项) |

**总计 16-24h**，8 天预算（按 6-8h/天）comfortable。

### P0.5（答辩后两周内，如果进入 demo 优化）

| # | 项 | 估时 |
|---|---|---|
| 9 | 吐槽气泡 / if 线分层入口（§3）| 6-10h |
| 10 | utterance 频次预算调优 + 跨集兜底池 | 4-6h |
| 11 | aggregate_stats demo_static → 半真实化（基于 sessionStore 累计）| 6-8h |

### P1（长期）

- 多剧扩展 + catalog 改集列表
- 持久化账户 / 跨 session 记忆
- image generation 接入
- voice layer
- producer Studio UI

P1 项目不在本规格范围。

---

## 13. 验收（补 P0_Mobile_UX_Acceptance v0.1）

在现有验收清单基础上，新增以下验收点：

### 13.1 搭子主动性（§4）
- [ ] 视频播放过程中，搭子至少出现 1 次主动 utterance
- [ ] utterance 不打断 marker 触发流程
- [ ] utterance 文案不超过 18 字
- [ ] 同集每用户 utterance 不超过 5 次

### 13.2 路过姿态（§5）
- [ ] marker 命中后 5-8 秒未交互，搭子自动收手
- [ ] 收手时显示"算了，下次再有"类话术
- [ ] 收手后 interaction_window 内重新触发 marker 仍能正常工作

### 13.3 再吐入口（§6）
- [ ] 结果面板有"还想说"按钮
- [ ] 点击后可进入自由输入态
- [ ] 第二次结果有"接着你上一手"前缀

### 13.4 搭子还记得（§7）
- [ ] 同集第二次 marker 命中时显示"上次你说……"
- [ ] safe_to_reference=false 时不显示
- [ ] 文案口吻是朋友式不是评委式

### 13.5 文案规范（§8）
- [ ] 所有结果回弹文案不超过 58 字
- [ ] 文案不包含 §11.1 禁词
- [ ] 文案符合"朋友式"而非"分析式"

### 13.6 字段消费（§9）
- [ ] Tier A 6 字段在 UI 可见
- [ ] Tier D + E + F 字段在 UI 完全不可见
- [ ] DevTools network 不暴露 producer-only debug 字段

---

## 14. 上下游文档关系

### 14.1 本规格依赖的上游

| 文档 | 引用章节 |
|---|---|
| `Branch3_要是我来_PRD_v0.3.md` | §3 (insight) / §7 (UX) / §0 (v0.3.1 fix) |
| `Resident_Companion_Runtime_Tech_Plan_v0.1.md` | §1 (UX 原则) |
| `external_review_v0.3_pivoted_lens.md` | 5 个 gap + 字段分层结论 |

### 14.2 本规格的下游产出物

| 产出 | 谁写 |
|---|---|
| 前端 PR：state machine 扩展 + ResultPanel patch + catalog 文案 | 前端工程 |
| 后端 PR：utterance 注入 + LEAD_BANK 重写 + tap_reaction 分支 | 后端工程 |
| Moment Pack 升级：`companion_utterance_anchor` 字段 | 数据 / producer |
| UI 验收：`P0_Mobile_UX_Acceptance_Checklist_v0.2`（追加 §13）| QA / 设计 |

### 14.3 PRD 触动

PRD v0.3 **正文不动**。仅在 §18 Key Source Documents 末尾追加：

```
- 产品细节方案: `docs/Branch3_Companion_Product_Detail_Spec_v0.1.md`
```

这一条由本规格作者在 commit 时一并加入。

---

## 15. 一句话总结

> 本规格把 PRD v0.3 §3 / §7 的"陪伴搭子 + 不吐不快承接 + 轻度 if 线讨论"总领翻译成 8 项可执行的产品细节工作（§4-§10），把 44 个 payload 字段归位到 7 层（§9），并明文 P0 / P0.5 / P1 范围（§12）。8 天内全部 P0 项目可完成。
