import { useMemo, useState } from "react";
import { Branch3PlayerDemo } from "./player/Branch3PlayerDemo";
import { StageList } from "./stage/StageList";
import { StudioReview } from "./studio/StudioReview";
import { PackReviewStandalone } from "./studio/PackReviewStandalone";
import { StudioPipeline } from "./studio/StudioPipeline";
import { VizDemo } from "./studio/VizDemo";
import "./App.css";

// App = the top-level screen switch. Routing is PATH-ONLY (clean IA): the viewer lives at /Stage,
// the producer at /studio. There is no /demo surface and no ?studio_*=1 query gates. Surface 1
// (StageList — Claude Design「海报架」) is the catalog; selecting a card hands the real drama_id +
// current-highlight seek to the player.
//
// Path IA (served by server.py as the SAME index.html):
//   • /studio/pack-review[/] → <PackReviewStandalone/> (reviewed-pack verdict surface)
//   • /studio/dataset-review → <StudioReview/> (in-player dev dataset review)
//   • /studio… (anything else) → <StudioPipeline/> (the React authoring console)
//   • /Stage… /stage… → the viewer (catalog default; player if ?branch3_player/?deadman/?dramaId)
//   • root "/" served by the server as the landing — the SPA default is the catalog for safety.
// Under /Stage, ?branch3_player=1 (or ?deadman=1) opens the player directly and ?dramaId=<slug>
// picks which drama it loads — this is the Studio publish deep-link target.
export default function App() {
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const pathname = typeof window !== "undefined" ? window.location.pathname : "";
  const onStudioPath = /^\/studio(\/|$)/i.test(pathname); // /studio… → React Studio surfaces
  const onPackReviewPath = /^\/studio\/pack-review(\/|$)/i.test(pathname); // /studio/pack-review[/]
  const onDatasetReviewPath = /^\/studio\/dataset-review(\/|$)/i.test(pathname); // /studio/dataset-review

  const directDrama = params.get("dramaId")?.trim() || "";
  const openPlayerDirectly = params.get("branch3_player") === "1" || params.get("deadman") === "1";
  const seekParam = Number(params.get("seek")); // deep-link from Studio 发布 → land on the same moment (?episodeId is read by the player)

  // The viewer catalog is the default surface; ?branch3_player/?deadman/?dramaId open the player
  // directly so the Studio publish deep-link (which lands on /Stage) goes straight to the moment.
  const [screen, setScreen] = useState<"catalog" | "player">(openPlayerDirectly ? "player" : "catalog");
  const [activeDramaId, setActiveDramaId] = useState<string>(directDrama || "huangnian");
  const [seekSeconds, setSeekSeconds] = useState<number>(Number.isFinite(seekParam) && seekParam > 0 ? seekParam : 0);

  // ---- DEV-ONLY: viz harness to iterate the graph viz without a real run (?vizdemo=1) ----
  if (params.get("vizdemo") === "1") {
    return <VizDemo />;
  }

  // ---- Path-only IA ----
  if (onStudioPath) {
    if (onPackReviewPath) {
      return <PackReviewStandalone />;
    }
    if (onDatasetReviewPath) {
      return <StudioReview />;
    }
    return <StudioPipeline />;
  }
  // /Stage… (and the SPA default for root) is the viewer; it falls through to the switch below.

  if (screen === "player") {
    return <Branch3PlayerDemo dramaId={activeDramaId} startSeconds={seekSeconds} onBack={() => setScreen("catalog")} />;
  }

  return (
    <StageList
      onOpenPlayer={(dramaId, startSeconds) => {
        setActiveDramaId(dramaId);
        setSeekSeconds(startSeconds);
        setScreen("player");
      }}
    />
  );
}
