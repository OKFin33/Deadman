// AgenticPipelineViz — the marquee「看 production-graph 自我纠错」⑤ view for the unified Studio
// pipeline. It renders the FULL production graph as a single readable spine of warm node chips with
// a REAL curved REJECT loop-arc (评审 judge → 创作A stage_a) drawn above the self-correction nodes,
// plus a forward ACCEPT exit (judge → owner_review_gate). The loop-arc LIGHTS UP when the
// current/last round's verdict rejected.
//
// A⑤ REAL progress: there is NO fake scripted timer. The console starts the agentic author as a
// BACKGROUND run and polls its status; the live `currentNode` and the REAL per-round `rounds`
// trace drive the highlighting directly:
//  • running=true  → the node named by `currentNode` is "running"; every earlier node is "done";
//    the reject loop-arc lights when the current round's REAL verdict rejected.
//  • running=false → it renders the completed run faithfully from `rounds` (+ judge_available).
//
// `rounds` is tolerant: a completed synchronous call may still hand an INTEGER count (legacy shape),
// but the live background flow hands the real per-round trace array, which renders verbatim.
//
// Layout is hand-positioned (NOT React Flow) so the chips stay readable and the loop-arc is drawn
// exactly where it should be — a fixed-geometry SVG, so it never collapses or gets auto-shrunk.

// ---------------------------------------------------------------- node set ----
// The FULL production graph, left-to-right. ids MUST match the backend status `current_node`
// strings. Old (v0.3) currentNode values (window_gate..judge) are a subset and map 1:1.
type StateKind = "idle" | "done" | "running" | "flash";

const NODES = [
  // front (prep)
  { id: "ingest_batch", name: "摄取" },
  { id: "asr", name: "转写" },
  { id: "propose_windows", name: "提窗" },
  { id: "build_scaffold", name: "搭骨架" },
  { id: "build_episode_memory", name: "建记忆" },
  // per-window self-correction loop (judge → stage_a is the ↺)
  { id: "window_gate", name: "开窗判" },
  { id: "context", name: "补context" },
  { id: "stage_a", name: "创作A" },
  { id: "stage_b", name: "接话B" },
  { id: "judge", name: "评审" },
  // tail
  { id: "owner_review_gate", name: "人审闸" },
  { id: "promote", name: "落库" },
  { id: "final_report", name: "报告" },
] as const;

const NODE_INDEX: Record<string, number> = NODES.reduce(
  (acc, n, i) => ((acc[n.id] = i), acc),
  {} as Record<string, number>,
);

// Backward-compat: older status polls / callers may use a couple of alternate ids.
const NODE_ALIASES: Record<string, string> = {
  "stage A": "stage_a",
  "stage B": "stage_b",
  author_and_judge: "stage_a",
  owner_review: "owner_review_gate",
  report: "final_report",
};

function canonicalNode(id?: string): string {
  if (!id) return "window_gate";
  if (id in NODE_INDEX) return id;
  if (id in NODE_ALIASES) return NODE_ALIASES[id];
  return "window_gate";
}

// ---- hand-laid geometry (fixed, never auto-shrunk) ----
const CHIP_W = 56;
const CHIP_H = 46;
const COL_W = 67; // chip + gap
const ROW_Y = 44; // top of the chip row (leaves room above for the loop arc)
const ARC_TOP = 7;
const CANVAS_H = ROW_Y + CHIP_H + 8;
const TOTAL_W = (NODES.length - 1) * COL_W + CHIP_W;
const chipLeft = (i: number) => i * COL_W;
const chipCx = (i: number) => i * COL_W + CHIP_W / 2;
const ROW_MID = ROW_Y + CHIP_H / 2;

const REVISE_LAYERS = ["开场 (lead)", "三条 (replies)", "接话 (echo)"];

export type RoundTrace = {
  verdict?: string | null;
  overall_verdict?: string | null;
  accepted?: boolean;
  revised_layer?: string | null;
  note?: string | null;
};

export type AgenticRounds = number | RoundTrace[] | null | undefined;

function roundCount(rounds: AgenticRounds): number {
  if (Array.isArray(rounds)) return rounds.length;
  if (typeof rounds === "number" && rounds > 0) return Math.floor(rounds);
  return 0;
}

export function AgenticPipelineViz({
  rounds,
  running,
  judgeAvailable,
  currentNode,
  currentRound,
}: {
  rounds?: AgenticRounds;
  running: boolean;
  judgeAvailable?: boolean;
  currentNode?: string; // A⑤: the REAL node the background loop is on (any production-graph node)
  currentRound?: number; // A⑤: the REAL 1-based round currently running
}) {
  const total = roundCount(rounds);
  const traces: RoundTrace[] | null = Array.isArray(rounds) ? rounds : null;

  const liveNode = canonicalNode(currentNode);
  const liveIndex = NODE_INDEX[liveNode];

  const lastTrace = traces && traces.length > 0 ? traces[traces.length - 1] : null;
  const livePass = currentRound && currentRound > 0 ? currentRound : traces ? traces.length : 1;
  const liveReject = running && !!lastTrace && lastTrace.accepted === false;
  const idleHadReject = !running && !!traces && traces.some((t) => t.accepted === false);
  const rejectActive = liveReject || idleHadReject;

  const stateFor = (i: number, id: string): StateKind => {
    if (running) {
      if (id === "judge" && liveReject) return "flash";
      if (i < liveIndex) return "done";
      if (i === liveIndex) return "running";
      return "idle";
    }
    return total > 0 ? "done" : "idle";
  };

  const iStageA = NODE_INDEX["stage_a"];
  const iJudge = NODE_INDEX["judge"];
  const iGate = NODE_INDEX["owner_review_gate"];
  // reject ↺ loop-arc: judge top → up → stage_a top (a hump over the loop nodes)
  const rejectPath = `M ${chipCx(iJudge)} ${ROW_Y} C ${chipCx(iJudge)} ${ARC_TOP} ${chipCx(
    iStageA,
  )} ${ARC_TOP} ${chipCx(iStageA)} ${ROW_Y}`;

  return (
    <div data-testid="agentic-viz">
      <div className="cab-graph" data-testid="viz-graph">
        <div className="cab-graph-canvas" style={{ width: TOTAL_W, height: CANVAS_H }}>
          <svg className="cab-graph-arcs" width={TOTAL_W} height={CANVAS_H} aria-hidden="true">
            {/* linear connectors between adjacent chips */}
            {NODES.slice(0, -1).map((n, i) => {
              const isAccept = i === iJudge && i + 1 === iGate; // judge → owner_review_gate
              return (
                <line
                  key={`c-${n.id}`}
                  className={`cab-conn${isAccept ? " cab-conn--accept" : ""}`}
                  x1={chipLeft(i) + CHIP_W}
                  y1={ROW_MID}
                  x2={chipLeft(i + 1)}
                  y2={ROW_MID}
                />
              );
            })}
            {/* the REAL reject loop-arc */}
            <path
              className={`cab-arc cab-arc--reject${rejectActive ? " is-active" : ""}`}
              d={rejectPath}
              fill="none"
            />
            <text
              className={`cab-arc__glyph${rejectActive ? " is-active" : ""}`}
              x={(chipCx(iStageA) + chipCx(iJudge)) / 2}
              y={ARC_TOP + 1}
              textAnchor="middle"
            >
              ↺
            </text>
          </svg>
          {NODES.map((n, i) => (
            <div
              key={n.id}
              className={`cab-graph-node is-${stateFor(i, n.id)}`}
              data-node={n.id}
              style={{ left: chipLeft(i), top: ROW_Y, width: CHIP_W, height: CHIP_H }}
            >
              <span className="cab-graph-node__dot" aria-hidden="true" />
              <span className="cab-graph-node__name">{n.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Edge-state markers — carry the pinned testids and name the two judge-exit outcomes in plain
          copy (the lit arc above is the visual signal; this reads without hovering). */}
      <div className="cab-graph-legend">
        <span
          className={`cab-graph-legend__edge cab-graph-legend__edge--reject${
            rejectActive ? " is-active" : ""
          }${liveReject ? " is-flash" : ""}`}
          data-testid="viz-loop-edge"
          data-active={rejectActive ? "1" : "0"}
        >
          <span className="cab-graph-legend__arrow">↺</span>
          {liveReject
            ? `reject ↺ 第 ${livePass} 轮被评审驳回 · 回 创作A 定向重写（同窗口）`
            : "reject ↺ 定向重写（同窗口）"}
        </span>
        <span
          className="cab-graph-legend__edge cab-graph-legend__edge--accept"
          data-testid="viz-accept-edge"
        >
          <span className="cab-graph-legend__arrow cab-graph-legend__arrow--accept">→</span>
          accept → 通过 · 送人审闸
        </span>
      </div>

      {running ? (
        <div className="cab-stage-label" data-testid="viz-running">
          agentic 创作 + 风味评审运行中（约 100–200s，评审耗时为主）… <span className="caret" />
        </div>
      ) : total > 0 ? (
        <>
          <div className="cab-stage-label" data-testid="viz-done">
            agent 自我纠错共 <b>{total}</b> 轮{" "}
            {judgeAvailable === false ? (
              <span className="sc-badge sc-badge--degraded" data-testid="viz-degraded">
                降级 · judge 不可用
              </span>
            ) : (
              <span className="sc-badge sc-badge--pass">judge 在线</span>
            )}
          </div>
          <div className="cab-rounds" data-testid="viz-rounds">
            {Array.from({ length: total }).map((_, i) => {
              const isFinal = i === total - 1;
              const trace = traces?.[i];
              const accepted =
                trace?.accepted ??
                (trace
                  ? ["accept", "approved", "pass"].includes(
                      String(trace.overall_verdict || trace.verdict || "").toLowerCase(),
                    )
                  : isFinal);
              const layer = trace?.revised_layer || REVISE_LAYERS[i % REVISE_LAYERS.length];
              return (
                <div
                  key={i}
                  className={`cab-round ${accepted ? "is-accept" : "is-revise"}`}
                  data-testid={`viz-round-${i + 1}`}
                >
                  <span className="cab-round__n">{accepted ? "✓" : i + 1}</span>
                  <div className="cab-round__body">
                    <div className="cab-round__head">
                      第 {i + 1} 轮 ·{" "}
                      {accepted ? "评审通过 accept" : `评审需返工 · 定向重写 ${layer}`}
                    </div>
                    {trace?.note ? <div className="cab-round__note">{trace.note}</div> : null}
                    {!accepted && !trace?.note ? (
                      <div className="cab-round__note">评审标出失败项 → 同一窗口重新创作下一轮</div>
                    ) : null}
                    {accepted ? (
                      <div className="cab-round__note">这一轮在窗口约束内站住了 ✓</div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
}
