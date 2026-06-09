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
import { loadStageRows, formatClock, type StageRow } from "../api/deadmanStageApi";
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

  return (
    <main className="deadman-stage" aria-label="看剧搭子短剧目录">
      <div className="deadman-stage__bg" aria-hidden="true" />

      <header className="deadman-stage__bar">
        <div className="deadman-stage__brand">
          <p>短剧高光</p>
          <h1>看剧搭子</h1>
        </div>
        <span className="deadman-stage__tag">陪看</span>
      </header>

      {phase === "loading" && <SkeletonList />}
      {phase === "empty" && <EmptyState onRefresh={() => load("refresh")} />}
      {phase === "error" && <ErrorState onRetry={() => load("initial")} />}
      {phase === "ready" && (
        <PullToRefresh refreshing={refreshing} onRefresh={() => load("refresh")}>
          <div className="deadman-stage__section">
            <b>在追的短剧</b>
            <span>{rows.length} 部 · 搭子在场</span>
          </div>
          <div className="deadman-stage__cards">
            {rows.map((row) => (
              <PosterCard key={row.drama_id} row={row} onOpenPlayer={onOpenPlayer} />
            ))}
          </div>
        </PullToRefresh>
      )}
    </main>
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
  const enter = () => onOpenPlayer(row.drama_id, row.currentHighlightSeconds ?? 0);
  // Covers are drama keyframes served locally; the public repo doesn't ship them, so
  // fall back to a titled tile when the image is absent or fails to load.
  const [coverOk, setCoverOk] = useState(true);
  return (
    <article className="deadman-stage__post" onClick={enter}>
      <div className="deadman-stage__post-cover">
        {row.genreTag && <span className="deadman-stage__post-genre">{row.genreTag}</span>}
        {row.coverUrl && coverOk ? (
          <img src={row.coverUrl} alt={row.title} loading="lazy" onError={() => setCoverOk(false)} />
        ) : (
          <div className="deadman-stage__cover-fallback" aria-hidden="true">
            {row.title.slice(0, 6)}
          </div>
        )}
      </div>
      <div className="deadman-stage__post-body">
        <div>
          <p className="deadman-stage__post-title">{row.title}</p>
          {row.hook && <p className="deadman-stage__post-hook">「{row.hook}」</p>}
        </div>
        <div className="deadman-stage__post-foot">
          <span className="deadman-stage__moments">
            <IDots count={row.momentCount} />
            <span>
              <b>{row.momentCount}</b> 介入点
            </span>
          </span>
          <button
            className="deadman-stage__post-enter"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              enter();
            }}
          >
            <PlayIcon /> 进入
          </button>
        </div>
        {row.currentHighlightSeconds != null && (
          <span className="deadman-stage__post-hl">当前高光 {formatClock(row.currentHighlightSeconds)}</span>
        )}
      </div>
    </article>
  );
}

/* ----------------------------------------------------- shared bits -------- */
function IDots({ count }: { count: number }) {
  return (
    <span className="deadman-stage__idots" aria-hidden="true">
      {Array.from({ length: Math.min(count, 8) }).map((_, i) => (
        <i key={i} />
      ))}
    </span>
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
      <div className="deadman-stage__section">
        <b>在追的短剧</b>
        <span>加载中…</span>
      </div>
      <div className="deadman-stage__cards">
        {[0, 1, 2].map((i) => (
          <div className="deadman-stage__post deadman-stage__post--skel" key={i}>
            <div className="deadman-stage__post-cover shimmer" />
            <div className="deadman-stage__post-body">
              <div className="skel-line shimmer" style={{ width: "82%" }} />
              <div className="skel-line shimmer" style={{ width: "54%" }} />
              <div className="skel-line shimmer" style={{ width: "40%", marginTop: "auto" }} />
            </div>
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
