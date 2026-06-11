import { useEffect, useMemo, useRef, useState } from "react";
import { listDramaMoments, type DeadmanMomentSummary } from "../api/deadmanApi";
import { ElementLabelPanel } from "./ElementLabelPanel";
import { loadReviewLabels, saveReviewLabels, type MomentLabel, type ReviewLabels } from "./reviewApi";
import "./reviewStudio.css";

// Studio in-player human review. Isolated surface (?studio_review=1), does NOT touch Branch3PlayerDemo.
// Viewer experience = the REAL player, embedded via same-origin iframe deep-linked to the moment, so the
// reviewer watches the actual 「!」+ 搭子 + 3 候选 and labels each element beside it. Styled to the Studio
// design system (reviewStudio.css). Same infra now serves dev dataset review + (later) Studio pack review.
const PRODUCTION_DRAMAS = ["huangnian", "lihun", "yunmiao"];

function candidatesOf(m: DeadmanMomentSummary) {
  return m.companion_exchange?.reply_candidates ?? m.mouthpiece_candidates ?? [];
}

function isDone(l?: MomentLabel): boolean {
  if (!l) return false;
  const got = (e?: { v?: string }) => !!e?.v;
  return got(l.lead) && (l.says?.length ?? 0) >= 1 && (l.says ?? []).every(got) && (l.echoes ?? []).every(got);
}

function PlayerFrame({ moment }: { moment: DeadmanMomentSummary }) {
  const win = moment.interaction_window ?? {};
  const start = Math.max(0, Number(win.start_seconds ?? win.notice_at_seconds ?? 0) - 2);
  const ep = moment.source_drama?.episode_id ?? "";
  // Real player, same SPA, deep-linked to this moment. key=moment forces a reload on selection change.
  const src = `/Stage/?branch3_player=1&dramaId=${encodeURIComponent(moment.drama_id)}&episodeId=${encodeURIComponent(ep)}&seek=${start}`;
  return (
    <div>
      <iframe key={moment.moment_id} src={src} title="真播放器" allow="autoplay" className="sr-frame" />
      <div className="sr-hint">
        真播放器 · 跳到 {start}s → 播到窗口出「!」，点搭子看 3 条 + 接话。这是观众真实体验，对着它评每个元素。
      </div>
    </div>
  );
}

export function StudioReview() {
  const [moments, setMoments] = useState<DeadmanMomentSummary[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [err, setErr] = useState("");
  const [labels, setLabels] = useState<ReviewLabels>({});
  const [saved, setSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        const all: DeadmanMomentSummary[] = [];
        for (const d of PRODUCTION_DRAMAS) {
          all.push(...(await listDramaMoments(d, { signal: ctrl.signal })));
        }
        setMoments(all);
        setSelected(all[0]?.moment_id ?? "");
        setStatus("ready");
      } catch (e: unknown) {
        if ((e as { name?: string })?.name !== "AbortError") {
          setErr(e instanceof Error ? e.message : String(e));
          setStatus("error");
        }
      }
    })();
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    void loadReviewLabels().then(setLabels);
  }, []);

  const updateMomentLabel = (momentId: string, next: MomentLabel) => {
    const merged = { ...labels, [momentId]: next };
    setLabels(merged);
    setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void saveReviewLabels(merged).then(setSaved), 400);
  };

  const current = useMemo(() => moments.find((m) => m.moment_id === selected), [moments, selected]);

  if (status !== "ready") {
    return (
      <div className="studio-review" style={{ display: "block" }}>
        <div className="center">{status === "loading" ? "加载 moment…" : `加载失败：${err}`}</div>
      </div>
    );
  }

  return (
    <div className="studio-review">
      <aside>
        <div className="sr-brand">
          <span className="sr-brand__name">看剧搭子 · 人审</span>
          <span className="sr-brand__sub">{moments.length} moment</span>
        </div>
        <div className="sr-rail">
          {moments.map((m) => (
            <button
              key={m.moment_id}
              className={`sr-moment${m.moment_id === selected ? " is-active" : ""}${isDone(labels[m.moment_id]) ? " is-done" : ""}`}
              onClick={() => setSelected(m.moment_id)}
            >
              <span className="sr-moment__mark">!</span>
              <span className="sr-moment__id">{m.moment_id}</span>
            </button>
          ))}
        </div>
      </aside>
      <main>
        {current ? (
          <div className="sr-main">
            <div className="sr-stage">
              <div className="sr-stage__head">
                <span className="sr-title">{current.source_drama?.title ?? current.moment_id}</span>
                {saved && <span className="sr-saved">已保存 ✓</span>}
              </div>
              <PlayerFrame moment={current} />
            </div>
            <div className="sr-eval">
              <ElementLabelPanel
                lead={current.companion_lead ?? ""}
                candidates={candidatesOf(current)}
                value={labels[current.moment_id] ?? {}}
                onChange={(next) => updateMomentLabel(current.moment_id, next)}
              />
            </div>
          </div>
        ) : (
          <div className="center">选左侧一个 moment</div>
        )}
      </main>
    </div>
  );
}
