// ---------------------------------------------------------------------------
// Deadman Studio · Run Monitor view.
// Pipeline graph (phase-grouped rounded nodes) + a clean node detail panel.
// Shell commands / failure codes live behind an optional "技术细节" disclosure.
// ---------------------------------------------------------------------------

const { useState, useEffect, useRef } = React;

// Map a raw artifact path -> a human-friendly producer label. Returns null for
// non-file lines (state notes, prose) so they don't show as artifacts.
function friendlyArtifact(path) {
  const p = path;
  if (/manifest\.status|validation_result|manifest\.validation/.test(p)) return null;
  if (/[\u4e00-\u9fa5]/.test(p) && !/\.json|\.md/.test(p)) return null;
  if (p.includes("media_index")) return "媒体索引";
  if (p.includes("media_registry")) return "媒体注册表";
  if (p.includes("_windows")) return "时间窗";
  if (p.includes("_candidates.v0.1") || /candidates\.v0\.1\.(json|md)/.test(p)) return "候选表";
  if (p.includes("mechanism_buckets")) return "机制分组";
  if (p.includes("field_hypotheses")) return "场压假设";
  if (p.includes("llm_semantic_candidates")) return "语义候选";
  if (p.includes("llm_candidate_judgment")) return "LLM 初筛结果";
  if (p.includes("llm_drama_context_draft")) return "上下文草稿";
  if (p.includes("llm_moment_pack_drafts")) return "Moment 草稿";
  if (p.includes("review_request")) return "评审请求";
  if (p.includes("reviewed_demo_nodes")) return "已评审节点";
  if (p.includes("reviewed_candidates")) return "已评审候选";
  if (p.includes("drama_context")) return "剧目上下文";
  if (p.includes("validation_report") || p.includes("producer_bridge_validation")) return "校验报告";
  if (p.includes("final_report")) return "最终报告";
  if (p.includes("manifest")) return "运行清单";
  if (p.includes("context.v0.1")) return "上下文包";
  if (p.includes("moments.v0.1")) return "Moment 包";
  if (p.includes("evidence")) return "证据";
  if (p.includes("promoted")) return "已发布到剧目目录";
  return null;
}

function NodeCard({ node, status, selected, isCurrent, onClick }) {
  const { STATUS } = window.Studio;
  const tone = (STATUS[status] || {}).tone || "muted";
  return (
    <button
      className={"node-card tone-" + tone +
        (selected ? " is-selected" : "") +
        (isCurrent ? " is-current" : "") +
        (node.gate ? " is-gate" : "") +
        (node.llm ? " is-llm" : "")}
      onClick={onClick}
    >
      <span className={"node-dot tone-" + tone + (status === "running" ? " pulse" : "")}></span>
      <span className="node-body">
        <span className="node-zh">{node.zh}{node.gate ? " ⏸" : ""}</span>
        <span className="node-en">{node.id}</span>
      </span>
      {node.llm && <span className="node-tag">LLM</span>}
    </button>
  );
}

function Pipeline({ run, selected, onSelect }) {
  const { NODE_CATALOG, PHASES } = window.DeadmanData;
  return (
    <div className="pipeline">
      {PHASES.map((phase) => {
        const nodes = NODE_CATALOG.filter((n) => n.phase === phase);
        return (
          <div className="phase" key={phase}>
            <div className="phase-label">{phase}</div>
            <div className="phase-nodes">
              {nodes.map((n) => {
                const st = run.node_statuses[n.id] || "planned";
                if (st === "skipped_by_config") return null;
                return (
                  <NodeCard key={n.id} node={n} status={st}
                    selected={selected === n.id}
                    isCurrent={run.current_node === n.id && run.status !== "pass"}
                    onClick={() => onSelect(n.id)} />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function NodeDetail({ run, nodeId, onGoReview }) {
  const { NODE_CATALOG } = window.DeadmanData;
  const { StatusPill } = window.Studio;
  const [showTech, setShowTech] = useState(false);
  const node = NODE_CATALOG.find((n) => n.id === nodeId);
  useEffect(() => { setShowTech(false); }, [nodeId]);
  if (!node) return <div className="detail-empty">选择左侧任一节点查看详情</div>;
  const status = run.node_statuses[nodeId] || "planned";
  const err = (run.errors || []).find((e) => e.node === nodeId);

  const fill = (s) => s
    .replaceAll("{drama_id}", run.drama_id)
    .replaceAll("{drama_title}", '"' + run.drama_title + '"')
    .replaceAll("{run_id}", run.run_id)
    .replaceAll("{run_dir}", "tmp/deadman_producer_runs/" + run.run_id)
    .replaceAll("{analysis_dir}", "tmp/ars_" + run.drama_id + "_analysis")
    .replaceAll("{drama_dir}", "data/dramas/" + run.drama_id)
    .replaceAll("{video_dir}", "tmp/视频素材/" + run.drama_id)
    .replaceAll("{episode_ids}", "…")
    .replaceAll("{recall_budget}", run.recall_budget);

  const artifacts = [...new Set(node.outputs.map((o) => friendlyArtifact(fill(o))).filter(Boolean))];

  return (
    <div className="detail">
      <div className="detail-head">
        <div>
          <div className="detail-zh">{node.zh}{node.gate ? " ⏸" : ""}</div>
          <div className="detail-en">{node.id}</div>
        </div>
        <StatusPill status={status} />
      </div>

      <div className="detail-purpose">{node.purpose}</div>

      <div className="detail-row">
        <span className="detail-k">职责</span>
        <span className="detail-authority">{node.authority}</span>
      </div>

      {node.gate && status === "waiting_for_review" && (
        <button className="btn btn-primary detail-cta" onClick={onGoReview}>
          前往评审闸门 →
        </button>
      )}

      {err && (
        <div className="detail-error">
          <div className="err-code">校验失败</div>
          <div className="err-msg">{err.message}</div>
        </div>
      )}

      {artifacts.length > 0 && (
        <React.Fragment>
          <div className="detail-k mt">产物</div>
          <div className="artifact-list">
            {artifacts.map((a) => (
              <span className="artifact" key={a}><span className="artifact-ico">▤</span>{a}</span>
            ))}
          </div>
        </React.Fragment>
      )}

      <button className="tech-toggle" onClick={() => setShowTech((v) => !v)}>
        {showTech ? "隐藏技术细节 ▲" : "技术细节（命令 / 失败码）▾"}
      </button>
      {showTech && (
        <div className="tech-body">
          <div className="detail-k">子命令</div>
          <pre className="codeblock">{fill(node.cmd)}</pre>
          <div className="detail-k mt">失败码</div>
          <div className="fail-codes">
            {node.fails.map((f) => <code key={f}>{f}</code>)}
          </div>
          {err && err.artifact_refs && (
            <React.Fragment>
              <div className="detail-k mt">受影响文件</div>
              {err.artifact_refs.map((a) => <div className="err-ref" key={a}>{a}</div>)}
            </React.Fragment>
          )}
        </div>
      )}
    </div>
  );
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
    if (initial) { setRun(null); setReport(null); }
    window.StudioAPI.getRun(runId).then((r) => {
      if (!alive) return;
      setRun(r);
      if (initial && r) { setSelected(r.current_node || "prepare_assets"); lastRunId.current = runId; }
    });
    window.StudioAPI.getReport(runId).then((rep) => { if (alive) setReport(rep); });
    return () => { alive = false; };
  }, [runId, refreshKey]);

  if (!run) return <div className="loading">载入运行…</div>;

  const passCount = Object.values(run.node_statuses).filter((s) => s === "pass").length;
  const totalNodes = Object.values(run.node_statuses).filter((s) => s !== "skipped_by_config").length;

  return (
    <div className="monitor">
      <div className="run-head">
        <div className="run-head-main">
          <div className="run-title-row">
            <h2 className="run-title">{run.drama_title}</h2>
            <StatusPill status={run.status} size="lg" />
          </div>
          <div className="run-id mono">{run.run_id}</div>
        </div>
        <div className="run-meta">
          <Chip cls={run.graph_mode === "llm" ? "mode-llm" : "mode-base"}>
            {run.graph_mode === "llm" ? "LLM 增强" : "基础流水线"}
          </Chip>
          <span className="meta-item"><b>{passCount}</b>/{totalNodes} 步完成</span>
          {run.episodes && <span className="meta-item"><b>{run.episodes.length}</b> 集素材</span>}
          {run.published_moments != null && (
            <span className="meta-item">发布 <b>{run.published_moments}</b> moments</span>
          )}
          <span className="meta-item dim">更新 {run.updated_at}</span>
        </div>
      </div>

      <div className="monitor-body">
        <div className="monitor-left">
          <Pipeline run={run} selected={selected} onSelect={setSelected} />
          {report && (
            <div className="report-card">
              <div className="report-head">最终报告 · final_report</div>
              <pre className="report-body">{report}</pre>
            </div>
          )}
        </div>
        <div className="monitor-right">
          <NodeDetail run={run} nodeId={selected} onGoReview={onGoReview} />
        </div>
      </div>
    </div>
  );
}

window.Studio = Object.assign(window.Studio || {}, { RunMonitor });
