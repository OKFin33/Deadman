import { describe, expect, it } from "vitest";
import {
  type TomatoCompanionEvent,
  type TomatoCompanionState,
  isTomatoCompanionBusy,
  tomatoCompanionReducer,
  tomatoCompanionStateToAsset,
} from "./tomatoCompanionMachine";

function reduce(
  initialState: TomatoCompanionState,
  events: TomatoCompanionEvent[],
): TomatoCompanionState {
  return events.reduce(tomatoCompanionReducer, initialState);
}

describe("tomatoCompanionReducer", () => {
  it("moves through the normal companion flow", () => {
    expect(
      reduce("idle", [
        { type: "TIMELINE_NOTICE", marker: "exclaim" },
        { type: "TAP" },
        { type: "SUBMIT" },
        { type: "RESULT_READY" },
        { type: "DISMISS" },
        { type: "DISMISSED_END" },
      ]),
    ).toBe("idle");
  });

  it("does not let new timeline notices interrupt active interaction states", () => {
    expect(
      tomatoCompanionReducer("thinking", {
        type: "TIMELINE_NOTICE",
        marker: "question",
      }),
    ).toBe("thinking");
    expect(
      tomatoCompanionReducer("verdict", {
        type: "TIMELINE_NOTICE",
        marker: "exclaim",
      }),
    ).toBe("verdict");
  });

  it("keeps one-shot transition end events local to their transition states", () => {
    expect(tomatoCompanionReducer("idle", { type: "RUNOUT_END" })).toBe("idle");
    expect(tomatoCompanionReducer("runout", { type: "RUNOUT_END" })).toBe("stand_bubble");
    expect(tomatoCompanionReducer("notice_exclaim", { type: "TAP" })).toBe("stand_bubble");
    expect(tomatoCompanionReducer("verdict", { type: "DISMISSED_END" })).toBe("verdict");
    expect(tomatoCompanionReducer("dismissed", { type: "DISMISSED_END" })).toBe("idle");
  });

  it("represents failed judgment as an error state, not a verdict", () => {
    expect(
      reduce("stand_bubble", [
        { type: "SUBMIT" },
        { type: "RESULT_ERROR" },
      ]),
    ).toBe("error");
    expect(tomatoCompanionStateToAsset("error")).toBe("thinking");
    expect(tomatoCompanionReducer("error", { type: "RETRY" })).toBe("stand_bubble");
    expect(tomatoCompanionReducer("error", { type: "DISMISS" })).toBe("dismissed");
  });

  it("uses idle art for the dismissed transition and marks busy states", () => {
    expect(tomatoCompanionStateToAsset("dismissed")).toBe("idle");
    expect(tomatoCompanionStateToAsset("verdict")).toBe("verdict");
    expect(isTomatoCompanionBusy("idle")).toBe(false);
    expect(isTomatoCompanionBusy("thinking")).toBe(true);
  });
});
