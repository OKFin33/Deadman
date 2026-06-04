import { useMemo, useState } from "react";
import { Branch3PlayerDemo } from "./player/Branch3PlayerDemo";
import "./App.css";

const PUBLIC_BASE = import.meta.env.BASE_URL.replace(/\/$/, "");
const CATALOG_THUMBNAIL_URL = `${PUBLIC_BASE}/assets/branch3/companion/tomato-robes/webp/runout.webp`;

export default function App() {
  const shouldOpenPlayerDirectly = useMemo(() => {
    const searchParams = new URLSearchParams(window.location.search);
    return searchParams.get("branch3_player") === "1" || searchParams.get("deadman") === "1";
  }, []);
  const [screen, setScreen] = useState<"catalog" | "player">(shouldOpenPlayerDirectly ? "player" : "catalog");

  if (screen === "player") {
    return <Branch3PlayerDemo />;
  }

  return (
    <main className="deadman-catalog-app">
      <section aria-label="要是我来短剧目录" className="deadman-catalog__device" role="region">
        <header className="deadman-catalog__topbar">
          <div>
            <span>短剧高光</span>
            <h1>要是我来</h1>
          </div>
          <strong>Branch 3</strong>
        </header>

        <section className="deadman-catalog__hero" aria-label="今日高光">
          <div className="deadman-catalog__hero-still" aria-hidden="true">
            <span>第 12 集</span>
            <strong>兔子肉要不要下锅</strong>
          </div>
          <p>四蛋把兔子拎回灶边，全家都盯着那口锅。</p>
        </section>

        <article className="deadman-catalog__drama">
          <div className="deadman-catalog__thumbnail-wrap">
            <img alt="番茄搭子荒年互动预览" className="deadman-catalog__thumbnail" src={CATALOG_THUMBNAIL_URL} />
            <span>搭子已在场</span>
          </div>
          <div className="deadman-catalog__drama-copy">
            <p>荒年全村啃树皮，我有系统满仓肉</p>
            <strong>第 12 集 · 兔子肉要不要下锅</strong>
            <span>5 个已发布介入点 · 当前高光 00:12</span>
          </div>
          <button onClick={() => setScreen("player")} type="button">
            进入
          </button>
        </article>
      </section>
    </main>
  );
}
