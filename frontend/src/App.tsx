import { useMemo, useState } from "react";
import { Branch3PlayerDemo } from "./player/Branch3PlayerDemo";
import { StageList } from "./stage/StageList";
import "./App.css";

// App = the top-level screen switch. Surface 1 (StageList — Claude Design「海报架」) is
// the catalog; selecting a card hands the real drama_id + current-highlight seek to the
// player. ?branch3_player=1 (or ?deadman=1) opens the player directly for legacy/demo
// URLs; ?dramaId=<slug> picks which drama that direct player loads.
export default function App() {
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const directDrama = params.get("dramaId")?.trim() || "";
  const openPlayerDirectly = params.get("branch3_player") === "1" || params.get("deadman") === "1";
  const seekParam = Number(params.get("seek")); // deep-link from Studio 发布 → land on the same moment (?episodeId is read by the player)

  const [screen, setScreen] = useState<"catalog" | "player">(openPlayerDirectly ? "player" : "catalog");
  const [activeDramaId, setActiveDramaId] = useState<string>(directDrama || "huangnian");
  const [seekSeconds, setSeekSeconds] = useState<number>(Number.isFinite(seekParam) && seekParam > 0 ? seekParam : 0);

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
