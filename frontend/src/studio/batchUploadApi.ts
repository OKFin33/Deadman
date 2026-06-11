// batchUploadApi — Track D batch-upload wiring for the Studio graph-run console.
//
// Contract (studio-graph-centric §3a / §4a, owner decision #1 = per-drama batch):
//   POST /api/studio/batch   (multipart/form-data)
//     fields: drama_id (internal string), drama_name (display string),
//             files[] (N videos, repeated), episode_names[] (parallel, same order)
//     → { batch_id, drama_id, drama_name, episodes:[ EpisodeProposal... ] }
//
// The operator picks N clips of ONE drama, names each episode, and gets a per-episode
// "proposed windows" preview (timecoded transcript excerpts) before the graph run kicks off.
// The backend half (Track E) is sequenced AFTER this; until it lands the POST 404s, so the
// component must degrade to a clear "backend not ready" state. We surface that distinctly via
// BatchUploadNotReadyError so the UI can tell "endpoint missing" apart from a real failure.

// ---- response shape (Track E produces exactly this) --------------------------------------------

export interface ProposedWindow {
  window_id: string;
  start_seconds: number;
  end_seconds: number;
  /** when the「想说一句」notice fires inside the window */
  notice_at_seconds: number;
  /** transcript excerpt for the window (read-only preview) */
  excerpt: string;
}

export interface EpisodeProposal {
  episode_id: string;
  /** operator-supplied display name, e.g. "第1集" */
  name: string;
  duration_seconds: number;
  /** whether the ASR ran live or fell back to a bundled sample */
  asr_source: "live" | "sample";
  proposed_windows: ProposedWindow[];
}

export interface BatchResponse {
  batch_id: string;
  drama_id: string;
  drama_name: string;
  episodes: EpisodeProposal[];
}

// ---- request shape ------------------------------------------------------------------------------

export interface BatchFile {
  file: File;
  /** parallel episode name for `file`; same order is preserved into the multipart body */
  episode_name: string;
}

export interface BatchUploadInput {
  drama_id: string;
  drama_name: string;
  files: BatchFile[];
}

// ---- errors -------------------------------------------------------------------------------------

/** Thrown when /api/studio/batch is not yet served (404) — i.e. the backend (Track E) isn't ready.
 *  The UI shows a distinct "backend not ready" state instead of a generic failure. */
export class BatchUploadNotReadyError extends Error {
  constructor(message = "批量上传后端尚未就绪（/api/studio/batch 未上线）") {
    super(message);
    this.name = "BatchUploadNotReadyError";
  }
}

// ---- base url -----------------------------------------------------------------------------------
// Mirrors the /api/studio/* convention (studioPipelineApi.ts hardcodes the relative root); we add a
// `studioApiBase` query override for parity with deadmanApi's `deadmanApiBase` escape hatch.

const DEFAULT_STUDIO_BASE = "/api/studio";

export function getStudioApiBase(): string {
  let queryBase: string | undefined;
  if (typeof window !== "undefined" && window.location?.search) {
    queryBase = new URLSearchParams(window.location.search).get("studioApiBase")?.trim() || undefined;
  }
  const configuredBase = import.meta.env.VITE_DEADMAN_STUDIO_API_BASE_URL?.trim();
  return (queryBase || configuredBase || DEFAULT_STUDIO_BASE).replace(/\/$/, "");
}

// ---- upload -------------------------------------------------------------------------------------

/** POST the batch as multipart/form-data. Files + episode_names are repeated in matching order.
 *  Throws BatchUploadNotReadyError on 404 (backend not yet wired), or Error on any other failure. */
export async function uploadBatch(
  input: BatchUploadInput,
  signal?: AbortSignal,
): Promise<BatchResponse> {
  const form = new FormData();
  form.append("drama_id", input.drama_id);
  form.append("drama_name", input.drama_name);
  for (const { file, episode_name } of input.files) {
    form.append("files", file);
    form.append("episode_names", episode_name);
  }

  const res = await fetch(`${getStudioApiBase()}/batch`, {
    method: "POST",
    body: form, // do NOT set Content-Type — the browser sets the multipart boundary
    signal,
  });

  if (res.status === 404) {
    throw new BatchUploadNotReadyError();
  }

  const data = (await res.json().catch(() => null)) as
    | (BatchResponse & { error?: { message?: string } })
    | null;

  if (!res.ok || (data && (data as { error?: unknown }).error)) {
    const message =
      data?.error?.message || `批量上传失败 (${res.status})`;
    throw new Error(message);
  }
  if (!data) {
    throw new Error("批量上传返回了空响应");
  }
  return data;
}

// ---- helpers (shared with the component + tests) -----------------------------------------------

/** Internal drama_id slug rule from the backend contract. The UI should generate this. */
export const DRAMA_ID_PATTERN = /^[a-z0-9_]+$/;

export function isValidDramaId(value: string): boolean {
  return DRAMA_ID_PATTERN.test(value);
}

export function makeDramaId(displayName: string, seed: number = Date.now()): string {
  const asciiStem = displayName
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 32);
  const stem = asciiStem || "drama";
  const suffix = Math.max(0, seed).toString(36);
  return `${stem}_${suffix}`.slice(0, 64).replace(/_+$/g, "");
}

/** mm:ss clock (matches the player + deadmanStageApi.formatClock). */
export function formatClock(totalSeconds: number | null | undefined): string {
  if (totalSeconds == null || Number.isNaN(totalSeconds)) return "--:--";
  const s = Math.max(0, Math.round(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Default episode name for the Nth (1-based) clip. */
export function defaultEpisodeName(index1Based: number): string {
  return `第${index1Based}集`;
}
