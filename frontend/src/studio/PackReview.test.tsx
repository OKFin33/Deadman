import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { PackReview } from "./PackReview";
import type { DeadmanMomentSummary } from "../api/deadmanApi";
import type { PackLabel } from "./packReviewApi";

function makePack(): DeadmanMomentSummary {
  return {
    moment_id: "huangnian_ep12_m001",
    drama_id: "huangnian",
    source_drama: { title: "荒年", episode_id: "huangnian_ep12" },
    interaction_window: { start_seconds: 65, notice_at_seconds: 65, end_seconds: 85 },
    companion_lead: "我刚刚真想替四蛋说一句。",
    companion_exchange: {
      schema_version: "companion_exchange_pack.v0.1",
      scene_signal: "四蛋把兔子交出来时，先把自己排除在肉外面",
      notice_marker: "!",
      companion_lead: "我刚刚真想替四蛋说一句。",
      reply_candidates: [
        { candidate_id: "preset_0", display_text: "四蛋该吃肉", action_payload: {}, emotion_role: "心疼", semantic_role: "include", selected_echo: "可不是" },
        { candidate_id: "preset_1", display_text: "别让娃白懂事", action_payload: {}, emotion_role: "不忍", semantic_role: "preserve", selected_echo: "确实" },
        { candidate_id: "preset_2", display_text: "功劳算孩子的", action_payload: {}, emotion_role: "撑腰", semantic_role: "name", selected_echo: "嗯" },
      ],
    },
  };
}

// Harness mirrors how PackReviewStandalone owns the label state.
function Harness() {
  const [value, setValue] = useState<PackLabel>({
    pack_id: "huangnian_ep12_m001",
    moment_id: "huangnian_ep12_m001",
    drama_id: "huangnian",
  });
  return (
    <div>
      <div data-testid="json">{JSON.stringify(value)}</div>
      <PackReview pack={makePack()} value={value} onVerdict={setValue} />
    </div>
  );
}

function state(): PackLabel {
  return JSON.parse(screen.getByTestId("json").textContent || "{}");
}

describe("PackReview", () => {
  it("renders the lead + say×3 + echo×3 elements and the immutable scene_signal", () => {
    render(<Harness />);
    // lead
    expect(screen.getByText("我刚刚真想替四蛋说一句。")).toBeInTheDocument();
    // say×3
    expect(screen.getByText("四蛋该吃肉")).toBeInTheDocument();
    expect(screen.getByText("别让娃白懂事")).toBeInTheDocument();
    expect(screen.getByText("功劳算孩子的")).toBeInTheDocument();
    // echo×3
    expect(screen.getByText("可不是")).toBeInTheDocument();
    expect(screen.getByText("确实")).toBeInTheDocument();
    expect(screen.getByText("嗯")).toBeInTheDocument();
    // scene_signal shown as immutable context
    expect(screen.getByText("四蛋把兔子交出来时，先把自己排除在肉外面")).toBeInTheDocument();
    // 7 element rows -> 7 達標 toggles (lead, say1, echo1, say2, echo2, say3, echo3)
    expect(screen.getAllByText("达标")).toHaveLength(7);
  });

  it("records the top-level verdict and a per-element three-state", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("通过")); // top-level verdict = approved
    expect(state().verdict).toBe("approved");

    fireEvent.click(screen.getAllByText("达标")[0]); // first 达标 = lead
    expect(state().lead?.v).toBe("ok");

    fireEvent.click(screen.getAllByText("不达标")[2]); // echo1 (DOM order: lead, say1, echo1, ...)
    expect(state().echoes?.[0]?.v).toBe("bad");
  });

  it("captures a free-form reason", () => {
    render(<Harness />);
    fireEvent.change(screen.getByPlaceholderText(/理由/), { target: { value: "接话太硬" } });
    expect(state().reason).toBe("接话太硬");
  });
});

describe("packReviewApi", () => {
  it("savePackReviewLabels POSTs the labels to the pack-label endpoint", async () => {
    const { savePackReviewLabels } = await import("./packReviewApi");
    let captured: { url: string; init?: RequestInit } | null = null;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      captured = { url, init };
      return { ok: true, json: async () => ({ ok: true }) };
    });
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    const ok = await savePackReviewLabels({
      m1: { pack_id: "m1", moment_id: "m1", drama_id: "huangnian", verdict: "approved" },
    });

    expect(ok).toBe(true);
    expect(captured!.url).toBe("/api/studio/review/pack-label");
    expect(captured!.init?.method).toBe("POST");
    const body = JSON.parse(captured!.init?.body as string);
    expect(body.m1.verdict).toBe("approved");
    vi.unstubAllGlobals();
  });
});
