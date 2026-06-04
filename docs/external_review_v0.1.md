# Deadman 使用侧外部评测 v0.1

> 评测日期：2026-06-03  
> 评测视角：模拟评委 + 首用用户的外部视角，不读 backend 实现细节、不进 docs/ 内部 artifacts。  
> 评测口径：宣讲题目官方 rubric（40/30/20/10）为主轴，叠加"外部首用体验"作为质量观察项。不做与三个示例 Demo 的差异度对照。  
> 评测方式：Web dev server（Vite + 后端 uvicorn 7860 已起），mobile 视口 375×812 全程驱动。

---

## 0. TL;DR

| 维度 | 权重 | 得分 | 备注 |
|---|---|---|---|
| 整体功能完整性 | 40% | 28 / 40 | MVP 闭环（播放+互动+部署）打通；列表只有 1 部剧，用户互动维度未做 |
| 技术选型与实现 | 30% | 24 / 30 | 架构清晰、CABRuntime adapter 真实出 verdict；静态 fallback 与 API 不一致 |
| 创新与自由探索 | 20% | 13 / 20 | 搭子人格化 + 火气点命名 + 自由输入 = 真亮点；视觉/玩法层创新薄 |
| 文档与表达能力 | 10% |  8 / 10 | README/Axis 骨架好；缺面向评委的 1 页 narrative |
| **官方 rubric 总分** | 100% | **73 / 100** | |

**关键判断**：MVP 跑得通，差异化（搭子 + 自由输入 + canon-safe judgment）真实存在；但首用体验有一个**关键缺陷**——首次互动不会自动触发，新用户大概率第一次就错过。8 天内必须补这一项。

---

## 1. 评测路径

走过以下用户路径，全程在 mobile 视口（375×812）：

1. 冷启动 → catalog 单卡片 → 进入播放器
2. 播放 EP12 完整 1:06，期间观察首次互动是否触发
3. 倒回到 0:00，手动点时间轴 "!" 标记 → 点搭子 → 弹出选项 → 选 A → 看结果
4. 点 EP12 dropdown → 看到 5 个 episode 列表 → 切到 EP07
5. EP07 触发互动 → 选"我有不同想法" → 自由输入"要是我来，我会先扣下那碗脏饭..." → 看 AI verdict
6. 点"分享" → 观察是否有反馈
7. 切换 desktop 视口检查响应式
8. 检查 session 持久化（localStorage / sessionStorage）

---

## 2. 官方 Rubric 评分

### A1. 整体功能完整性 (40% → 28/40)

逐项对照宣讲的 MVP 闭环：

| 必选项 | 状态 | 证据 / 备注 |
|---|---|---|
| 短剧列表页 | ⚠️ 部分 | catalog 只有 1 部剧（荒年），后端 `/api/deadman/dramas` 返回数组但只 1 项；其他 9 部允许的剧（北派寻宝/天下第一纨绔/十八岁太奶奶等）都未实装；视觉上是单卡片而非"列表" |
| 播放 + 播控（暂停/播放/进度条） | ✅ 完整 | 自定义 vertical player，进度条、时间码、暂停/播放、episode 切换都到位；视频用 206 Partial Content 流式 |
| 互动能力（必选，二选一） | ✅ 完整 | 走第二条"剧情分支或拓展"；3 个预设选项 + 自由输入 → AI 判定结构化输出；EP12/EP07 两集都验证可用 |
| 服务部署 | ✅ 完整 | uvicorn 后端 + Vite 前端，proxy /api/deadman → 127.0.0.1:7860；本地部署符合"个人 PC Local Server"要求 |
| 用户互动能力（可选） | ❌ 缺失 | 无他人反应/点赞/评论可视；judgment 响应里 `aggregate_stats=null`，明确未做 |

**评分**：完成度约 70%，折算 **28/40**。

**为什么不是更高**：
- "列表"在用户眼里就是 1 张卡，缺少"短剧列表页"的视觉重量
- 用户互动（可选加分项）完全没做，丢掉了拿差异化分的机会

**为什么不是更低**：
- 必选项里只有"用户互动可选"完全空白，其他都至少有
- 互动质量明显高于"按一个选项→放个动画"的最小化实现

### A2. 技术选型与实现 (30% → 24/30)

**观测到的好点**：
- 技术栈现代：Vite + React 18 + TypeScript + Capacitor（同时跑 Web 和 Android）
- 接口分层清晰：catalog / moments / media / judgment / runtime/session/event
- 用 viewer_session_id 串联用户行为（每次状态变化都 POST session/event）
- 搭子状态机干净：idle → notice_exclaim → thinking → verdict → idle，每个状态都有 webp 资源对应
- 视频 206 Partial Content + seek 友好，体感播放流畅
- 后端 verdict 输出 schema 严谨（包含 evidence_refs / applied_constraints / inference_notes / warnings），符合 CAB Runtime 的 contract 设计
- Custom prompt 提交后 ~1-2 秒返回 verdict，感知良好

**扣分点**：
- **静态 fallback 与 API 不一致**：`Branch3PlayerDemo.tsx` 里 `STATIC_HIGHLIGHT_MARKERS` 用 12/24/36/48/60 秒作为 noticeAt，但 API 实际返回 0/20/0/60/60。UI 显示的 marker 时间是 API 的，但 hook 文本是 static 的——意味着如果后端挂掉走 fallback，时间和文本都会漂移。
- **session 持久化只用 sessionStorage**：刷新标签页 session 还在（OK），关掉再打开就丢了；如果用 localStorage 用户可以"回到上次看到哪"
- **"分享"按钮无任何反馈**：点了之后只是关闭弹窗，没有 toast / dialog / 复制确认。承诺了功能但没交付。
- **"继续看"按钮不自动恢复播放**：点完关闭弹窗但 video 仍是 paused 状态，用户要再点一次 ▶；流程被打断

**评分**：折算 **24/30**。架构足够撑住答辩，但首用看得见的"瑕疵"会被评委捕获。

### A3. 创新与自由探索 (20% → 13/20)

**真亮点**（按对评委的"哇"程度排序）：

1. **搭子人格化**："要是我来"的本意是"如果我是这个角色"——把 AI 互动激发具象化成一个会眨眼/举牌/思考的搭子，而不是冷冰冰的选项弹窗。从 idle → notice_exclaim → thinking → verdict → idle 的 webp 序列让 AI 不再是 chatbot 框
2. **"懂你❤" 举牌反馈**：用户选完之后搭子举着"懂你❤""就是啊""我懂"这种小牌子，每个选项一种 stamp——是"陪伴感"的微设计
3. **自由输入"我有不同想法"**：把用户的原话嵌进 consequence 文本（"'要是我来，我会先扣下那碗脏饭...'站得住，但..."）——"被听到"的感受是真的
4. **后端 canon-safe judgment**：verdict 输出里有 canon_anchor、applied_constraints、warnings 等防漂移设计（"不要声称未来集数也会按这个分支""不要把生成图当作剧情证据"）——这是认真做"governed runtime"的痕迹
5. **文案有粗粝感**："别让娃白懂事""规矩先停一停"这种短句比"立刻让儿媳上桌（推翻旧规矩）"自然得多

**弱点**：
- 创新基本集中在角色与文案层；视觉化没有更进一步——没有结果图（API 留了 placeholder slot 但未接入图像生成）、没有动效爽点
- 结果文本目前看下来都是"温和支持型"（"我接住你咯"），缺少"反对/质疑/挑战你"那一面，体验维度单一
- 6 维评分（爽度/可信度/风险/暴露度/关系冲击/回看顺滑度）刻意不展示给用户——这是 Axis 文档里"do not expose score_axes"的设计决定，但从"创新展现"角度损失了一个可视化爽点

**评分**：折算 **13/20**。搭子和 canon-safe judgment 是真创新；视觉层创新单薄。

### A4. 文档与表达能力 (10% → 8/10)

只看 README 和 Axis（按用户要求不深入 docs/）：

- `Deadman/README.md`：分层清楚（layout / reorientation / host bridge），有 owner 表
- `docs/Axis_For_Main_Agent.md`：明确写出 current station / last reliable validation / do not do 清单——这种"诚实声明边界"的写法对评委很有效
- 频繁出现"我们没做 X 因为 Y"的表达（"do not connect image generation", "no LLM/ASR or external provider is connected"）——主动声明边界比掩盖来得可信

**未补足**：
- 缺面向评委的 1 页 narrative（"为什么是这个题/差异化在哪/演示脚本"）
- 缺产品视角的 1 张截图大图（README 全是文字）

**评分**：折算 **8/10**。

---

## 3. 外部首用体验观察（rubric 外，但答辩会被问）

| 窗口 | 观察 | 等级 |
|---|---|---|
| 0-30s 冷启动 | catalog 单页直接给"短剧高光 · 要是我来 · Branch 3"。"Branch 3" 是内部命名漏给用户会困惑；Hero 区是手绘风占位图而非剧情封面 | ⚠️ 中 |
| 30s-2min 首次交互 | **关键缺陷**：进入播放器后，video 自动播放经过 notice_at_seconds=0 但不自动暂停/不自动开面板；用户必须主动点搭子或时间轴 "!" 标记。新用户大概率错过第一次互动，看完一遍 1:06 完整片以为这就是个普通播放器。 | ❌ 关键 |
| 2-5min 第二次互动 | 一旦学会流程（点时间轴 "!" → 点搭子 → 选项 → 结果），体验是顺畅的：verdict 文案质量好，不是模板灌水，AI 真的在判 | ✅ 好 |
| 异常路径 | "分享"按钮无任何反馈/UI；"继续看"按钮关闭弹窗但不自动恢复播放；session 用 sessionStorage 关闭浏览器就丢 | ⚠️ 中 |
| AI 输出质量 | verdict.summary 是真实定制（自由输入会被原话引用）；但 UI 只展示 summary 一行短句，consequence 长文本（更深入的判断）被丢弃 | ⚠️ 中-好 |

**额外发现**：
- Desktop 视口下播放器保持 mobile 形状居中，侧边显示了平台合规提示"剧情无不良导向 请树立正确价值观"——细节加分
- 后端 verdict 里有 6 维分数 + canon_anchor + warnings，但全都没暴露给 UI——按 Axis 文档"do not expose score_axes"是有意为之

---

## 4. 8 天内最值得补救的 3 项

按"对评委首用印象 / 答辩自检表打勾"的边际效用排序：

### 优先级 1：首次互动自动触发（必修）
**问题**：notice_at_seconds 命中时搭子只是切到 notice_exclaim 状态、显示一个小 "!"，video 继续播。新用户没有任何强引导知道要点搭子。

**改法**：在 tomatoCompanionMachine 加 auto-invoke 路径——notice_exclaim 进入时直接 setTimeout 触发 panel open（或者立即触发，看产品口径）。或者在视频上叠加一个"点这里参与决策"的浮动 hint。

**成本**：< 2 小时；对评委首用印象提升幅度极大。

### 优先级 2：catalog 视觉脱单卡形态
**问题**：catalog 只有 1 张大卡看起来像"未完成"。即便后端只有 1 部剧，前端也应该让"列表"不像 demo。

**改法**：
- 短期：把单卡视觉做大、加 hero motion、加 "更多剧集即将解锁" 占位条目
- 中期：把 catalog 加 2-3 个灰色不可点的占位卡（北派寻宝/天下第一纨绔等都在允许清单里，标"敬请期待"）

**成本**：4-6 小时。

### 优先级 3：结果面板展开 consequence 长文本
**问题**：verdict 返回了 consequence.text（深度判断、引用用户原话），但 UI 只展示 verdict.summary 一行短句，浪费了 AI 的真实判断深度。

**改法**：在结果卡上加"展开看完整后果"按钮（或默认双段：summary 当标题、consequence 当正文）。

**成本**：1-2 小时。

---

## 5. 答辩自检表（一页）

| 评委可能问的问题 | 准备好答案 | 现状 |
|---|---|---|
| 你的差异化是什么？ | 搭子陪伴 + 火气点 + 自由输入 + canon-safe judgment | ✅ |
| 为什么不做高光弹幕互动？ | 我们走 MVP 第二条"剧情分支或拓展"，主张"参与一个角色"而不是"评论一段视频" | ✅ |
| MVP 闭环每项 demo 一遍？ | 列表 → 播放 → 切集 → 互动 → 自由输入 → 结果 → 继续看 | ✅（但首交互别忘了手动点搭子） |
| 评委试用没触发互动会怎样？ | ⚠️ 需补救（见优先级 1） | ❌ |
| 你的 AI 真的在干活吗？ | 后端 CABRuntime adapter 出 verdict；自由输入会被引用进 consequence；输出 6 维评分 + applied_constraints + warnings | ✅ |
| 一部剧够吗？ | 5 个 moment 全过人工 review，扩展性靠 producer pipeline；不堆数量是因为题目重视 reviewed-only 而非 quantity | ⚠️ 需要 catalog 包装 |
| 用了什么模型？官方 Doubao 还是别的？ | 需要补充：CABRuntime adapter 串接 Doubao-Seed-2.0-lite？还是用了别的？ | ❓ 需补 |
| 200 元报销额度用在哪？ | 需补充 | ❓ 需补 |
| 为什么用 React/Vite 而不是 Android 原生？ | 单人/小组按宣讲"Web 端+服务端"是合规路径；Capacitor 壳保留可打 APK 的可能性 | ✅ |
| 你的代码 AI 参与了多少？ | 需要补充（宣讲鼓励但要求声明） | ❓ 需补 |

---

## 6. 评测结论

**73/100 是有故事的中上水平**，关键三句话：

1. MVP 闭环真实跑通，**搭子 + canon-safe judgment + 自由输入**是评委会记住的差异化记号
2. 首次互动不自动触发是**唯一一个会显著拉低首用印象的缺陷**，2 小时可修，必修
3. catalog 单卡 + 缺 consequence 展开是"看得见的简陋"，4-6 小时可处理，能把分数推到 78-82 区间

**不建议在 8 天内做的事**：
- 不要去接图像生成（Axis 已明确不做，强行接会破坏 canon 边界）
- 不要去做多剧扩展（人工 review 时间不够，会拉低评分而非提升）
- 不要去做 user-to-user 互动（设计成本远超 8 天）

**建议把时间砸在**：
- 优先级 1-3 三项补救
- 答辩 1 页 narrative + demo 录屏脚本
- 答辩自检表里 ❓ 标记的两项（模型用量 + AI 参与声明）补全到 README

---

## 附录：观测到的具体 bug / 不一致

1. **静态 fallback 漂移**：`Branch3PlayerDemo.tsx` 的 `STATIC_HIGHLIGHT_MARKERS` 用 noticeAtSeconds = 12/24/36/48/60，但 API 实际返回 0/20/0/60/60。后端挂掉时 fallback 时间和文本都不对。
2. **EP12 m001 hook 不一致**：API hook = "四蛋抓到兔子，兔子肉今晚要不要真的下锅？"，UI "火气点" 显示的是 "四蛋抓到兔子那一眼，懂事得让人难受。"（来自 static fallback）——混用了两套数据源。
3. **"分享"按钮黑洞**：点了无任何 UI 反馈/toast/复制确认。
4. **"继续看"不恢复播放**：弹窗关闭但 video 仍 paused。
5. **Session 持久化弱**：用 sessionStorage 不是 localStorage，关浏览器就丢上下文。
6. **首次互动不自动触发**：（见优先级 1）

---

_本评测由外部视角执行，未读 `docs/` 内部 artifacts、未运行测试套件、未做代码级 review。如需 internal code review 或答辩材料定稿请另开 slice。_
