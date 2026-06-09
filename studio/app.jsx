/* global React, ReactDOM, Rail, Stepper, STEPS, LintCaption, NegCard, TastePanel, StagePreview,
   STUDIO_DRAMAS, STUDIO_MOMENTS, STUDIO_DEMO, STUDIO_EXCHANGES, STUDIO_COVERAGE_LABEL, studioLint, studioNegative */
const { useState, useEffect, useRef, useMemo } = React;

const CATCH_TOKENS = ["太对了", "确实", "可不是", "也是", "是啊", "可不"];
const hasCatch = (s) => CATCH_TOKENS.some((t) => s.includes(t));
const dramaOf = (m) => STUDIO_DRAMAS.find((d) => d.drama_id === m.drama_id);
const DEMO_MOMENT = STUDIO_MOMENTS.find((m) => m.isDemo);

function CovTag({ coverage }) {
  const parts = (STUDIO_COVERAGE_LABEL[coverage] || coverage).split(" · ");
  return <span className="reply__cov">{parts.map((p, k) => (k === 1 ? <b key={k}> {p}</b> : p))}</span>;
}

/* ============================ STEP 1 · WINDOW ============================== */
function WindowStep({ moment, onNext, readOnly }) {
  const drama = dramaOf(moment);
  const dur = 120;
  const w = moment.window;
  const pct = (t) => Math.min(100, Math.max(0, (t / dur) * 100));
  return (
    <div className="win-grid">
      <div className="win-film">
        <div className="win-film__poster"><img src={drama.cover} alt="" /></div>
        <span className="win-film__tag">{dramaShort(moment.drama_id)} · {epLabel(moment.episode_id)}</span>
        <div className="win-film__sig">{moment.scene_signal}</div>
        <div className="win-track">
          <div className="win-track__bar" />
          <div className="win-track__win" style={{ left: pct(w.start) + "%", width: (pct(w.end) - pct(w.start)) + "%" }} />
          <div className="win-track__notice" style={{ left: pct(w.notice_at) + "%" }}>{moment.notice_marker}</div>
          <div className="win-track__labels"><span>00:00</span><span>候选窗口 ~{w.end - w.start}s</span><span>02:00</span></div>
        </div>
      </div>

      <div className="panel win-meta">
        <div className="panel__head">
          <span className="panel__title">候选窗口</span>
          <span className="panel__en">~20s beat</span>
        </div>
        <div className="panel__body">
          <dl className="kv">
            <dt>情绪标记</dt><dd>{moment.notice_marker} · {moment.notice_marker === "!" ? "高情绪·立刻想说" : "可介入·想接一句"}</dd>
            <dt>介入窗口</dt><dd>{w.start}–{w.end}s（约 {w.end - w.start} 秒）· 触发 {w.notice_at}s</dd>
          </dl>
          <div className="win-rationale">{moment.window_rationale}</div>
          {!readOnly && (
            <button className="btn btn--primary btn--lg" onClick={onNext} style={{ marginTop: 4 }}>
              送去创作 →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================ STEP 2 · AUTHOR ============================== */
const CAB_NODES = [
  { ico: "⊹", name: "确定性召回", en: "recall" },
  { ico: "⌘", name: "语义候选", en: "semantic" },
  { ico: "✎", name: "阶段 A · 开场+三条", en: "lead+replies" },
  { ico: "❝", name: "阶段 B · 接话", en: "echo" },
  { ico: "✓", name: "自检", en: "self-check" },
];
function AuthorStep({ moment, exchange, onNext, onLive, readOnly }) {
  const [nodes, setNodes] = useState(readOnly ? CAB_NODES.length : 0);
  const [done, setDone] = useState(readOnly);
  const [live, setLive] = useState(null);    // live CAB result (null = show baked)
  const [loading, setLoading] = useState(false);
  const [liveErr, setLiveErr] = useState(null);

  useEffect(() => {
    if (readOnly) { setNodes(CAB_NODES.length); setDone(true); return; }
    setNodes(0); setDone(false); setLive(null); setLiveErr(null);
    let i = 0, t;
    const tick = () => {
      i += 1; setNodes(i);
      if (i < CAB_NODES.length) t = setTimeout(tick, 540);
      else t = setTimeout(() => setDone(true), 420);
    };
    t = setTimeout(tick, 380);
    return () => clearTimeout(t);
  }, [moment.moment_id, readOnly]);

  const runLive = async () => {
    setLoading(true); setLiveErr(null);
    try {
      const res = await fetch("/api/studio/author", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drama_id: moment.drama_id, moment_id: moment.moment_id }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error((data.error && data.error.message) || "授权失败");
      const draft = { companion_lead: data.companion_lead, replies: data.replies };
      setLive(draft);
      if (onLive) onLive(draft);  // lift to App so 发布 can publish the live-authored content
    } catch (e) {
      setLiveErr(String((e && e.message) || e));
    } finally {
      setLoading(false);
    }
  };

  const shown = live || exchange;

  return (
    <div>
      <div className="cab-graph">
        {CAB_NODES.map((n, i) => (
          <React.Fragment key={n.en}>
            {i > 0 && <span className="cab-arrow">→</span>}
            <div className={"cab-node" + (i < nodes ? " is-done" : i === nodes ? " is-running" : "")}>
              <span className="cab-node__ico">{i < nodes ? "✓" : n.ico}</span>
              <span className="cab-node__name">{n.name}</span>
            </div>
          </React.Fragment>
        ))}
      </div>

      <div className="panel">
        <div className="panel__head">
          <span className="panel__title">创作产物{live ? "（live · 实时生成）" : ""}</span>
          <span className="panel__en">{loading ? "模型生成中…" : done ? (live ? "live draft" : "草稿就绪") : "创作中…"}</span>
        </div>
        <div className="panel__body">
          {loading ? (
            <div className="authoring">
              <div className="cab-stage-label">真调 Doubao 生成中（约 20–30s）… <span className="caret" /></div>
            </div>
          ) : !done ? (
            <div className="authoring">
              <div className="cab-stage-label">正在生成<b>开场白</b>与三条候选… <span className="caret" /></div>
            </div>
          ) : (
            <ExchangeView lead={shown.companion_lead} replies={shown.replies} />
          )}
          {liveErr && (
            <div className="cab-stage-label" style={{ color: "#e07a55", marginTop: 10 }}>
              live 失败：{liveErr}（已回落预置草稿）
            </div>
          )}
        </div>
      </div>

      {done && !readOnly && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
          <button className="btn" onClick={runLive} disabled={loading} title="真调 Doubao 跑一次 CAB">
            {loading ? "生成中…" : live ? "↻ 再跑一次" : "▶ 真跑一次 CAB（live）"}
          </button>
          <button className="btn btn--primary btn--lg" onClick={onNext}>送去风味评审 →</button>
        </div>
      )}
    </div>
  );
}

/* read-only exchange (author preview + reviewed moments) ------------------- */
function ExchangeView({ lead, replies }) {
  return (
    <div className="exch">
      <div className="exch-lead">
        <div className="exch-lead__k">搭子开场</div>
        <div className="exch-lead__t">{lead}</div>
      </div>
      <div className="exch-replies">
        {replies.map((r, i) => (
          <div className="reply" key={i}>
            <div className="reply__top"><CovTag coverage={r.coverage} /></div>
            <div className="reply__display"><div className="val">{r.display_text}</div></div>
            <div className="reply__echo"><div className="val"><span className="echo-k">接话</span>{r.echo}</div></div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================ STEP 3 · REVIEW ============================== */
function ReviewStep({ moment, demo, exchange, onApprove, onToast }) {
  // editable working copy
  const init = demo ? STUDIO_DEMO.draft : null;
  const [lead, setLead] = useState(demo ? init.companion_lead.text : exchange.companion_lead);
  const [displays, setDisplays] = useState(
    demo ? init.replies.map((r) => r.display_text) : exchange.replies.map((r) => r.display_text)
  );
  const echoes = demo ? init.replies.map((r) => r.echo) : exchange.replies.map((r) => r.echo);
  const motivations = demo ? init.replies.map((r) => r.motivation) : exchange.replies.map((r) => r.motivation);
  const coverages = demo ? init.replies.map((r) => r.coverage) : exchange.replies.map((r) => r.coverage);

  // reset when moment changes
  useEffect(() => {
    setLead(demo ? init.companion_lead.text : exchange.companion_lead);
    setDisplays(demo ? init.replies.map((r) => r.display_text) : exchange.replies.map((r) => r.display_text));
  }, [moment.moment_id]);

  const leadFlag = studioLint("lead", lead);
  const displayFlags = displays.map((d) => studioLint("display", d));
  const echoFlags = echoes.map((e) => studioLint("echo", e));

  const hitIds = [leadFlag, ...displayFlags, ...echoFlags].filter(Boolean);
  const hardCount = hitIds.length; // all named-negatives here are hard
  const catchCount = echoes.filter(hasCatch).length;
  const catchSoft = catchCount === echoes.length; // 3/3 → soft preference

  const repairLead = () => setLead(STUDIO_DEMO.gold.companion_lead);
  const repairDisplay = (i) =>
    setDisplays((prev) => prev.map((d, k) => (k === i ? STUDIO_DEMO.gold.replies[i].display_text : d)));
  const repairAll = () => {
    setLead(STUDIO_DEMO.gold.companion_lead);
    setDisplays(STUDIO_DEMO.gold.replies.map((r) => r.display_text));
  };

  const leadResult = leadFlag
    ? { kind: "hard", text: "不通过 · 命中硬性负例（详见下方卡片）" }
    : { kind: "pass", text: "纯粹在场反应，不点题" };

  return (
    <div className="rev-grid">
      <div>
        <div className="exch">
          {/* lead */}
          <div className={"exch-lead" + (leadFlag ? " is-flagged" : "")}>
            <div className="exch-lead__k">搭子开场</div>
            {demo ? (
              <React.Fragment>
                <textarea className="edit-field" rows={1} value={lead} onChange={(e) => setLead(e.target.value)} />
                {(lead.length > 40 || leadFlag) && (
                  <div className="edit-row">
                    {lead.length > 40 && <span className="char-count over">{lead.length}/40</span>}
                    {leadFlag && <button className="link-btn" onClick={repairLead}>采纳金样修复 →</button>}
                  </div>
                )}
              </React.Fragment>
            ) : (
              <div className="exch-lead__t">{lead}</div>
            )}
            <LintCaption result={leadResult} />
            {leadFlag && <NegCard id={leadFlag} />}
          </div>

          {/* replies */}
          <div className="exch-replies">
            {displays.map((d, i) => {
              const flag = displayFlags[i];
              const echoFlag = echoFlags[i];
              return (
                <div className={"reply" + (flag ? " is-flagged" : demo ? " is-fixed" : "")} key={i}>
                  <div className="reply__top">
                    <CovTag coverage={coverages[i]} />
                    {d.length > 14 && <span className="char-count over mono">{d.length}/14</span>}
                  </div>
                  <div className="reply__display">
                    {demo ? (
                      <textarea className="edit-field" rows={1} value={d}
                        onChange={(e) => setDisplays((prev) => prev.map((x, k) => (k === i ? e.target.value : x)))} />
                    ) : (
                      <div className="val">{d}</div>
                    )}
                    <LintCaption result={flag
                      ? { kind: "hard", text: "不通过 · 命中硬性负例（详见下方卡片）" }
                      : { kind: "pass", text: "简单、宽泛" }} />
                    {flag && demo && (
                      <div className="edit-row"><button className="link-btn" onClick={() => repairDisplay(i)}>采纳金样修复 →</button></div>
                    )}
                  </div>
                  {flag && <NegCard id={flag} />}
                  <div className="reply__echo">
                    <div className="val"><span className="echo-k">接话</span>{echoes[i]}</div>
                    <LintCaption result={echoFlag
                      ? { kind: "hard", text: studioNegative(echoFlag).pattern }
                      : { kind: "pass", text: hasCatch(echoes[i]) ? "带「接」接住观众" : "更软的一条" }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* catch ratio meter */}
          <div className="ratio">
            <div className="ratio__bars">
              {echoes.map((e, i) => <i key={i} className={hasCatch(e) ? "on" : ""} />)}
            </div>
            <div className="ratio__txt">
              echo「接」比例 <b>{catchCount}∶{echoes.length - catchCount}</b>
              {catchSoft ? " · 建议留一条更软（soft，不阻断发布）" : " · 符合 ≈2∶1 偏好"}
            </div>
          </div>
        </div>

        {/* action bar */}
        <div className="rev-bar">
          <div className={"rev-bar__status" + (hardCount === 0 ? " ok" : "")}>
            {hardCount === 0
              ? <React.Fragment><b>0</b> 个硬性负例 · 可发布{catchSoft ? "（1 条软偏好待定）" : ""}</React.Fragment>
              : <React.Fragment><b>{hardCount}</b> 个硬性负例待修复，发布闸门关闭</React.Fragment>}
          </div>
          <div className="rev-bar__actions">
            {demo && hardCount > 0 && <button className="btn btn--ghost" onClick={repairAll}>一键采纳全部修复</button>}
            <button className="btn btn--danger" onClick={() => onToast("已驳回这条搭子互动")}>驳回</button>
            <button className="btn" onClick={() => onToast("已退回重写")}>请改</button>
            <button className="btn btn--pass" disabled={hardCount > 0} onClick={onApprove}>批准并发布 →</button>
          </div>
        </div>
      </div>

      <TastePanel hitIds={hitIds} />
    </div>
  );
}

/* ============================ STEP 4 · PROMOTE ============================= */
function PromoteStep({ moment, demo, liveDraft }) {
  const drama = dramaOf(moment);
  const gold = demo ? STUDIO_DEMO.gold : STUDIO_EXCHANGES[moment.moment_id];
  const draft = demo ? STUDIO_DEMO.draft : null;
  const publishDraft = liveDraft || gold;  // publish what was authored: live draft if run, else reviewed gold
  const [sel, setSel] = useState(0);
  const [pub, setPub] = useState(null);        // promote result {drama_id, stage_url, …}
  const [pubLoading, setPubLoading] = useState(false);
  const [pubErr, setPubErr] = useState(null);

  const publish = async () => {
    setPubLoading(true); setPubErr(null);
    try {
      const res = await fetch("/api/studio/promote", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          drama_id: moment.drama_id, moment_id: moment.moment_id,
          draft: { companion_lead: publishDraft.companion_lead, replies: publishDraft.replies },
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error((data.error && data.error.message) || "发布失败");
      setPub(data);
    } catch (e) {
      setPubErr(String((e && e.message) || e));
    } finally {
      setPubLoading(false);
    }
  };

  return (
    <div className="promote-grid">
      <div>
        <div className="promote-hero">
          <div className="promote-hero__check">✓</div>
          <div>
            <h2>已通过评审，可上线</h2>
            <p>状态 · <span style={{ color: "var(--pass)", fontWeight: 700 }}>已评审</span>。
              {pub
                ? <React.Fragment>已真写入 <b>{pub.drama_id}</b> · Stage 列表已多出这部样片，可立即播放。</React.Fragment>
                : <React.Fragment>点右侧「发布」把这条真写成 pack，Stage 即可播放。</React.Fragment>}
            </p>
          </div>
        </div>

        <div className="panel">
          <div className="panel__head">
            <span className="panel__title">{liveDraft ? "发布内容 · live 草稿" : "本轮修复 · 草稿 → 已评审"}</span>
            <span className="panel__en">{liveDraft ? "real-time CAB" : "已应用风味"}</span>
          </div>
          <div className="panel__body">
            {liveDraft ? (
              <p style={{ color: "var(--cream-dim)", fontSize: 13, margin: 0 }}>
                这条是刚刚<b>真跑 CAB</b> 实时生成、并经评审的草稿，将原样发布到 Stage。
              </p>
            ) : demo ? (
              <React.Fragment>
                <div className="diff-line">
                  <span className="diff-old">{draft.companion_lead.text}</span>
                  <span className="diff-arrow">→</span>
                  <span className="diff-new">{gold.companion_lead}</span>
                </div>
                {gold.replies.map((r, i) => {
                  const changed = draft.replies[i].display_text !== r.display_text;
                  return (
                    <div className={"diff-line" + (changed ? "" : " clean")} key={i}>
                      <span className="diff-old">{draft.replies[i].display_text}</span>
                      <span className="diff-arrow">{changed ? "→" : "="}</span>
                      <span className="diff-new">{r.display_text}</span>
                    </div>
                  );
                })}
              </React.Fragment>
            ) : (
              <p style={{ color: "var(--cream-dim)", fontSize: 13, margin: 0 }}>这条已是评审过的金样，直接服务于 Stage 播放。</p>
            )}
          </div>
        </div>
      </div>

      <div className="panel" style={{ padding: 18 }}>
        <div className="panel__title" style={{ marginBottom: 14 }}>在 Stage 播放器中</div>
        <StagePreview drama={drama} lead={publishDraft.companion_lead} replies={publishDraft.replies} selectedIndex={sel} />
        <div style={{ display: "flex", gap: 6, justifyContent: "center", marginTop: 12 }}>
          {publishDraft.replies.map((_, i) => (
            <button key={i} className={"btn" + (i === sel ? " btn--primary" : "")} style={{ minHeight: 32, padding: "0 12px", fontSize: 12 }} onClick={() => setSel(i)}>第 {i + 1} 条</button>
          ))}
        </div>

        {pub ? (
          <React.Fragment>
            <a className="btn btn--pass" href={pub.stage_url} target="_blank" rel="noopener noreferrer"
              style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", marginTop: 14, textDecoration: "none" }}>
              ▶ 在 Stage 看刚发布的这条 →
            </a>
            <p style={{ color: "var(--pass)", fontSize: 12, textAlign: "center", marginTop: 8 }}>
              ✓ 已写入 {pub.drama_id} · {pub.episode_id}（沙箱样片，不动三部 demo 剧）
            </p>
          </React.Fragment>
        ) : (
          <button className="btn btn--primary" disabled={pubLoading} onClick={publish}
            style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", marginTop: 14 }}>
            {pubLoading ? "写入 pack 中…" : "🚀 发布到 Stage（真写 pack）"}
          </button>
        )}
        {pubErr && (
          <p style={{ color: "#e07a55", fontSize: 12, textAlign: "center", marginTop: 8 }}>发布失败：{pubErr}</p>
        )}
      </div>
    </div>
  );
}

/* ===================== UPLOAD FLOW (L3/C · bring-your-own-video) ==================== */
const uplClock = (s) => `${String(Math.floor((s || 0) / 60)).padStart(2, "0")}:${String((s || 0) % 60).padStart(2, "0")}`;
const UPL_ASR = { live_volc_flash: "live ASR · 火山", sample_fallback: "示例字幕（未配 ASR 凭据）" };
const UPL_WIN = { llm_ark: "模型选窗口 · Doubao", heuristic_fallback: "启发式选窗口" };

function UploadFlow({ onToast, onExit }) {
  const [phase, setPhase] = useState("pick");   // pick | windows | author | done
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [winIdx, setWinIdx] = useState(0);
  const [win, setWin] = useState(null);
  const [draft, setDraft] = useState(null);
  const [pub, setPub] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const post = async (url, opts) => {
    const res = await fetch(url, opts);
    const data = await res.json();
    if (!res.ok || data.error) throw new Error((data.error && data.error.message) || "请求失败");
    return data;
  };
  const upload = async () => {
    if (!file) return;
    setLoading(true); setErr(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const data = await post("/api/studio/upload", { method: "POST", body: fd });
      setJob(data); setWinIdx(0); setWin({ ...data.proposed_windows[0] }); setPhase("windows");
    } catch (e) { setErr(String(e.message || e)); } finally { setLoading(false); }
  };
  const pickWindow = (i) => { setWinIdx(i); setWin({ ...job.proposed_windows[i] }); };
  const nudge = (k, d) => setWin((w) => ({ ...w, [k]: Math.max(0, (Number(w[k]) || 0) + d) }));
  const author = async () => {
    setLoading(true); setErr(null);
    try {
      const data = await post("/api/studio/upload/author", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.job_id, window: win }),
      });
      setDraft({ companion_lead: data.companion_lead, replies: data.replies }); setPhase("author");
    } catch (e) { setErr(String(e.message || e)); } finally { setLoading(false); }
  };
  const promote = async () => {
    setLoading(true); setErr(null);
    try {
      const data = await post("/api/studio/upload/promote", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.job_id, window: win, draft }),
      });
      setPub(data); setPhase("done"); if (onToast) onToast("已发布上传样片到 Stage");
    } catch (e) { setErr(String(e.message || e)); } finally { setLoading(false); }
  };

  return (
    <div className="upl">
      <div className="upl__head">
        <div className="upl__steps">
          {["上传", "选窗口·人审", "创作", "发布"].map((s, i) => (
            <span key={i} className={"upl__step" + (["pick", "windows", "author", "done"][i] === phase ? " on" : "")}>{i + 1} {s}</span>
          ))}
        </div>
        <button className="btn btn--ghost" onClick={onExit}>← 返回授权台</button>
      </div>

      {err && <div className="upl__err">出错：{err}</div>}

      {phase === "pick" && (
        <div className="panel"><div className="panel__body">
          <p className="upl__lead">上传一段短剧视频，系统会自动：抽音轨 → ASR 转写 → <b>模型挑出互动窗口</b>（可人审微调）→ CAB 授权 → 发布到 Stage。</p>
          <label className="upl__drop">
            <input type="file" accept="video/*" style={{ display: "none" }} onChange={(e) => setFile(e.target.files[0])} />
            {file ? <span>已选：<b>{file.name}</b>（{(file.size / 1e6).toFixed(1)}MB）</span> : <span>点此选择视频文件（mp4 / mov）</span>}
          </label>
          <button className="btn btn--primary btn--lg" disabled={!file || loading} onClick={upload}>
            {loading ? "分析中（抽音轨 → ASR → 选窗口）…" : "上传并分析 →"}
          </button>
          {loading && <div className="upl__hint">首次约 15–40s：ffmpeg 抽音轨、ASR 转写、模型在字幕上挑窗口。</div>}
        </div></div>
      )}

      {phase === "windows" && job && (
        <div className="upl__cols">
          <div className="panel"><div className="panel__head">
            <span className="panel__title">系统选出的候选窗口</span>
            <span className="panel__en">{UPL_WIN[job.window_source] || job.window_source} · {UPL_ASR[job.asr_source] || job.asr_source}</span>
          </div>
            <div className="panel__body">
              {job.proposed_windows.map((w, i) => (
                <div key={i} className={"upl__wcard" + (i === winIdx ? " on" : "")} onClick={() => pickWindow(i)}>
                  <div className="upl__wsig">{w.scene_signal}<span className="upl__wt">{uplClock(w.start_seconds)}–{uplClock(w.end_seconds)} · 触发 {w.notice_at_seconds}s</span></div>
                  <div className="upl__wrat">{w.rationale}</div>
                  <div className="upl__wex">{w.transcript_excerpt}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel"><div className="panel__head"><span className="panel__title">人审微调</span><span className="panel__en">系统提议 · 你可改</span></div>
            <div className="panel__body">
              {win && (
                <React.Fragment>
                  <div className="upl__sig">{win.scene_signal}</div>
                  {[["notice_at_seconds", "触发"], ["start_seconds", "起"], ["end_seconds", "止"]].map(([k, lbl]) => (
                    <div className="upl__nudge" key={k}>
                      <span className="upl__nlbl">{lbl}</span>
                      <button className="btn" onClick={() => nudge(k, -1)}>−</button>
                      <b className="upl__nval">{win[k]}s</b>
                      <button className="btn" onClick={() => nudge(k, +1)}>＋</button>
                    </div>
                  ))}
                  <div className="upl__wex" style={{ marginTop: 10 }}>{win.transcript_excerpt}</div>
                  <button className="btn btn--primary btn--lg" disabled={loading} onClick={author} style={{ marginTop: 14, width: "100%" }}>
                    {loading ? "CAB 创作中（约 30–40s）…" : "用这个窗口送去创作 →"}
                  </button>
                </React.Fragment>
              )}
            </div>
          </div>
        </div>
      )}

      {phase === "author" && draft && (
        <div className="upl__cols">
          <div className="panel"><div className="panel__head"><span className="panel__title">CAB 授权产物（live）</span><span className="panel__en">real-time · 上传窗口</span></div>
            <div className="panel__body"><ExchangeView lead={draft.companion_lead} replies={draft.replies} /></div>
          </div>
          <div className="panel"><div className="panel__body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p className="upl__lead">这条由<b>真 CAB</b> 在你上传视频的「<b>{win.scene_signal}</b>」窗口上实时生成。满意就发布——会真写一个 pack，Stage 用你上传的视频即可播放。</p>
            <button className="btn" disabled={loading} onClick={author}>{loading ? "…" : "↻ 重新创作"}</button>
            <button className="btn btn--primary btn--lg" disabled={loading} onClick={promote}>{loading ? "写入 pack 中…" : "🚀 发布到 Stage（真写 pack）"}</button>
          </div></div>
        </div>
      )}

      {phase === "done" && pub && (
        <div className="panel"><div className="panel__body" style={{ textAlign: "center" }}>
          <div className="promote-hero__check" style={{ margin: "0 auto 12px" }}>✓</div>
          <h2 style={{ margin: "0 0 6px" }}>已发布上传样片</h2>
          <p className="upl__lead" style={{ justifyContent: "center" }}>已真写入 <b>{pub.drama_id}</b>，媒体用你上传的视频。Stage 列表已多出这部样片。</p>
          <a className="btn btn--pass btn--lg" href={pub.stage_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none", marginTop: 12, display: "inline-flex" }}>▶ 在 Stage 看刚发布的这条 →</a>
          <div style={{ marginTop: 10 }}>
            <button className="btn btn--ghost" onClick={() => { setPhase("pick"); setFile(null); setJob(null); setDraft(null); setPub(null); }}>再上传一个</button>
          </div>
        </div></div>
      )}
    </div>
  );
}

/* ================================= APP ==================================== */
function StudioApp() {
  const [active, setActive] = useState(DEMO_MOMENT);
  const [step, setStep] = useState(0);
  const [maxStep, setMaxStep] = useState(0);
  const [toast, setToast] = useState(null);
  const [liveDraft, setLiveDraft] = useState(null);  // live CAB draft lifted from AuthorStep → publishable
  const [mode, setMode] = useState("moment");        // moment (curated queue) | upload (bring-your-own-video)

  const demo = !!active.isDemo;
  const exchange = useMemo(() => {
    if (demo) return STUDIO_DEMO.gold; // author/promote show gold; review handles draft internally
    const ex = STUDIO_EXCHANGES[active.moment_id];
    return { companion_lead: ex.companion_lead, replies: ex.replies };
  }, [active]);

  const select = (m) => {
    setActive(m);
    setStep(0);
    setMaxStep(m.isDemo ? 0 : 3);
    setLiveDraft(null);
  };
  const go = (s) => { if (s <= maxStep) setStep(s); };
  const advance = (s) => { setStep(s); setMaxStep((x) => Math.max(x, s)); };
  const flash = (msg) => setToast(msg);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 3200); return () => clearTimeout(t); }, [toast]);

  return (
    <div className="studio">
      <Rail activeId={active.moment_id} onSelect={select} />
      <div className="studio__main">
        <div className="s-topbar">
          <div className="s-context">
            <div className="s-context__sig">{mode === "upload" ? "上传新片 · 跑通完整链路" : active.scene_signal}</div>
            <div className="s-context__id">{mode === "upload" ? "上传视频 → ASR → 系统选窗口（人审）→ CAB → 发布" : `${dramaShort(active.drama_id)} · ${epLabel(active.episode_id)} · ${demo ? "示例创作流程" : "已评审内容"}`}</div>
          </div>
          {mode === "moment" ? (
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <Stepper step={step} maxStep={maxStep} onGo={go} />
              <button className="btn btn--primary" onClick={() => setMode("upload")}>＋ 上传新片授权</button>
            </div>
          ) : null}
        </div>
        <div className="s-stage">
          {mode === "upload" ? (
            <UploadFlow onToast={flash} onExit={() => setMode("moment")} />
          ) : (
            <React.Fragment>
              {step === 0 && <WindowStep moment={active} readOnly={!demo} onNext={() => advance(1)} />}
              {step === 1 && <AuthorStep moment={active} exchange={exchange} readOnly={!demo} onLive={setLiveDraft} onNext={() => advance(2)} />}
              {step === 2 && <ReviewStep moment={active} demo={demo} exchange={exchange}
                onApprove={() => { advance(3); flash("已批准并发布 · 状态：已评审"); }} onToast={flash} />}
              {step === 3 && <PromoteStep moment={active} demo={demo} liveDraft={liveDraft} />}
            </React.Fragment>
          )}
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<StudioApp />);
