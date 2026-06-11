import { afterEach, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "./App";

function jsonResponse(data: unknown, init: { ok?: boolean; status?: number } = {}) {
  const body = JSON.stringify(data);
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    text: async () => body,
    headers: {
      get: () => "application/json",
    },
  };
}

function makeMomentSummary(overrides: Record<string, unknown> = {}) {
  return {
    moment_id: "huangnian_ep12_m001",
    drama_id: "huangnian",
    source_drama: { episode_id: "huangnian_ep12" },
    interaction_window: {
      notice_at_seconds: 65,
      start_seconds: 65,
      end_seconds: 85,
      source: "reviewed_ars",
      confidence: "high",
      pause_policy: "pause_on_invite",
      expire_behavior: "return_to_idle",
    },
    notice_marker: "!",
    hook: "四蛋抓到兔子那一眼，懂事得让人难受。",
    companion_lead: "我刚刚真想替四蛋说一句。",
    action_type: "resource",
    default_options: [
      "今晚分兔肉，先让四蛋确认自己也有份",
      "先留下兔子和皮毛，改用别的食物补这一顿",
      "把兔子当成四蛋的功劳，只少量处理给全家尝味",
    ],
    mouthpiece_candidates_schema_version: "mouthpiece_candidates.v0.1",
    mouthpiece_candidates: [
      {
        candidate_id: "preset_0",
        display_text: "四蛋该吃肉",
        action_payload: {
          text: "今晚分兔肉，先让四蛋确认自己也有份",
          action_type: "resource",
          intent: "include_child_in_food_distribution",
          target_actors: ["四蛋"],
          risk_posture: "balanced",
        },
        emotion_role: "心疼孩子",
        semantic_role: "include_child_first",
        selected_echo: "对，这孩子都懂事到先把自己排除出去了，这口肉不能再让他干闻着。",
        distinctness_rationale: "Calls out the unfairness of excluding the child who contributed.",
        evidence_refs: ["huangnian_ep12_u002"],
        constraint_refs: ["current_scene_only"],
      },
      {
        candidate_id: "preset_1",
        display_text: "别让娃白懂事",
        action_payload: {
          text: "先留下兔子和皮毛，改用别的食物补这一顿",
          action_type: "resource",
          intent: "protect_child_contribution",
          target_actors: ["四蛋"],
          risk_posture: "cautious",
        },
        emotion_role: "不忍亏待",
        semantic_role: "preserve_child_contribution",
        selected_echo: "嗯，孩子不是来交差的，他这点心意得被看见。",
        distinctness_rationale: "Protects the emotional meaning of the child's contribution.",
        evidence_refs: ["huangnian_ep12_u004"],
        constraint_refs: ["current_scene_only"],
      },
      {
        candidate_id: "preset_2",
        display_text: "功劳算孩子的",
        action_payload: {
          text: "把兔子当成四蛋的功劳，只少量处理给全家尝味",
          action_type: "resource",
          intent: "credit_child_publicly",
          target_actors: ["四蛋"],
          risk_posture: "balanced",
        },
        emotion_role: "给孩子撑腰",
        semantic_role: "name_child_contribution",
        selected_echo: "这句我懂，孩子出力了，就该让他被家里人认真看见一次。",
        distinctness_rationale: "Names the child's contribution without turning the scene into a branch.",
        evidence_refs: ["huangnian_ep12_u005"],
        constraint_refs: ["current_scene_only"],
      },
    ],
    companion_exchange: {
      schema_version: "companion_exchange_pack.v0.1",
      scene_signal: "四蛋把兔子交出来时，先把自己排除在肉外面",
      window_rationale: "孩子把兔子交出来，却先把自己排除在这口肉之外。",
      notice_marker: "!",
      companion_lead: "我刚刚真想替四蛋说一句。",
      reply_candidates: [
        {
          candidate_id: "preset_0",
          display_text: "四蛋该吃肉",
          action_payload: {
            text: "今晚分兔肉，先让四蛋确认自己也有份",
            action_type: "resource",
            intent: "include_child_in_food_distribution",
            target_actors: ["四蛋"],
            risk_posture: "balanced",
          },
          emotion_role: "心疼孩子",
          semantic_role: "include_child_first",
          selected_echo: "对，这孩子都懂事到先把自己排除出去了，这口肉不能再让他干闻着。",
          distinctness_rationale: "Calls out the unfairness of excluding the child who contributed.",
          evidence_refs: ["huangnian_ep12_u002"],
          constraint_refs: ["current_scene_only"],
        },
        {
          candidate_id: "preset_1",
          display_text: "别让娃白懂事",
          action_payload: {
            text: "先留下兔子和皮毛，改用别的食物补这一顿",
            action_type: "resource",
            intent: "protect_child_contribution",
            target_actors: ["四蛋"],
            risk_posture: "cautious",
          },
          emotion_role: "不忍亏待",
          semantic_role: "preserve_child_contribution",
          selected_echo: "嗯，孩子不是来交差的，他这点心意得被看见。",
          distinctness_rationale: "Protects the emotional meaning of the child's contribution.",
          evidence_refs: ["huangnian_ep12_u004"],
          constraint_refs: ["current_scene_only"],
        },
        {
          candidate_id: "preset_2",
          display_text: "功劳算孩子的",
          action_payload: {
            text: "把兔子当成四蛋的功劳，只少量处理给全家尝味",
            action_type: "resource",
            intent: "credit_child_publicly",
            target_actors: ["四蛋"],
            risk_posture: "balanced",
          },
          emotion_role: "给孩子撑腰",
          semantic_role: "name_child_contribution",
          selected_echo: "这句我懂，孩子出力了，就该让他被家里人认真看见一次。",
          distinctness_rationale: "Names the child's contribution without turning the scene into a branch.",
          evidence_refs: ["huangnian_ep12_u005"],
          constraint_refs: ["current_scene_only"],
        },
      ],
      custom_reply_policy: {
        allowed: true,
        runtime_personalization: "bounded",
        reject_or_soften: ["future branch claim", "source-window-unsupported fact"],
      },
      evidence_refs: ["huangnian_ep12_u002"],
      constraint_refs: ["current_scene_only"],
      blocked_claims: ["Do not claim later-episode outcomes."],
      review_status: "reviewed",
    },
    result_media: {
      preset_options: [
        {
          option_index: 0,
          status: "placeholder",
          image_url: "",
          prompt: "huangnian_ep12_m001 option 0",
          source: "manual_placeholder",
          fallback_text: "P0 result image slot reserved; render text consequence when no image is available.",
        },
      ],
      custom_action: {
        status: "not_requested",
        mode: "realtime_generate_or_text_only_fallback",
        timeout_ms: 8000,
      },
    },
    original_plot_note: "原剧情把兔子处理成家人信任修复的一步。",
    ...overrides,
  };
}

function makeJudgmentResponse() {
  return {
    drama_id: "huangnian",
    moment_id: "huangnian_ep12_m001",
    action: {
      source: "preset",
      text: "今晚分兔肉，先让四蛋确认自己也有份",
      option_index: 0,
    },
    verdict: {
      label: "稳，但别摊太大",
      stance: "support",
      summary: "这一步站得住。",
    },
    consequence: {
      text: "后端搭子文本：四蛋先确认自己被照顾，解释压力还能压住。",
      time_horizon: "current_scene_or_immediate_aftermath",
      watch_flow_fit: "high",
    },
    canon_anchor: {
      original_plot_note: "原剧情把兔子处理成家人信任修复的一步。",
      safe_to_continue: true,
    },
    scores: { 爽度: 82, 可信度: 80 },
    result_card: {
      mode: "fallback_card",
      title: "四蛋抓到兔子那一眼，懂事得让人难受。",
      prompt: "镜头停在兔肉被重新分配的一刻。",
    },
    media: {
      type: "image",
      status: "placeholder",
      image_url: "",
      prompt: "huangnian_ep12_m001 option 0",
      source: "manual_placeholder",
      fallback_text: "P0 result image slot reserved; render text consequence when no image is available.",
    },
    aggregate_stats: {
      mode: "demo_static",
      total_count: 231,
      choices: [
        { label: "A", percent: 50, selected: true },
        { label: "B", percent: 30, selected: false },
        { label: "C", percent: 20, selected: false },
      ],
      note: "P0 演示静态分布；正式上线需要接入持久化统计。",
    },
    judgment_basis: {
      evidence_refs: [],
      applied_constraints: [],
      inference_notes: [],
      warnings: [],
    },
    engine: {
      mode: "demo_deterministic",
      schema_version: "deadman_judgment_result.v0.1",
    },
  };
}

function makeRuntimeResponse(body: any = {}) {
  const judgment = makeJudgmentResponse();
  return {
    viewer_session_id: body.viewer_session_id || "test-session",
    event_id: body.event_id || "evt-test",
    status: "ok",
    companion: {
      next_state: body.event_type === "user_action" ? "verdict" : "idle",
      marker: "!",
      utterance: "",
      should_interrupt: body.event_type === "user_action",
    },
    moment: {
      moment_id: body.moment_id || "huangnian_ep12_m001",
      interaction_window_active: true,
      default_options: makeMomentSummary().default_options,
      mouthpiece_candidates_schema_version: makeMomentSummary().mouthpiece_candidates_schema_version,
      mouthpiece_candidates: makeMomentSummary().mouthpiece_candidates,
      companion_exchange: makeMomentSummary().companion_exchange,
      hook: makeMomentSummary().hook,
    },
    judgment: body.event_type === "user_action" ? { ...judgment, action: body.action || judgment.action } : null,
    result_surface:
      body.event_type === "user_action"
        ? {
            mode: "single_narrative",
            text: "后端搭子文本：四蛋先确认自己被照顾，解释压力还能压住。",
            micro_cue: {
              kind: "aggregate_hint",
              text: "有50%其他观众也这么想。",
            },
            continue_label: "继续看",
          }
        : null,
    session_memory: {
      last_choice_summary: body.event_type === "user_action" ? "你上一手是先稳住四蛋。" : "",
      safe_to_reference: body.event_type === "user_action",
    },
    engine: {
      mode: "host_policy",
      cab_session_id: "deadman-viewer-test-session",
    },
    error: null,
  };
}

function makeEpisodeThreeMoment() {
  return makeMomentSummary({
    moment_id: "huangnian_ep03_m001",
    source_drama: {
      episode_id: "huangnian_ep03",
      runtime_video_url: "/assets/branch3/dramas/huangnian/huangnian_ep03.mp4",
    },
    interaction_window: {
      notice_at_seconds: 0,
      start_seconds: 0,
      end_seconds: 18,
      source: "reviewed_ars",
      confidence: "high",
      pause_policy: "pause_on_invite",
      expire_behavior: "return_to_idle",
    },
    notice_marker: "!",
    hook: "系统面板露出来，野蕨菜忽然成了救命线。",
    action_type: "system",
    default_options: [
      "这菜真能救命",
      "先别让人看见",
      "等离开灶台再试",
    ],
    companion_lead: "这一下我都替她绷住了。",
    companion_exchange: {
      schema_version: "companion_exchange_pack.v0.1",
      scene_signal: "系统面板露出来，野蕨菜忽然成了救命线",
      window_rationale: "EP03 test fixture keeps the active marker scoped to this episode.",
      notice_marker: "!",
      companion_lead: "这一下我都替她绷住了。",
      reply_candidates: [
        {
          candidate_id: "preset_0",
          display_text: "这菜真能救命",
          action_payload: { text: "这菜真能救命", action_type: "system", intent: "test_system_resource" },
          selected_echo: "这句我懂，眼前这点东西突然像救命线了。",
          emotion_role: "惊讶",
          semantic_role: "system_resource_surprise",
          distinctness_rationale: "Names the surprise of the resource.",
          evidence_refs: ["huangnian_ep03_u001"],
          constraint_refs: ["current_scene_only"],
        },
        {
          candidate_id: "preset_1",
          display_text: "先别让人看见",
          action_payload: { text: "先别让人看见", action_type: "system", intent: "hide_system_surface" },
          selected_echo: "对，这时候先别让所有人的眼神都追过来。",
          emotion_role: "警惕",
          semantic_role: "visibility_boundary",
          distinctness_rationale: "Keeps the response about exposure risk.",
          evidence_refs: ["huangnian_ep03_u001"],
          constraint_refs: ["current_scene_only"],
        },
        {
          candidate_id: "preset_2",
          display_text: "等离开灶台再试",
          action_payload: { text: "等离开灶台再试", action_type: "system", intent: "delay_test" },
          selected_echo: "这句稳，先把当下这口气压住，再找地方确认。",
          emotion_role: "收边界",
          semantic_role: "delay_and_verify",
          distinctness_rationale: "Keeps the viewer inside the current window.",
          evidence_refs: ["huangnian_ep03_u001"],
          constraint_refs: ["current_scene_only"],
        },
      ],
      custom_reply_policy: {
        allowed: true,
        runtime_personalization: "bounded",
        reject_or_soften: ["future branch claim", "source-window-unsupported fact"],
      },
      evidence_refs: ["huangnian_ep03_u001"],
      constraint_refs: ["current_scene_only"],
      blocked_claims: ["Do not claim later-episode outcomes."],
      review_status: "reviewed",
    },
  });
}

function makeEpisodeMoment(
  episodeId: string,
  hook: string,
  overrides: Record<string, unknown> = {},
) {
  return makeMomentSummary({
    moment_id: `${episodeId}_m001`,
    source_drama: {
      title: "荒年全村啃树皮，我有系统满仓肉",
      episode_id: episodeId,
      runtime_video_url: `/assets/branch3/dramas/huangnian/${episodeId}.mp4`,
    },
    interaction_window: {
      notice_at_seconds: 6,
      start_seconds: 6,
      end_seconds: 18,
      source: "reviewed_ars",
      confidence: "high",
      pause_policy: "pause_on_invite",
      expire_behavior: "return_to_idle",
    },
    hook,
    default_options: ["这段我先替他说一句", "先别冲，留个后手", "这口气不能白咽"],
    ...overrides,
  });
}

function moveVideoTo(video: HTMLVideoElement, currentTime: number) {
  Object.defineProperty(video, "currentTime", { configurable: true, value: currentTime, writable: true });
  fireEvent.timeUpdate(video);
}

function stubMomentsFetch() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
      return jsonResponse([makeMomentSummary()]);
    }
    if (url.endsWith("/api/deadman/runtime/session/event")) {
      return jsonResponse(makeRuntimeResponse(JSON.parse(String(init?.body || "{}"))));
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Deadman standalone app", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("opens on a mobile drama catalog (data-driven) and enters the 陪看 player", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas")) {
        return jsonResponse([{ drama_id: "huangnian", title: "荒年全村啃树皮，我有系统满仓肉", moment_count: 5 }]);
      }
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        return jsonResponse(makeRuntimeResponse(JSON.parse(String(init?.body || "{}"))));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(screen.getByRole("main", { name: "看剧搭子短剧目录" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /进入/ }));

    expect(screen.getByRole("region", { name: "看剧搭子播放器" })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/deadman/dramas/huangnian/moments", expect.any(Object)));
  });

  it("can still render the 陪看 mobile player directly for legacy demo URLs", async () => {
    const fetchMock = stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    expect(screen.getByRole("region", { name: "看剧搭子播放器" })).toBeInTheDocument();
    expect(screen.getByLabelText("短剧 MP4 播放器")).not.toHaveAttribute("src");
    expect(screen.getByTestId("branch3-hook")).toHaveTextContent("最后一点野菜");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/deadman/dramas/huangnian/moments", expect.any(Object)));
    expect(screen.getAllByTestId("branch3-highlight-marker")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /1:05 四蛋把兔子/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();
  });

  it("does not open a future highlight before its interaction window", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });

    await user.click(screen.getByRole("button", { name: "看剧搭子待机中" }));
    expect(screen.queryByRole("button", { name: /四蛋该吃肉/ })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();

    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    expect(await screen.findByText("我刚刚真想替四蛋说一句。")).toBeInTheDocument();
    expect(screen.queryByText("哪句像你想说的？")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /四蛋该吃肉/ })).toBeInTheDocument();
  });

  it("dismisses an open companion bubble when the viewer taps outside it", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));

    expect(await screen.findByLabelText("看剧搭子互动气泡")).toBeInTheDocument();
    fireEvent.pointerDown(screen.getByRole("region", { name: "看剧搭子播放器" }));

    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();
  });

  it("can reopen from idle inside the active interaction window after dismissal", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));

    expect(await screen.findByLabelText("看剧搭子互动气泡")).toBeInTheDocument();
    fireEvent.pointerDown(screen.getByRole("region", { name: "看剧搭子播放器" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "看剧搭子待机中" }));
    expect(await screen.findByRole("button", { name: /四蛋该吃肉/ })).toBeInTheDocument();
  });

  it("does not reopen a completed highlight after continuing", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    await user.click(await screen.findByRole("button", { name: /四蛋该吃肉/ }));
    await user.click(await screen.findByRole("button", { name: "继续看 ▷" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "看剧搭子待机中" }));

    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();
  });

  it("uses pack interaction windows for companion notice timing", async () => {
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });

    moveVideoTo(video, 64);
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();

    moveVideoTo(video, 66);
    expect(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("slider", { name: "播放进度" }), { target: { value: "90" } });
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();
  });

  it("keeps playback running on notice and pauses only when opening choices", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    const pauseSpy = vi.spyOn(video, "pause").mockImplementation(() => undefined);
    Object.defineProperty(video, "paused", { configurable: true, value: false });

    moveVideoTo(video, 66);
    expect(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" })).toBeInTheDocument();
    expect(pauseSpy).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    expect(pauseSpy).toHaveBeenCalledTimes(1);
    expect(await screen.findByLabelText("看剧搭子互动气泡")).toBeInTheDocument();
  });

  it("lets the idle companion reopen a missed (started-but-passed) highlight after its window", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });

    // The window started at 65 and ends at 85; at t=90 it has passed and the companion is idle.
    // The viewer missed it, so the companion must stay tappable and reopen that window's interaction.
    moveVideoTo(video, 90);
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "看剧搭子待机中" }));

    expect(await screen.findByLabelText("看剧搭子互动气泡")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /四蛋该吃肉/ })).toBeInTheDocument();
  });

  it("auto-shows the exclaim notice when playback reaches a window, with no tap", async () => {
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });

    // Idle before the window (notice_at = 65).
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();
    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();

    // A plain timeupdate crossing the window auto-promotes idle → notice_exclaim (!), no tap.
    moveVideoTo(video, 66);
    expect(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" })).toBeInTheDocument();
    // The notice does not open the choices bubble on its own.
    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();
  });

  it("ignores an idle companion tap before any window has started", async () => {
    const user = userEvent.setup();
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1");
    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });

    // At t=10, before the window starts at 65, the idle companion tap must be a no-op.
    moveVideoTo(video, 10);
    expect(screen.getByRole("button", { name: "看剧搭子待机中" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "看剧搭子待机中" }));

    expect(screen.queryByLabelText("看剧搭子互动气泡")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /四蛋该吃肉/ })).not.toBeInTheDocument();
  });

  it("keeps markers scoped to the active episode when the pack contains multiple episodes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary(), makeEpisodeThreeMoment()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        return jsonResponse(makeRuntimeResponse(JSON.parse(String(init?.body || "{}"))));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1");

    render(<App />);

    await screen.findByRole("button", { name: /0:00 系统面板露出来/ });
    expect(screen.getAllByTestId("branch3-highlight-marker")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /四蛋抓到兔子/ })).not.toBeInTheDocument();
  });

  it("can select a non-default episode from the promoted pack", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary(), makeEpisodeThreeMoment()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        return jsonResponse(makeRuntimeResponse(JSON.parse(String(init?.body || "{}"))));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1&episodeId=huangnian_ep03");

    render(<App />);

    expect(await screen.findByRole("button", { name: /0:00 系统面板露出来/ })).toBeInTheDocument();
    expect(screen.getAllByTestId("branch3-highlight-marker")).toHaveLength(1);
    expect(screen.getByLabelText("短剧 MP4 播放器")).toHaveAttribute(
      "src",
      "/assets/branch3/dramas/huangnian/huangnian_ep03.mp4",
    );
    expect(screen.queryByRole("button", { name: /四蛋抓到兔子/ })).not.toBeInTheDocument();
  });

  it("builds a lightweight episode picker from imported moment pack data", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([
          makeMomentSummary({
            source_drama: {
              title: "荒年全村啃树皮，我有系统满仓肉",
              episode_id: "huangnian_ep12",
              runtime_video_url: "/assets/branch3/dramas/huangnian/huangnian_ep12.mp4",
            },
          }),
          makeEpisodeThreeMoment(),
          makeEpisodeMoment("huangnian_ep04", "偷粮帽子扣下来，先问凭什么。"),
          makeEpisodeMoment("huangnian_ep06", "白米一露，全家眼神都变了。"),
          makeEpisodeMoment("huangnian_ep07", "儿媳被逼吃脏饭，桌上没人站出来。"),
        ]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        return jsonResponse(makeRuntimeResponse(JSON.parse(String(init?.body || "{}"))));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1");

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /EP03/ }));
    const episodePicker = screen.getByRole("region", { name: "选择演示集" });
    expect(episodePicker).toBeInTheDocument();
    expect(within(episodePicker).getAllByRole("button", { name: /EP\d+/ })).toHaveLength(5);

    await user.click(within(episodePicker).getByRole("button", { name: /EP03/ }));

    expect(screen.queryByRole("region", { name: "选择演示集" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("短剧 MP4 播放器")).toHaveAttribute(
      "src",
      "/assets/branch3/dramas/huangnian/huangnian_ep03.mp4",
    );
    expect(screen.getByRole("button", { name: /0:00 系统面板露出来/ })).toBeInTheDocument();
  });

  it("accepts a videoUrl query parameter in standalone mode", () => {
    stubMomentsFetch();
    window.history.replaceState({}, "", "/?branch3_player=1&videoUrl=/assets/custom/drama.mp4");

    render(<App />);

    expect(screen.getByLabelText("短剧 MP4 播放器")).toHaveAttribute("src", "/assets/custom/drama.mp4");
  });

  it("posts a mouthpiece candidate action to the Deadman runtime API", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        const body = JSON.parse(String(init?.body));
        if (body.event_type !== "user_action") {
          return jsonResponse(makeRuntimeResponse(body));
        }
        expect(init?.method).toBe("POST");
        expect(body.event_type).toBe("user_action");
        expect(body.moment_id).toBe("huangnian_ep12_m001");
        expect(body.action.source).toBe("preset_candidate");
        expect(body.action.candidate_id).toBe("preset_0");
        expect(body.action.text).toBe("四蛋该吃肉");
        expect(body.action.action_payload.text).toBe("今晚分兔肉，先让四蛋确认自己也有份");
        return jsonResponse(makeRuntimeResponse(body));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1");

    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    await user.click(await screen.findByRole("button", { name: /四蛋该吃肉/ }));

    expect(await screen.findByText(/我接住你咯/)).toBeInTheDocument();
    expect(screen.getByText(/后端搭子文本：四蛋先确认自己被照顾/)).toBeInTheDocument();
    expect(screen.getByText(/有50%其他观众也这么想/)).toBeInTheDocument();
    expect(screen.queryByText(/原剧情锚点/)).not.toBeInTheDocument();
    expect(screen.queryByText(/大家都怎么选/)).not.toBeInTheDocument();
    expect(screen.queryByText("结果图像位")).not.toBeInTheDocument();
    expect(screen.queryByText(/P0 result image slot reserved/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "回到原剧情" })).not.toBeInTheDocument();
    expect(screen.queryByText(/score_axes/)).not.toBeInTheDocument();
  });

  it("keeps custom action on text-only fallback when no image provider is configured", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        const body = JSON.parse(String(init?.body));
        if (body.event_type !== "user_action") {
          return jsonResponse(makeRuntimeResponse(body));
        }
        expect(body.action.source).toBe("custom");
        return jsonResponse(makeRuntimeResponse(body));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1");

    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    await user.click(await screen.findByRole("button", { name: /我有不同想法/ }));
    await user.type(await screen.findByPlaceholderText(/憋着的那句/), "先稳住四蛋");
    await user.click(screen.getByRole("button", { name: "送" }));

    expect(await screen.findByText(/我接住你咯/)).toBeInTheDocument();
    expect(screen.getByText(/后端搭子文本/)).toBeInTheDocument();
    expect(screen.queryByText(/实时图像生成未配置/)).not.toBeInTheDocument();
  });

  it("renders failed judgment as a structured error state with retry and close", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.endsWith("/api/deadman/runtime/session/event")) {
        const body = JSON.parse(String(init?.body || "{}"));
        if (body.event_type === "runtime_retry") {
          return jsonResponse(makeRuntimeResponse({ ...body, event_type: "user_action" }));
        }
        if (body.event_type !== "user_action") {
          return jsonResponse(makeRuntimeResponse(body));
        }
        return jsonResponse({
          viewer_session_id: body.viewer_session_id,
          event_id: body.event_id,
          status: "error",
          companion: {
            next_state: "error",
            marker: null,
            utterance: "这次我卡住了，刚才那手先收一下。",
            should_interrupt: true,
          },
          moment: {
            moment_id: body.moment_id,
            interaction_window_active: true,
            default_options: makeMomentSummary().default_options,
            mouthpiece_candidates_schema_version: makeMomentSummary().mouthpiece_candidates_schema_version,
            mouthpiece_candidates: makeMomentSummary().mouthpiece_candidates,
            hook: makeMomentSummary().hook,
          },
          judgment: null,
          result_surface: null,
          session_memory: {
            last_choice_summary: "",
            safe_to_reference: false,
          },
          engine: {
            mode: "host_policy",
            cab_session_id: "deadman-viewer-test-session",
          },
          error: {
            code: "runtime_failed",
            message: "CABRuntime execution failed.",
            retryable: true,
          },
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/?branch3_player=1");

    render(<App />);

    const video = screen.getByLabelText("短剧 MP4 播放器") as HTMLVideoElement;
    await screen.findByRole("button", { name: /1:05 四蛋把兔子/ });
    moveVideoTo(video, 66);
    await user.click(screen.getByRole("button", { name: "看剧搭子发现了一个高情绪介入点" }));
    await user.click(await screen.findByRole("button", { name: /四蛋该吃肉/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("搭子卡住了");
    expect(screen.getByRole("alert")).toHaveTextContent("刚才那手先收一下");
    expect(screen.queryByText(/^判断：/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText(/我接住你咯/)).toBeInTheDocument();
  });
});

// Clean IA: server.py serves the SAME SPA index.html under /Stage, /stage, and /studio; App routes
// ONLY by window.location.pathname (no ?studio_*=1 query gates, no /demo surface). These pin that
// path routing: /studio→pipeline, /studio/pack-review→PackReview, /studio/dataset-review→StudioReview,
// /Stage→viewer catalog, /Stage?branch3_player=1→player.
describe("Deadman path-only IA routing", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("/studio renders the React Studio pipeline (not the catalog)", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas")) {
        return jsonResponse([{ drama_id: "huangnian", title: "荒年剧" }]);
      }
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/studio/");

    render(<App />);

    expect(await screen.findByText("看剧搭子 Studio")).toBeInTheDocument();
    expect(screen.queryByRole("main", { name: "看剧搭子短剧目录" })).not.toBeInTheDocument();
  });

  it("/studio/pack-review renders the PackReview standalone surface (not the pipeline)", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas")) {
        return jsonResponse([{ drama_id: "huangnian", title: "荒年剧" }]);
      }
      if (/\/api\/deadman\/dramas\/[^/]+\/moments$/.test(url)) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.includes("/api/studio/")) {
        return jsonResponse({});
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/studio/pack-review/");

    render(<App />);

    expect(await screen.findByText("看剧搭子 · 已审包人审")).toBeInTheDocument();
    expect(screen.queryByText("看剧搭子 Studio")).not.toBeInTheDocument();
    expect(screen.queryByRole("main", { name: "看剧搭子短剧目录" })).not.toBeInTheDocument();
  });

  it("/studio/dataset-review renders the StudioReview dataset surface (not the pipeline)", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (/\/api\/deadman\/dramas\/[^/]+\/moments$/.test(url)) {
        return jsonResponse([makeMomentSummary()]);
      }
      if (url.includes("/api/studio/review/labels")) {
        return jsonResponse({});
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/studio/dataset-review");

    render(<App />);

    expect(await screen.findByText("看剧搭子 · 人审")).toBeInTheDocument();
    expect(screen.queryByText("看剧搭子 Studio")).not.toBeInTheDocument();
    expect(screen.queryByRole("main", { name: "看剧搭子短剧目录" })).not.toBeInTheDocument();
  });

  it("/Stage renders the viewer catalog by default", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/deadman/dramas")) {
        return jsonResponse([{ drama_id: "huangnian", title: "荒年剧", moment_count: 5 }]);
      }
      if (url.endsWith("/api/deadman/dramas/huangnian/moments")) {
        return jsonResponse([makeMomentSummary()]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/Stage/");

    render(<App />);

    expect(await screen.findByRole("main", { name: "看剧搭子短剧目录" })).toBeInTheDocument();
    expect(screen.queryByText("看剧搭子 Studio")).not.toBeInTheDocument();
  });

  it("/Stage with ?branch3_player=1 deep-link opens the player directly (Studio publish target)", async () => {
    const fetchMock = stubMomentsFetch();
    window.history.replaceState({}, "", "/Stage/?branch3_player=1&seek=66");

    render(<App />);

    expect(screen.getByRole("region", { name: "看剧搭子播放器" })).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/deadman/dramas/huangnian/moments", expect.any(Object)),
    );
    expect(await screen.findByRole("button", { name: /1:05 四蛋把兔子/ })).toBeInTheDocument();
  });
});
