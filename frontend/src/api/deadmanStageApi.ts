/* =============================================================================
 * deadmanStageApi.ts — Surface 1 (Stage · multi-drama list) data layer
 * -----------------------------------------------------------------------------
 * Drop-in companion to the existing frontend/src/api/deadmanApi.ts.
 * It adds the ONE missing call (`listDramas`) plus a pure helper that derives
 * the list-row view-model from the two live endpoints. Field + route names are
 * verbatim from the contract — do not rename.
 *
 *   GET /api/deadman/dramas              -> DeadmanDrama[]
 *   GET /api/deadman/dramas/{id}/moments -> DeadmanMomentSummary[]   (already exists)
 *
 * Reuses requestJson / getDeadmanApiBase / DeadmanMomentSummary from deadmanApi.ts.
 * ===========================================================================*/

import {
  getDeadmanApiBase,
  requestJson,
  listDramaMoments,
  type DeadmanMomentSummary,
} from "./deadmanApi";

/** Shape returned by GET /api/deadman/dramas. Extra fields are tolerated. */
export interface DeadmanDrama {
  drama_id: string;
  title: string;
  /** Optional — if the API serves cover art. Falls back to COVER_FALLBACK below. */
  cover_image_url?: string | null;
  genre_tag?: string | null;
  [key: string]: unknown;
}

/** View-model the Stage list renders one card from. */
export interface StageRow {
  drama_id: string;
  title: string;
  coverUrl: string;
  genreTag: string | null;
  episodeLabel: string | null;
  hook: string | null;
  /** moments.length */
  momentCount: number;
  /** first moment's interaction_window.notice_at_seconds (the "当前高光") */
  currentHighlightSeconds: number | null;
  /** short-drama-app display: play-count label (e.g. "9.2万") */
  playLabel: string | null;
  /** short-drama-app display: total episodes */
  episodeCount: number | null;
}

/**
 * Local cover fallback for the 3 reviewed dramas (data/dramas/{id}).
 * Remove once GET /dramas serves cover_image_url. Keys are the REAL drama_id slugs.
 */
export const COVER_FALLBACK: Record<string, string> = {
  huangnian: "/assets/covers/huangnian.png",
  yunmiao: "/assets/covers/yunmiao.png",
  lihun: "/assets/covers/xingde.png",
};
export const DEFAULT_DEMO_COVER = "/assets/covers/deadman-demo.png";

/**
 * Short-drama-app display meta (play count + total episodes) for the poster grid.
 * Illustrative demo values — swap in real numbers when available.
 */
export const DRAMA_META: Record<string, { plays: string; episodes: number }> = {
  huangnian: { plays: "9.2万", episodes: 20 },
  lihun: { plays: "15.8万", episodes: 20 },
  yunmiao: { plays: "7.3万", episodes: 20 },
};

export async function listDramas(opts: { signal?: AbortSignal } = {}): Promise<DeadmanDrama[]> {
  return requestJson<DeadmanDrama[]>(`${getDeadmanApiBase()}/dramas`, { signal: opts.signal });
}

/** mm:ss formatter (matches the player's clock). */
export function formatClock(totalSeconds: number | null | undefined): string {
  if (totalSeconds == null) return "--:--";
  const s = Math.max(0, Math.round(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Pure: fold one drama + its moments into a StageRow. */
export function deriveStageRow(drama: DeadmanDrama, moments: DeadmanMomentSummary[]): StageRow {
  const sorted = [...moments].sort(
    (a, b) =>
      (a.interaction_window?.notice_at_seconds ?? Infinity) -
      (b.interaction_window?.notice_at_seconds ?? Infinity),
  );
  const first = sorted[0];
  const meta = DRAMA_META[drama.drama_id];
  return {
    drama_id: drama.drama_id,
    title: drama.title,
    coverUrl: drama.cover_image_url || COVER_FALLBACK[drama.drama_id] || DEFAULT_DEMO_COVER,
    genreTag: drama.genre_tag ?? null,
    episodeLabel: first?.source_drama?.episode_id ?? null,
    hook: first?.hook ?? null,
    momentCount: moments.length,
    currentHighlightSeconds: first?.interaction_window?.notice_at_seconds ?? null,
    playLabel: meta?.plays ?? null,
    // 显示真实「可看集数」= 有互动点的不同集数（不再硬编码 20，与实际可看内容对齐）。
    episodeCount:
      new Set(moments.map((m) => m.source_drama?.episode_id).filter(Boolean)).size || null,
  };
}

/**
 * Loads the whole Stage list: GET /dramas, then GET /dramas/{id}/moments per drama.
 * (Mirrors the brief — per-drama highlight count/time come from /moments.)
 */
export async function loadStageRows(opts: { signal?: AbortSignal } = {}): Promise<StageRow[]> {
  const dramas = await listDramas(opts);
  return Promise.all(
    dramas.map(async (drama) => {
      const moments = await listDramaMoments(drama.drama_id, { signal: opts.signal });
      return deriveStageRow(drama, moments);
    }),
  );
}
