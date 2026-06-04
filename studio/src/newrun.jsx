// ---------------------------------------------------------------------------
// Deadman Studio · New Run view. The GUI ingest entry: name the drama, drop
// MP4 episodes, pick the graph mode, and start the producer run.
// ---------------------------------------------------------------------------

const { useState: useStateN, useRef: useRefN } = React;

function slugify(s) {
  return (s || "").trim().toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 24) || "";
}
const fmtMB = (bytes) => (bytes / 1e6).toFixed(1) + " MB";

function NewRun({ onStart, busy }) {
  const [title, setTitle] = useStateN("");
  const [dramaId, setDramaId] = useStateN("");
  const [idTouched, setIdTouched] = useStateN(false);
  const [episodes, setEpisodes] = useStateN([]); // {key,name,size,epId}
  const [mode, setMode] = useStateN("llm");
  const [drag, setDrag] = useStateN(false);
  const inputRef = useRefN(null);

  const effId = dramaId || slugify(title) || "drama";

  const renumber = (list) => list.map((e, i) => ({ ...e, epId: `${effId}_ep${String(i + 1).padStart(2, "0")}` }));

  const addFiles = (fileList) => {
    const vids = Array.from(fileList).filter((f) => /\.(mp4|mov|m4v|mkv)$/i.test(f.name) || f.type.startsWith("video"));
    const next = vids.map((f, i) => ({ key: f.name + f.size + Math.random(), name: f.name, size: f.size }));
    setEpisodes((cur) => renumber([...cur, ...next]));
  };

  const onDrop = (e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files) addFiles(e.dataTransfer.files); };
  const removeEp = (key) => setEpisodes((cur) => renumber(cur.filter((e) => e.key !== key)));

  const recall = Math.max(20, Math.min(400, Math.round(episodes.length * 4)));
  const canStart = title.trim() && episodes.length > 0 && !busy;

  const start = () => {
    if (!canStart) return;
    onStart({
      dramaId: effId, dramaTitle: title.trim(), mode,
      episodes: renumber(episodes).map((e) => ({ epId: e.epId, name: e.name, sizeMB: +(e.size / 1e6).toFixed(1) })),
    });
  };

  return (
    <div className="newrun">
      <div className="nr-head">
        <h2 className="run-title">新建运行</h2>
        <div className="nr-sub">上传短剧素材，启动生产流水线 · New producer run</div>
      </div>

      <div className="nr-card">
        <div className="nr-card-title">剧目 Drama</div>
        <div className="nr-fields">
          <label className="field">
            <span className="field-k">剧目名称</span>
            <input className="field-in" placeholder="如：荒年全村啃树皮，我有系统满仓肉"
              value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="field field-narrow">
            <span className="field-k">剧目 ID</span>
            <input className="field-in mono" placeholder={slugify(title) || "drama"}
              value={idTouched ? dramaId : (dramaId || slugify(title))}
              onChange={(e) => { setIdTouched(true); setDramaId(slugify(e.target.value)); }} />
          </label>
        </div>
      </div>

      <div className="nr-card">
        <div className="nr-card-title">剧集素材 Episodes
          {episodes.length > 0 && <span className="nr-count">{episodes.length} 集</span>}
        </div>

        <div className={"dropzone" + (drag ? " is-drag" : "")}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current && inputRef.current.click()}>
          <div className="dz-ico">⤓</div>
          <div className="dz-main">拖入 MP4 文件，或点击选择</div>
          <div className="dz-sub">支持 .mp4 / .mov / .m4v · 视频仅暂存在本地制作环境，不写入 runtime 包</div>
          <input ref={inputRef} type="file" accept="video/*,.mp4,.mov,.m4v" multiple
            style={{ display: "none" }} onChange={(e) => addFiles(e.target.files)} />
        </div>

        {episodes.length > 0 && (
          <div className="ep-list">
            {renumber(episodes).map((e) => (
              <div className="ep-row" key={e.key}>
                <span className="ep-id mono">{e.epId}</span>
                <span className="ep-name">{e.name}</span>
                <span className="ep-size mono">{fmtMB(e.size)}</span>
                <button className="ep-x" onClick={() => removeEp(e.key)} title="移除">✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="nr-card">
        <div className="nr-card-title">流水线选项 Pipeline</div>
        <div className="nr-options">
          <div className="opt">
            <span className="field-k">图模式 graph_mode</span>
            <div className="segmented">
              <button className={"seg" + (mode === "base" ? " is-on" : "")} onClick={() => setMode("base")}>
                基础 base
              </button>
              <button className={"seg" + (mode === "llm" ? " is-on" : "")} onClick={() => setMode("llm")}>
                LLM 增强
              </button>
            </div>
            <span className="opt-hint">
              {mode === "llm"
                ? "确定性召回 + LLM 语义挖掘与初筛，shortlist 更贴近观众情绪点。"
                : "仅确定性召回，可复现基线，不调用任何 provider。"}
            </span>
          </div>
          <div className="opt">
            <span className="field-k">候选召回预算</span>
            <div className="recall-val mono">{episodes.length ? recall : "—"}</div>
            <span className="opt-hint">按素材数自动推导（约 4×集数，限 20–400）。</span>
          </div>
        </div>
      </div>

      <div className="nr-actions">
        <span className="nr-note">人工评审是发布前的必经闸门——启动后流水线会停在评审闸门等待你确认。</span>
        <button className="btn btn-primary btn-lg" disabled={!canStart} onClick={start}>
          {busy ? "启动中…" : "开始运行 →"}
        </button>
      </div>
    </div>
  );
}

window.Studio = Object.assign(window.Studio || {}, { NewRun });
