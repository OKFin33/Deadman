import { describe, expect, it, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgenticPipelineViz, type RoundTrace } from "./AgenticPipelineViz";
// Vite ?raw import of the component source so we can pin the scripted-timer DELETION at build/test
// time (works in both tsc and vitest, no node fs/process needed).
import vizSource from "./AgenticPipelineViz.tsx?raw";

// React Flow measures node/viewport geometry via ResizeObserver, which jsdom doesn't provide.
// Polyfill it (no-op) so React Flow mounts and renders its custom nodes. (Edges are laid out from
// measured geometry, so they don't render in jsdom — that's exactly why the two pinned edge testids
// are co-located as state-reflecting legend markers in the component.)
beforeAll(() => {
  // @ts-expect-error jsdom polyfill
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

// ⑤ AgenticPipelineViz is now a REAL React Flow production graph (NOT a flat CSS row): the full
// node set ingest_batch…final_report, a forward ACCEPT edge (judge → owner_review_gate), and a
// REAL curved REJECT back-edge (judge → stage_a) that LIGHTS when a round bounced. These tests pin:
//  • both judge-exit edges (reject + accept) are always present,
//  • the reject edge lights only when a REAL round verdict rejected,
//  • node highlighting is driven 1:1 by the REAL currentNode prop (no fake scripted timer),
//  • the real per-round trace renders verbatim when done.

const nodeAt = (id: string) =>
  screen.getByTestId("agentic-viz").querySelector(`[data-node="${id}"]`)!;

describe("AgenticPipelineViz production graph", () => {
  it("renders the reject ↺ and accept edges back from judge even when idle (not running)", () => {
    render(<AgenticPipelineViz running={false} />);
    // the React Flow graph viewport is present
    expect(screen.getByTestId("viz-graph")).toBeInTheDocument();
    // BOTH judge-exit edges are present at rest, so the graph shows a LOOP, not a flat line
    const loopEdge = screen.getByTestId("viz-loop-edge");
    expect(loopEdge).toBeInTheDocument();
    expect(loopEdge).toHaveTextContent("reject");
    expect(loopEdge).toHaveTextContent("定向重写（同窗口）");
    // idle → reject edge is NOT lit
    expect(loopEdge.className).not.toContain("is-active");
    const acceptEdge = screen.getByTestId("viz-accept-edge");
    expect(acceptEdge).toHaveTextContent("accept");
    expect(acceptEdge).toHaveTextContent("通过");
  });

  it("renders the FULL production-graph node set (13 nodes)", () => {
    render(<AgenticPipelineViz running={false} />);
    // the extended graph: ingest_batch→asr→propose_windows→build_scaffold→build_episode_memory→
    // window_gate→context→stage_a→stage_b→judge→owner_review_gate→promote→final_report
    expect(
      screen.getByTestId("agentic-viz").querySelectorAll(".cab-graph-node"),
    ).toHaveLength(13);
    // a few key ids are addressable for highlighting
    expect(nodeAt("ingest_batch")).toBeInTheDocument();
    expect(nodeAt("judge")).toBeInTheDocument();
    expect(nodeAt("owner_review_gate")).toBeInTheDocument();
    expect(nodeAt("final_report")).toBeInTheDocument();
  });

  it("keeps both judge-exit edges present while running", () => {
    render(<AgenticPipelineViz running={true} />);
    expect(screen.getByTestId("viz-graph")).toBeInTheDocument();
    expect(screen.getByTestId("viz-loop-edge")).toBeInTheDocument();
    expect(screen.getByTestId("viz-accept-edge")).toBeInTheDocument();
  });

  it("still shows the edges alongside a completed per-round trace", () => {
    render(<AgenticPipelineViz running={false} rounds={2} judgeAvailable={true} />);
    // the judge-exit edges stay present after a run, with the real rounds trace below them
    expect(screen.getByTestId("viz-loop-edge")).toBeInTheDocument();
    expect(screen.getByTestId("viz-accept-edge")).toBeInTheDocument();
    expect(screen.getByTestId("viz-rounds")).toBeInTheDocument();
    expect(screen.getByTestId("viz-round-1")).toBeInTheDocument();
    expect(screen.getByTestId("viz-round-2")).toBeInTheDocument();
  });

  it("lights the node named by the REAL currentNode prop while running (no fake timer)", () => {
    // running on stage_b → stage_b is running; every node before it (incl. the new front nodes
    // and window_gate/context/stage_a) is done; judge ahead is NOT running.
    const { rerender } = render(
      <AgenticPipelineViz running={true} currentNode="stage_b" currentRound={1} rounds={[]} />,
    );
    expect(nodeAt("stage_b").className).toContain("is-running");
    expect(nodeAt("stage_a").className).toContain("is-done");
    expect(nodeAt("context").className).toContain("is-done");
    expect(nodeAt("ingest_batch").className).toContain("is-done"); // front node already done
    expect(nodeAt("judge").className).not.toContain("is-running");

    // advancing the REAL prop to judge moves the highlight — deterministic, prop-driven (no setTimeout).
    rerender(<AgenticPipelineViz running={true} currentNode="judge" currentRound={2} rounds={[]} />);
    expect(nodeAt("judge").className).toContain("is-running");
    expect(nodeAt("stage_b").className).toContain("is-done");
  });

  it("highlights a new front/tail node id straight from the status poll", () => {
    // currentNode values from the backend (e.g. asr early, promote late) map 1:1 onto node ids.
    const { rerender } = render(
      <AgenticPipelineViz running={true} currentNode="asr" currentRound={1} rounds={[]} />,
    );
    expect(nodeAt("asr").className).toContain("is-running");
    expect(nodeAt("ingest_batch").className).toContain("is-done");
    expect(nodeAt("judge").className).not.toContain("is-running");

    rerender(<AgenticPipelineViz running={true} currentNode="promote" currentRound={1} rounds={[]} />);
    expect(nodeAt("promote").className).toContain("is-running");
    expect(nodeAt("owner_review_gate").className).toContain("is-done");
  });

  it("lights the reject back-edge ONLY when a REAL round verdict rejected", () => {
    // running, current round rejected → the reject edge is active + names the bounced round.
    const rejected: RoundTrace[] = [
      { verdict: "reject", overall_verdict: "reject", accepted: false, revised_layer: "开场 (lead)", note: "x" },
    ];
    const { rerender } = render(
      <AgenticPipelineViz running={true} currentNode="judge" currentRound={1} rounds={rejected} />,
    );
    expect(screen.getByTestId("viz-loop-edge").className).toContain("is-active");
    expect(screen.getByTestId("viz-loop-edge")).toHaveTextContent("第 1 轮被评审驳回");
    // judge node itself flashes on a reject bounce
    expect(nodeAt("judge").className).toContain("is-flash");

    // an accepted round does NOT light the reject back-edge.
    const accepted: RoundTrace[] = [
      { verdict: "accept", overall_verdict: "accept", accepted: true, revised_layer: null, note: null },
    ];
    rerender(<AgenticPipelineViz running={true} currentNode="judge" currentRound={1} rounds={accepted} />);
    expect(screen.getByTestId("viz-loop-edge").className).not.toContain("is-active");
  });

  it("lights the reject back-edge at rest when ANY completed round rejected", () => {
    const traces: RoundTrace[] = [
      { verdict: "reject", overall_verdict: "reject", accepted: false, revised_layer: "接话 (echo)", note: "echo 偏弱" },
      { verdict: "accept", overall_verdict: "accept", accepted: true, revised_layer: null, note: null },
    ];
    render(<AgenticPipelineViz running={false} rounds={traces} judgeAvailable={true} />);
    expect(screen.getByTestId("viz-loop-edge").className).toContain("is-active");
  });

  it("renders the REAL per-round trace (verdict + revised layer) verbatim when done", () => {
    const traces: RoundTrace[] = [
      { verdict: "reject", overall_verdict: "reject", accepted: false, revised_layer: "接话 (echo)", note: "echo 偏弱" },
      { verdict: "accept", overall_verdict: "accept", accepted: true, revised_layer: null, note: null },
    ];
    render(<AgenticPipelineViz running={false} rounds={traces} judgeAvailable={true} />);
    expect(screen.getByText(/接话 \(echo\)/)).toBeInTheDocument(); // real revised layer, not a fallback
    expect(screen.getByText("echo 偏弱")).toBeInTheDocument(); // real note
    expect(screen.getByText(/评审通过 accept/)).toBeInTheDocument();
  });

  it("contains NO hardcoded scripted-timer progression in the source", () => {
    // pin the deletion of the fake timer: highlighting must be entirely prop-driven (A⑤). The
    // component uses no scripted progression, no setTimeout, and no time-driven effects.
    expect(vizSource).not.toContain("useScriptedProgression");
    expect(vizSource).not.toContain("setTimeout");
    expect(vizSource).not.toContain("useEffect");
  });
});
