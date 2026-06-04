import { useReducer } from "react";

export type TomatoNoticeMarker = "question" | "exclaim";

export type TomatoCompanionState =
  | "idle"
  | "notice_question"
  | "notice_exclaim"
  | "runout"
  | "stand_bubble"
  | "thinking"
  | "verdict"
  | "error"
  | "dismissed";

export type TomatoCompanionAssetState = Exclude<TomatoCompanionState, "dismissed" | "error">;

export type TomatoCompanionEvent =
  | { type: "TIMELINE_NOTICE"; marker: TomatoNoticeMarker }
  | { type: "TAP" }
  | { type: "RUNOUT_END" }
  | { type: "SUBMIT" }
  | { type: "RESULT_READY" }
  | { type: "RESULT_ERROR" }
  | { type: "RETRY" }
  | { type: "DISMISS" }
  | { type: "DISMISSED_END" }
  | { type: "RESET" };

export const TOMATO_COMPANION_INITIAL_STATE: TomatoCompanionState = "idle";

const BUSY_STATES = new Set<TomatoCompanionState>(["runout", "stand_bubble", "thinking", "verdict", "error"]);

export function tomatoCompanionReducer(
  state: TomatoCompanionState,
  event: TomatoCompanionEvent,
): TomatoCompanionState {
  switch (event.type) {
    case "TIMELINE_NOTICE":
      if (state !== "idle" && state !== "notice_question" && state !== "notice_exclaim") {
        return state;
      }
      return event.marker === "question" ? "notice_question" : "notice_exclaim";

    case "TAP":
      if (state === "idle" || state === "notice_question" || state === "notice_exclaim") {
        return "stand_bubble";
      }
      return state;

    case "RUNOUT_END":
      return state === "runout" ? "stand_bubble" : state;

    case "SUBMIT":
      if (
        state === "idle" ||
        state === "notice_question" ||
        state === "notice_exclaim" ||
        state === "stand_bubble"
      ) {
        return "thinking";
      }
      return state;

    case "RESULT_READY":
      return state === "thinking" ? "verdict" : state;

    case "RESULT_ERROR":
      return state === "thinking" ? "error" : state;

    case "RETRY":
      return state === "error" ? "stand_bubble" : state;

    case "DISMISS":
      if (state === "idle" || state === "dismissed") {
        return state;
      }
      return "dismissed";

    case "DISMISSED_END":
      return state === "dismissed" ? "idle" : state;

    case "RESET":
      return "idle";

    default:
      return state;
  }
}

export function isTomatoCompanionBusy(state: TomatoCompanionState): boolean {
  return BUSY_STATES.has(state);
}

export function tomatoCompanionStateToAsset(state: TomatoCompanionState): TomatoCompanionAssetState {
  if (state === "dismissed") {
    return "idle";
  }
  if (state === "stand_bubble" || state === "error") {
    return "thinking";
  }
  return state;
}

export function useTomatoCompanionMachine(initialState = TOMATO_COMPANION_INITIAL_STATE) {
  const [state, send] = useReducer(tomatoCompanionReducer, initialState);
  return {
    state,
    send,
    isBusy: isTomatoCompanionBusy(state),
  };
}
