(() => {
  const { useState: useStateA, useEffect: useEffectA } = React;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  function Toast({ msg, onDone }) {
    useEffectA(() => {
      const t = setTimeout(onDone, 3600);
      return () => clearTimeout(t);
    }, []);
    return /* @__PURE__ */ React.createElement("div", { className: "toast" }, msg);
  }
  function RunRow({ run, active, onClick }) {
    const { StatusPill } = window.Studio;
    return /* @__PURE__ */ React.createElement("button", { className: "run-row" + (active ? " is-active" : ""), onClick }, /* @__PURE__ */ React.createElement("div", { className: "rr-top" }, /* @__PURE__ */ React.createElement("span", { className: "rr-title" }, run.drama_title), /* @__PURE__ */ React.createElement(StatusPill, { status: run.status })), /* @__PURE__ */ React.createElement("div", { className: "rr-id mono" }, run.run_id.split(":")[1]));
  }
  function App() {
    const { RunMonitor, ReviewGate, NewRun } = window.Studio;
    const [runs, setRuns] = useStateA([]);
    const [activeRun, setActiveRun] = useStateA(null);
    const [view, setView] = useStateA("monitor");
    const [toast, setToast] = useStateA(null);
    const [rev, setRev] = useStateA(0);
    const [simBusy, setSimBusy] = useStateA(false);
    const bump = () => setRev((x) => x + 1);
    useEffectA(() => {
      window.StudioAPI.listRuns().then((rs) => {
        setRuns(rs);
        setActiveRun((cur) => cur || rs[0] && rs[0].run_id);
      });
    }, [rev]);
    const active = runs.find((r) => r.run_id === activeRun);
    const waitingCount = runs.filter((r) => r.status === "waiting_for_review").length;
    const canReview = active && active.status === "waiting_for_review";
    const handleStart = async (payload) => {
      setSimBusy(true);
      const run = await window.StudioAPI.startRun(payload);
      setActiveRun(run.run_id);
      setView("monitor");
      bump();
      const order = window.StudioAPI.ingestOrder(run.run_id);
      for (const node of order) {
        await window.StudioAPI.setNode(run.run_id, node, "running");
        bump();
        await sleep(230);
        await window.StudioAPI.setNode(run.run_id, node, "pass");
        bump();
        await sleep(120);
      }
      await window.StudioAPI.gateWaiting(run.run_id);
      bump();
      setSimBusy(false);
      setToast("\u7D20\u6750\u5DF2\u5C31\u7EEA\uFF0C\u6D41\u6C34\u7EBF\u5DF2\u505C\u5728\u8BC4\u5BA1\u95F8\u95E8\uFF0C\u7B49\u5F85\u4F60\u786E\u8BA4\u3002");
    };
    const onResolved = (decision, n) => {
      setView("monitor");
      bump();
      setToast(decision === "approve" ? `\u5DF2\u6279\u51C6\u5E76\u53D1\u5E03 ${n} \u4E2A moment \xB7 \u8FD0\u884C\u901A\u8FC7\u6821\u9A8C` : "\u5DF2\u9A73\u56DE\u6574\u6B21 run\uFF08rejected_by_human_review\uFF09");
    };
    return /* @__PURE__ */ React.createElement("div", { className: "app" }, /* @__PURE__ */ React.createElement("aside", { className: "rail" }, /* @__PURE__ */ React.createElement("div", { className: "brand" }, /* @__PURE__ */ React.createElement("div", { className: "brand-mark" }, "D"), /* @__PURE__ */ React.createElement("div", { className: "brand-text" }, /* @__PURE__ */ React.createElement("div", { className: "brand-name" }, "Deadman Studio"), /* @__PURE__ */ React.createElement("div", { className: "brand-sub" }, "\u751F\u4EA7\u4FA7 \xB7 Producer"))), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "newrun-btn" + (view === "new" ? " is-active" : ""),
        onClick: () => setView("new")
      },
      /* @__PURE__ */ React.createElement("span", { className: "nr-plus" }, "\uFF0B"),
      " \u65B0\u5EFA\u8FD0\u884C"
    ), /* @__PURE__ */ React.createElement("div", { className: "nav" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "nav-btn" + (view === "monitor" ? " is-active" : ""),
        onClick: () => setView("monitor")
      },
      /* @__PURE__ */ React.createElement("span", { className: "nav-ico" }, "\u25E7"),
      " \u8FD0\u884C\u76D1\u89C6 ",
      /* @__PURE__ */ React.createElement("span", { className: "nav-en" }, "Monitor")
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "nav-btn" + (view === "review" ? " is-active" : ""),
        onClick: () => setView("review"),
        disabled: !canReview
      },
      /* @__PURE__ */ React.createElement("span", { className: "nav-ico" }, "\u2713"),
      " \u8BC4\u5BA1\u95F8\u95E8 ",
      /* @__PURE__ */ React.createElement("span", { className: "nav-en" }, "Review"),
      waitingCount > 0 && /* @__PURE__ */ React.createElement("span", { className: "nav-badge" }, waitingCount)
    )), /* @__PURE__ */ React.createElement("div", { className: "rail-label" }, "\u8FD0\u884C Runs"), /* @__PURE__ */ React.createElement("div", { className: "runs-list" }, runs.map((r) => /* @__PURE__ */ React.createElement(
      RunRow,
      {
        key: r.run_id,
        run: r,
        active: r.run_id === activeRun,
        onClick: () => {
          setActiveRun(r.run_id);
          setView(r.status === "waiting_for_review" ? "review" : "monitor");
        }
      }
    ))), /* @__PURE__ */ React.createElement("div", { className: "rail-foot" }, /* @__PURE__ */ React.createElement("div", { className: "rf-line" }, "\u672C\u5730\u68C0\u67E5\u70B9 \xB7 \u53EF\u6682\u505C / \u6062\u590D"))), /* @__PURE__ */ React.createElement("main", { className: "main" }, view === "new" && /* @__PURE__ */ React.createElement(NewRun, { onStart: handleStart, busy: simBusy }), view === "monitor" && (active ? /* @__PURE__ */ React.createElement(
      RunMonitor,
      {
        key: active.run_id,
        runId: active.run_id,
        refreshKey: rev,
        onGoReview: () => setView("review")
      }
    ) : /* @__PURE__ */ React.createElement("div", { className: "loading" }, "\u8F7D\u5165\u2026")), view === "review" && (canReview ? /* @__PURE__ */ React.createElement(ReviewGate, { key: active.run_id, runId: active.run_id, onResolved }) : active ? /* @__PURE__ */ React.createElement(RunMonitor, { key: active.run_id, runId: active.run_id, refreshKey: rev, onGoReview: () => {
    } }) : /* @__PURE__ */ React.createElement("div", { className: "loading" }, "\u8F7D\u5165\u2026"))), toast && /* @__PURE__ */ React.createElement(Toast, { msg: toast, onDone: () => setToast(null) }));
  }
  ReactDOM.createRoot(document.getElementById("root")).render(/* @__PURE__ */ React.createElement(App, null));
})();
