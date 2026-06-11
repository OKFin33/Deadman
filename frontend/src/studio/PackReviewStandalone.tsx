import { useEffect, useMemo, useRef, useState } from "react";
import { listDramaMoments, type DeadmanMomentSummary } from "../api/deadmanApi";
import { listDramas } from "../api/deadmanStageApi";
import { PackReview, PackPlayerFrame } from "./PackReview";
import {
  loadPackReviewLabels,
  savePackReviewLabels,
  type PackLabel,
  type PackReviewLabels,
} from "./packReviewApi";
import "./reviewStudio.css";

// PackReviewStandalone — thin host for the reusable <PackReview>. Gated by ?studio_pack_review=1
// (parallel to ?studio_review=1). It loads every drama (GET /dramas) and each drama's reviewed
// packs (GET /dramas/{id}/moments, keeping only moments that carry a companion_exchange), folds
// them into a rail, and renders <PackReview> for the selected pack with its iframe player.
// Owns the PackLabel state and autosaves it to tmp via packReviewApi — never mutates the packs.

type RailItem = { pack: DeadmanMomentSummary; dramaId: string; dramaTitle: string };

function isReviewedPack(m: DeadmanMomentSummary): boolean {
  return !!m.companion_exchange;
}

function verdictDot(label?: PackLabel): string {
  if (label?.verdict === "approved") return " is-approved";
  if (label?.verdict === "needs_rework") return " is-rework";
  if (label?.verdict === "rejected") return " is-rejected";
  return "";
}

export function PackReviewStandalone() {
  const [items, setItems] = useState<RailItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [err, setErr] = useState("");
  const [labels, setLabels] = useState<PackReviewLabels>({});
  const [saved, setSaved] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        const dramas = await listDramas({ signal: ctrl.signal });
        const all: RailItem[] = [];
        for (const d of dramas) {
          const moments = await listDramaMoments(d.drama_id, { signal: ctrl.signal });
          for (const m of moments.filter(isReviewedPack)) {
            all.push({ pack: m, dramaId: d.drama_id, dramaTitle: d.title });
          }
        }
        setItems(all);
        setSelected(all[0]?.pack.moment_id ?? "");
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
    void loadPackReviewLabels().then(setLabels);
  }, []);

  const updatePackLabel = (packId: string, next: PackLabel) => {
    const merged = { ...labels, [packId]: next };
    setLabels(merged);
    setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void savePackReviewLabels(merged).then(setSaved), 400);
  };

  const current = useMemo(() => items.find((it) => it.pack.moment_id === selected), [items, selected]);

  if (status !== "ready") {
    return (
      <div className="studio-review" style={{ display: "block" }}>
        <div className="center">{status === "loading" ? "加载已审包…" : `加载失败：${err}`}</div>
      </div>
    );
  }

  return (
    <div className="studio-review">
      <aside>
        <div className="sr-brand">
          <span className="sr-brand__name">看剧搭子 · 已审包人审</span>
          <span className="sr-brand__sub">{items.length} pack</span>
        </div>
        <div className="sr-rail">
          {items.map((it) => (
            <button
              key={it.pack.moment_id}
              className={`sr-moment${it.pack.moment_id === selected ? " is-active" : ""}`}
              onClick={() => setSelected(it.pack.moment_id)}
            >
              <span className={`sr-moment__mark pr-mark${verdictDot(labels[it.pack.moment_id])}`}>!</span>
              <span className="sr-moment__id">{it.pack.moment_id}</span>
            </button>
          ))}
        </div>
      </aside>
      <main>
        {current ? (
          <div className="sr-main">
            <div className="sr-stage">
              <div className="sr-stage__head">
                <span className="sr-title">{current.dramaTitle || current.pack.source_drama?.title || current.pack.moment_id}</span>
                {saved && <span className="sr-saved">已保存 ✓</span>}
              </div>
              <PackPlayerFrame pack={current.pack} />
            </div>
            <div className="sr-eval">
              <PackReview
                pack={current.pack}
                value={
                  labels[current.pack.moment_id] ?? {
                    pack_id: current.pack.moment_id,
                    moment_id: current.pack.moment_id,
                    drama_id: current.dramaId,
                  }
                }
                onVerdict={(next) =>
                  updatePackLabel(current.pack.moment_id, {
                    ...next,
                    pack_id: current.pack.moment_id,
                    moment_id: current.pack.moment_id,
                    drama_id: current.dramaId,
                  })
                }
              />
            </div>
          </div>
        ) : (
          <div className="center">选左侧一条已审包</div>
        )}
      </main>
    </div>
  );
}
