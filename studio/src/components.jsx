// ---------------------------------------------------------------------------
// Deadman Studio · shared UI primitives + status config.
// ---------------------------------------------------------------------------

// Status -> { label(zh), tone }. tone maps to CSS classes (.tone-*).
const STATUS = {
  // run statuses
  planned:                 { label: "已计划",   tone: "muted" },
  running:                 { label: "运行中",   tone: "info" },
  publishing:              { label: "发布中",   tone: "info" },
  waiting_for_review:      { label: "待评审",   tone: "warn" },
  waiting_for_llm:         { label: "等待 LLM", tone: "violet" },
  llm_failed:              { label: "LLM 失败", tone: "danger" },
  skipped_by_config:       { label: "已跳过",   tone: "muted" },
  failed:                  { label: "失败",     tone: "danger" },
  validation_failed:       { label: "校验失败", tone: "danger" },
  rejected_by_human_review:{ label: "已驳回",   tone: "danger" },
  blocked_by_prior_failure:{ label: "上游阻断", tone: "muted" },
  pass:                    { label: "通过",     tone: "ok" },
};

const ACTION_TYPE = {
  system_rule:  "系统规则",
  resource:     "资源分配",
  humiliation:  "羞辱反转",
  relationship: "关系压力",
};

const SOURCE_LABEL = {
  deterministic:          { t: "确定性召回", cls: "src-det" },
  deterministic_enriched: { t: "确定性增强", cls: "src-enr" },
  llm_discovered:         { t: "语义发现",   cls: "src-llm" },
};

const LLM_LABEL = {
  recommend:       { t: "推荐",   cls: "judge-rec" },
  keep_for_review: { t: "待定",   cls: "judge-keep" },
  reject:          { t: "建议弃", cls: "judge-rej" },
};

const GRADE = { high: "高", medium: "中", low: "低" };

function StatusPill({ status, size }) {
  const s = STATUS[status] || { label: status, tone: "muted" };
  const dot = status === "running" || status === "publishing";
  return (
    <span className={"pill tone-" + s.tone + (size === "lg" ? " pill-lg" : "")}>
      <span className={"pill-dot" + (dot ? " pulse" : "")}></span>
      {s.label}
    </span>
  );
}

function Chip({ children, cls }) {
  return <span className={"chip " + (cls || "")}>{children}</span>;
}

// Small horizontal score bar.
function Score({ label, value }) {
  return (
    <div className="score">
      <span className="score-k">{label}</span>
      <span className="score-track"><span className="score-fill" style={{ width: value + "%" }}></span></span>
      <span className="score-v">{value}</span>
    </div>
  );
}

const SCORE_KEYS = [
  ["emotion_heat", "情绪热度"],
  ["choice_leverage", "选择杠杆"],
  ["world_constraint_value", "世界约束"],
  ["watch_flow_fit", "观看贴合"],
];

window.Studio = Object.assign(window.Studio || {}, {
  STATUS, ACTION_TYPE, SOURCE_LABEL, LLM_LABEL, GRADE, SCORE_KEYS,
  StatusPill, Chip, Score,
});
