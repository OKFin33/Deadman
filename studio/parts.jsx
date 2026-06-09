/* global React, STUDIO_DRAMAS, STUDIO_TASTE, STUDIO_GOLD, STUDIO_MOMENTS, STUDIO_COVERAGE_LABEL, studioNegative */
const { useState: useStateP } = React;

/* ----------------------------------------------------------------- pills -- */
const STATUS_LABEL = {
  reviewed: "已评审", needs_review: "待评审", queued: "排队中", draft: "草稿",
};
function Pill({ status }) {
  return <span className={"s-pill s-pill--" + status}>{STATUS_LABEL[status] || status}</span>;
}

/* ------------------------------------------------------------------ rail -- */
function Rail({ activeId, onSelect }) {
  return (
    <aside className="studio__rail">
      <div className="s-brand">
        <div className="s-brand__mark"><img src="assets/mascot/idle.png" alt="" /></div>
        <div>
          <div className="s-brand__name">看剧搭子 Studio</div>
          <div className="s-brand__sub">生产侧 · Producer 后台</div>
        </div>
      </div>

      <div className="rail__label">创作队列 · AUTHORING QUEUE</div>
      <div className="rail__queue">
        {STUDIO_DRAMAS.map((d) => {
          const moments = STUDIO_MOMENTS.filter((m) => m.drama_id === d.drama_id);
          return (
            <div className="s-dgroup" key={d.drama_id}>
              <div className="s-dgroup__head">
                <img className="s-dgroup__cover" src={d.cover} alt="" />
                <div>
                  <div className="s-dgroup__title">{d.title}</div>
                  <div className="s-dgroup__meta">
                    {d.authored > 0 ? `${d.authored} 个已创作` : ""}
                    {d.authored > 0 && d.queued > 0 ? " · " : ""}
                    {d.queued > 0 ? `${d.queued} 个排队` : ""}
                  </div>
                </div>
              </div>
              {moments.map((m) => (
                <button
                  key={m.moment_id}
                  className={"s-moment" + (m.moment_id === activeId ? " is-active" : "")}
                  onClick={() => onSelect(m)}
                >
                  <span className="s-moment__mark">{m.notice_marker}</span>
                  <span>
                    <span className="s-moment__sig">{m.scene_signal}</span>
                    <span className="s-moment__id">{epLabel(m.episode_id)}</span>
                  </span>
                  <Pill status={m.status} />
                </button>
              ))}
              {moments.length === 0 && d.queued > 0 && (
                <button className="s-moment" disabled style={{ opacity: 0.6, cursor: "default" }}>
                  <span className="s-moment__mark" style={{ color: "var(--cream-faint)" }}>·</span>
                  <span>
                    <span className="s-moment__sig" style={{ color: "var(--cream-faint)" }}>
                      {d.queued} 个候选窗口待创作
                    </span>
                    <span className="s-moment__id">等待创作</span>
                  </span>
                  <Pill status="queued" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className="rail__foot">
        <span className="dot" />
        本地检查点 · 人工评审是发布前的必经闸门
      </div>
    </aside>
  );
}

/* --------------------------------------------------------------- stepper -- */
const STEPS = [
  { id: 0, name: "选窗口" },
  { id: 1, name: "创作" },
  { id: 2, name: "风味评审" },
  { id: 3, name: "发布" },
];
function Stepper({ step, maxStep, onGo }) {
  return (
    <div className="s-steps">
      {STEPS.map((s, i) => (
        <React.Fragment key={s.id}>
          {i > 0 && <span className="s-step-sep" />}
          <button
            className={"s-step" + (step === s.id ? " is-on" : "") + (s.id < step ? " is-done" : "")}
            disabled={s.id > maxStep}
            onClick={() => onGo(s.id)}
          >
            <span className="s-step__n">{s.id < step ? "✓" : s.id + 1}</span>
            <span>{s.name}</span>
          </button>
        </React.Fragment>
      ))}
    </div>
  );
}

/* ------------------------------------------- lint caption (per line) ------ */
function LintCaption({ result }) {
  if (!result) return null;
  if (result.kind === "pass") {
    return (
      <div className="lint lint--pass">
        <span className="lint__badge">✓</span>
        <span>{result.text || "符合风味规则"}</span>
      </div>
    );
  }
  const cls = result.kind === "hard" ? "lint--hard" : "lint--soft";
  return (
    <div className={"lint " + cls}>
      <span className="lint__badge">!</span>
      <span>{result.text}</span>
    </div>
  );
}

/* ------------------------------------------- inline named-negative card --- */
function NegCard({ id }) {
  const n = studioNegative(id);
  if (!n) return null;
  return (
    <div className="neg-card">
      <div className="neg-card__top">
        <span className="neg-card__id">{window.STUDIO_NEG_TITLE[n.id] || n.id}</span>
        <span className={"sev sev--" + n.severity}>{n.severity === "hard" ? "硬性" : "偏好"}</span>
      </div>
      <div className="neg-card__pattern">{n.pattern}</div>
    </div>
  );
}

/* ------------------------------------------------------- taste panel ------ */
function TastePanel({ hitIds = [] }) {
  const [tab, setTab] = useStateP("rules");
  const T = STUDIO_TASTE;
  return (
    <div className="panel taste">
      <div className="taste__tabs">
        <button className={"taste__tab" + (tab === "rules" ? " is-on" : "")} onClick={() => setTab("rules")}>
          规则<span className="n">{T.rules.reduce((a, g) => a + g.items.length, 0)}</span>
        </button>
        <button className={"taste__tab" + (tab === "neg" ? " is-on" : "")} onClick={() => setTab("neg")}>
          命名负例<span className="n">{T.negatives.length}</span>
        </button>
        <button className={"taste__tab" + (tab === "gold" ? " is-on" : "")} onClick={() => setTab("gold")}>
          金样<span className="n">{STUDIO_GOLD.length}</span>
        </button>
      </div>
      <div className="taste__body">
        {tab === "rules" && T.rules.map((g) => (
          <div className="rule-group" key={g.layer}>
            <div className="rule-group__h"><span className="layer-tag">{window.STUDIO_LAYER_LABEL[g.layer] || g.layer}</span>{g.title}</div>
            <ul>{g.items.map((it, i) => <li key={i}>{it}</li>)}</ul>
          </div>
        ))}
        {tab === "neg" && T.negatives.map((n) => (
          <div className={"neg-item" + (hitIds.includes(n.id) ? " is-hit" : "")} key={n.id}>
            <div className="neg-item__top">
              {hitIds.includes(n.id) && <span className="lint__badge" style={{ width: 16, height: 16, background: "rgba(255,111,77,0.18)", color: "var(--hard)" }}>!</span>}
              <span className="neg-item__id">{window.STUDIO_NEG_TITLE[n.id] || n.id}</span>
              <span className={"sev sev--" + n.severity}>{n.severity === "hard" ? "硬性" : "偏好"}</span>
              <span className="layer-tag">{window.STUDIO_LAYER_LABEL[n.layer] || n.layer}</span>
            </div>
            <div className="neg-item__pattern">{n.pattern}</div>
          </div>
        ))}
        {tab === "gold" && STUDIO_GOLD.map((g) => (
          <div className="gold-card" key={g.moment_id} style={{ marginBottom: 14 }}>
            <div className="gold-card__h">★ 金样 · {dramaShort(g.drama_id)} {epLabel(g.episode_id)}</div>
            <div className="gold-lead">{g.companion_lead}</div>
            {g.replies.map((r, i) => (
              <div className="gold-reply" key={i}>
                <div className="gold-reply__d">{r.display_text}</div>
                <div className="gold-reply__e">↳ {r.echo}</div>
              </div>
            ))}
            <div className="gold-note">{g.taste_note}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------------- Stage player preview (promote) --- */
function StagePreview({ drama, lead, replies, selectedIndex = 0 }) {
  return (
    <div>
      <div className="preview-phone">
        <div className="preview-poster"><img src={drama.cover} alt="" /></div>
        <img className="preview-mascot" src="assets/mascot/stand.png" alt="" />
        <div className="preview-bubble">
          <div className="preview-bubble__lead">{lead}</div>
          <div className="preview-bubble__opts">
            {replies.map((r, i) => (
              <div className={"preview-opt" + (i === selectedIndex ? " sel" : "")} key={i}>{r.display_text}</div>
            ))}
          </div>
          <div className="preview-bubble__echo">
            <span className="k">搭子接话</span>
            {replies[selectedIndex].echo}
          </div>
        </div>
      </div>
      <div className="preview-cap">这就是观众在 Stage 播放器里看到的样子（已选第 {selectedIndex + 1} 条）</div>
    </div>
  );
}

Object.assign(window, { Pill, Rail, Stepper, STEPS, LintCaption, NegCard, TastePanel, StagePreview });
