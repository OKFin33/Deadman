// studioPipelineApi — the two additive Studio-console wiring calls used by StudioPipeline:
//   POST /api/studio/author  {drama_id, moment_id, agentic} → {companion_lead, replies, rounds, judge_available}
//   POST /api/studio/promote {drama_id, moment_id, draft}     → {drama_id, stage_url, episode_id, …}
// Both endpoints already exist server-side (additive, env-only creds). The agentic author call is
// long (~100–200s, judge-dominated) and is NOT awaited on the render thread by callers.
import type { RoundTrace } from "./AgenticPipelineViz";

export type AuthorReply = {
  display_text: string;
  echo: string;
  motivation?: string;
  coverage?: string;
};

export type AuthorResult = {
  drama_id: string;
  moment_id: string;
  episode_id?: string;
  companion_lead: string;
  replies: AuthorReply[];
  rounds?: number | RoundTrace[];
  judge_available?: boolean;
};

export type PromoteResult = {
  drama_id: string;
  title?: string;
  moment_id?: string;
  episode_id?: string;
  stage_url: string;
};

async function postJson<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const data = (await res.json()) as T & { error?: { message?: string } };
  if (!res.ok || (data && (data as { error?: unknown }).error)) {
    const message = (data as { error?: { message?: string } })?.error?.message || `请求失败 (${res.status})`;
    throw new Error(message);
  }
  return data as T;
}

// agentic:true → run the v0.3 taste self-correction loop (returns rounds + judge_available).
// agentic:false → the existing single-shot path (skip / 单发).
export function authorMoment(
  drama_id: string,
  moment_id: string,
  agentic: boolean,
  signal?: AbortSignal,
): Promise<AuthorResult> {
  return postJson<AuthorResult>("/api/studio/author", { drama_id, moment_id, agentic }, signal);
}

export function promoteDraft(
  drama_id: string,
  moment_id: string,
  draft: { companion_lead: string; replies: AuthorReply[] },
  signal?: AbortSignal,
): Promise<PromoteResult> {
  return postJson<PromoteResult>("/api/studio/promote", { drama_id, moment_id, draft }, signal);
}

// ---- A⑤ background agentic run + REAL progress polling ------------------------------------------
// The agentic author is long (~100–200s). Instead of awaiting it on the render thread (which forces
// ⑤ to fake progress), the console STARTS a background run and polls its status for the real
// current_node + per-round traces the backend folds from on_progress events.

export type StartAuthorResult = { run_id: string; status: "running" };

// current_node mirrors AgenticPipelineViz NODES ids; rounds is the REAL per-round trace array.
export type AuthorStatus = {
  run_id: string;
  status: "running" | "done" | "error";
  current_node: string;
  round: number;
  rounds: RoundTrace[];
  result: AuthorResult | null;
  judge_available: boolean | null;
  error: string | null;
};

// POST {agentic:true, background:true} → {run_id, status:"running"} immediately.
export function startAuthor(
  drama_id: string,
  moment_id: string,
  signal?: AbortSignal,
): Promise<StartAuthorResult> {
  return postJson<StartAuthorResult>(
    "/api/studio/author",
    { drama_id, moment_id, agentic: true, background: true },
    signal,
  );
}

// GET /api/studio/author/status/{run_id} — one poll of the run-store entry.
export async function pollAuthorStatus(run_id: string, signal?: AbortSignal): Promise<AuthorStatus> {
  const res = await fetch(`/api/studio/author/status/${encodeURIComponent(run_id)}`, { signal });
  const data = (await res.json()) as AuthorStatus & { error?: unknown };
  if (!res.ok) {
    const message =
      (data as { error?: { message?: string } })?.error?.message || `请求失败 (${res.status})`;
    throw new Error(message);
  }
  return data;
}

// ---- Graph-run API (Track E) — the graph-centric console drives ONE production-graph run --------
// POST /run/start → {run_id}; GET /run/status/{run_id} polled ~1s drives the graph viz (current_node
// + rounds) and, when the graph PAUSES at owner_review_gate, carries the `review` packs for the gate.

import type { RunReview } from "./reviewGateApi";

export type RunPhase = "running" | "waiting_for_review" | "published" | "done" | "error";

export type RunStatus = {
  run_id: string;
  drama_id: string;
  status: RunPhase;
  current_node: string;
  progress?: { node_index: number; total: number };
  rounds: RoundTrace[];
  review: RunReview | null; // present only when status === "waiting_for_review"
  report?: unknown;
  error: string | null;
};

export const RUN_TERMINAL: RunPhase[] = ["waiting_for_review", "published", "done", "error"];

// POST /api/studio/run/start {drama_id, max_rounds} → {run_id, status:"running"} immediately.
export function startRun(
  drama_id: string,
  max_rounds = 2,
  signal?: AbortSignal,
): Promise<{ run_id: string; status: "running" }> {
  return postJson<{ run_id: string; status: "running" }>(
    "/api/studio/run/start",
    { drama_id, max_rounds },
    signal,
  );
}

// GET /api/studio/run/status/{run_id} — one poll of the production run-store entry.
export async function pollRunStatus(run_id: string, signal?: AbortSignal): Promise<RunStatus> {
  const res = await fetch(`/api/studio/run/status/${encodeURIComponent(run_id)}`, { signal });
  const data = (await res.json()) as RunStatus & { error?: unknown };
  if (!res.ok) {
    const message =
      (data as { error?: { message?: string } })?.error?.message || `请求失败 (${res.status})`;
    throw new Error(message);
  }
  return data;
}
