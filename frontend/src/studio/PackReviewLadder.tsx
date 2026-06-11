import { momentGate, type ElLabel, type MomentLabel } from "./reviewApi";

// PackReviewLadder — the per-pack hierarchical short-circuit gate for the in-graph review (Track C).
//
// Adapted from ElementLabelPanel (the dataset-review gate) wholesale: same window→direction→element
// short-circuit, same three-state 达标/不达标/跳过, same RPG sub-pattern tag taxonomies. It adds the
// ONE new short-circuit the owner asked for (decision #2):
//   ③ lead (引子) is three-state; if lead === "bad" → DO NOT show/collect say & echo (collapse them,
//      show a note: lead 坏 → 这条 pack 退回，不必审 say/echo).
//
// The owner's full ladder, in order:
//   ① window (这一刻该不该出搭子) reject → STOP (whole pack reject, reason only)
//   ② 剧情/情绪理解方向 reject     → STOP (whole pack reject, reason only)
//   ③ lead bad                    → STOP say/echo (whole pack reject, reason only)
//   else lead ok → say×3 + echo×3 three-state + sub-pattern tag + reason
//
// Stateless: the parent (ReviewGate) owns the MomentLabel and derives/persists the per-pack verdict.

// Production gate = binary: 这一刻观众会不会想说一句. (The 4-way accept/也许/reject/abstain was inherited
// from the dataset-labeling tool — that nuance is for building a dataset, not for an approve/reject gate.)
const WVERDS: [string, string][] = [["accept", "会想说"], ["reject", "不会想说"]];
const LEAD_TAGS: [string, string][] = [["lead_question_shape", "问句形"], ["lead_too_flat_declarative", "太平淡/像陈述"], ["lead_tone_too_harsh", "语气过尺度"], ["lead_ui_prompt", "UI提示感"], ["lead_plot_prediction", "剧情预测"], ["other", "其他"]];
const SAY_TAGS: [string, string][] = [["display_rpg_or_action_menu", "像RPG选项/改剧情⚠"], ["display_paraphrases_lead", "复述lead"], ["display_not_distinct", "与另一条不够区分"], ["display_ambiguous_subject", "主语不明/不明所以"], ["display_low_emotion", "情绪不足"], ["display_tone_mismatch_with_role", "语气与角色不符"], ["display_exaggeration", "夸张"], ["display_excess_commentary_tail", "结尾多余评论"], ["other", "其他"]];
const ECHO_TAGS: [string, string][] = [["echo_rpg_or_action_menu", "附和RPG/像选项/改剧情⚠"], ["echo_weak_responsiveness", "回应感不足"], ["echo_awkward_phrasing", "语句怪/太硬/太正式"], ["echo_too_long", "太长"], ["echo_exaggeration", "夸张/破坏沉浸"], ["echo_promotes_show", "夸剧像广告"], ["echo_unnatural_illogical", "不自然/逻辑怪"], ["echo_overshadows", "抢戏"], ["echo_unclear_reference", "指代不明"], ["echo_factual_error", "剧世界事实错"], ["echo_paraphrases_display", "复述display"], ["echo_formulaic_opening", "三条同开头"], ["other", "其他"]];

type Cand = { display_text?: string; selected_echo?: string | null; friend_voice_seed?: string | null };
type Kind = "lead" | "say" | "echo";

/** lead is the NEW short-circuit tier: lead marked bad collapses say/echo. */
export function leadIsBad(value: MomentLabel | undefined): boolean {
  return value?.lead?.v === "bad";
}

export function PackReviewLadder({ lead, candidates, value, onChange }: {
  lead: string;
  candidates: Cand[];
  value: MomentLabel;
  onChange: (next: MomentLabel) => void;
}) {
  const gate = momentGate(value);
  const says = value.says ?? [];
  const echoes = value.echoes ?? [];

  const setEl = (kind: Kind, idx: number, patch: Partial<ElLabel>) => {
    if (kind === "lead") {
      onChange({ ...value, lead: { ...value.lead, ...patch } });
      return;
    }
    const key = kind === "say" ? "says" : "echoes";
    const arr = [...(kind === "say" ? says : echoes)];
    arr[idx] = { ...arr[idx], ...patch };
    onChange({ ...value, [key]: arr });
  };

  const allOk = () =>
    onChange({
      ...value,
      lead: { ...value.lead, v: "ok" },
      says: candidates.map((_, i) => ({ ...says[i], v: "ok" })),
      echoes: candidates.map((_, i) => ({ ...echoes[i], v: "ok" })),
    });

  const cur = (kind: Kind, idx: number): ElLabel =>
    (kind === "lead" ? value.lead : kind === "say" ? says[idx] : echoes[idx]) ?? {};

  const elRow = (kind: Kind, idx: number, label: string, text: string, tags: [string, string][]) => {
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
        {bad && (
          <div className="sr-tagrow">
            <select value={c.tag ?? ""} onChange={(e) => setEl(kind, idx, { tag: e.target.value })}>
              <option value="">选细分模式…</option>
              {tags.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
            </select>
          </div>
        )}
        <input className="sr-note" placeholder="理由 / 备注（可选，写它代表的情况）" value={c.note ?? ""}
          onChange={(e) => setEl(kind, idx, { note: e.target.value })} />
      </div>
    );
  };

  return (
    <div className="sr-panel">
      <div className="sr-q">① 这一刻观众会想说一句吗?（窗口选择 — 邀请，不是打断）</div>
      <div className="sr-win">
        {WVERDS.map(([v, t]) => (
          <button key={v} className={value.window === v ? "on" : ""} onClick={() => onChange({ ...value, window: v })}>{t}</button>
        ))}
      </div>

      {gate === "window_reject" ? (
        <>
          <input className="sr-note" placeholder="窗口否的原因（为什么这一刻不该出现搭子）" value={value.window_note ?? ""}
            onChange={(e) => onChange({ ...value, window_note: e.target.value })} />
          <div className="sr-gate">窗口否决 → 整个 pack 退回，无需逐元素打标。</div>
        </>
      ) : (
        <>
          <div className="sr-q">② 整体方向（情绪 / 剧情读法）对吗?</div>
          <div className="sr-win sr-dir">
            <button className={`ok${value.direction !== "reject" ? " on" : ""}`} onClick={() => onChange({ ...value, direction: "ok" })}>方向对</button>
            <button className={`no${value.direction === "reject" ? " on" : ""}`} onClick={() => onChange({ ...value, direction: "reject" })}>方向否（读法错，整条退回）</button>
          </div>

          {gate === "direction_reject" ? (
            <>
              <input className="sr-note" placeholder="方向否的原因（读法 / 情绪 / 剧情哪里错了）" value={value.direction_note ?? ""}
                onChange={(e) => onChange({ ...value, direction_note: e.target.value })} />
              <div className="sr-gate">方向否决 → 整个 pack 退回，无需逐元素打标。</div>
            </>
          ) : (
            <>
              <button className="sr-allok" onClick={allOk}>✓ 本卡全达标</button>
              <div className="sr-q">③ 引子（坏 → 这条 pack 退回，不审 say/echo）</div>
              {elRow("lead", 0, "引子", lead, LEAD_TAGS)}

              {leadIsBad(value) ? (
                <div className="sr-gate">lead 坏 → 这条 pack 退回，不必审 say/echo。</div>
              ) : (
                candidates.map((c, i) => (
                  <div key={i}>
                    {elRow("say", i, `说${i + 1}`, c.display_text ?? "", SAY_TAGS)}
                    {elRow("echo", i, `接${i + 1}`, c.selected_echo ?? c.friend_voice_seed ?? "", ECHO_TAGS)}
                  </div>
                ))
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
