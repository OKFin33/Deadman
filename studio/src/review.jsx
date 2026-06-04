// ---------------------------------------------------------------------------
// Deadman Studio · Review Gate view.
// Batch shortlist: reviewer keeps/rejects which candidates publish, then
// approves (resume with kept ids) or rejects the whole run.
// ---------------------------------------------------------------------------

const { useState: useStateR, useEffect: useEffectR } = React;

function CandidateCard({ c, onToggle, expanded, onExpand }) {
  const { ACTION_TYPE, SOURCE_LABEL, LLM_LABEL, GRADE, SCORE_KEYS, Chip, Score } = window.Studio;
  const src = SOURCE_LABEL[c.source];
  const judge = LLM_LABEL[c.llm_label];
  return (
    <div className={"cand" + (c.keep ? " is-kept" : " is-dropped")}>
      <label className="cand-check">
        <input type="checkbox" checked={c.keep} onChange={() => onToggle(c.id)} />
        <span className="checkbox-box"></span>
      </label>

      <div className="cand-main">
        <div className="cand-top">
          <span className="cand-ep mono">{c.episode}</span>
          <span className="cand-win mono">{c.window[0]}–{c.window[1]}s</span>
          <Chip cls={"at-" + c.action_type}>{ACTION_TYPE[c.action_type] || c.action_type}</Chip>
          <Chip cls={src.cls}>{src.t}</Chip>
          <Chip cls={judge.cls}>{judge.t}</Chip>
          <span className={"grade grade-" + c.grade}>证据 {GRADE[c.grade]}</span>
        </div>

        <div className="cand-hook">{c.hook}</div>
        <div className="cand-impulse">{c.impulse}</div>

        {c.failure_mode && <div className="cand-failmode">⚠ {c.failure_mode}</div>}

        <div className="cand-foot">
          <div className="cand-scores">
            {SCORE_KEYS.map(([k, lbl]) => <Score key={k} label={lbl} value={c.scores[k]} />)}
          </div>
          <button className="cand-expand" onClick={() => onExpand(c.id)}>
            {expanded ? "收起证据 ▲" : "查看证据与选项 ▼"}
          </button>
        </div>

        {expanded && (
          <div className="cand-detail">
            <div className="cd-k">预设选项 default_options</div>
            <ol className="cd-options">
              {c.options.map((o, i) => <li key={i}>{o}</li>)}
            </ol>
            <div className="cd-k">源窗口摘录 evidence excerpt</div>
            <div className="cd-excerpt">{c.excerpt}</div>
            <div className="cd-k">评审备注 reviewer note</div>
            <div className="cd-note">{c.note}</div>
          </div>
        )}
      </div>
    </div>
  );
}

const FILTERS = [
  { id: "all", label: "全部" },
  { id: "recommend", label: "推荐" },
  { id: "keep_for_review", label: "待定" },
  { id: "kept", label: "已保留" },
  { id: "dropped", label: "已驳回" },
];

function ReviewGate({ runId, onResolved }) {
  const { StatusPill } = window.Studio;
  const [review, setReview] = useStateR(null);
  const [cands, setCands] = useStateR([]);
  const [filter, setFilter] = useStateR("all");
  const [expanded, setExpanded] = useStateR(null);
  const [note, setNote] = useStateR("");
  const [busy, setBusy] = useStateR(false);
  const [confirmReject, setConfirmReject] = useStateR(false);

  useEffectR(() => {
    let alive = true;
    window.StudioAPI.getReview(runId).then((r) => {
      if (!alive) return;
      setReview(r);
      setCands(r ? r.candidates : []);
    });
    return () => { alive = false; };
  }, [runId]);

  if (!review) {
    return (
      <div className="review-none">
        <div className="review-none-card">
          <div className="rn-title">该运行当前没有待评审请求</div>
          <div className="rn-sub">只有停在 <code>human_review_gate</code>（status = waiting_for_review）的运行才会出现评审清单。</div>
        </div>
      </div>
    );
  }

  const toggle = (id) => setCands((cs) => cs.map((c) => c.id === id ? { ...c, keep: !c.keep } : c));
  const setAll = (val, ids) => setCands((cs) => cs.map((c) =>
    (!ids || ids.includes(c.id)) ? { ...c, keep: val } : c));

  const keptIds = cands.filter((c) => c.keep).map((c) => c.id);
  const recIds = cands.filter((c) => c.llm_label === "recommend").map((c) => c.id);

  const shown = cands.filter((c) => {
    if (filter === "all") return true;
    if (filter === "kept") return c.keep;
    if (filter === "dropped") return !c.keep;
    return c.llm_label === filter;
  });

  const doApprove = async () => {
    setBusy(true);
    await window.StudioAPI.resume(runId, "approve", keptIds, note);
    const seq = window.StudioAPI.publishSequence(runId);
    for (let i = 0; i < seq.length; i++) {
      await window.StudioAPI.advancePublish(runId, seq[i], i === seq.length - 1);
    }
    setBusy(false);
    onResolved("approve", keptIds.length);
  };

  const doReject = async () => {
    setBusy(true);
    await window.StudioAPI.resume(runId, "reject", [], note);
    setBusy(false);
    onResolved("reject", 0);
  };

  return (
    <div className="review">
      <div className="review-head">
        <div>
          <div className="run-title-row">
            <h2 className="run-title">{review.drama_title}</h2>
            <StatusPill status="waiting_for_review" size="lg" />
          </div>
          <div className="run-id mono">{review.run_id}</div>
        </div>
        <div className="review-counts">
          <span className="meta-item">确定性召回 <b>{review.input_candidate_count}</b></span>
          <span className="meta-item">LLM shortlist <b>{cands.length}</b></span>
          <span className="meta-item">推荐 <b>{recIds.length}</b></span>
          <span className="meta-item">建议数 <b>{review.shortlist_target}</b></span>
        </div>
      </div>

      <div className="review-instructions">
        {review.human_instructions.map((t, i) => <div key={i} className="ri-item">{i + 1}. {t}</div>)}
      </div>

      <div className="review-toolbar">
        <div className="filters">
          {FILTERS.map((f) => (
            <button key={f.id}
              className={"filter" + (filter === f.id ? " is-active" : "")}
              onClick={() => setFilter(f.id)}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="bulk">
          <button className="link-btn" onClick={() => setAll(true, recIds)}>保留全部推荐</button>
          <button className="link-btn" onClick={() => setAll(true)}>全选</button>
          <button className="link-btn" onClick={() => setAll(false)}>清空</button>
        </div>
      </div>

      <div className="cand-list">
        {shown.map((c) => (
          <CandidateCard key={c.id} c={c} onToggle={toggle}
            expanded={expanded === c.id}
            onExpand={(id) => setExpanded(expanded === id ? null : id)} />
        ))}
        {shown.length === 0 && <div className="cand-empty">该筛选下没有候选。</div>}
      </div>

      <div className="review-bar">
        <div className="rb-left">
          <span className="rb-count"><b>{keptIds.length}</b> / {cands.length} 项将发布</span>
          <input className="rb-note" placeholder="评审备注（reviewer_note，可选）"
            value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="rb-actions">
          {confirmReject ? (
            <React.Fragment>
              <span className="rb-confirm">驳回将终结此 run，需新建 run_id 重来。</span>
              <button className="btn btn-ghost" disabled={busy} onClick={() => setConfirmReject(false)}>取消</button>
              <button className="btn btn-danger" disabled={busy} onClick={doReject}>确认驳回整次 run</button>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <button className="btn btn-ghost" disabled={busy} onClick={() => setConfirmReject(true)}>驳回整次 run</button>
              <button className="btn btn-primary" disabled={busy || keptIds.length === 0} onClick={doApprove}>
                {busy ? "发布中…" : "批准并发布保留项 →"}
              </button>
            </React.Fragment>
          )}
        </div>
      </div>
    </div>
  );
}

window.Studio = Object.assign(window.Studio || {}, { ReviewGate });
