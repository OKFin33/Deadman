// ---------------------------------------------------------------------------
// Deadman Studio · mock data shaped like the real producer-graph artifacts.
//
// Shapes intentionally mirror the on-disk contract so the API layer (api.jsx)
// can be swapped to real endpoints with no UI changes:
//   - manifest      ~ tmp/deadman_producer_runs/{run_id}/producer_job_manifest.json
//   - reviewRequest ~ tmp/deadman_producer_runs/{run_id}/review_request.json
//   - finalReport   ~ tmp/deadman_producer_runs/{run_id}/final_report.md
// ---------------------------------------------------------------------------

// Canonical node catalog (base graph + LLM extension), in graph order.
// phase groups the pipeline; authority is the contract's authority split.
const NODE_CATALOG = [
  { id: "prepare_assets",        zh: "准备素材",       phase: "采集 · Ingest",   llm: false,
    purpose: "把本地 MP4 转成忽略的制作资产（音频 / 关键帧 / contact sheet）。",
    authority: "本地资产准备",
    cmd: "python3 tools/ars/deadman_prepare_drama_assets.py \\\n  --drama-id {drama_id} --drama-title {drama_title} \\\n  --video-dir {video_dir} --analysis-dir {analysis_dir}",
    outputs: ["{analysis_dir}/media_index.json", "（忽略的音频/关键帧/contact-sheet 产物）"],
    fails: ["asset_video_dir_missing", "asset_media_index_missing", "asset_prepare_failed"] },

  { id: "register_media",        zh: "注册媒体",       phase: "采集 · Ingest",   llm: false,
    purpose: "生成 runtime 安全的媒体注册表；本地路径只留在 producer_media 元数据里。",
    authority: "媒体注册（runtime 安全）",
    cmd: "python3 tools/ars/deadman_register_media.py \\\n  --media-index {analysis_dir}/media_index.json \\\n  --out {drama_dir}/media_registry.v0.1.json \\\n  --episode-ids {episode_ids}",
    outputs: ["{drama_dir}/media_registry.v0.1.json"],
    fails: ["media_index_invalid", "media_required_episode_missing", "media_register_failed"] },

  { id: "build_timeline_windows", zh: "构建时间窗",    phase: "采集 · Ingest",   llm: false,
    purpose: "用 ASR / 关键帧生成带时间戳的源窗口；缺 ASR 会降低 source_quality 并记录。",
    authority: "源窗口构建",
    cmd: "python3 tools/ars/deadman_build_timeline_windows.py \\\n  --analysis-dir {analysis_dir} --drama-id {drama_id} --version v0.1",
    outputs: ["{analysis_dir}/candidates/{drama_id}_windows.v0.1.json"],
    fails: ["windows_media_index_missing", "windows_build_failed"] },

  { id: "mine_candidates",       zh: "候选挖掘",       phase: "挖掘 · Mining",   llm: false,
    purpose: "确定性广召回与可回放证据池。只提议、排序、保留证据——从不批准、从不定稿。",
    authority: "提议 / 排序 / 可回放基线",
    cmd: "python3 tools/ars/deadman_mine_candidates.py \\\n  --candidate-dir {analysis_dir}/candidates \\\n  --max-candidates {recall_budget} --drama-id {drama_id}",
    outputs: ["{analysis_dir}/candidates/{drama_id}_candidates.v0.1.json", "…_candidates.v0.1.md"],
    fails: ["candidate_windows_missing", "candidate_mine_failed"] },

  { id: "llm_semantic_miner",    zh: "语义挖掘",       phase: "挖掘 · Mining",   llm: true,
    purpose: "找关键词召回漏掉或解释不足的语义强交互点；区分 deterministic_enriched 与 llm_discovered。",
    authority: "语义理解与候选提议（不写 runtime 包）",
    cmd: "（图内 LLM 节点，--enable-llm 时启用）\n# 输出: {run_dir}/llm_semantic_candidates.json",
    outputs: ["{run_dir}/llm_semantic_candidates.json"],
    fails: ["llm_schema_invalid", "provider_failed"] },

  { id: "cluster_candidates",    zh: "机制聚类",       phase: "挖掘 · Mining",   llm: false,
    purpose: "按机制与场压（field pressure）给候选分组；解释场压，但从不自行扩展 runtime schema。",
    authority: "解释场压",
    cmd: "python3 tools/ars/deadman_cluster_candidates.py \\\n  --candidate-dir {analysis_dir}/candidates --drama-id {drama_id}",
    outputs: ["{drama_id}_mechanism_buckets.v0.1.json", "{drama_id}_field_hypotheses.v0.1.md"],
    fails: ["cluster_candidates_missing", "cluster_failed"] },

  { id: "llm_candidate_judge",   zh: "候选初筛",       phase: "挖掘 · Mining",   llm: true,
    purpose: "确定性召回与人工评审之间的语义初筛闸；只选观众会情绪波动、想立刻发声的时刻，产出 shortlist。",
    authority: "二次筛选 + 失败模式标注（不晋升 runtime）",
    cmd: "（图内 LLM 节点，--enable-llm 时启用）\n# 输出: {run_dir}/llm_candidate_judgment.json",
    outputs: ["{run_dir}/llm_candidate_judgment.json"],
    fails: ["llm_schema_invalid", "provider_failed"] },

  { id: "prepare_human_review",  zh: "准备评审",       phase: "评审 · Review",   llm: false,
    purpose: "在 interrupt 之前持久化评审请求，并把 run 标记为 waiting_for_review（与 checkpoint 一致）。",
    authority: "评审请求持久化",
    cmd: "（图内节点）写 review_request.json，计算 request_hash",
    outputs: ["{run_dir}/review_request.json", "manifest.status = waiting_for_review"],
    fails: ["review_request_drift"] },

  { id: "human_review_gate",     zh: "人工评审闸门",   phase: "评审 · Review",   llm: false, gate: true,
    purpose: "用 LangGraph interrupt() 在任何可发布状态变更前暂停。批准→build_drama_context；驳回→终态。",
    authority: "唯一批准权",
    cmd: "# resume:\npython3 tools/ars/deadman_run_producer_graph.py resume \\\n  --run-id {run_id} --review-decision approve|reject",
    outputs: ["reviewed_demo_nodes.v0.1.json", "reviewed_candidates.reviewed.v0.1.json"],
    fails: ["review_request_drift", "review_resume_invalid", "review_artifact_missing"] },

  { id: "llm_drama_context_draft", zh: "上下文草稿",   phase: "发布 · Publish",  llm: true,
    purpose: "为制作人评审起草剧目上下文；inferred 字段标 draft，绝不直接覆盖已追踪的 context.v0.1.json。",
    authority: "草稿（评审通过后才运行）",
    cmd: "（图内 LLM 节点，approve 后运行）\n# 输出: {run_dir}/llm_drama_context_draft.json",
    outputs: ["{run_dir}/llm_drama_context_draft.json"],
    fails: ["llm_schema_invalid", "provider_failed"] },

  { id: "llm_moment_pack_draft", zh: "Moment 草稿",    phase: "发布 · Publish",  llm: true,
    purpose: "为已批准候选起草 Moment Pack 字段；每条强制 requires_human_review=true，绝不直接发布。",
    authority: "草稿（仅用已批准候选）",
    cmd: "（图内 LLM 节点，approve 后运行）\n# 输出: {run_dir}/llm_moment_pack_drafts.json",
    outputs: ["{run_dir}/llm_moment_pack_drafts.json"],
    fails: ["llm_schema_invalid", "provider_failed"] },

  { id: "build_drama_context",   zh: "构建剧目上下文", phase: "发布 · Publish",  llm: false,
    purpose: "把已评审证据转成上下文与 moment pack 源材料，并 promote 到 drama_dir。仅从已评审输入构建。",
    authority: "仅从已评审输入构建",
    cmd: "python3 tools/ars/deadman_build_drama_context.py \\\n  --drama-id {drama_id} --reviewed-demo-nodes … --promote --promote-dir {drama_dir}",
    outputs: ["{analysis_dir}/drama_context/*", "promoted → {drama_dir}/"],
    fails: ["context_review_not_approved", "context_build_failed"] },

  { id: "publish_p0_bridge",     zh: "发布 P0 包",     phase: "发布 · Publish",  llm: false,
    purpose: "把已评审输入写成 runtime 可读的 pack 文件（manifest / context / moments / evidence）。",
    authority: "只从已评审输入写 runtime 包",
    cmd: "python3 tools/ars/deadman_publish_p0_bridge.py \\\n  --drama-dir {drama_dir} --reviewed-demo-nodes … --media-registry …",
    outputs: ["{drama_dir}/manifest.v0.1.json", "context.v0.1.json", "moments.v0.1.json", "evidence/"],
    fails: ["publish_input_not_reviewed", "publish_media_registry_missing", "publish_failed"] },

  { id: "validate_producer_bridge", zh: "发布校验",    phase: "发布 · Publish",  llm: false,
    purpose: "拦截不安全的 runtime 产物：检查一致性、review 状态、runtime 安全源引用、无 raw media / .env。",
    authority: "发布后唯一安全权",
    cmd: "python3 tools/ars/deadman_validate_producer_bridge.py \\\n  --drama-dir {drama_dir} --report {analysis_dir}/producer_bridge_validation_report.md",
    outputs: ["producer_bridge_validation_report.md", "manifest.validation_result"],
    fails: ["validation_failed", "validation_report_missing"] },

  { id: "final_report",          zh: "最终报告",       phase: "发布 · Publish",  llm: false,
    purpose: "给操作者与评审人的总结：最终状态、节点表、子命令、评审决定、校验结果、runtime 包路径。",
    authority: "只报告，不改已发布数据",
    cmd: "（图内节点）写 final_report.md",
    outputs: ["{run_dir}/final_report.md"],
    fails: ["final_report_failed"] },
];

const PHASES = ["采集 · Ingest", "挖掘 · Mining", "评审 · Review", "发布 · Publish"];

// Helper: build a node_statuses map from a list of pass nodes + overrides.
function nodeStatuses(passList, overrides, mode) {
  const out = {};
  for (const n of NODE_CATALOG) {
    if (n.llm && mode !== "llm") { out[n.id] = "skipped_by_config"; continue; }
    out[n.id] = passList.includes(n.id) ? "pass" : "planned";
  }
  return Object.assign(out, overrides || {});
}

// --- Runs ------------------------------------------------------------------
const RUNS = [
  {
    run_id: "deadman-producer:huangnian-20260603-01",
    thread_id: "deadman-producer:huangnian-20260603-01",
    drama_id: "huangnian",
    drama_title: "荒年全村啃树皮，我有系统满仓肉",
    graph_mode: "llm",
    status: "waiting_for_review",
    started_at: "2026-06-03 09:41",
    updated_at: "2026-06-03 09:58",
    current_node: "human_review_gate",
    recall_budget: 80,
    deterministic_candidate_count: 80,
    node_statuses: nodeStatuses(
      ["prepare_assets","register_media","build_timeline_windows","mine_candidates",
       "llm_semantic_miner","cluster_candidates","llm_candidate_judge","prepare_human_review"],
      { human_review_gate: "waiting_for_review" }, "llm"),
  },
  {
    run_id: "deadman-producer:huangnian-20260524-07",
    thread_id: "deadman-producer:huangnian-20260524-07",
    drama_id: "huangnian",
    drama_title: "荒年全村啃树皮，我有系统满仓肉",
    graph_mode: "base",
    status: "pass",
    started_at: "2026-05-24 14:02",
    updated_at: "2026-05-24 14:39",
    current_node: "final_report",
    recall_budget: 80,
    deterministic_candidate_count: 80,
    review_decision: "approve",
    validation_result: "pass",
    published_moments: 5,
    node_statuses: nodeStatuses(NODE_CATALOG.map(n => n.id), {}, "base"),
  },
  {
    run_id: "deadman-producer:yunmiao-20260603-02",
    thread_id: "deadman-producer:yunmiao-20260603-02",
    drama_id: "yunmiao",
    drama_title: "云渺",
    graph_mode: "llm",
    status: "running",
    started_at: "2026-06-03 10:12",
    updated_at: "2026-06-03 10:15",
    current_node: "llm_candidate_judge",
    recall_budget: 64,
    deterministic_candidate_count: 64,
    node_statuses: nodeStatuses(
      ["prepare_assets","register_media","build_timeline_windows","mine_candidates",
       "llm_semantic_miner","cluster_candidates"],
      { llm_candidate_judge: "running" }, "llm"),
  },
  {
    run_id: "deadman-producer:lihun-20260531-04",
    thread_id: "deadman-producer:lihun-20260531-04",
    drama_id: "lihun",
    drama_title: "幸得相遇离婚时",
    graph_mode: "base",
    status: "validation_failed",
    started_at: "2026-05-31 16:20",
    updated_at: "2026-05-31 16:54",
    current_node: "validate_producer_bridge",
    recall_budget: 48,
    deterministic_candidate_count: 48,
    review_decision: "approve",
    validation_result: "failed",
    node_statuses: nodeStatuses(
      ["prepare_assets","register_media","build_timeline_windows","mine_candidates",
       "cluster_candidates","prepare_human_review","human_review_gate","build_drama_context","publish_p0_bridge"],
      { validate_producer_bridge: "failed", final_report: "blocked_by_prior_failure" }, "base"),
    errors: [
      { node: "validate_producer_bridge", code: "validation_failed", retryable: false,
        message: "moments.v0.1.json 含未脱敏本地路径 tmp/视频素材/...，runtime 源引用不安全。",
        artifact_refs: ["data/dramas/lihun/moments.v0.1.json"] },
    ],
  },
];

// --- Review shortlist for the waiting run ----------------------------------
// Shaped from llm_candidate_judgment.json + candidate table fields.
const SHORTLIST = {
  run_id: "deadman-producer:huangnian-20260603-01",
  drama_id: "huangnian",
  drama_title: "荒年全村啃树皮，我有系统满仓肉",
  review_policy_version: "deadman_studio_review_gate.v0.1",
  input_candidate_count: 80,
  shortlist_target: 6,
  expected_reviewed_paths: {
    reviewed_demo_nodes: "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
    reviewed_candidates: "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json",
  },
  human_instructions: [
    "确认 interaction_window 时间戳足以触发播放器提示。",
    "确认 hook 与选项贴合源窗口证据，不暗示连续改写后续剧集。",
    "勾选要发布的候选；驳回整次 run 需新建 run_id 重来。",
  ],
  candidates: [
    { id: "huangnian_ep03_c001", episode: "huangnian_ep03", window: [0,20], action_type: "system_rule",
      source: "deterministic_enriched", llm_label: "recommend", grade: "high", keep: true,
      hook: "野蕨菜能卖钱，系统面板要不要现在试？",
      impulse: "要是我来，想用系统能力快速改局面。",
      options: ["立刻售卖野蕨菜验证系统","只卖一小部分，确认别人看不见面板","先不卖，离开灶台再单独测试"],
      excerpt: "天然无污染野蕨菜一斤价值十文钱，是否售卖？呵，这是系统？……这个面板只有我能看见，我得找个地方试验一下系统的功能。",
      scores: { emotion_heat: 78, choice_leverage: 84, world_constraint_value: 88, watch_flow_fit: 82 },
      note: "系统第一次出现，P0 最干净的 hidden-power 规则边界。" },

    { id: "huangnian_ep04_c001", episode: "huangnian_ep04", window: [12,32], action_type: "resource",
      source: "deterministic", llm_label: "recommend", grade: "high", keep: true,
      hook: "换来的粮食只够一顿，先紧着谁？",
      impulse: "要是我来，先把最饿的人喂饱。",
      options: ["全给孩子，自己扛饿","均分一小份，留一点应急","换成耐放的杂粮，拉长这点存量"],
      excerpt: "就这一点了……省着点吃，撑不到下回赶集。",
      scores: { emotion_heat: 80, choice_leverage: 72, world_constraint_value: 79, watch_flow_fit: 81 },
      note: "资源分配压力清晰，证据来自赶集/分粮 ASR。" },

    { id: "huangnian_ep06_c001", episode: "huangnian_ep06", window: [40,62], action_type: "relationship",
      source: "llm_discovered", llm_label: "keep_for_review", grade: "medium", keep: true,
      hook: "村邻上门借粮，借还是不借？",
      impulse: "要是我来，不想撕破脸，也不想被掏空。",
      options: ["借一点，立个明确的还法","不借，但帮着出别的主意","只借给真正断顿的那家"],
      excerpt: "都是一个村的，你家有余粮，匀我们一口……",
      scores: { emotion_heat: 74, choice_leverage: 70, world_constraint_value: 83, watch_flow_fit: 76 },
      note: "暴露与人情风险并存；语义挖掘补到，需人工确认窗口。" },

    { id: "huangnian_ep07_c001", episode: "huangnian_ep07", window: [20,40], action_type: "humiliation",
      source: "deterministic_enriched", llm_label: "recommend", grade: "high", keep: true,
      hook: "儿媳被逼吃最脏的东西，要不要当场改桌规？",
      impulse: "要是我来，先让眼前的人吃上一口干净的。",
      options: ["当场让儿媳上桌，推翻旧规矩","先把饭换掉，再私下处理婆媳权力","不当众翻脸，只让她先吃一口干净的"],
      excerpt: "你是地位最低，根本不配上桌吃饭，只能吃最难吃最脏的东西，不然就给我饿着。",
      scores: { emotion_heat: 85, choice_leverage: 74, world_constraint_value: 76, watch_flow_fit: 82 },
      note: "首轮误标 resource_crisis，实为家庭羞辱+秩序修复；情绪热度最高。" },

    { id: "huangnian_ep12_c001", episode: "huangnian_ep12", window: [0,20], action_type: "resource",
      source: "deterministic", llm_label: "recommend", grade: "high", keep: true,
      hook: "四蛋抓到兔子，兔子肉今晚要不要真的下锅？",
      impulse: "要是我来，先让眼前的人吃上东西。",
      options: ["今晚分兔肉，先让四蛋确认有份","先留兔子和皮毛，改用别的食物补这顿","当成四蛋的功劳，少量处理给全家尝味"],
      excerpt: "四蛋抓了只兔子，今天晚上咱吃兔肉……咱家一年都没吃过肉了，虽然肯定没我的份。",
      scores: { emotion_heat: 85, choice_leverage: 74, world_constraint_value: 88, watch_flow_fit: 82 },
      note: "资源分配 + 亲子信任同时触发，视觉证据 00:00 明确可见兔子。" },

    { id: "huangnian_ep05_c002", episode: "huangnian_ep05", window: [88,104], action_type: "resource",
      source: "llm_discovered", llm_label: "keep_for_review", grade: "low", keep: false,
      hook: "灶上多出一袋米，要不要解释来路？",
      impulse: "要是我来，怕被追问，想含糊过去。",
      options: ["主动给个普通说法","转移话题，先藏起来","只跟最亲的人交底"],
      excerpt: "（关键帧仅见灶台与口袋，ASR 未明确米的来路）",
      scores: { emotion_heat: 58, choice_leverage: 55, world_constraint_value: 64, watch_flow_fit: 52 },
      failure_mode: "evidence_thin · 来路缺 ASR 佐证，易越界暴露系统。",
      note: "证据偏弱，窗口模糊；建议先不发布。" },

    { id: "huangnian_ep09_c003", episode: "huangnian_ep09", window: [203,219], action_type: "resource",
      source: "deterministic", llm_label: "keep_for_review", grade: "low", keep: false,
      hook: "集市上有人压价，卖不卖？",
      impulse: "要是我来，想多换点钱。",
      options: ["照价卖掉","僵着等更好价","换个买家"],
      excerpt: "（关键词命中“卖/价”，但场压低，情绪平淡）",
      scores: { emotion_heat: 41, choice_leverage: 48, world_constraint_value: 50, watch_flow_fit: 44 },
      failure_mode: "low_pressure · 关键词召回噪声，观众不会想立刻发声。",
      note: "确定性召回噪声，留作 audit 证据即可。" },

    { id: "huangnian_ep11_c004", episode: "huangnian_ep11", window: [150,168], action_type: "humiliation",
      source: "llm_discovered", llm_label: "keep_for_review", grade: "medium", keep: false,
      hook: "当众被泼脏水，要不要立刻自证？",
      impulse: "要是我来，气不过，想当场说清楚。",
      options: ["当众对质","先忍，私下取证","拉一个证人出来"],
      excerpt: "（ASR 有口角，但被指控的具体事实在窗口内不完整）",
      scores: { emotion_heat: 69, choice_leverage: 60, world_constraint_value: 58, watch_flow_fit: 63 },
      failure_mode: "window_incomplete · 指控事实跨窗口，触发点不稳。",
      note: "情绪有张力，但窗口边界需重切后再评。" },
  ],
};

// A rendered final_report.md for the completed run.
const FINAL_REPORT = `# Deadman Studio Final Report

- run_id: deadman-producer:huangnian-20260524-07
- drama: huangnian · 荒年全村啃树皮，我有系统满仓肉
- graph_mode: base
- final status: **pass**
- review decision: **approve**
- validation_result: **pass**
- LLM enrichment: skipped_by_config

## 节点表
prepare_assets ✓ · register_media ✓ · build_timeline_windows ✓ · mine_candidates ✓ ·
cluster_candidates ✓ · prepare_human_review ✓ · human_review_gate ✓(approve) ·
build_drama_context ✓ · publish_p0_bridge ✓ · validate_producer_bridge ✓ · final_report ✓

## Runtime 包路径
- data/dramas/huangnian/manifest.v0.1.json
- data/dramas/huangnian/context.v0.1.json
- data/dramas/huangnian/moments.v0.1.json  (5 moments)
- data/dramas/huangnian/evidence/reviewed_demo_nodes.v0.1.json

## 有意排除的制作产物
raw MP4 / keyframes / contact sheets / score_axes 调试字段 — 仅保留在 tmp/ 忽略目录。`;

window.DeadmanData = { NODE_CATALOG, PHASES, RUNS, SHORTLIST, FINAL_REPORT };
