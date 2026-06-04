import {
  getDeadmanApiBase,
  requestJson,
  type DeadmanJudgmentAction,
  type DeadmanJudgmentResponse,
} from "./deadmanApi";

export type DeadmanRuntimeEventType =
  | "session_start"
  | "player_tick"
  | "moment_notice"
  | "companion_tap"
  | "user_action"
  | "continue_watching"
  | "runtime_retry";

export type DeadmanRuntimeMicroCue = {
  kind: "aggregate_hint" | "cost_hint" | "visual_fallback_hint";
  text: string;
};

export type DeadmanResultSurface = {
  mode: "single_narrative";
  text: string;
  micro_cue?: DeadmanRuntimeMicroCue | null;
  continue_label: string;
  stamp?: string | null;
};

export type DeadmanRuntimeResponse = {
  viewer_session_id: string;
  event_id: string;
  status: "ok" | "error";
  companion: {
    next_state: string;
    marker?: string | null;
    utterance?: string;
    should_interrupt?: boolean;
  };
  moment: {
    moment_id?: string | null;
    interaction_window_active: boolean;
    default_options: string[];
    hook?: string | null;
  };
  judgment?: DeadmanJudgmentResponse | null;
  result_surface?: DeadmanResultSurface | null;
  session_memory: {
    last_choice_summary: string;
    safe_to_reference: boolean;
  };
  engine: {
    mode: string;
    cab_session_id?: string | null;
  };
  error?: {
    code: string;
    message: string;
    retryable?: boolean;
  } | null;
};

export type DeadmanRuntimeEventPayload = {
  viewer_session_id: string;
  event_id: string;
  event_type: DeadmanRuntimeEventType;
  drama_id: string;
  episode_id?: string;
  playback_time_seconds?: number;
  moment_id?: string;
  companion_state?: string;
  action?: DeadmanJudgmentAction;
};

const VIEWER_SESSION_KEY = "deadman_viewer_session_id";

export function getOrCreateViewerSessionId(): string {
  const existing = window.sessionStorage.getItem(VIEWER_SESSION_KEY);
  if (existing) {
    return existing;
  }
  const next = `web-${createRuntimeEventId()}`;
  window.sessionStorage.setItem(VIEWER_SESSION_KEY, next);
  return next;
}

export function createRuntimeEventId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export async function sendRuntimeEvent(payload: DeadmanRuntimeEventPayload): Promise<DeadmanRuntimeResponse> {
  return requestJson<DeadmanRuntimeResponse>(`${getDeadmanApiBase()}/runtime/session/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...payload,
      viewer_profile: {
        tone: "friend",
        risk_preference: "balanced",
      },
    }),
  });
}
