import { useMemo, useState } from "react";
import { momentGate } from "./reviewApi";
import { PackReviewLadder, leadIsBad } from "./PackReviewLadder";
import {
  resumeRun,
  ResumeNotReadyError,
  type GatePackLabel,
  type PackDecision,
  type ResumeRunBody,
  type ResumeRunResult,
  type ReviewPack,
  type RunReview,
} from "./reviewGateApi";
import "./reviewStudio.css";

// ReviewGate — Track C: the in-graph human-review GATE as a SPLIT view.
//   left  = mobile player iframe deep-linked to THIS pack's window (StudioReview's PlayerFrame idiom)
//   right = the per-pack short-circuit ladder (PackReviewLadder) + episode-grouped pack nav + SUBMIT.
// It appears when a production run is paused at owner_review_gate (status "waiting_for_review").
//
// Granularity (decision #2): per-pack, episode-grouped, ONE pack at a time, player-assisted.
// SUBMIT (decision #5): one button (enabled once every pack has a verdict) → resumeRun() with
// pack_decisions + element_labels; approve resumes straight through promote → playable.

export interface ReviewGateProps {
  runId: string;
  review: RunReview; // the waiting payload
  /** integration hook: called after a successful resume (Track F deep-links to the new drama). */
  onResolved?: (result: { promoted_moment_ids?: string[]; stage_url?: string }) => void;
  /** test/demo override for the resume call; defaults to the real resumeRun(). */
  onResume?: (runId: string, body: ResumeRunBody) => Promise<ResumeRunResult>;
}

// --- per-pack derived verdict (decision #2) ----------------------------------------------------
// A pack is REJECT iff window rejected OR direction rejected OR lead bad; otherwise APPROVE.
// say/echo `bad` marks are recorded as taste signal but do NOT auto-reject (the pack is one
// companion_exchange, promoted whole). The owner can still explicitly override via the verdict pill.
export function derivedVerdict(label: GatePackLabel | undefined): PackDecision {
  const gate = momentGate(label);
  if (gate === "window_reject" || gate === "direction_reject") return "reject";
  if (leadIsBad(label)) return "reject";
  return "approve";
}

/** the effective verdict = explicit override if set, else the derived one. */
function effectiveVerdict(label: GatePackLabel | undefined): PackDecision {
  return label?.pack_override ?? derivedVerdict(label);
}

/** a pack counts as "visited" once any review signal has been touched (window/direction/lead/override). */
function isVisited(label: GatePackLabel | undefined): boolean {
  if (!label) return false;
  return Boolean(
    label.window ||
      label.direction ||
      label.lead?.v ||
      label.pack_override ||
      (label.says ?? []).some((e) => e?.v) ||
      (label.echoes ?? []).some((e) => e?.v),
  );
}

function PlayerFrame({ pack }: { pack: ReviewPack }) {
  const win = pack.interaction_window ?? {};
  const start = Math.max(0, Number(win.start_seconds ?? win.notice_at_seconds ?? 0) - 2);
  const src = `/Stage/?branch3_player=1&dramaId=${encodeURIComponent(pack.drama_id)}&episodeId=${encodeURIComponent(pack.episode_id)}&seek=${start}`;
  return (
    <div>
      <iframe key={pack.moment_id} src={src} title="真播放器" allow="autoplay" className="sr-frame" />
      <div className="sr-hint">
        真播放器 · 跳到 {start}s → 播到窗口出「!」，点搭子看 3 条 + 接话。对着观众真实体验审这条 pack。
      </div>
    </div>
  );
}

export function ReviewGate({ runId, review, onResolved, onResume }: ReviewGateProps): JSX.Element {
  const packs = review.packs ?? [];
  const [idx, setIdx] = useState(0);
  const [labels, setLabels] = useState<Record<string, GatePackLabel>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");
  const [notReady, setNotReady] = useState(false);

  const current = packs[idx];
  const curLabel = current ? labels[current.moment_id] : undefined;

  const visitedCount = useMemo(
    () => packs.filter((p) => isVisited(labels[p.moment_id])).length,
    [packs, labels],
  );
  const allVisited = packs.length > 0 && visitedCount === packs.length;

  // episode-grouped ordering for the nav rail: stable group-by episode, preserving pack order.
  const groups = useMemo(() => {
    const order: string[] = [];
    const byEp = new Map<string, { name: string; packs: { pack: ReviewPack; index: number }[] }>();
    packs.forEach((pack, i) => {
      if (!byEp.has(pack.episode_id)) {
        byEp.set(pack.episode_id, { name: pack.episode_name || pack.episode_id, packs: [] });
        order.push(pack.episode_id);
      }
      byEp.get(pack.episode_id)!.packs.push({ pack, index: i });
    });
    return order.map((ep) => ({ episode_id: ep, ...byEp.get(ep)! }));
  }, [packs]);

  const updateLabel = (momentId: string, next: GatePackLabel) => {
    setLabels((prev) => ({ ...prev, [momentId]: next }));
  };

  const setOverride = (momentId: string, verdict: PackDecision) => {
    setLabels((prev) => {
      const existing = prev[momentId] ?? {};
      // toggle off if the override already matches; otherwise set it.
      const next: GatePackLabel =
        existing.pack_override === verdict
          ? { ...existing, pack_override: undefined }
          : { ...existing, pack_override: verdict };
      return { ...prev, [momentId]: next };
    });
  };

  const go = (next: number) => setIdx(Math.max(0, Math.min(packs.length - 1, next)));

  const handleSubmit = async () => {
    if (!allVisited || submitting) return;
    setSubmitting(true);
    setError("");
    setNotReady(false);

    const pack_decisions: Record<string, PackDecision> = {};
    const element_labels: Record<string, GatePackLabel> = {};
    for (const p of packs) {
      const label = labels[p.moment_id];
      pack_decisions[p.moment_id] = effectiveVerdict(label);
      element_labels[p.moment_id] = label ?? {};
    }

    const body: ResumeRunBody = { decision: "approve", pack_decisions, element_labels };
    const resume = onResume ?? resumeRun;

    try {
      const result = await resume(runId, body);
      onResolved?.({
        promoted_moment_ids: result.promoted_moment_ids,
        stage_url: result.stage_url,
      });
    } catch (e: unknown) {
      if (e instanceof ResumeNotReadyError) {
        setNotReady(true);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (packs.length === 0) {
    return (
      <div className="studio-review rg-root">
        <div className="center">本次运行没有待审 pack。</div>
      </div>
    );
  }

  const curVerdict = effectiveVerdict(curLabel);

  return (
    <div className="studio-review rg-root">
      <aside>
        <div className="sr-brand">
          <span className="sr-brand__name">看剧搭子 · 在图审阅</span>
          <span className="sr-brand__sub">{packs.length} 个待审片段</span>
        </div>
        <div className="rg-progress" data-testid="rg-progress">
          已审 {visitedCount} / 共 {packs.length}
        </div>
        <div className="sr-rail rg-rail">
          {groups.map((g) => (
            <div key={g.episode_id} className="rg-group">
              <div className="rg-group__name">{g.name}</div>
              {g.packs.map(({ pack, index }) => {
                const lab = labels[pack.moment_id];
                const visited = isVisited(lab);
                const verdict = effectiveVerdict(lab);
                return (
                  <button
                    key={pack.moment_id}
                    data-testid={`rg-pack-${pack.moment_id}`}
                    className={`sr-moment rg-pack${index === idx ? " is-active" : ""}${visited ? " is-visited" : ""}`}
                    onClick={() => go(index)}
                  >
                    <span className={`sr-moment__mark rg-mark is-${verdict}`}>{verdict === "approve" ? "✓" : "退"}</span>
                    <span className="sr-moment__id">{pack.moment_id}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      <main>
        <div className="sr-main">
          <div className="sr-stage">
            <div className="sr-stage__head">
              <span className="sr-title">{current.episode_name} · pack {idx + 1}/{packs.length}</span>
            </div>
            <PlayerFrame pack={current} />
          </div>

          <div className="sr-eval rg-eval">
            <div className="rg-nav">
              <button className="rg-step" data-testid="rg-prev" disabled={idx === 0} onClick={() => go(idx - 1)}>← 上一条</button>
              <span className="rg-verdict-pill" data-testid="rg-verdict">
                <button
                  className={`pr-approved${curVerdict === "approve" ? " on" : ""}`}
                  data-testid="rg-set-approve"
                  onClick={() => setOverride(current.moment_id, "approve")}
                >通过</button>
                <button
                  className={`pr-rejected${curVerdict === "reject" ? " on" : ""}`}
                  data-testid="rg-set-reject"
                  onClick={() => setOverride(current.moment_id, "reject")}
                >退回</button>
              </span>
              <button className="rg-step" data-testid="rg-next" disabled={idx === packs.length - 1} onClick={() => go(idx + 1)}>下一条 →</button>
            </div>

            {curLabel?.pack_override && (
              <div className="rg-override-note" data-testid="rg-override-note">已手动覆盖默认判定</div>
            )}

            <PackReviewLadder
              lead={current.companion_lead ?? ""}
              candidates={current.reply_candidates ?? []}
              value={curLabel ?? {}}
              onChange={(next) => updateLabel(current.moment_id, next)}
            />

            <div className="rg-submit-row">
              <button
                className="rg-submit"
                data-testid="rg-submit"
                disabled={!allVisited || submitting}
                onClick={handleSubmit}
              >
                {submitting ? "提交中…" : `提交并恢复运行（${visitedCount}/${packs.length}）`}
              </button>
              {!allVisited && <span className="rg-submit-hint">每条 pack 都给出判定后才能提交</span>}
              {notReady && <span className="rg-submit-err" data-testid="rg-not-ready">恢复后端尚未就绪（/run/resume 未上线）</span>}
              {error && <span className="rg-submit-err" data-testid="rg-error">{error}</span>}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
