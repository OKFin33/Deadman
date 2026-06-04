(() => {
  const STATUS = {
    // run statuses
    planned: { label: "\u5DF2\u8BA1\u5212", tone: "muted" },
    running: { label: "\u8FD0\u884C\u4E2D", tone: "info" },
    publishing: { label: "\u53D1\u5E03\u4E2D", tone: "info" },
    waiting_for_review: { label: "\u5F85\u8BC4\u5BA1", tone: "warn" },
    waiting_for_llm: { label: "\u7B49\u5F85 LLM", tone: "violet" },
    llm_failed: { label: "LLM \u5931\u8D25", tone: "danger" },
    skipped_by_config: { label: "\u5DF2\u8DF3\u8FC7", tone: "muted" },
    failed: { label: "\u5931\u8D25", tone: "danger" },
    validation_failed: { label: "\u6821\u9A8C\u5931\u8D25", tone: "danger" },
    rejected_by_human_review: { label: "\u5DF2\u9A73\u56DE", tone: "danger" },
    blocked_by_prior_failure: { label: "\u4E0A\u6E38\u963B\u65AD", tone: "muted" },
    pass: { label: "\u901A\u8FC7", tone: "ok" }
  };
  const ACTION_TYPE = {
    system_rule: "\u7CFB\u7EDF\u89C4\u5219",
    resource: "\u8D44\u6E90\u5206\u914D",
    humiliation: "\u7F9E\u8FB1\u53CD\u8F6C",
    relationship: "\u5173\u7CFB\u538B\u529B"
  };
  const SOURCE_LABEL = {
    deterministic: { t: "\u786E\u5B9A\u6027\u53EC\u56DE", cls: "src-det" },
    deterministic_enriched: { t: "\u786E\u5B9A\u6027\u589E\u5F3A", cls: "src-enr" },
    llm_discovered: { t: "\u8BED\u4E49\u53D1\u73B0", cls: "src-llm" }
  };
  const LLM_LABEL = {
    recommend: { t: "\u63A8\u8350", cls: "judge-rec" },
    keep_for_review: { t: "\u5F85\u5B9A", cls: "judge-keep" },
    reject: { t: "\u5EFA\u8BAE\u5F03", cls: "judge-rej" }
  };
  const GRADE = { high: "\u9AD8", medium: "\u4E2D", low: "\u4F4E" };
  function StatusPill({ status, size }) {
    const s = STATUS[status] || { label: status, tone: "muted" };
    const dot = status === "running" || status === "publishing";
    return /* @__PURE__ */ React.createElement("span", { className: "pill tone-" + s.tone + (size === "lg" ? " pill-lg" : "") }, /* @__PURE__ */ React.createElement("span", { className: "pill-dot" + (dot ? " pulse" : "") }), s.label);
  }
  function Chip({ children, cls }) {
    return /* @__PURE__ */ React.createElement("span", { className: "chip " + (cls || "") }, children);
  }
  function Score({ label, value }) {
    return /* @__PURE__ */ React.createElement("div", { className: "score" }, /* @__PURE__ */ React.createElement("span", { className: "score-k" }, label), /* @__PURE__ */ React.createElement("span", { className: "score-track" }, /* @__PURE__ */ React.createElement("span", { className: "score-fill", style: { width: value + "%" } })), /* @__PURE__ */ React.createElement("span", { className: "score-v" }, value));
  }
  const SCORE_KEYS = [
    ["emotion_heat", "\u60C5\u7EEA\u70ED\u5EA6"],
    ["choice_leverage", "\u9009\u62E9\u6760\u6746"],
    ["world_constraint_value", "\u4E16\u754C\u7EA6\u675F"],
    ["watch_flow_fit", "\u89C2\u770B\u8D34\u5408"]
  ];
  window.Studio = Object.assign(window.Studio || {}, {
    STATUS,
    ACTION_TYPE,
    SOURCE_LABEL,
    LLM_LABEL,
    GRADE,
    SCORE_KEYS,
    StatusPill,
    Chip,
    Score
  });
})();
