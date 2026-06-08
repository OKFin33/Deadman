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
      <section aria-label="看剧搭子短剧目录" className="deadman-catalog__device" role="region">
        <header className="deadman-catalog__topbar">
          <div>
            <span>短剧高光</span>
            <h1>看剧搭子</h1>
          </div>
          <strong>陪看</strong>
        </header>

        <section className="deadman-catalog__hero" aria-label="今日高光">
          <div className="deadman-catalog__hero-still" aria-hidden="true">
            <span>第 3 集</span>
            <strong>最后一点野菜</strong>
          </div>
          <p>孩子盯着最后一点野菜，怕它又被送走。</p>
        </section>

        <article className="deadman-catalog__drama">
          <div className="deadman-catalog__thumbnail-wrap">
            <img alt="番茄搭子荒年互动预览" className="deadman-catalog__thumbnail" src={CATALOG_THUMBNAIL_URL} />
            <span>搭子已在场</span>
          </div>
          <div className="deadman-catalog__drama-copy">
            <p>荒年全村啃树皮，我有系统满仓肉</p>
            <strong>第 3 集 · 最后一口先留家里</strong>
            <span>5 个已发布介入点 · 当前高光 00:37</span>
          </div>
          <button onClick={() => setScreen("player")} type="button">
            进入
          </button>
        </article>
      </section>
    </main>
  );
}
