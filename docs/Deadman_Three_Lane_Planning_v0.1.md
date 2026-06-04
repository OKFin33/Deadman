# Deadman 三线统筹规划 v0.1

> Product: Deadman / 要是我来  
> Date: 2026-06-01  
> Purpose: 盘点已完成产物，明确三条开发线状态，规划后续任务优先级

## 总体位置

Deadman 处于 Macro Phase 6（Backend Adapter Mapping）已完成、Phase 7（Judgment Runtime Integration）等待 CABRuntime SDK 的状态。产品已拆分为 **用户侧播放器** 和 **Deadman Studio 生产侧** 两个产品面。

当前主站点：

```
backend adapter boundary complete → resident companion runtime implemented → waiting for formal P0 recording path
```

---

## 一、已完成产物清单

### 1. 设计文档体系

| 文档 | 位置 | 作用 |
|---|---|---|
| PRD v0.3 | `docs/Branch3_要是我来_PRD_v0.3.md` | 最新产品方向，含 v0.3.1 friend-first framing 修正 |
| Deadman Studio Product Brief | `docs/Deadman_Studio_Zero_Context_Product_Brief_v0.1.md` | 生产侧零上下文产品简介 |
| CABRuntime SDK Integration Contract | `docs/CABRuntime_SDK_Integration_Contract_v0.1.md` | Deadman ↔ CABRuntime 集成契约 |
| Producer Bridge Minimum Flow | `docs/Producer_Bridge_Minimum_Flow_v0.1.md` | 生产侧最小可复现流程 |
| P0 Mobile UX Acceptance Checklist | `docs/P0_Mobile_UX_Acceptance_Checklist_v0.1.md` | 前端验收标准 |
| Resident Companion Runtime Tech Plan | `docs/Resident_Companion_Runtime_Tech_Plan_v0.1.md` | 常驻伴侣运行时技术方案 |
| Development Axis | `docs/Development_Axis_v0.1.md` | 宏/微轴线定位文档 |
| Axis For Main Agent | `docs/Axis_For_Main_Agent.md` | 主 agent 恢复上下文用 |
| Competition Technical Doc Skeleton | `docs/Competition_Technical_Doc_Skeleton_v0.1.md` | 比赛技术文档骨架 |
| Submission Material Map | `docs/Submission_Material_Map_v0.1.md` | 提交材料清单 |

### 2. Goal Spec 体系（current `docs/goal_spec/`, archive `docs/archive/goal_spec/`）

已产出 16 个历史 goal spec，覆盖从 ARS 候选挖掘到 LangGraph 生产管线的全部执行契约。公开化整理后，当前入口只保留 LangGraph producer 两份精选 spec，其余已归档到 `docs/archive/goal_spec/` 作为证据：

| Spec | 状态 |
|---|---|
| `Deadman_ARS_First_Pass_Candidate_Mining` | ✅ 已执行 |
| `Deadman_Backend_Adapter_Mapping_v0.1` | ✅ 已执行，5/5荒年通过 |
| `Deadman_Backend_Judgment_API_Experiment` | ✅ 已执行 |
| `Deadman_Drama_Context_Pack_Extraction` | ✅ 已执行 |
| `Deadman_EndToEnd_Ingestion_Player_P0` | ✅ 已执行 |
| `Deadman_Field_Minimum_Red_Team_v0.1` | ✅ 已执行 |
| `Deadman_Frontend_Standalone_Package` | ✅ 已执行 |
| `Deadman_Huangnian_Review_Schema_Migration` | ✅ 已执行 |
| `Deadman_Minimum_Field_Induction_MultiDrama_v0.2` | ✅ 已执行 |
| `Deadman_Moment_Field_Minimum_Set_v0.3` | ✅ 已执行 |
| `Deadman_NonRuntime_P0_Targets_v0.1` | ✅ 已执行 |
| `Deadman_Typed_Subkeys_Interface_Prep_v0.1` | ✅ 已执行 |
| `Deadman_LangGraph_Producer_Pipeline_v0.1` | 📋 有 spec，待实现 |
| `Deadman_LangGraph_Producer_LLM_Extension_v0.1` | 📋 有 spec，待实现 |
| `Axis_Navigator_Skill_PRD_v0.1/v0.2` | 工具辅助 |

### 3. 数据与 Schema

| 产物 | 位置 |
|---|---|
| 荒年 Drama Context Pack | `data/dramas/huangnian/context.v0.1.json` |
| 荒年 Moments Pack | `data/dramas/huangnian/moments.v0.1.json` |
| 荒年 Manifest | `data/dramas/huangnian/manifest.v0.1.json` |
| 荒年 Media Registry | `data/dramas/huangnian/media_registry.v0.1.json` |
| 荒年 Reviewed Demo Nodes | `data/dramas/huangnian/evidence/reviewed_demo_nodes.v0.1.json` |
| Adapter Input Schema | `data/schemas/deadman_judgment_adapter_input.v0.1.json` |
| Adapter Output Schema | `data/schemas/deadman_judgment_adapter_output.v0.1.json` |
| Moment Causality Pack v0.3 Draft | `data/schemas/moment_causality_pack.v0.3.draft.json` |
| Field Minimum Set v0.3 Schema | `data/schemas/moment_field_minimum_set.v0.3.json` |
| Field Minimum Red Team Evals | `data/evals/field_minimum_red_team.v0.1.json` |
| Visual Result Request/Response/Plan Schemas | `data/schemas/visual_result_*.v0.1.json` |

### 4. 后端代码（`backend/`）

| 模块 | 作用 | 状态 |
|---|---|---|
| `adapter_mapping.py` | promoted v0.1 packs → v0.3 typed adapter input | ✅ 5/5 通过 |
| `judgment.py` | 判定 API 入口 | ✅ 含 CAB/deterministic 双模式 |
| `runtime_client.py` | CABRuntime thin adapter | ✅ |
| `runtime_models.py` | viewer session / companion runtime 数据模型 | ✅ |
| `viewer_session.py` | viewer session 管理 | ✅ 含 notice 去重、retry 语义 |
| `companion_runtime.py` | headless companion runtime + event protocol | ✅ |
| `friend_voice.py` | FriendVoiceComposer，moment/action-type-aware | ✅ 已修复 hardcoded leads |
| `pack_store.py` | promoted drama/moment pack 加载 | ✅ |
| `models.py` | 公共数据模型 | ✅ |
| `api.py` | FastAPI 路由 | ✅ |
| tests（5个） | adapter / judgment / CAB client / companion runtime / API | ✅ 最近已知全绿 |

### 5. ARS 工具链（`tools/ars/`）

16 个脚本，覆盖从媒体注册到发布验证的完整生产侧 CLI 流程：

```
deadman_prepare_drama_assets.py
deadman_register_media.py
deadman_build_timeline_windows.py
deadman_mine_candidates.py
deadman_cluster_candidates.py
deadman_review_candidates.py
deadman_build_drama_context.py
deadman_publish_p0_bridge.py
deadman_validate_producer_bridge.py
deadman_print_recording_urls.py
deadman_check_submission_readiness.py
deadman_build_field_demand_matrix.py
deadman_induce_minimum_field_set.py
deadman_induce_moment_fields.py
deadman_redteam_field_minimum.py
deadman_volc_asr_flash.py / deadman_volc_asr_standard.py
```

### 6. 前端（`frontend/`）

| 模块 | 作用 |
|---|---|
| `Branch3PlayerDemo.tsx/.css` | 移动端竖屏播放器 + 高亮标记 + 交互窗口 |
| `TomatoCompanion.tsx/.css` | 番茄伴侣 UI 组件 |
| `tomatoCompanionMachine.ts` | 伴侣 9 状态机 |
| `deadmanApi.ts` | 旧 judgment 直调 API client |
| `deadmanRuntimeApi.ts` | 新 resident runtime API client |
| `App.tsx / main.tsx` | 独立 Vite 应用入口 |

### 7. 伴侣素材（`Deadman/assets/`）

番茄伴侣 `tomato-robes` 7 态 PNG/WebP 完成：idle / notice_question / notice_exclaim / stand_bubble / thinking / verdict / runout + spritesheet

---

## 二、三线当前状态与后续任务

### 线 1：CAB 使用侧（用户端播放器 + 伴侣运行时）

**当前站点**：Headless companion runtime 已实现，CABRuntime env-activated formal path 已通过 readiness gate。

**已完成里程碑**：

1. v0.3 typed adapter mapping（5/5 荒年节点通过）
2. CABRuntime SDK 集成契约
3. Headless companion runtime + viewer session + event protocol
4. FriendVoiceComposer（moment/action-type-aware lead selection）
5. Notice 去重 + retry 语义 + race auto-restore
6. `DEADMAN_JUDGMENT_ENGINE=cab_runtime` formal path + readiness gate
7. Fail-closed 结构化错误 → 前端 error state

**后续任务（按优先级）**：

| 优先级 | 任务 | 阻塞关系 | 说明 |
|---|---|---|---|
| P0 | CABRuntime Phase 2：正式录制路径 | — | 当 readiness gate 稳定通过后，移除 deterministic 作为 formal fallback 的任何语言 |
| P0 | Streaming 文本结果 | CABRuntime Phase 2 | provider streaming → friend voice streaming |
| P1 | 云渺/离婚 human review → runtime promotion | 需要线2 human review 流程 | 扩展 demo 跨类型证明 |
| P1 | 图片生成 spike | CABRuntime text 质量稳定后 | latency/quality/proof-contamination 实验 |
| P1 | Session 持久化 | — | 当前 in-memory，P1 需持久化 |
| P2 | Voice/TTS/ASR 输入 | 文本判定质量稳定后 | — |

### 线 2：LangGraph 生产侧（Deadman Studio）

**当前站点**：完整设计 spec 已产出（Pipeline v0.1 + LLM Extension v0.1），CLI 工具链已实现并验证，但 LangGraph 编排层尚未开始编码。

**已完成里程碑**：

1. 16 个 ARS 脚本全部就位
2. 荒年 P0 完整 CLI 可复现流程（从 MP4 → 注册 → ASR → 挖掘 → 审核 → 发布 → 验证）
3. Producer Bridge 验证器
4. 提交就绪检查器
5. 多剧 field induction（荒年/云渺/离婚，但只有荒年 promoted）
6. Red Team 对抗测试通过
7. 完整 LangGraph 设计 spec + LLM Extension spec + Product Brief

**后续任务（按优先级）**：

| 优先级 | 任务 | 阻塞关系 | 说明 |
|---|---|---|---|
| **P0 阻塞** | LangGraph cold-resume spike | 阻塞所有后续 | 必须先验证 Functional API + SQLite checkpointer 的 pause/exit/resume 生命周期 |
| P0 | `deadman_run_producer_graph.py` 基础实现 | spike 通过 | 10 节点固定图 + dry-run/start/resume CLI |
| P0 | Human review gate 文件化 pause/resume | 同上 | `review_request.json` 生成 + resume approve/reject |
| P1 | 4 个 LLM producer 节点 | 基础图实现后 | semantic miner / candidate judge / context draft / pack draft |
| P1 | Prompt templates + output schemas | 同上 | `tools/ars/prompts/` + `data/schemas/producer_llm/` |
| P1 | Mock provider fixtures | 同上 | `data/fixtures/llm_mock/` |
| P1 | 云渺/离婚 human review 实际执行 | LLM judge 或手动 | 筛选可 promote 的 runtime demo 节点 |
| P2 | Producer UI / Deadman Studio 前端 | P0 loop 稳定后 | 当前 CLI/report 足够 |

### 线 3：UI 设计 + 前端接入（未正式启动）

**当前站点**：有工程骨架（独立 Vite 包 + 状态机 + 素材），有验收清单，但没有经过正式视觉设计 pass，前端还在使用旧 judgment 直调而非 resident runtime API。

**已完成里程碑**：

1. `frontend` 独立 Vite React 包
2. Branch3PlayerDemo 移动端竖屏播放器
3. TomatoCompanion 9 状态机
4. 番茄伴侣 7 态素材完成
5. P0 Mobile UX Acceptance Checklist（3 视口 + 核心用户流 + 录制验收）
6. 旧 judgment API client + 新 runtime API client（但前端尚未完全切换）

**后续任务（按优先级）**：

| 优先级 | 任务 | 阻塞关系 | 说明 |
|---|---|---|---|
| **P0** | 正式视觉设计 pass | — | Catalog / Player / Companion / Bubble / Result 全流程视觉设计，当前是工程 placeholder |
| **P0** | 前端接入 resident companion runtime API | 线1 runtime 稳定 | 用 `deadmanRuntimeApi.ts` 替代 `deadmanApi.ts` 直调 judgment |
| P0 | Result surface 改为 single_narrative 渲染 | 接入 runtime API | 不再堆叠字段，用 FriendVoiceComposer 产出的自然语言 |
| P0 | Error state 产品化 | 同上 | 按 checklist 实现 structured error → companion error state |
| P0 | Bubble 交互完善 | 视觉设计后 | preset/custom 输入、键盘适配、滚动、关闭返回 |
| P1 | Catalog 页面设计 | — | 目前只是列表，需要移动端短剧卡片 |
| P1 | 录制验收 smoke | 全流程可用后 | 3 视口 × 完整用户流 Playwright 自动化 |
| P2 | Runtime/frontend bridge 清理 | Deadman 前端独立后 | 移除 legacy bridge 依赖 |

---

## 三、跨线依赖与关键路径

```
线2 LangGraph spike ──→ 线2 producer graph 实现 ──→ 线2 LLM nodes ──→ 云渺/离婚 review
                                                                          ↓
线1 CABRuntime Phase 2 ──→ Streaming ──→ 图片 spike                 线1 跨类型 promotion
       ↓
线3 视觉设计 ──→ 前端接入 runtime API ──→ result surface 重做 ──→ 录制验收
```

**比赛提交关键路径**：线3 视觉设计 + 线1 CABRuntime 正式路径 → 录制 demo → 技术文档定稿

**最短路径建议**：三线可以并行推进，但录制 demo 之前必须线1 runtime 和线3 UI 同时就绪。线2 LangGraph 对比赛提交不是硬阻塞（CLI 流程已可展示），但是"AI全栈"叙事的关键支撑。

---

## 四、当前已知债务

| 债务 | 影响 | 建议处理 |
|---|---|---|
| CABRuntime 默认打包要求 | 干净部署默认 `cab_runtime`，缺 CABRuntime 会 fail closed | 录制/部署环境必须保留 CABRuntime checkout/config；demo/test 才显式切 `demo_deterministic` |
| 图片生成未接入 | 结果只有文字/placeholder | 文本判定稳定后独立 spike |
| Producer surface 是 CLI | demo 可展示流程但非 polished UI | P0 loop 稳定后再建 |
| 云渺/离婚 未 promoted | 跨类型只有 schema 证据 | human review 后 promote |
| Runtime bridge 仍存在 | 部分 demo path 经 legacy host 编译 | sprint 内接受，后清理 |
| 前端未完全切换 runtime API | 仍有旧 judgment 直调残留 | 线3 首要任务 |
| Session in-memory only | 单进程，无持久化 | P1 |
