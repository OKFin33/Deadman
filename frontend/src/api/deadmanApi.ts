export type DeadmanMomentSummary = {
  moment_id: string;
  drama_id: string;
  source_drama?: {
    title?: string;
    episode_id?: string;
    time_range_seconds?: [number, number] | null;
    runtime_video_url?: string;
  };
  interaction_window?: {
    notice_at_seconds?: number;
    start_seconds?: number;
    end_seconds?: number;
    source?: "reviewed_ars" | "manual_p0_fallback" | string;
    confidence?: "low" | "medium" | "high" | string;
    pause_policy?: string;
    expire_behavior?: string;
  };
  notice_marker?: string | null;
  hook?: string | null;
  companion_lead?: string | null;
  action_type?: string | null;
  default_options?: string[];
  companion_exchange?: DeadmanCompanionExchange | null;
  mouthpiece_candidates_schema_version?: string | null;
  mouthpiece_candidates?: DeadmanMouthpieceCandidate[];
  result_media?: DeadmanResultMedia;
  original_plot_note?: string | null;
};

export type DeadmanMouthpieceCandidate = {
  candidate_id: string;
  display_text: string;
  action_payload: Record<string, unknown>;
  selected_echo?: string | null;
  emotion_role: string;
  semantic_role: string;
  distinctness_rationale?: string;
  evidence_refs?: string[];
  constraint_refs?: string[];
  friend_voice_seed?: string | null;
  requires_review?: boolean;
};

export type DeadmanCompanionExchange = {
  schema_version: string;
  scene_signal: string;
  window_rationale?: string;
  notice_marker: "!" | "?" | string;
  companion_lead: string;
  reply_candidates: DeadmanMouthpieceCandidate[];
  custom_reply_policy?: Record<string, unknown>;
  evidence_refs?: string[];
  constraint_refs?: string[];
  blocked_claims?: string[];
  review_status?: string;
};

export type DeadmanMediaSlot = {
  option_index?: number;
  status: "placeholder" | "pregenerated" | "not_available" | "generation_pending" | "generation_failed" | string;
  image_url?: string;
  prompt?: string;
  source?: string;
  fallback_text?: string;
};

export type DeadmanResultMedia = {
  preset_options?: DeadmanMediaSlot[];
  custom_action?: {
    status?: string;
    mode?: string;
    timeout_ms?: number;
  };
};

export type DeadmanJudgmentAction = {
  source: "preset_candidate" | "preset" | "custom";
  text: string;
  option_index?: number | null;
  candidate_id?: string | null;
  action_payload?: Record<string, unknown> | null;
};

export type DeadmanJudgmentResponse = {
  drama_id: string;
  moment_id: string;
  action: DeadmanJudgmentAction;
  verdict: {
    label: string;
    stance: "support" | "caution" | "reject_softly";
    summary: string;
  };
  consequence: {
    text: string;
    time_horizon: "current_scene_or_immediate_aftermath";
    watch_flow_fit: "high" | "medium" | "low";
  };
  canon_anchor: {
    original_plot_note: string;
    safe_to_continue: boolean;
  };
  scores: Record<string, number>;
  result_card: {
    mode: "fallback_card";
    title: string;
    prompt: string;
  };
  media?: DeadmanMediaSlot & { type?: "image" };
  aggregate_stats?: {
    mode: "demo_static";
    total_count: number;
    choices: Array<{
      label: string;
      percent: number;
      selected?: boolean;
    }>;
    note: string;
  } | null;
  judgment_basis: {
    evidence_refs: string[];
    applied_constraints: string[];
    inference_notes: string[];
    warnings: string[];
  };
  engine: {
    mode: "demo_deterministic" | "cab_runtime";
    schema_version: string;
  };
};

export class DeadmanApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "DeadmanApiError";
    this.status = status;
    this.code = code;
  }
}

const DEFAULT_API_BASE = "/api/deadman";

export function getDeadmanApiBase(): string {
  const configuredBase = import.meta.env.VITE_DEADMAN_API_BASE_URL?.trim();
  const queryBase = new URLSearchParams(window.location.search).get("deadmanApiBase")?.trim();
  return (queryBase || configuredBase || DEFAULT_API_BASE).replace(/\/$/, "");
}

export async function listDramaMoments(
  dramaId: string,
  options: { signal?: AbortSignal } = {},
): Promise<DeadmanMomentSummary[]> {
  return requestJson<DeadmanMomentSummary[]>(`${getDeadmanApiBase()}/dramas/${dramaId}/moments`, {
    signal: options.signal,
  });
}

export async function createJudgment(
  dramaId: string,
  momentId: string,
  action: DeadmanJudgmentAction,
): Promise<DeadmanJudgmentResponse> {
  return requestJson<DeadmanJudgmentResponse>(`${getDeadmanApiBase()}/judgment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      drama_id: dramaId,
      moment_id: momentId,
      action,
      viewer_profile: {
        tone: "friend",
        risk_preference: action.source === "custom" ? "balanced" : "balanced",
      },
    }),
  });
}

export async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, init);
  const text = await response.text();
  let body: any = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      throw new DeadmanApiError(response.status, "invalid_json", "Deadman API returned a non-JSON response.");
    }
  }
  if (!response.ok) {
    const error = body?.error;
    throw new DeadmanApiError(
      response.status,
      typeof error?.code === "string" ? error.code : "request_failed",
      typeof error?.message === "string" ? error.message : `Deadman API request failed with ${response.status}.`,
    );
  }
  return body as T;
}
