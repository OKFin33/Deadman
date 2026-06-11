import { useMemo, useRef, useState } from "react";
import {
  uploadBatch,
  BatchUploadNotReadyError,
  makeDramaId,
  formatClock,
  defaultEpisodeName,
  type BatchResponse,
  type BatchFile,
} from "./batchUploadApi";
import "./studioPipeline.css";

// BatchUpload — Track D: the entry point of the Studio graph-run console.
//
// The operator picks N video clips of ONE drama (owner decision #1 = per-drama batch), names the
// drama + episodes, uploads, and sees a per-clip「提议窗口」
// preview (timecoded transcript excerpts). On confirm it hands the whole BatchResponse up via
// onBatchReady — the parent (Track F) kicks off the graph run with it.
//
// This is backstage authoring UI: it stays demoable standalone. If /api/studio/batch isn't wired
// yet (Track E sequenced after), the POST 404s and we show a distinct "backend not ready" panel
// instead of a generic failure.

export interface BatchUploadProps {
  /** Called with the produced batch (incl. proposed windows) when the operator presses
   *  "开始制作 (跑 graph)". The parent kicks off the graph run with this. */
  onBatchReady: (batch: BatchResponse) => void;
}

type RowState = "pending" | "uploading" | "done" | "error";

interface ClipRow {
  /** stable key so renames/removes don't reorder React state */
  key: string;
  file: File;
  episodeName: string;
  state: RowState;
}

let ROW_SEQ = 0;
function nextRowKey(): string {
  ROW_SEQ += 1;
  return `clip-${ROW_SEQ}-${Date.now()}`;
}

export function BatchUpload({ onBatchReady }: BatchUploadProps) {
  const [dramaName, setDramaName] = useState("");
  const [rows, setRows] = useState<ClipRow[]>([]);

  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<BatchResponse | null>(null);
  const [err, setErr] = useState("");
  const [notReady, setNotReady] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const dramaNameValid = dramaName.trim().length > 0;
  const canSubmit = !uploading && rows.length > 0 && dramaNameValid;

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    // Capture the File objects NOW — synchronously — before resetting the input below. The setRows
    // updater runs LATER (React defers functional updates), so reading `fileList` lazily inside it
    // would see the already-reset (empty) FileList → zero rows. This was the「选了文件却不显示」bug.
    const picked = Array.from(fileList);
    setRows((prev) => [
      ...prev,
      ...picked.map((file, i) => ({
        key: nextRowKey(),
        file,
        episodeName: defaultEpisodeName(prev.length + i + 1),
        state: "pending" as RowState,
      })),
    ]);
    // reset the native input so re-picking the same file fires onChange again
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const renameRow = (key: string, name: string) => {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, episodeName: name } : r)));
  };

  const removeRow = (key: string) => {
    setRows((prev) => prev.filter((r) => r.key !== key));
  };

  const setAllRowStates = (state: RowState) => {
    setRows((prev) => prev.map((r) => ({ ...r, state })));
  };

  const submit = async () => {
    if (!canSubmit) return;
    setUploading(true);
    setErr("");
    setNotReady(false);
    setResult(null);
    setAllRowStates("uploading");

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const files: BatchFile[] = rows.map((r) => ({ file: r.file, episode_name: r.episodeName }));
    const displayName = dramaName.trim();
    try {
      const batch = await uploadBatch(
        { drama_id: makeDramaId(displayName), drama_name: displayName, files },
        ctrl.signal,
      );
      if (ctrl.signal.aborted) return;
      setResult(batch);
      setAllRowStates("done");
    } catch (e: unknown) {
      if ((e as { name?: string })?.name === "AbortError") return;
      setAllRowStates("error");
      if (e instanceof BatchUploadNotReadyError) {
        setNotReady(true);
        setErr(e.message);
      } else {
        setErr(e instanceof Error ? e.message : String(e));
      }
    } finally {
      if (abortRef.current === ctrl) abortRef.current = null;
      setUploading(false);
    }
  };

  const reset = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setResult(null);
    setErr("");
    setNotReady(false);
    setAllRowStates("pending");
  };

  const episodeByName = useMemo(() => {
    const map = new Map<string, string>();
    if (!result) return map;
    // align response episodes back to the operator's row order for the preview headers
    result.episodes.forEach((ep, i) => map.set(rows[i]?.key ?? ep.episode_id, ep.name));
    return map;
  }, [result, rows]);

  return (
    <div className="studio-console" style={{ display: "block", height: "auto", overflow: "visible" }}>
      <div className="bu-wrap" data-testid="batch-upload">
        <div className="bu-head">
          <div className="bu-head__title">批量上传 · 一部剧的多集</div>
          <div className="bu-head__sub">batch upload — per-drama, one graph run</div>
        </div>

        {/* drama-level header */}
        <div className="sc-panel">
          <div className="sc-panel__head">
            <span className="sc-panel__title">剧目信息</span>
            <span className="sc-panel__en">drama</span>
          </div>
          <div className="sc-panel__body">
            <div className="bu-field">
              <label className="bu-label" htmlFor="bu-drama-name">
                剧名
              </label>
              <input
                id="bu-drama-name"
                className="bu-input"
                value={dramaName}
                placeholder="云渺"
                onChange={(e) => setDramaName(e.target.value)}
                data-testid="drama-name"
              />
            </div>
          </div>
        </div>

        {/* file picker + per-clip rows */}
        <div className="sc-panel">
          <div className="sc-panel__head">
            <span className="sc-panel__title">剧集片段 · {rows.length} 个</span>
            <span className="sc-panel__en">video clips</span>
          </div>
          <div className="sc-panel__body">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="video/*"
              className="bu-file-input"
              onChange={(e) => addFiles(e.target.files)}
              data-testid="file-input"
            />
            <div className="sc-actions">
              <button
                type="button"
                className="sc-btn sc-btn--ghost"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                data-testid="pick-files"
              >
                + 选择视频片段
              </button>
            </div>

            {rows.length === 0 ? (
              <div className="bu-empty">还没有选片段。选这部剧的多集视频（一次可多选）。</div>
            ) : (
              <ul className="bu-rows" data-testid="clip-rows">
                {rows.map((r, i) => (
                  <li className={`bu-row is-${r.state}`} key={r.key} data-testid="clip-row">
                    <span className={`bu-row__state bu-row__state--${r.state}`} title={r.state} />
                    <span className="bu-row__num">{i + 1}</span>
                    <span className="bu-row__file" title={r.file.name}>
                      {r.file.name}
                    </span>
                    <input
                      className="bu-row__ep"
                      value={r.episodeName}
                      onChange={(e) => renameRow(r.key, e.target.value)}
                      disabled={uploading}
                      aria-label={`episode name ${i + 1}`}
                      data-testid="episode-name"
                    />
                    <button
                      type="button"
                      className="bu-row__remove"
                      onClick={() => removeRow(r.key)}
                      disabled={uploading}
                      aria-label={`remove ${r.file.name}`}
                      data-testid="remove-clip"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="sc-actions">
              <button
                type="button"
                className="sc-btn sc-btn--primary sc-btn--lg"
                onClick={submit}
                disabled={!canSubmit}
                data-testid="submit-batch"
              >
                {uploading ? "上传中…" : "上传并提议窗口"}
              </button>
              {result && (
                <button type="button" className="sc-btn sc-btn--ghost" onClick={reset} disabled={uploading}>
                  ↻ 重新上传
                </button>
              )}
            </div>

            {notReady && (
              <div className="bu-notready" data-testid="backend-not-ready">
                <b>后端尚未就绪</b>
                <p>
                  /api/studio/batch 还没上线（Track E 排在本组件之后）。前端已就绪，等后端接好即可直接联调。
                </p>
              </div>
            )}
            {err && !notReady && (
              <div className="sc-err" data-testid="batch-error">
                上传失败：{err}
              </div>
            )}
          </div>
        </div>

        {/* proposed-windows preview (read-only) */}
        {result && (
          <div className="sc-panel" data-testid="proposal-preview">
            <div className="sc-panel__head">
              <span className="sc-panel__title">提议窗口 · {result.drama_name || "新剧"}</span>
              <span className="sc-panel__en">{result.batch_id}</span>
            </div>
            <div className="sc-panel__body">
              {result.episodes.length === 0 ? (
                <div className="bu-empty">这一批没有提议出任何窗口。</div>
              ) : (
                <div className="bu-eps">
                  {result.episodes.map((ep, i) => (
                    <div className="bu-ep" key={ep.episode_id} data-testid="proposal-episode">
                      <div className="bu-ep__head">
                        <span className="bu-ep__name">
                          {episodeByName.get(rows[i]?.key ?? ep.episode_id) ?? ep.name}
                        </span>
                        <span className="bu-ep__meta">
                          {formatClock(ep.duration_seconds)} · ASR {ep.asr_source} ·{" "}
                          {ep.proposed_windows.length} 个提议窗口
                        </span>
                      </div>
                      {ep.proposed_windows.length === 0 ? (
                        <div className="bu-ep__empty">这一集没有提议窗口。</div>
                      ) : (
                        <ul className="bu-wins">
                          {ep.proposed_windows.map((w) => (
                            <li className="bu-win" key={w.window_id} data-testid="proposal-window">
                              <span className="bu-win__time">
                                {formatClock(w.start_seconds)}–{formatClock(w.end_seconds)}
                              </span>
                              <span className="bu-win__excerpt">{w.excerpt}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="sc-actions">
                <button
                  type="button"
                  className="sc-btn sc-btn--primary sc-btn--lg"
                  onClick={() => onBatchReady(result)}
                  data-testid="start-graph"
                >
                  ▶ 开始制作（跑 graph）
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
