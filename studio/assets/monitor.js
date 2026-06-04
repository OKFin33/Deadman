(() => {
  const { useState, useEffect, useRef } = React;
  function friendlyArtifact(path) {
    const p = path;
    if (/manifest\.status|validation_result|manifest\.validation/.test(p)) return null;
    if (/[\u4e00-\u9fa5]/.test(p) && !/\.json|\.md/.test(p)) return null;
    if (p.includes("media_index")) return "\u5A92\u4F53\u7D22\u5F15";
    if (p.includes("media_registry")) return "\u5A92\u4F53\u6CE8\u518C\u8868";
    if (p.includes("_windows")) return "\u65F6\u95F4\u7A97";
    if (p.includes("_candidates.v0.1") || /candidates\.v0\.1\.(json|md)/.test(p)) return "\u5019\u9009\u8868";
    if (p.includes("mechanism_buckets")) return "\u673A\u5236\u5206\u7EC4";
    if (p.includes("field_hypotheses")) return "\u573A\u538B\u5047\u8BBE";
    if (p.includes("llm_semantic_candidates")) return "\u8BED\u4E49\u5019\u9009";
    if (p.includes("llm_candidate_judgment")) return "LLM \u521D\u7B5B\u7ED3\u679C";
    if (p.includes("llm_drama_context_draft")) return "\u4E0A\u4E0B\u6587\u8349\u7A3F";
    if (p.includes("llm_moment_pack_drafts")) return "Moment \u8349\u7A3F";
    if (p.includes("review_request")) return "\u8BC4\u5BA1\u8BF7\u6C42";
    if (p.includes("reviewed_demo_nodes")) return "\u5DF2\u8BC4\u5BA1\u8282\u70B9";
    if (p.includes("reviewed_candidates")) return "\u5DF2\u8BC4\u5BA1\u5019\u9009";
    if (p.includes("drama_context")) return "\u5267\u76EE\u4E0A\u4E0B\u6587";
    if (p.includes("validation_report") || p.includes("producer_bridge_validation")) return "\u6821\u9A8C\u62A5\u544A";
    if (p.includes("final_report")) return "\u6700\u7EC8\u62A5\u544A";
    if (p.includes("manifest")) return "\u8FD0\u884C\u6E05\u5355";
    if (p.includes("context.v0.1")) return "\u4E0A\u4E0B\u6587\u5305";
    if (p.includes("moments.v0.1")) return "Moment \u5305";
    if (p.includes("evidence")) return "\u8BC1\u636E";
    if (p.includes("promoted")) return "\u5DF2\u53D1\u5E03\u5230\u5267\u76EE\u76EE\u5F55";
    return null;
  }
  function NodeCard({ node, status, selected, isCurrent, onClick }) {
    const { STATUS } = window.Studio;
    const tone = (STATUS[status] || {}).tone || "muted";
    return /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "node-card tone-" + tone + (selected ? " is-selected" : "") + (isCurrent ? " is-current" : "") + (node.gate ? " is-gate" : "") + (node.llm ? " is-llm" : ""),
        onClick
      },
      /* @__PURE__ */ React.createElement("span", { className: "node-dot tone-" + tone + (status === "running" ? " pulse" : "") }),
      /* @__PURE__ */ React.createElement("span", { className: "node-body" }, /* @__PURE__ */ React.createElement("span", { className: "node-zh" }, node.zh, node.gate ? " \u23F8" : ""), /* @__PURE__ */ React.createElement("span", { className: "node-en" }, node.id)),
      node.llm && /* @__PURE__ */ React.createElement("span", { className: "node-tag" }, "LLM")
    );
  }
  function Pipeline({ run, selected, onSelect }) {
    const { NODE_CATALOG, PHASES } = window.DeadmanData;
    return /* @__PURE__ */ React.createElement("div", { className: "pipeline" }, PHASES.map((phase) => {
      const nodes = NODE_CATALOG.filter((n) => n.phase === phase);
      return /* @__PURE__ */ React.createElement("div", { className: "phase", key: phase }, /* @__PURE__ */ React.createElement("div", { className: "phase-label" }, phase), /* @__PURE__ */ React.createElement("div", { className: "phase-nodes" }, nodes.map((n) => {
        const st = run.node_statuses[n.id] || "planned";
        if (st === "skipped_by_config") return null;
        return /* @__PURE__ */ React.createElement(
          NodeCard,
          {
            key: n.id,
            node: n,
            status: st,
            selected: selected === n.id,
            isCurrent: run.current_node === n.id && run.status !== "pass",
            onClick: () => onSelect(n.id)
          }
        );
      })));
    }));
  }
  function NodeDetail({ run, nodeId, onGoReview }) {
    const { NODE_CATALOG } = window.DeadmanData;
    const { StatusPill } = window.Studio;
    const [showTech, setShowTech] = useState(false);
    const node = NODE_CATALOG.find((n) => n.id === nodeId);
    useEffect(() => {
      setShowTech(false);
    }, [nodeId]);
    if (!node) return /* @__PURE__ */ React.createElement("div", { className: "detail-empty" }, "\u9009\u62E9\u5DE6\u4FA7\u4EFB\u4E00\u8282\u70B9\u67E5\u770B\u8BE6\u60C5");
    const status = run.node_statuses[nodeId] || "planned";
    const err = (run.errors || []).find((e) => e.node === nodeId);
    const fill = (s) => s.replaceAll("{drama_id}", run.drama_id).replaceAll("{drama_title}", '"' + run.drama_title + '"').replaceAll("{run_id}", run.run_id).replaceAll("{run_dir}", "tmp/deadman_producer_runs/" + run.run_id).replaceAll("{analysis_dir}", "tmp/ars_" + run.drama_id + "_analysis").replaceAll("{drama_dir}", "data/dramas/" + run.drama_id).replaceAll("{video_dir}", "tmp/\u89C6\u9891\u7D20\u6750/" + run.drama_id).replaceAll("{episode_ids}", "\u2026").replaceAll("{recall_budget}", run.recall_budget);
    const artifacts = [...new Set(node.outputs.map((o) => friendlyArtifact(fill(o))).filter(Boolean))];
    return /* @__PURE__ */ React.createElement("div", { className: "detail" }, /* @__PURE__ */ React.createElement("div", { className: "detail-head" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "detail-zh" }, node.zh, node.gate ? " \u23F8" : ""), /* @__PURE__ */ React.createElement("div", { className: "detail-en" }, node.id)), /* @__PURE__ */ React.createElement(StatusPill, { status })), /* @__PURE__ */ React.createElement("div", { className: "detail-purpose" }, node.purpose), /* @__PURE__ */ React.createElement("div", { className: "detail-row" }, /* @__PURE__ */ React.createElement("span", { className: "detail-k" }, "\u804C\u8D23"), /* @__PURE__ */ React.createElement("span", { className: "detail-authority" }, node.authority)), node.gate && status === "waiting_for_review" && /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary detail-cta", onClick: onGoReview }, "\u524D\u5F80\u8BC4\u5BA1\u95F8\u95E8 \u2192"), err && /* @__PURE__ */ React.createElement("div", { className: "detail-error" }, /* @__PURE__ */ React.createElement("div", { className: "err-code" }, "\u6821\u9A8C\u5931\u8D25"), /* @__PURE__ */ React.createElement("div", { className: "err-msg" }, err.message)), artifacts.length > 0 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "detail-k mt" }, "\u4EA7\u7269"), /* @__PURE__ */ React.createElement("div", { className: "artifact-list" }, artifacts.map((a) => /* @__PURE__ */ React.createElement("span", { className: "artifact", key: a }, /* @__PURE__ */ React.createElement("span", { className: "artifact-ico" }, "\u25A4"), a)))), /* @__PURE__ */ React.createElement("button", { className: "tech-toggle", onClick: () => setShowTech((v) => !v) }, showTech ? "\u9690\u85CF\u6280\u672F\u7EC6\u8282 \u25B2" : "\u6280\u672F\u7EC6\u8282\uFF08\u547D\u4EE4 / \u5931\u8D25\u7801\uFF09\u25BE"), showTech && /* @__PURE__ */ React.createElement("div", { className: "tech-body" }, /* @__PURE__ */ React.createElement("div", { className: "detail-k" }, "\u5B50\u547D\u4EE4"), /* @__PURE__ */ React.createElement("pre", { className: "codeblock" }, fill(node.cmd)), /* @__PURE__ */ React.createElement("div", { className: "detail-k mt" }, "\u5931\u8D25\u7801"), /* @__PURE__ */ React.createElement("div", { className: "fail-codes" }, node.fails.map((f) => /* @__PURE__ */ React.createElement("code", { key: f }, f))), err && err.artifact_refs && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "detail-k mt" }, "\u53D7\u5F71\u54CD\u6587\u4EF6"), err.artifact_refs.map((a) => /* @__PURE__ */ React.createElement("div", { className: "err-ref", key: a }, a)))));
  }
  function RunMonitor({ runId, refreshKey, onGoReview }) {
    const { StatusPill, Chip } = window.Studio;
    const [run, setRun] = useState(null);
    const [report, setReport] = useState(null);
    const [selected, setSelected] = useState("human_review_gate");
    const lastRunId = useRef(null);
    useEffect(() => {
      let alive = true;
      const initial = lastRunId.current !== runId;
      if (initial) {
        setRun(null);
        setReport(null);
      }
      window.StudioAPI.getRun(runId).then((r) => {
        if (!alive) return;
        setRun(r);
        if (initial && r) {
          setSelected(r.current_node || "prepare_assets");
          lastRunId.current = runId;
        }
      });
      window.StudioAPI.getReport(runId).then((rep) => {
        if (alive) setReport(rep);
      });
      return () => {
        alive = false;
      };
    }, [runId, refreshKey]);
    if (!run) return /* @__PURE__ */ React.createElement("div", { className: "loading" }, "\u8F7D\u5165\u8FD0\u884C\u2026");
    const passCount = Object.values(run.node_statuses).filter((s) => s === "pass").length;
    const totalNodes = Object.values(run.node_statuses).filter((s) => s !== "skipped_by_config").length;
    return /* @__PURE__ */ React.createElement("div", { className: "monitor" }, /* @__PURE__ */ React.createElement("div", { className: "run-head" }, /* @__PURE__ */ React.createElement("div", { className: "run-head-main" }, /* @__PURE__ */ React.createElement("div", { className: "run-title-row" }, /* @__PURE__ */ React.createElement("h2", { className: "run-title" }, run.drama_title), /* @__PURE__ */ React.createElement(StatusPill, { status: run.status, size: "lg" })), /* @__PURE__ */ React.createElement("div", { className: "run-id mono" }, run.run_id)), /* @__PURE__ */ React.createElement("div", { className: "run-meta" }, /* @__PURE__ */ React.createElement(Chip, { cls: run.graph_mode === "llm" ? "mode-llm" : "mode-base" }, run.graph_mode === "llm" ? "LLM \u589E\u5F3A" : "\u57FA\u7840\u6D41\u6C34\u7EBF"), /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, /* @__PURE__ */ React.createElement("b", null, passCount), "/", totalNodes, " \u6B65\u5B8C\u6210"), run.episodes && /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, /* @__PURE__ */ React.createElement("b", null, run.episodes.length), " \u96C6\u7D20\u6750"), run.published_moments != null && /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, "\u53D1\u5E03 ", /* @__PURE__ */ React.createElement("b", null, run.published_moments), " moments"), /* @__PURE__ */ React.createElement("span", { className: "meta-item dim" }, "\u66F4\u65B0 ", run.updated_at))), /* @__PURE__ */ React.createElement("div", { className: "monitor-body" }, /* @__PURE__ */ React.createElement("div", { className: "monitor-left" }, /* @__PURE__ */ React.createElement(Pipeline, { run, selected, onSelect: setSelected }), report && /* @__PURE__ */ React.createElement("div", { className: "report-card" }, /* @__PURE__ */ React.createElement("div", { className: "report-head" }, "\u6700\u7EC8\u62A5\u544A \xB7 final_report"), /* @__PURE__ */ React.createElement("pre", { className: "report-body" }, report))), /* @__PURE__ */ React.createElement("div", { className: "monitor-right" }, /* @__PURE__ */ React.createElement(NodeDetail, { run, nodeId: selected, onGoReview }))));
  }
  window.Studio = Object.assign(window.Studio || {}, { RunMonitor });
})();
