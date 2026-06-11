// reviewGateApi — Track C wiring for the in-graph human-review GATE.
//
// Contract (studio-graph-centric §4c + §8 decisions #2 + #5):
//   The production graph PAUSES at `owner_review_gate` with status "waiting_for_review".
//   GET /api/studio/run/status/{runId} then carries a `review` payload (RunReview below):
//   ALL accepted packs (one per accepted window), each with its window + scene_signal + lead
//   + the 3 reply candidates. The console pages pack-by-pack (episode-grouped), the owner walks
//   each pack's short-circuit ladder (window → direction → lead → say×3/echo×3), and ONE SUBMIT
//   resumes the same run:
//     POST /api/studio/run/resume/{runId}  { decision, pack_decisions, element_labels }
//   approve resumes straight through promote → playable; promote writes only the approved packs
//   (per-pack token filter, decision #5). Until Track E lands /run/resume the call degrades
//   gracefully (ResumeNotReadyError on 404) so the gate is demoable with a mock onResume.
//
// Mirrors the fetch / base-url style of api/deadmanApi.ts + studio/batchUploadApi.ts.

import type { MomentLabel } from "./reviewApi";

// GatePackLabel = the dataset-review MomentLabel (window/direction/lead/say/echo three-state +
// tags + notes) PLUS an explicit per-pack verdict override the owner can toggle at the gate.
// We extend rather than widen the shared MomentLabel (reviewApi.ts) so the dataset-review surfaces
// (ElementLabelPanel / StudioReview) are untouched.
export interface GatePackLabel extends MomentLabel {
  /** explicit owner override of the derived per-pack verdict ("approve" | "reject"). */
  pack_override?: PackDecision;
}

// ---- review payload shape (Track E produces exactly this under status.review) ------------------

export interface ReviewWindow {
  start_seconds: number;
  end_seconds: number;
  notice_at_seconds?: number;
}

export interface ReviewReplyCandidate {
  display_text: string;
  selected_echo: string;
}

export interface ReviewPack {
  moment_id: string;
  episode_id: string;
  /** display name for episode grouping, e.g. "第1集" */
  episode_name: string;
  drama_id: string;
  scene_signal: string;
  companion_lead: string;
  interaction_window: ReviewWindow;
  /** exactly 3 reply candidates */
  reply_candidates: ReviewReplyCandidate[];
}

export interface RunReview {
  drama_id: string;
  packs: ReviewPack[];
}

// ---- resume request / response -----------------------------------------------------------------

export type PackDecision = "approve" | "reject";

export interface ResumeRunBody {
  /** run-level decision; always "approve" for a SUBMIT that walks the gate (per-pack tokens carry
   *  the real accept/reject — promote filters by pack_decisions). */
  decision: "approve" | "reject";
  /** per-pack derived/overridden verdict, keyed by moment_id */
  pack_decisions: Record<string, PackDecision>;
  /** the taste signal: per-pack label (window/direction/element marks + tags + notes + override),
   *  keyed by moment_id, so the dataset captures the human read even on approve. */
  element_labels: Record<string, GatePackLabel>;
}

export interface ResumeRunResult {
  run_id: string;
  status?: string;
  promoted_moment_ids?: string[];
  stage_url?: string;
}

// ---- errors ------------------------------------------------------------------------------------

/** Thrown when /api/studio/run/resume/{runId} is not yet served (404) — i.e. Track E isn't wired.
 *  The gate degrades to a clear "backend not ready" state instead of a generic failure. */
export class ResumeNotReadyError extends Error {
  constructor(message = "审阅恢复后端尚未就绪（/api/studio/run/resume 未上线）") {
    super(message);
    this.name = "ResumeNotReadyError";
  }
}

// ---- base url ----------------------------------------------------------------------------------
// Same /api/studio/* convention + `studioApiBase` query override as batchUploadApi.

const DEFAULT_STUDIO_BASE = "/api/studio";

export function getStudioApiBase(): string {
  let queryBase: string | undefined;
  if (typeof window !== "undefined" && window.location?.search) {
    queryBase = new URLSearchParams(window.location.search).get("studioApiBase")?.trim() || undefined;
  }
  const configuredBase = import.meta.env.VITE_DEADMAN_STUDIO_API_BASE_URL?.trim();
  return (queryBase || configuredBase || DEFAULT_STUDIO_BASE).replace(/\/$/, "");
}

// ---- resume ------------------------------------------------------------------------------------

/** POST the review verdicts to resume the paused graph run.
 *  Throws ResumeNotReadyError on 404 (backend not yet wired), or Error on any other failure. */
export async function resumeRun(
  runId: string,
  body: ResumeRunBody,
  signal?: AbortSignal,
): Promise<ResumeRunResult> {
  const res = await fetch(`${getStudioApiBase()}/run/resume/${encodeURIComponent(runId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (res.status === 404) {
    throw new ResumeNotReadyError();
  }

  const data = (await res.json().catch(() => null)) as
    | (ResumeRunResult & { error?: { message?: string } })
    | null;

  if (!res.ok || (data && (data as { error?: unknown }).error)) {
    const message = data?.error?.message || `恢复运行失败 (${res.status})`;
    throw new Error(message);
  }
  if (!data) {
    throw new Error("恢复运行返回了空响应");
  }
  return data;
}
