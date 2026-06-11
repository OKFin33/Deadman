// In-player review labels — shared schema across frontend + backend store + dataset builder.
// Short-circuit gates (a higher gate failing makes lower labeling moot):
//   window === "reject"   -> gate "window_reject"   : moment isn't a companion moment; no content labeled
//   direction === "reject"-> gate "direction_reject": window ok but the read/方向 is wrong; whole exchange re-authored
//   else                  -> gate "detailed"        : per-element lead/say/echo verdicts (the granular taste signal)
// The Python dataset builder (tools/ars/deadman_build_review_dataset.py) mirrors momentGate() exactly.
export type ElLabel = { v?: "ok" | "bad" | "abstain"; tag?: string; note?: string };
export type MomentLabel = {
  window?: string; // accept | accept_with_minor_tweak | reject | abstain
  window_note?: string;
  direction?: "ok" | "reject";
  direction_note?: string;
  lead?: ElLabel;
  says?: ElLabel[];
  echoes?: ElLabel[];
};
export type ReviewLabels = Record<string, MomentLabel>;

export type Gate = "window_reject" | "direction_reject" | "detailed";
export function momentGate(l: MomentLabel | undefined): Gate {
  if (l?.window === "reject") return "window_reject";
  if (l?.direction === "reject") return "direction_reject";
  return "detailed";
}

const BASE = "/api/studio/review";

export async function loadReviewLabels(): Promise<ReviewLabels> {
  try {
    const r = await fetch(`${BASE}/labels`);
    if (!r.ok) return {};
    const data: unknown = await r.json();
    return data && typeof data === "object" ? (data as ReviewLabels) : {};
  } catch {
    return {};
  }
}

export async function saveReviewLabels(labels: ReviewLabels): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/label`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(labels),
    });
    return r.ok;
  } catch {
    return false;
  }
}
