import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReviewGate, derivedVerdict } from "./ReviewGate";
import type { ResumeRunBody, ReviewPack, RunReview } from "./reviewGateApi";

function makePack(over: Partial<ReviewPack> = {}): ReviewPack {
  return {
    moment_id: "huangnian_ep12_m001",
    episode_id: "huangnian_ep12",
    episode_name: "第1集",
    drama_id: "huangnian",
    scene_signal: "四蛋把兔子交出来时，先把自己排除在肉外面",
    companion_lead: "我刚刚真想替四蛋说一句。",
    interaction_window: { start_seconds: 65, end_seconds: 85, notice_at_seconds: 65 },
    reply_candidates: [
      { display_text: "四蛋该吃肉", selected_echo: "可不是" },
      { display_text: "别让娃白懂事", selected_echo: "确实" },
      { display_text: "功劳算孩子的", selected_echo: "嗯" },
    ],
    ...over,
  };
}

function makeReview(packs: ReviewPack[]): RunReview {
  return { drama_id: "huangnian", packs };
}

// ── single-pack ladder short-circuits ──────────────────────────────────────────────────────────

describe("ReviewGate — short-circuit ladder", () => {
  it("window reject → say/echo not rendered, pack verdict = 退回", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    fireEvent.click(screen.getByText("不会想说")); // window = reject
    // say/echo texts must be gone
    expect(screen.queryByText("四蛋该吃肉")).not.toBeInTheDocument();
    expect(screen.queryByText("可不是")).not.toBeInTheDocument();
    // the nav pack mark + verdict pill both show 退回 (reject)
    expect(screen.getByTestId("rg-set-reject").className).toContain("on");
  });

  it("direction reject → elements not rendered, verdict = 退回", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    // pass window (accept), reject direction
    fireEvent.click(screen.getByText("会想说"));
    fireEvent.click(screen.getByText(/方向否/));
    expect(screen.queryByText("引子")).not.toBeInTheDocument();
    expect(screen.queryByText("四蛋该吃肉")).not.toBeInTheDocument();
    expect(screen.getByTestId("rg-set-reject").className).toContain("on");
  });

  it("lead bad → say/echo COLLAPSED (not rendered), verdict = 退回 (the new short-circuit)", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    fireEvent.click(screen.getByText("会想说")); // window ok
    // direction defaults to ok (not reject) → lead row shows.
    expect(screen.getByText("引子")).toBeInTheDocument();
    // mark lead bad: the lead row's 不达标 is the first one rendered.
    fireEvent.click(screen.getAllByText("不达标")[0]);
    // collapse note appears; say/echo NOT rendered
    expect(screen.getByText(/lead 坏/)).toBeInTheDocument();
    expect(screen.queryByText("四蛋该吃肉")).not.toBeInTheDocument();
    expect(screen.queryByText("可不是")).not.toBeInTheDocument();
    expect(screen.getByTestId("rg-set-reject").className).toContain("on");
  });

  it("all ok → say/echo rendered, verdict = 通过", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    fireEvent.click(screen.getByText("会想说")); // window ok
    fireEvent.click(screen.getByText("✓ 本卡全达标")); // lead+say+echo all ok
    expect(screen.getByText("四蛋该吃肉")).toBeInTheDocument();
    expect(screen.getByText("可不是")).toBeInTheDocument();
    expect(screen.getByTestId("rg-set-approve").className).toContain("on");
  });
});

// ── derived verdict (pure) ──────────────────────────────────────────────────────────────────────

describe("derivedVerdict", () => {
  it("window reject / direction reject / lead bad → reject; else approve; say bad alone → approve", () => {
    expect(derivedVerdict({ window: "reject" })).toBe("reject");
    expect(derivedVerdict({ direction: "reject" })).toBe("reject");
    expect(derivedVerdict({ lead: { v: "bad" } })).toBe("reject");
    expect(derivedVerdict({ window: "accept", lead: { v: "ok" } })).toBe("approve");
    // say/echo bad marks are taste signal only — do NOT auto-reject
    expect(derivedVerdict({ window: "accept", lead: { v: "ok" }, says: [{ v: "bad" }] })).toBe("approve");
  });
});

// ── verdict override ────────────────────────────────────────────────────────────────────────────

describe("ReviewGate — verdict override", () => {
  it("owner can override an approve pack to 退回", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    fireEvent.click(screen.getByText("会想说"));
    fireEvent.click(screen.getByText("✓ 本卡全达标"));
    expect(screen.getByTestId("rg-set-approve").className).toContain("on");
    // override → reject
    fireEvent.click(screen.getByTestId("rg-set-reject"));
    expect(screen.getByTestId("rg-set-reject").className).toContain("on");
    expect(screen.getByTestId("rg-override-note")).toBeInTheDocument();
  });
});

// ── multi-pack episode-grouped nav + SUBMIT gating ─────────────────────────────────────────────

describe("ReviewGate — multi-pack nav + submit", () => {
  const packs = [
    makePack({ moment_id: "huangnian_ep12_m001", episode_id: "huangnian_ep12", episode_name: "第1集" }),
    makePack({ moment_id: "huangnian_ep12_m002", episode_id: "huangnian_ep12", episode_name: "第1集" }),
    makePack({ moment_id: "huangnian_ep13_m001", episode_id: "huangnian_ep13", episode_name: "第2集" }),
  ];

  it("groups packs by episode and shows progress", () => {
    render(<ReviewGate runId="r1" review={makeReview(packs)} />);
    expect(screen.getAllByText("第1集").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("第2集").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("rg-progress").textContent).toContain("已审 0 / 共 3");
  });

  it("SUBMIT disabled until every pack is visited", () => {
    render(<ReviewGate runId="r1" review={makeReview(packs)} />);
    expect(screen.getByTestId("rg-submit")).toBeDisabled();

    // visit pack 1 (window accept)
    fireEvent.click(screen.getByText("会想说"));
    expect(screen.getByTestId("rg-progress").textContent).toContain("已审 1 / 共 3");
    expect(screen.getByTestId("rg-submit")).toBeDisabled();

    // pack 2 via nav rail
    fireEvent.click(screen.getByTestId("rg-pack-huangnian_ep12_m002"));
    fireEvent.click(screen.getByText("会想说"));
    // pack 3
    fireEvent.click(screen.getByTestId("rg-pack-huangnian_ep13_m001"));
    fireEvent.click(screen.getByText("会想说"));

    expect(screen.getByTestId("rg-progress").textContent).toContain("已审 3 / 共 3");
    expect(screen.getByTestId("rg-submit")).not.toBeDisabled();
  });

  it("SUBMIT posts pack_decisions for ALL packs (mock onResume) with element_labels", async () => {
    let captured: { runId: string; body: ResumeRunBody } | null = null;
    const onResume = vi.fn(async (runId: string, body: ResumeRunBody) => {
      captured = { runId, body };
      return { run_id: runId, status: "running", promoted_moment_ids: ["huangnian_ep12_m001"] };
    });
    const onResolved = vi.fn();

    render(<ReviewGate runId="run-42" review={makeReview(packs)} onResume={onResume} onResolved={onResolved} />);

    // pack 1: full approve (window + all elements ok)
    fireEvent.click(screen.getByText("会想说"));
    fireEvent.click(screen.getByText("✓ 本卡全达标"));
    // pack 2: window reject → derived reject
    fireEvent.click(screen.getByTestId("rg-pack-huangnian_ep12_m002"));
    fireEvent.click(screen.getByText("不会想说"));
    // pack 3: window accept only
    fireEvent.click(screen.getByTestId("rg-pack-huangnian_ep13_m001"));
    fireEvent.click(screen.getByText("会想说"));

    fireEvent.click(screen.getByTestId("rg-submit"));

    await waitFor(() => expect(onResume).toHaveBeenCalledTimes(1));
    expect(captured!.runId).toBe("run-42");
    expect(captured!.body.decision).toBe("approve");
    expect(captured!.body.pack_decisions).toEqual({
      huangnian_ep12_m001: "approve",
      huangnian_ep12_m002: "reject",
      huangnian_ep13_m001: "approve",
    });
    // element_labels carries every pack's MomentLabel (taste signal)
    expect(Object.keys(captured!.body.element_labels)).toHaveLength(3);
    expect(captured!.body.element_labels.huangnian_ep12_m002.window).toBe("reject");
    await waitFor(() =>
      expect(onResolved).toHaveBeenCalledWith({
        promoted_moment_ids: ["huangnian_ep12_m001"],
        stage_url: undefined,
      }),
    );
  });
});

// ── player iframe deep-link ─────────────────────────────────────────────────────────────────────

describe("ReviewGate — player iframe", () => {
  it("iframe src is the /Stage/ deep-link at start-2", () => {
    render(<ReviewGate runId="r1" review={makeReview([makePack()])} />);
    const frame = screen.getByTitle("真播放器") as HTMLIFrameElement;
    expect(frame.getAttribute("src")).toBe(
      "/Stage/?branch3_player=1&dramaId=huangnian&episodeId=huangnian_ep12&seek=63",
    );
  });
});

// ── resume api degradation ──────────────────────────────────────────────────────────────────────

describe("resumeRun", () => {
  it("throws ResumeNotReadyError on 404 (backend not yet wired)", async () => {
    const { resumeRun, ResumeNotReadyError } = await import("./reviewGateApi");
    vi.stubGlobal("fetch", vi.fn(async () => ({ status: 404, ok: false, json: async () => null })) as unknown as typeof fetch);
    await expect(
      resumeRun("r1", { decision: "approve", pack_decisions: {}, element_labels: {} }),
    ).rejects.toBeInstanceOf(ResumeNotReadyError);
    vi.unstubAllGlobals();
  });

  it("POSTs the resume body to /api/studio/run/resume/{runId}", async () => {
    const { resumeRun } = await import("./reviewGateApi");
    let captured: { url: string; init?: RequestInit } | null = null;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        captured = { url, init };
        return { status: 200, ok: true, json: async () => ({ run_id: "r1", status: "running" }) };
      }) as unknown as typeof fetch,
    );
    const body: ResumeRunBody = {
      decision: "approve",
      pack_decisions: { m1: "approve" },
      element_labels: { m1: { window: "accept" } },
    };
    const res = await resumeRun("run-7", body);
    expect(res.run_id).toBe("r1");
    expect(captured!.url).toBe("/api/studio/run/resume/run-7");
    expect(captured!.init?.method).toBe("POST");
    expect(JSON.parse(captured!.init?.body as string)).toEqual(body);
    vi.unstubAllGlobals();
  });
});
