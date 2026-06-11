import type { DeadmanMomentSummary } from "../api/deadmanApi";
import type { ElLabel } from "./reviewApi";
import type { PackLabel, PackVerdict } from "./packReviewApi";
import "./reviewStudio.css";

// PackReview — REUSABLE Studio review surface for ONE reviewed CompanionExchangePack.
// It is the pack-level twin of StudioReview's dataset review: same real-player iframe deep-link
// (PlayerFrame) and the same per-element three-state (达标/不达标/跳过) taxonomy lifted from
// ElementLabelPanel, but the unit is a reviewed pack and the top-level decision is a SIMPLIFIED
// verdict pill row (approved | needs_rework | rejected) + reason — not the dataset gate ladder.
//
// Stateless: the parent owns the PackLabel and persists it (autosave) via packReviewApi.
// It does NOT mutate the pack; scene_signal is shown as immutable context.

const VERDICTS: [PackVerdict, string][] = [
  ["approved", "通过"],
  ["needs_rework", "需返工"],
  ["rejected", "否决"],
];

type Cand = { display_text?: string; selected_echo?: string | null; friend_voice_seed?: string | null };
type Kind = "lead" | "say" | "echo";

function candidatesOf(pack: DeadmanMomentSummary): Cand[] {
  return pack.companion_exchange?.reply_candidates ?? pack.mouthpiece_candidates ?? [];
}

function leadOf(pack: DeadmanMomentSummary): string {
  return pack.companion_exchange?.companion_lead ?? pack.companion_lead ?? "";
}

function sceneSignalOf(pack: DeadmanMomentSummary): string {
  return pack.companion_exchange?.scene_signal ?? "";
}

// Same real-player deep-link as StudioReview's PlayerFrame: the reviewer watches the actual
// 「!」+ 搭子 + 3 候选, then labels each element beside it. key=moment forces reload on change.
function PackPlayerFrame({ pack }: { pack: DeadmanMomentSummary }) {
  const win = pack.interaction_window ?? {};
  const start = Math.max(0, Number(win.start_seconds ?? win.notice_at_seconds ?? 0) - 2);
  const ep = pack.source_drama?.episode_id ?? "";
  const src = `/Stage/?branch3_player=1&dramaId=${encodeURIComponent(pack.drama_id)}&episodeId=${encodeURIComponent(ep)}&seek=${start}`;
  return (
    <div>
      <iframe key={pack.moment_id} src={src} title="真播放器" allow="autoplay" className="sr-frame" />
      <div className="sr-hint">
        真播放器 · 跳到 {start}s → 播到窗口出「!」，点搭子看 3 条 + 接话。对着观众真实体验评这条已审包。
      </div>
    </div>
  );
}

export function PackReview({
  pack,
  value,
  onVerdict,
}: {
  pack: DeadmanMomentSummary;
  value: PackLabel;
  onVerdict?: (label: PackLabel) => void;
}) {
  const candidates = candidatesOf(pack);
  const lead = leadOf(pack);
  const sceneSignal = sceneSignalOf(pack);
  const says = value.says ?? [];
  const echoes = value.echoes ?? [];

  const emit = (next: PackLabel) => onVerdict?.(next);

  const setEl = (kind: Kind, idx: number, patch: Partial<ElLabel>) => {
    if (kind === "lead") {
      emit({ ...value, lead: { ...value.lead, ...patch } });
      return;
    }
    const key = kind === "say" ? "says" : "echoes";
    const arr = [...(kind === "say" ? says : echoes)];
    arr[idx] = { ...arr[idx], ...patch };
    emit({ ...value, [key]: arr });
  };

  const cur = (kind: Kind, idx: number): ElLabel =>
    (kind === "lead" ? value.lead : kind === "say" ? says[idx] : echoes[idx]) ?? {};

  // Same three-state row as ElementLabelPanel (reused class surface .sr-el/.sr-v),
  // minus the sub-pattern tag picker — pack review collapses tags into the free-form reason.
  const elRow = (kind: Kind, idx: number, label: string, text: string) => {
    const c = cur(kind, idx);
    const bad = c.v === "bad";
    return (
      <div className={`sr-el ${kind}${bad ? " is-bad" : ""}`}>
        <div className="sr-el__row">
          <span className="sr-k">{label}</span>
          <span className="sr-t">{text}</span>
        </div>
        <div className="sr-vrow">
          <button className={`sr-v ok${c.v === "ok" ? " on" : ""}`} onClick={() => setEl(kind, idx, { v: "ok" })}>达标</button>
          <button className={`sr-v bad${bad ? " on" : ""}`} onClick={() => setEl(kind, idx, { v: "bad" })}>不达标</button>
          <button className={`sr-v skip${c.v === "abstain" ? " on" : ""}`} onClick={() => setEl(kind, idx, { v: "abstain" })}>跳过</button>
        </div>
      </div>
    );
  };

  return (
    <div className="sr-panel pr-panel">
      {sceneSignal && (
        <div className="pr-signal">
          <span className="pr-signal__k">场景信号</span>
          <span className="pr-signal__t">{sceneSignal}</span>
        </div>
      )}

      <div className="sr-q">① 这条已审包整体通过吗?</div>
      <div className="sr-win pr-verdict">
        {VERDICTS.map(([v, t]) => (
          <button
            key={v}
            className={`pr-${v}${value.verdict === v ? " on" : ""}`}
            onClick={() => emit({ ...value, verdict: v })}
          >
            {t}
          </button>
        ))}
      </div>
      <textarea
        className="sr-note pr-reason"
        placeholder="理由（为什么通过 / 哪里要返工 / 为什么否决）"
        value={value.reason ?? ""}
        onChange={(e) => emit({ ...value, reason: e.target.value })}
      />

      <div className="sr-q">② 逐元素 · 引子 + 说×3 + 接×3</div>
      {elRow("lead", 0, "引子", lead)}
      {candidates.map((c, i) => (
        <div key={i}>
          {elRow("say", i, `说${i + 1}`, c.display_text ?? "")}
          {elRow("echo", i, `接${i + 1}`, c.selected_echo ?? c.friend_voice_seed ?? "")}
        </div>
      ))}

      <div className="pr-foot">当前片段 · 已审包</div>
    </div>
  );
}

export { PackPlayerFrame };
