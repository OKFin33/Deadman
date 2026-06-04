import type { AnimationEvent } from "react";
import {
  type TomatoCompanionState,
  tomatoCompanionStateToAsset,
} from "./tomatoCompanionMachine";
import "./TomatoCompanion.css";

const ASSET_BASE = `${import.meta.env.BASE_URL.replace(/\/$/, "")}/assets/branch3/companion/tomato-robes`;

const STATE_LABELS: Record<TomatoCompanionState, string> = {
  idle: "要是我来搭子待机中",
  notice_question: "要是我来搭子发现了一个可介入点",
  notice_exclaim: "要是我来搭子发现了一个高情绪介入点",
  runout: "要是我来搭子正在跑出",
  stand_bubble: "要是我来搭子等待你的选择",
  thinking: "要是我来搭子正在判断后果",
  verdict: "要是我来搭子给出判断",
  error: "要是我来搭子判定失败，需要重试或关闭",
  dismissed: "要是我来搭子正在退回待机",
};

interface TomatoCompanionProps {
  className?: string;
  state: TomatoCompanionState;
  stampText?: string;
  onTap?: (state: TomatoCompanionState) => void;
  onTransitionDone?: (state: TomatoCompanionState) => void;
}

export function TomatoCompanion({
  className = "",
  state,
  stampText,
  onTap,
  onTransitionDone,
}: TomatoCompanionProps) {
  const assetState = tomatoCompanionStateToAsset(state);

  function handleAnimationEnd(event: AnimationEvent<HTMLButtonElement>) {
    if (event.currentTarget !== event.target) {
      return;
    }
    if (state === "runout" || state === "dismissed") {
      onTransitionDone?.(state);
    }
  }

  return (
    <div
      aria-live="polite"
      className={`tomato-companion-layer ${className}`.trim()}
      data-companion-state={state}
    >
      <button
        aria-label={STATE_LABELS[state]}
        className={`tomato-companion tomato-companion--${state}`}
        data-state={state}
        key={state}
        onAnimationEnd={handleAnimationEnd}
        onClick={() => onTap?.(state)}
        type="button"
      >
        <picture className="tomato-companion__sprite">
          <source srcSet={`${ASSET_BASE}/webp/${assetState}.webp`} type="image/webp" />
          <img alt="" draggable={false} src={`${ASSET_BASE}/png/${assetState}.png`} />
        </picture>
        {state === "verdict" && stampText ? (
          <span className="tomato-companion__stamp" aria-hidden="true">
            {stampText}
          </span>
        ) : null}
      </button>
    </div>
  );
}
