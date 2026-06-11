// Studio pack review labels — the reviewed-pack verdict surface (?studio_pack_review=1).
// Parallel to reviewApi.ts (the dev dataset review): same warm-serif Studio look, same
// element three-state taxonomy (ElLabel), same autosave-to-tmp discipline, but the unit
// under review is a *reviewed* CompanionExchangePack (lead + say×3 + echo×3) and it adds a
// SIMPLIFIED top-level verdict (approved | needs_rework | rejected) + a reason field.
//
// Labels persist ONLY to tmp/studio_pack_review_labels.json (git-ignored) via the additive
// /api/studio/review/pack-label{,s} endpoints. Review NEVER mutates the curated data/dramas packs.
import type { ElLabel } from "./reviewApi";

export type PackVerdict = "approved" | "needs_rework" | "rejected";

export type PackLabel = {
  pack_id: string; // stable key = moment_id (one reviewed pack per moment)
  moment_id: string;
  drama_id: string;
  verdict?: PackVerdict;
  reason?: string;
  lead?: ElLabel;
  says?: ElLabel[];
  echoes?: ElLabel[];
};

export type PackReviewLabels = Record<string, PackLabel>;

const BASE = "/api/studio/review";

export async function loadPackReviewLabels(): Promise<PackReviewLabels> {
  try {
    const r = await fetch(`${BASE}/pack-labels`);
    if (!r.ok) return {};
    const data: unknown = await r.json();
    return data && typeof data === "object" ? (data as PackReviewLabels) : {};
  } catch {
    return {};
  }
}

export async function savePackReviewLabels(labels: PackReviewLabels): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/pack-label`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(labels),
    });
    return r.ok;
  } catch {
    return false;
  }
}
