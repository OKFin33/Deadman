import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

// StudioPipeline is the GRAPH-CENTRIC console: upload(batch) → /run/start → poll /run/status →
// the real graph viz animates → on waiting_for_review the split review gate appears → SUBMIT
// resumes → a playable deep-link. The heavy child surfaces (BatchUpload, ReviewGate) are tested in
// isolation, so here we mock them to small stubs that fire their callbacks, and test the
// ORCHESTRATION: start a run on batch-ready, poll, swap viz→gate→play.

vi.mock("./BatchUpload", () => ({
  BatchUpload: ({ onBatchReady }: { onBatchReady: (b: unknown) => void }) => (
    <button
      data-testid="mock-batch-ready"
      onClick={() =>
        onBatchReady({
          batch_id: "b1",
          drama_id: "yunmiao_demo",
          drama_name: "云渺(新)",
          episodes: [
            { episode_id: "yunmiao_demo_ep01", name: "第1集", duration_seconds: 0,
              asr_source: "live", proposed_windows: [] },
          ],
        })
      }
    >
      上传并提议窗口
    </button>
  ),
}));

vi.mock("./ReviewGate", () => ({
  ReviewGate: ({ runId, review, onResolved }: {
    runId: string;
    review: { packs: unknown[] };
    onResolved?: (r: { promoted_moment_ids?: string[]; stage_url?: string }) => void;
  }) => (
    <div data-testid="mock-review-gate">
      <span data-testid="rg-runid">{runId}</span>
      <span data-testid="rg-packs">{review.packs.length}</span>
      <button
        data-testid="mock-resolve"
        onClick={() =>
          onResolved?.({ promoted_moment_ids: ["m1"], stage_url: "/Stage/?branch3_player=1&dramaId=yunmiao_demo" })
        }
      >
        提交
      </button>
    </div>
  ),
}));

import { StudioPipeline } from "./StudioPipeline";

function jsonResponse(data: unknown, init: { ok?: boolean; status?: number } = {}) {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: { get: () => "application/json" },
  };
}

const STATUS_RUNNING = {
  run_id: "prod_x", drama_id: "yunmiao_demo", status: "running", current_node: "stage_a",
  progress: { node_index: 5, total: 9 }, rounds: [], review: null, error: null,
};
const STATUS_WAITING = {
  run_id: "prod_x", drama_id: "yunmiao_demo", status: "waiting_for_review", current_node: "owner_review_gate",
  progress: { node_index: 6, total: 9 },
  rounds: [{ verdict: "accept", overall_verdict: "accept", accepted: true, revised_layer: null, note: null }],
  review: {
    drama_id: "yunmiao_demo",
    packs: [{
      moment_id: "m1", episode_id: "yunmiao_demo_ep01", episode_name: "第1集", drama_id: "yunmiao_demo",
      scene_signal: "她终于开口", companion_lead: "这一句憋太久了。",
      interaction_window: { start_seconds: 10, end_seconds: 20, notice_at_seconds: 11 },
      reply_candidates: [{ display_text: "替她不值", selected_echo: "对" }],
    }],
  },
  error: null,
};

function installFetch() {
  const calls: { url: string; body?: any }[] = [];
  let statusCalls = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ url, body });
    if (url.endsWith("/api/studio/run/start")) return jsonResponse({ run_id: "prod_x", status: "running" });
    if (url.includes("/api/studio/run/status/")) {
      statusCalls += 1;
      return jsonResponse(statusCalls >= 2 ? STATUS_WAITING : STATUS_RUNNING); // running once, then paused
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { calls };
}

describe("StudioPipeline (graph-centric)", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/?studio_pipeline=1");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the graph-centric brand + the batch-upload entry first", async () => {
    installFetch();
    render(<StudioPipeline />);
    expect(await screen.findByText("看剧搭子 Studio")).toBeInTheDocument();
    expect(screen.getByText("生产侧 · 图中心授权台")).toBeInTheDocument();
    expect(screen.getByTestId("mock-batch-ready")).toBeInTheDocument();
    expect(screen.getByTestId("phase-upload")).toHaveClass("is-on");
    // no stepper: it's a status chip row, the review/publish phases are not "on" yet
    expect(screen.getByTestId("phase-review")).not.toHaveClass("is-on");
  });

  it("on batch-ready starts a graph run, polls, swaps viz→review-gate, and resumes to a play link", async () => {
    const { calls } = installFetch();
    render(<StudioPipeline />);
    fireEvent.click(await screen.findByTestId("mock-batch-ready"));

    // /run/start is called with the batch's drama_id
    await waitFor(() => {
      const start = calls.find((c) => c.url.endsWith("/api/studio/run/start"));
      expect(start).toBeTruthy();
      expect(start!.body.drama_id).toBe("yunmiao_demo");
    });

    // the REAL graph viz renders once the run starts
    expect(await screen.findByTestId("agentic-viz")).toBeInTheDocument();

    // polling reaches waiting_for_review → the in-graph review gate appears with the run + packs
    const gate = await screen.findByTestId("mock-review-gate", undefined, { timeout: 2500 });
    expect(gate).toBeInTheDocument();
    expect(screen.getByTestId("rg-runid")).toHaveTextContent("prod_x");
    expect(screen.getByTestId("rg-packs")).toHaveTextContent("1");
    expect(screen.getByTestId("phase-review")).toHaveClass("is-on");

    // SUBMIT (resume) resolves → publish phase + a Stage deep-link to the produced drama
    fireEvent.click(screen.getByTestId("mock-resolve"));
    const link = (await screen.findByTestId("play-link")) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toContain("branch3_player=1");
    expect(link.getAttribute("href")).toContain("dramaId=yunmiao_demo");
    expect(screen.getByTestId("phase-publish")).toHaveClass("is-on");
  });
});
