// ---------------------------------------------------------------------------
// Deadman Studio · app shell. Rail = new-run + nav + runs list; main routes
// between New Run, Run Monitor, and Review Gate.
// ---------------------------------------------------------------------------

const { useState: useStateA, useEffect: useEffectA } = React;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function Toast({ msg, onDone }) {
  useEffectA(() => { const t = setTimeout(onDone, 3600); return () => clearTimeout(t); }, []);
  return <div className="toast">{msg}</div>;
}

function RunRow({ run, active, onClick }) {
  const { StatusPill } = window.Studio;
  return (
    <button className={"run-row" + (active ? " is-active" : "")} onClick={onClick}>
      <div className="rr-top">
        <span className="rr-title">{run.drama_title}</span>
        <StatusPill status={run.status} />
      </div>
      <div className="rr-id mono">{run.run_id.split(":")[1]}</div>
    </button>
  );
}

function App() {
  const { RunMonitor, ReviewGate, NewRun } = window.Studio;
  const [runs, setRuns] = useStateA([]);
  const [activeRun, setActiveRun] = useStateA(null);
  const [view, setView] = useStateA("monitor"); // new | monitor | review
  const [toast, setToast] = useStateA(null);
  const [rev, setRev] = useStateA(0);          // refresh runs list + monitor
  const [simBusy, setSimBusy] = useStateA(false);

  const bump = () => setRev((x) => x + 1);

  useEffectA(() => {
    window.StudioAPI.listRuns().then((rs) => {
      setRuns(rs);
      setActiveRun((cur) => cur || (rs[0] && rs[0].run_id));
    });
  }, [rev]);

  const active = runs.find((r) => r.run_id === activeRun);
  const waitingCount = runs.filter((r) => r.status === "waiting_for_review").length;
  const canReview = active && active.status === "waiting_for_review";

  // Create + animate a run through ingest/mining up to the review gate.
  const handleStart = async (payload) => {
    setSimBusy(true);
    const run = await window.StudioAPI.startRun(payload);
    setActiveRun(run.run_id);
    setView("monitor");
    bump();
    const order = window.StudioAPI.ingestOrder(run.run_id);
    for (const node of order) {
      await window.StudioAPI.setNode(run.run_id, node, "running"); bump(); await sleep(230);
      await window.StudioAPI.setNode(run.run_id, node, "pass"); bump(); await sleep(120);
    }
    await window.StudioAPI.gateWaiting(run.run_id); bump();
    setSimBusy(false);
    setToast("素材已就绪，流水线已停在评审闸门，等待你确认。");
  };

  const onResolved = (decision, n) => {
    setView("monitor");
    bump();
    setToast(decision === "approve"
      ? `已批准并发布 ${n} 个 moment · 运行通过校验`
      : "已驳回整次 run（rejected_by_human_review）");
  };

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark">D</div>
          <div className="brand-text">
            <div className="brand-name">Deadman Studio</div>
            <div className="brand-sub">生产侧 · Producer</div>
          </div>
        </div>

        <button className={"newrun-btn" + (view === "new" ? " is-active" : "")}
          onClick={() => setView("new")}>
          <span className="nr-plus">＋</span> 新建运行
        </button>

        <div className="nav">
          <button className={"nav-btn" + (view === "monitor" ? " is-active" : "")}
            onClick={() => setView("monitor")}>
            <span className="nav-ico">◧</span> 运行监视 <span className="nav-en">Monitor</span>
          </button>
          <button className={"nav-btn" + (view === "review" ? " is-active" : "")}
            onClick={() => setView("review")} disabled={!canReview}>
            <span className="nav-ico">✓</span> 评审闸门 <span className="nav-en">Review</span>
            {waitingCount > 0 && <span className="nav-badge">{waitingCount}</span>}
          </button>
        </div>

        <div className="rail-label">运行 Runs</div>
        <div className="runs-list">
          {runs.map((r) => (
            <RunRow key={r.run_id} run={r} active={r.run_id === activeRun}
              onClick={() => {
                setActiveRun(r.run_id);
                setView(r.status === "waiting_for_review" ? "review" : "monitor");
              }} />
          ))}
        </div>

        <div className="rail-foot">
          <div className="rf-line">本地检查点 · 可暂停 / 恢复</div>
        </div>
      </aside>

      <main className="main">
        {view === "new" && <NewRun onStart={handleStart} busy={simBusy} />}

        {view === "monitor" && (active
          ? <RunMonitor key={active.run_id} runId={active.run_id} refreshKey={rev}
              onGoReview={() => setView("review")} />
          : <div className="loading">载入…</div>)}

        {view === "review" && (canReview
          ? <ReviewGate key={active.run_id} runId={active.run_id} onResolved={onResolved} />
          : active
            ? <RunMonitor key={active.run_id} runId={active.run_id} refreshKey={rev} onGoReview={() => {}} />
            : <div className="loading">载入…</div>)}
      </main>

      {toast && <Toast msg={toast} onDone={() => setToast(null)} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
