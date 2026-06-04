(() => {
  const { useState: useStateR, useEffect: useEffectR } = React;
  function CandidateCard({ c, onToggle, expanded, onExpand }) {
    const { ACTION_TYPE, SOURCE_LABEL, LLM_LABEL, GRADE, SCORE_KEYS, Chip, Score } = window.Studio;
    const src = SOURCE_LABEL[c.source];
    const judge = LLM_LABEL[c.llm_label];
    return /* @__PURE__ */ React.createElement("div", { className: "cand" + (c.keep ? " is-kept" : " is-dropped") }, /* @__PURE__ */ React.createElement("label", { className: "cand-check" }, /* @__PURE__ */ React.createElement("input", { type: "checkbox", checked: c.keep, onChange: () => onToggle(c.id) }), /* @__PURE__ */ React.createElement("span", { className: "checkbox-box" })), /* @__PURE__ */ React.createElement("div", { className: "cand-main" }, /* @__PURE__ */ React.createElement("div", { className: "cand-top" }, /* @__PURE__ */ React.createElement("span", { className: "cand-ep mono" }, c.episode), /* @__PURE__ */ React.createElement("span", { className: "cand-win mono" }, c.window[0], "\u2013", c.window[1], "s"), /* @__PURE__ */ React.createElement(Chip, { cls: "at-" + c.action_type }, ACTION_TYPE[c.action_type] || c.action_type), /* @__PURE__ */ React.createElement(Chip, { cls: src.cls }, src.t), /* @__PURE__ */ React.createElement(Chip, { cls: judge.cls }, judge.t), /* @__PURE__ */ React.createElement("span", { className: "grade grade-" + c.grade }, "\u8BC1\u636E ", GRADE[c.grade])), /* @__PURE__ */ React.createElement("div", { className: "cand-hook" }, c.hook), /* @__PURE__ */ React.createElement("div", { className: "cand-impulse" }, c.impulse), c.failure_mode && /* @__PURE__ */ React.createElement("div", { className: "cand-failmode" }, "\u26A0 ", c.failure_mode), /* @__PURE__ */ React.createElement("div", { className: "cand-foot" }, /* @__PURE__ */ React.createElement("div", { className: "cand-scores" }, SCORE_KEYS.map(([k, lbl]) => /* @__PURE__ */ React.createElement(Score, { key: k, label: lbl, value: c.scores[k] }))), /* @__PURE__ */ React.createElement("button", { className: "cand-expand", onClick: () => onExpand(c.id) }, expanded ? "\u6536\u8D77\u8BC1\u636E \u25B2" : "\u67E5\u770B\u8BC1\u636E\u4E0E\u9009\u9879 \u25BC")), expanded && /* @__PURE__ */ React.createElement("div", { className: "cand-detail" }, /* @__PURE__ */ React.createElement("div", { className: "cd-k" }, "\u9884\u8BBE\u9009\u9879 default_options"), /* @__PURE__ */ React.createElement("ol", { className: "cd-options" }, c.options.map((o, i) => /* @__PURE__ */ React.createElement("li", { key: i }, o))), /* @__PURE__ */ React.createElement("div", { className: "cd-k" }, "\u6E90\u7A97\u53E3\u6458\u5F55 evidence excerpt"), /* @__PURE__ */ React.createElement("div", { className: "cd-excerpt" }, c.excerpt), /* @__PURE__ */ React.createElement("div", { className: "cd-k" }, "\u8BC4\u5BA1\u5907\u6CE8 reviewer note"), /* @__PURE__ */ React.createElement("div", { className: "cd-note" }, c.note))));
  }
  const FILTERS = [
    { id: "all", label: "\u5168\u90E8" },
    { id: "recommend", label: "\u63A8\u8350" },
    { id: "keep_for_review", label: "\u5F85\u5B9A" },
    { id: "kept", label: "\u5DF2\u4FDD\u7559" },
    { id: "dropped", label: "\u5DF2\u9A73\u56DE" }
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
      return () => {
        alive = false;
      };
    }, [runId]);
    if (!review) {
      return /* @__PURE__ */ React.createElement("div", { className: "review-none" }, /* @__PURE__ */ React.createElement("div", { className: "review-none-card" }, /* @__PURE__ */ React.createElement("div", { className: "rn-title" }, "\u8BE5\u8FD0\u884C\u5F53\u524D\u6CA1\u6709\u5F85\u8BC4\u5BA1\u8BF7\u6C42"), /* @__PURE__ */ React.createElement("div", { className: "rn-sub" }, "\u53EA\u6709\u505C\u5728 ", /* @__PURE__ */ React.createElement("code", null, "human_review_gate"), "\uFF08status = waiting_for_review\uFF09\u7684\u8FD0\u884C\u624D\u4F1A\u51FA\u73B0\u8BC4\u5BA1\u6E05\u5355\u3002")));
    }
    const toggle = (id) => setCands((cs) => cs.map((c) => c.id === id ? { ...c, keep: !c.keep } : c));
    const setAll = (val, ids) => setCands((cs) => cs.map((c) => !ids || ids.includes(c.id) ? { ...c, keep: val } : c));
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
    return /* @__PURE__ */ React.createElement("div", { className: "review" }, /* @__PURE__ */ React.createElement("div", { className: "review-head" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "run-title-row" }, /* @__PURE__ */ React.createElement("h2", { className: "run-title" }, review.drama_title), /* @__PURE__ */ React.createElement(StatusPill, { status: "waiting_for_review", size: "lg" })), /* @__PURE__ */ React.createElement("div", { className: "run-id mono" }, review.run_id)), /* @__PURE__ */ React.createElement("div", { className: "review-counts" }, /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, "\u786E\u5B9A\u6027\u53EC\u56DE ", /* @__PURE__ */ React.createElement("b", null, review.input_candidate_count)), /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, "LLM shortlist ", /* @__PURE__ */ React.createElement("b", null, cands.length)), /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, "\u63A8\u8350 ", /* @__PURE__ */ React.createElement("b", null, recIds.length)), /* @__PURE__ */ React.createElement("span", { className: "meta-item" }, "\u5EFA\u8BAE\u6570 ", /* @__PURE__ */ React.createElement("b", null, review.shortlist_target)))), /* @__PURE__ */ React.createElement("div", { className: "review-instructions" }, review.human_instructions.map((t, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "ri-item" }, i + 1, ". ", t))), /* @__PURE__ */ React.createElement("div", { className: "review-toolbar" }, /* @__PURE__ */ React.createElement("div", { className: "filters" }, FILTERS.map((f) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: f.id,
        className: "filter" + (filter === f.id ? " is-active" : ""),
        onClick: () => setFilter(f.id)
      },
      f.label
    ))), /* @__PURE__ */ React.createElement("div", { className: "bulk" }, /* @__PURE__ */ React.createElement("button", { className: "link-btn", onClick: () => setAll(true, recIds) }, "\u4FDD\u7559\u5168\u90E8\u63A8\u8350"), /* @__PURE__ */ React.createElement("button", { className: "link-btn", onClick: () => setAll(true) }, "\u5168\u9009"), /* @__PURE__ */ React.createElement("button", { className: "link-btn", onClick: () => setAll(false) }, "\u6E05\u7A7A"))), /* @__PURE__ */ React.createElement("div", { className: "cand-list" }, shown.map((c) => /* @__PURE__ */ React.createElement(
      CandidateCard,
      {
        key: c.id,
        c,
        onToggle: toggle,
        expanded: expanded === c.id,
        onExpand: (id) => setExpanded(expanded === id ? null : id)
      }
    )), shown.length === 0 && /* @__PURE__ */ React.createElement("div", { className: "cand-empty" }, "\u8BE5\u7B5B\u9009\u4E0B\u6CA1\u6709\u5019\u9009\u3002")), /* @__PURE__ */ React.createElement("div", { className: "review-bar" }, /* @__PURE__ */ React.createElement("div", { className: "rb-left" }, /* @__PURE__ */ React.createElement("span", { className: "rb-count" }, /* @__PURE__ */ React.createElement("b", null, keptIds.length), " / ", cands.length, " \u9879\u5C06\u53D1\u5E03"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "rb-note",
        placeholder: "\u8BC4\u5BA1\u5907\u6CE8\uFF08reviewer_note\uFF0C\u53EF\u9009\uFF09",
        value: note,
        onChange: (e) => setNote(e.target.value)
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "rb-actions" }, confirmReject ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("span", { className: "rb-confirm" }, "\u9A73\u56DE\u5C06\u7EC8\u7ED3\u6B64 run\uFF0C\u9700\u65B0\u5EFA run_id \u91CD\u6765\u3002"), /* @__PURE__ */ React.createElement("button", { className: "btn btn-ghost", disabled: busy, onClick: () => setConfirmReject(false) }, "\u53D6\u6D88"), /* @__PURE__ */ React.createElement("button", { className: "btn btn-danger", disabled: busy, onClick: doReject }, "\u786E\u8BA4\u9A73\u56DE\u6574\u6B21 run")) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("button", { className: "btn btn-ghost", disabled: busy, onClick: () => setConfirmReject(true) }, "\u9A73\u56DE\u6574\u6B21 run"), /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary", disabled: busy || keptIds.length === 0, onClick: doApprove }, busy ? "\u53D1\u5E03\u4E2D\u2026" : "\u6279\u51C6\u5E76\u53D1\u5E03\u4FDD\u7559\u9879 \u2192")))));
  }
  window.Studio = Object.assign(window.Studio || {}, { ReviewGate });
})();
