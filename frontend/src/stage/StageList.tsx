/* =============================================================================
 * StageList.tsx — Surface 1 · multi-drama list (Direction B · 海报架 / Poster)
 * -----------------------------------------------------------------------------
 * Replaces the hard-coded single catalog card in frontend/src/App.tsx with a
 * data-driven list. Selecting a card hands `drama_id` (+ the current-highlight
 * seek) to the player — wire `onOpenPlayer` to your existing player entry.
 *
 * States: loading (skeleton) · ready · empty · error · pull-to-refresh.
 * Visual language is the player's own (see stage.css — tokens lifted from
 * Branch3PlayerDemo.css). Mobile-first; no device frame.
 * ===========================================================================*/

import { useCallback, useEffect, useRef, useState } from "react";
import { loadStageRows, type StageRow } from "../api/deadmanStageApi";
import "./stage.css";

type Phase = "loading" | "ready" | "empty" | "error";

export interface StageListProps {
  /** Called when the viewer enters a drama. seek = currentHighlightSeconds (or 0). */
  onOpenPlayer: (dramaId: string, startSeconds: number) => void;
}

export function StageList({ onOpenPlayer }: StageListProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [rows, setRows] = useState<StageRow[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (mode: "initial" | "refresh") => {
    if (mode === "initial") setPhase("loading");
    else setRefreshing(true);
    try {
      const next = await loadStageRows();
      setRows(next);
      setPhase(next.length ? "ready" : "empty");
    } catch {
      setPhase("error");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load("initial");
  }, [load]);

  // genre tabs (推荐 = all) — derived from the dramas actually present
  const genres = Array.from(new Set(rows.map((r) => r.genreTag).filter(Boolean))) as string[];
  const tabs = ["推荐", ...genres];
  const [tab, setTab] = useState<string>("推荐");
  const shown = tab === "推荐" ? rows : rows.filter((r) => r.genreTag === tab);

  return (
    <div className="deadman-stage-app">
    <main className="deadman-stage" aria-label="看剧搭子短剧目录">
      <div className="deadman-stage__bg" aria-hidden="true" />

      <header className="deadman-stage__bar">
        <div className="deadman-stage__brand">
          <p>短剧高光</p>
          <h1>看剧搭子</h1>
        </div>
        <span className="deadman-stage__tag">陪看</span>
      </header>

      {phase === "ready" && tabs.length > 1 && (
        <nav className="deadman-stage__tabs" aria-label="分类">
          {tabs.map((t) => (
            <button
              key={t}
              type="button"
              className={`deadman-stage__tab${t === tab ? " is-active" : ""}`}
              onClick={() => setTab(t)}
            >
              {t === "推荐" && <FlameIcon />}
              {t}
            </button>
          ))}
        </nav>
      )}

      {phase === "loading" && <SkeletonList />}
      {phase === "empty" && <EmptyState onRefresh={() => load("refresh")} />}
      {phase === "error" && <ErrorState onRetry={() => load("initial")} />}
      {phase === "ready" && (
        <PullToRefresh refreshing={refreshing} onRefresh={() => load("refresh")}>
          <div className="deadman-stage__grid">
            {shown.map((row) => (
              <PosterCard key={row.drama_id} row={row} onOpenPlayer={onOpenPlayer} />
            ))}
          </div>
        </PullToRefresh>
      )}
    </main>
    </div>
  );
}

/* ----------------------------------------- Direction B · poster card ------ */
function PosterCard({
  row,
  onOpenPlayer,
}: {
  row: StageRow;
  onOpenPlayer: (dramaId: string, startSeconds: number) => void;
}) {
  // Catalog entry always starts the drama from 0s (and the player best-effort autoplays);
  // the per-highlight seek is the Studio deep-link path (?seek=N) handled in App.tsx, not catalog entry.
  const enter = () => onOpenPlayer(row.drama_id, 0);
  // Covers are drama keyframes served locally; fall back to a titled tile if absent.
  const [coverOk, setCoverOk] = useState(true);
  return (
    <article
      className="deadman-stage__poster"
      role="button"
      tabIndex={0}
      aria-label={`进入 ${row.title}`}
      onClick={enter}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          enter();
        }
      }}
    >
      <div className="deadman-stage__poster-cover">
        {row.coverUrl && coverOk ? (
          <img src={row.coverUrl} alt={row.title} onError={() => setCoverOk(false)} />
        ) : (
          <div className="deadman-stage__poster-fallback" aria-hidden="true">{row.title.slice(0, 8)}</div>
        )}
        {row.genreTag && <span className="deadman-stage__poster-genre">{row.genreTag}</span>}
        <span className="deadman-stage__poster-plays">
          <PlayIcon /> {row.playLabel ?? String(row.momentCount)}
        </span>
      </div>
      <p className="deadman-stage__poster-title">{row.title}</p>
      <div className="deadman-stage__poster-meta">
        <span>{row.genreTag ?? "热播"}</span>
        <b>{row.episodeCount ?? row.momentCount}集</b>
      </div>
    </article>
  );
}

/* ----------------------------------------------------- shared bits -------- */
function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" aria-hidden="true">
      <path d="M12 2c1 3-1 4.5-2.3 6C8 10 8.6 13.5 12 13.5c1.8 0 3-1.6 2.6-3.6 1.6 1 2.4 3 1.4 5.4C19 14 20 11.4 18.8 8.6 17.6 5.8 14.2 5 12 2Z" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" fill="currentColor" aria-hidden="true">
      <path d="M2.5 1.5 10 6l-7.5 4.5z" />
    </svg>
  );
}

/* --------------------------------------------------------- skeleton ------- */
function SkeletonList() {
  return (
    <div className="deadman-stage__scroll">
      <div className="deadman-stage__grid">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div className="deadman-stage__poster deadman-stage__poster--skel" key={i}>
            <div className="deadman-stage__poster-cover shimmer" />
            <div className="skel-line shimmer" style={{ width: "88%", marginTop: "8px" }} />
            <div className="skel-line shimmer" style={{ width: "50%", marginTop: "6px" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------------------------------- empty / error ------ */
function EmptyState({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="deadman-stage__state">
      <img className="deadman-stage__mascot" src="/assets/branch3/companion/tomato-robes/png/runout.png" alt="" />
      <h3>搭子先到一步</h3>
      <p>还没有上线的短剧。新剧上架时，搭子会第一时间在这儿等你。</p>
      <button className="deadman-stage__state-btn" type="button" onClick={onRefresh}>
        刷新看看
      </button>
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="deadman-stage__state">
      <img
        className="deadman-stage__mascot deadman-stage__mascot--peek"
        src="/assets/branch3/companion/tomato-robes/png/notice_question.png"
        alt=""
      />
      <h3>没连上</h3>
      <p>目录没加载出来。检查下网络，再让搭子试一次。</p>
      <button className="deadman-stage__state-btn" type="button" onClick={onRetry}>
        重试
      </button>
      <span className="deadman-stage__state-code">GET /api/deadman/dramas — failed</span>
    </div>
  );
}

/* ------------------------------------------------- pull to refresh -------- */
function PullToRefresh({
  refreshing,
  onRefresh,
  children,
}: {
  refreshing: boolean;
  onRefresh: () => void;
  children: React.ReactNode;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [pull, setPull] = useState(0);
  const drag = useRef({ on: false, startY: 0, atTop: true });

  const down = (e: React.PointerEvent) => {
    const el = scrollRef.current;
    drag.current = { on: true, startY: e.clientY, atTop: !el || el.scrollTop <= 0 };
  };
  const move = (e: React.PointerEvent) => {
    const s = drag.current;
    if (!s.on) return;
    const dy = e.clientY - s.startY;
    setPull(dy > 0 && s.atTop && !refreshing ? Math.min(92, dy * 0.5) : 0);
  };
  const up = () => {
    if (pull >= 56 && !refreshing) onRefresh();
    drag.current.on = false;
    setPull(0);
  };

  const offset = refreshing ? 54 : pull;
  return (
    <div className="deadman-stage__pull-wrap">
      <div className="deadman-stage__pull" style={{ opacity: refreshing || pull > 8 ? 1 : 0 }}>
        {refreshing || pull >= 56 ? <div className="deadman-stage__spinner" /> : <span>下拉刷新</span>}
      </div>
      <div
        ref={scrollRef}
        className="deadman-stage__scroll"
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerLeave={up}
        style={{
          transform: `translateY(${offset}px)`,
          transition: drag.current.on ? "none" : "transform 320ms cubic-bezier(0.2,0.85,0.25,1)",
        }}
      >
        {children}
      </div>
    </div>
  );
}
