import { useEffect, useRef, useState } from "react";
import { AgenticPipelineViz } from "./AgenticPipelineViz";
import { BatchUpload } from "./BatchUpload";
import type { BatchResponse } from "./batchUploadApi";
import { ReviewGate } from "./ReviewGate";
import { startRun, pollRunStatus, RUN_TERMINAL, type RunStatus } from "./studioPipelineApi";
import "./studioPipeline.css";

// StudioPipeline — the GRAPH-CENTRIC producer console (gated by ?studio_pipeline=1). It is NOT a
// manual stepper: the operator uploads a batch of clips and ONE LangGraph run does everything
// backstage — ingest → ASR → propose windows → episode memory → author (self-correction loop) —
// then PAUSES at owner_review_gate. The console polls the run and:
//   · drives the real graph viz (AgenticPipelineViz) from current_node + per-round traces;
//   · when the run interrupts (status waiting_for_review), shows the split review gate (ReviewGate:
//     left player iframe + right per-pack hierarchical short-circuit ladder + SUBMIT);
//   · SUBMIT resumes the graph → promote → a playable Stage deep-link.
// Human review is a NODE, not a UI step — the gate appears because the graph interrupted there.

const PHASES = [
  { key: "upload", name: "上传批量" },
  { key: "run", name: "跑 graph" },
  { key: "review", name: "人审 gate" },
  { key: "publish", name: "发布·可播" },
];
const PHASE_ORDER = ["upload", "run", "review", "publish"];

export function StudioPipeline() {
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [resolved, setResolved] = useState<{ promoted_moment_ids?: string[]; stage_url?: string } | null>(null);
  const [runErr, setRunErr] = useState("");

  const runCtrl = useRef<AbortController | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = () => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  };
  useEffect(
    () => () => {
      runCtrl.current?.abort();
      stopPolling();
    },
    [],
  );

  // naturalPhase = where the run actually is. The displayed phase follows it forward automatically,
  // but the operator can click any already-reached stepper chip to jump among reached phases.
  const naturalPhase: string = resolved
    ? "publish"
    : runStatus?.status === "waiting_for_review"
      ? "review"
      : runId
        ? "run"
        : "upload";
  const [viewPhase, setViewPhase] = useState<string>("upload");
  useEffect(() => {
    setViewPhase(naturalPhase);
  }, [naturalPhase]);
  const phase = viewPhase;
  const naturalIdx = PHASE_ORDER.indexOf(naturalPhase);
  // Any phase chip is clickable at ANY time — it just shows that phase's PAGE (with an empty state
  // when there's no live run/data). The view still auto-follows the run forward (the effect above).
  const goPhase = (p: string) => setViewPhase(p);

  // BatchUpload fires onBatchReady when the operator presses "开始制作（跑 graph）" — start the run.
  const beginRun = async (b: BatchResponse) => {
    stopPolling();
    runCtrl.current?.abort();
    setBatch(b);
    setResolved(null);
    setRunStatus(null);
    setRunErr("");
    const ctrl = new AbortController();
    runCtrl.current = ctrl;
    try {
      const { run_id } = await startRun(b.drama_id, 2, ctrl.signal);
      if (ctrl.signal.aborted) return;
      setRunId(run_id);
      const tick = async () => {
        if (ctrl.signal.aborted) return;
        try {
          const s = await pollRunStatus(run_id, ctrl.signal);
          if (ctrl.signal.aborted) return;
          setRunStatus(s);
          if (s.status === "error") {
            setRunErr(s.error || "图运行失败");
            return;
          }
          if (RUN_TERMINAL.includes(s.status)) return; // pause at gate (or done) → stop polling
          pollTimer.current = setTimeout(tick, 1000);
        } catch (e: unknown) {
          if ((e as { name?: string })?.name === "AbortError") return;
          setRunErr(e instanceof Error ? e.message : String(e));
        }
      };
      void tick();
    } catch (e: unknown) {
      if ((e as { name?: string })?.name === "AbortError") return;
      setRunErr(e instanceof Error ? e.message : String(e));
    }
  };

  const restart = () => {
    runCtrl.current?.abort();
    stopPolling();
    setBatch(null);
    setRunId(null);
    setRunStatus(null);
    setResolved(null);
    setRunErr("");
    setViewPhase("upload");
  };

  const stageUrl =
    resolved?.stage_url ||
    (batch ? `/Stage/?branch3_player=1&dramaId=${encodeURIComponent(batch.drama_id)}` : "/Stage/");

  return (
    <div className="studio-console">
      <aside className="sc-rail">
        <div className="sc-brand">
          <div className="sc-brand__mark">
            <img src="/assets/branch3/companion/tomato-robes/png/idle.png" alt="" />
          </div>
          <div>
            <div className="sc-brand__name">看剧搭子 Studio</div>
            <div className="sc-brand__sub">生产侧 · 图中心授权台</div>
          </div>
        </div>

        <div className="sc-rail__label">UPLOAD → GRAPH → GATE → PLAY</div>

        {(runId || batch) && (
          <div className="sc-actions" style={{ marginTop: 18 }}>
            <button className="sc-btn sc-btn--ghost" onClick={restart} data-testid="restart">
              ↺ 新建一批
            </button>
          </div>
        )}

        <div className="sc-rail__foot">
          <span className="dot" />
          人审 gate 是落库前的必经闸门
        </div>
        <div className="sc-rail__foot">
          <span className="dot" />
          模型在 <code>.env</code> 配置（已给预设）；创作与评审建议用<b>不同</b>模型，跨模型评审更可信
        </div>
      </aside>

      <div className="sc-main">
        <div className="sc-topbar">
          <div className="sc-context">
            <div className="sc-context__sig">{batch ? batch.drama_name : "看剧搭子 · 图中心授权台"}</div>
            <div className="sc-context__id">
              {batch ? `${batch.episodes.length} 集片段` : "上传一批片段开始"}
            </div>
          </div>
          <div className="sc-steps">
            {PHASES.map((p, i) => {
              const idx = PHASE_ORDER.indexOf(p.key);
              return (
                <span key={p.key} style={{ display: "contents" }}>
                  {i > 0 && <span className="sc-step-sep" />}
                  <button
                    type="button"
                    className={`sc-step${phase === p.key ? " is-on" : ""}${idx < naturalIdx ? " is-done" : ""}`}
                    data-testid={`phase-${p.key}`}
                    onClick={() => goPhase(p.key)}
                  >
                    <span className="sc-step__n">{idx < naturalIdx ? "✓" : i + 1}</span>
                    <span>{p.name}</span>
                  </button>
                </span>
              );
            })}
          </div>
        </div>

        <div className="sc-stage">
          {/* Every phase is a navigable PAGE — any chip is clickable any time; a phase with no live
              run/data shows an empty state instead of being hidden. */}

          {/* ① upload — start a production graph from a batch of clips */}
          {phase === "upload" && (
            <div className="sc-panel">
              <div className="sc-panel__head">
                <span className="sc-panel__title">上传批量片段 · 起一条生产图</span>
                <span className="sc-panel__en">batch upload</span>
              </div>
              <div className="sc-panel__body">
                <BatchUpload onBatchReady={beginRun} />
              </div>
            </div>
          )}

          {/* ② run — the REAL graph viz (renders the idle graph structure when there's no live run). */}
          {phase === "run" && (
            <div className="sc-panel">
              <div className="sc-panel__head">
                <span className="sc-panel__title">production graph · LangGraph</span>
                <span className="sc-panel__en">
                  {runStatus?.status === "running"
                    ? "运行中…"
                    : runId
                      ? "已跑完"
                      : "未运行 · 仅预览图结构"}
                </span>
              </div>
              <div className="sc-panel__body">
                <AgenticPipelineViz
                  running={runStatus?.status === "running"}
                  rounds={runStatus?.rounds}
                  currentNode={runStatus?.current_node}
                  currentRound={runStatus?.rounds?.length}
                />
                {runErr && <div className="sc-err">图运行失败：{runErr}</div>}
                {runStatus?.status === "running" && (
                  <div className="sc-actions">
                    <button className="sc-btn sc-btn--ghost" onClick={restart} data-testid="cancel-run">
                      取消运行
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ③ review — DEDICATED full view (graph hidden). Empty state when no run has paused here. */}
          {phase === "review" &&
            (runStatus?.review && runId ? (
              <div className="sc-panel sc-panel--review" data-testid="review-gate-panel">
                <div className="sc-panel__body">
                  <ReviewGate runId={runId} review={runStatus.review} onResolved={(r) => setResolved(r)} />
                </div>
              </div>
            ) : (
              <div className="sc-panel">
                <div className="sc-panel__head">
                  <span className="sc-panel__title">owner_review_gate · 人审闸门</span>
                  <span className="sc-panel__en">in-graph review</span>
                </div>
                <div className="sc-panel__body">
                  <div className="sc-empty">
                    图跑到人审闸门会在这里暂停，左边放该窗口的移动端播放器、右边逐 pack 审（窗口 → 方向 → 引子/说/接话，短路退回）。
                    现在还没有待审 pack —— 上传一批片段、跑一条 graph 就会停在这里。
                  </div>
                </div>
              </div>
            ))}

          {/* ④ publish — playable deep-link, or an empty state before anything is promoted. */}
          {phase === "publish" &&
            (resolved ? (
              <div className="sc-panel">
                <div className="sc-panel__head">
                  <span className="sc-panel__title">已落库 · 可在 Stage 播放</span>
                  <span className="sc-panel__en">promoted</span>
                </div>
                <div className="sc-panel__body">
                  <div className="sc-hero">
                    <div className="sc-hero__check">✓</div>
                    <div>
                      <h2>{resolved.promoted_moment_ids?.length ?? 0} 条已落库</h2>
                      <p>graph 已把通过人审的 pack 写进这部剧，Stage 列表即可播放。</p>
                    </div>
                  </div>
                  <div className="sc-actions">
                    <a
                      className="sc-btn sc-btn--pass sc-btn--lg"
                      href={stageUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid="play-link"
                    >
                      ▶ 在 Stage 看刚产出的这部 →
                    </a>
                    <button className="sc-btn sc-btn--ghost" onClick={restart}>
                      ↺ 再做一批
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="sc-panel">
                <div className="sc-panel__head">
                  <span className="sc-panel__title">发布 · 落库可播</span>
                  <span className="sc-panel__en">promoted</span>
                </div>
                <div className="sc-panel__body">
                  <div className="sc-empty">
                    人审通过后，graph 会把 approve 的 pack 落库进这部剧，这里给出「在 Stage 看刚产出的这部」深链。
                    现在还没有落库的产物。
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
