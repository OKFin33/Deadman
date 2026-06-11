import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type PointerEvent } from "react";
import { TomatoCompanion } from "../companion/TomatoCompanion";
import {
  type TomatoCompanionState,
  useTomatoCompanionMachine,
} from "../companion/tomatoCompanionMachine";
import {
  DeadmanApiError,
  type DeadmanJudgmentAction,
  type DeadmanJudgmentResponse,
  type DeadmanMediaSlot,
  type DeadmanMouthpieceCandidate,
  type DeadmanResultMedia,
  listDramaMoments,
  type DeadmanMomentSummary,
} from "../api/deadmanApi";
import {
  createRuntimeEventId,
  getOrCreateViewerSessionId,
  sendRuntimeEvent,
  type DeadmanRuntimeResponse,
} from "../api/deadmanRuntimeApi";
import "./Branch3PlayerDemo.css";

const DEFAULT_VIDEO_URL = "";
const FALLBACK_DURATION_SECONDS = 90;
const FALLBACK_WINDOW_SECONDS = 8;
const DRAMA_ID = "huangnian";
const DRAMA_TITLE = "荒年全村啃树皮，我有系统满仓肉";
const DEFAULT_EPISODE_ID = "huangnian_ep03";
const FALLBACK_MARKER_TIMES = [12, 24, 36, 48, 60];

type HighlightOption = {
  label: "A" | "B" | "C";
  text: string;
  displayText?: string;
  stampText?: string;
  candidateId?: string;
  actionPayload?: Record<string, unknown>;
  emotionRole?: string;
  semanticRole?: string;
  requiresReview?: boolean;
};

type HighlightMarker = {
  id: string;
  momentId: string;
  episodeId: string;
  timeSeconds: number;
  noticeAtSeconds: number;
  startSeconds: number;
  endSeconds: number;
  timingSource: string;
  episodeTitle?: string;
  runtimeVideoUrl?: string;
  type: string;
  marker: "!" | "?";
  hook: string;
  companionLead?: string;
  options: HighlightOption[];
  resultMedia?: DeadmanResultMedia;
};

type StaticResult = {
  kind: "result";
  text: string;
  microCue?: string;
  continueLabel?: string;
  media?: DeadmanMediaSlot & { type?: "image" };
};

type ErrorResult = {
  kind: "error";
  title: string;
  message: string;
  detail: string;
  media?: DeadmanMediaSlot & { type?: "image" };
};

type ViewerResult = StaticResult | ErrorResult;

type EpisodeOption = {
  episodeId: string;
  label: string;
  title: string;
  hook: string;
  markerCount: number;
  firstNoticeAtSeconds: number;
  runtimeVideoUrl?: string;
};

const STATIC_HIGHLIGHT_MARKERS: HighlightMarker[] = [
  {
    id: "huangnian_ep12_m001",
    momentId: "huangnian_ep12_m001",
    episodeId: "huangnian_ep12",
    timeSeconds: 12,
    noticeAtSeconds: 12,
    startSeconds: 12,
    endSeconds: 20,
    timingSource: "local_fallback",
    type: "resource",
    marker: "!",
    hook: "四蛋抓到兔子那一眼，懂事得让人难受。",
    options: [
      { label: "A", text: "今晚分兔肉，先让四蛋确认自己也有份", displayText: "四蛋该吃肉", stampText: "懂你❤" },
      { label: "B", text: "先留下兔子和皮毛，改用别的食物补这一顿", displayText: "别让娃白懂事", stampText: "就是啊" },
      { label: "C", text: "把兔子当成四蛋的功劳，只少量处理给全家尝味", displayText: "功劳算孩子的", stampText: "我懂" },
    ],
  },
  {
    id: "huangnian_ep07_m001",
    momentId: "huangnian_ep07_m001",
    episodeId: "huangnian_ep07",
    timeSeconds: 24,
    noticeAtSeconds: 24,
    startSeconds: 24,
    endSeconds: 32,
    timingSource: "local_fallback",
    type: "relationship",
    marker: "!",
    hook: "儿媳被逼吃脏饭那一下，桌上没人站出来。",
    options: [
      { label: "A", text: "当场让儿媳上桌，直接推翻旧规矩", displayText: "凭什么啊", stampText: "就是啊" },
      { label: "B", text: "先把饭换掉，再私下处理婆媳权力", displayText: "先护住她", stampText: "懂你❤" },
      { label: "C", text: "不当众翻脸，只让儿媳先吃一口干净的", displayText: "别让她白挨", stampText: "我懂" },
    ],
  },
  {
    id: "huangnian_ep03_m001",
    momentId: "huangnian_ep03_m001",
    episodeId: "huangnian_ep03",
    timeSeconds: 37,
    noticeAtSeconds: 37,
    startSeconds: 37,
    endSeconds: 47,
    timingSource: "local_fallback",
    type: "resource",
    marker: "!",
    hook: "最后一点野菜又要送出去，孩子急了。",
    companionLead: "原主的人设有点离谱😂",
    options: [
      { label: "A", text: "直接告诉孩子，这点野菜先留在家里", displayText: "这妈当得离谱", stampText: "就是啊" },
      { label: "B", text: "先安孩子，别让他们再怕这口吃的", displayText: "孩子都吓成这样", stampText: "抱一下" },
      { label: "C", text: "大舅那边先停，家里这顿饭要保住", displayText: "先别管大舅了", stampText: "懂你❤" },
    ],
  },
  {
    id: "huangnian_ep04_m001",
    momentId: "huangnian_ep04_m001",
    episodeId: "huangnian_ep04",
    timeSeconds: 48,
    noticeAtSeconds: 48,
    startSeconds: 48,
    endSeconds: 56,
    timingSource: "local_fallback",
    type: "evidence",
    marker: "?",
    hook: "当众扣偷粮帽子，这口气真咽不下去。",
    options: [
      { label: "A", text: "当场让大家看清楚不是稻子，直接反打", displayText: "凭什么扣帽子", stampText: "就是啊" },
      { label: "B", text: "先问对方凭什么认定，再把小鹅菜拿出来", displayText: "证据先上桌", stampText: "我懂" },
      { label: "C", text: "不扩大骂战，只保住东西和名声底线", displayText: "不陪她乱吵", stampText: "懂你❤" },
    ],
  },
  {
    id: "huangnian_ep06_m001",
    momentId: "huangnian_ep06_m001",
    episodeId: "huangnian_ep06",
    timeSeconds: 60,
    noticeAtSeconds: 60,
    startSeconds: 60,
    endSeconds: 68,
    timingSource: "local_fallback",
    type: "exposure",
    marker: "!",
    hook: "白米一露，全家眼神都变了。",
    options: [
      { label: "A", text: "直接承认有白米，先让全家安心", displayText: "先安人心", stampText: "就是啊" },
      { label: "B", text: "只说捡到/换到少量白米，压住追问", displayText: "别把底露光", stampText: "我懂" },
      { label: "C", text: "先把米收回去，改成更不显眼的吃法", displayText: "别让他们顺着问", stampText: "懂你❤" },
    ],
  },
];

function getConfiguredVideoUrl(): string {
  const searchParams = new URLSearchParams(window.location.search);
  return searchParams.get("videoUrl")?.trim() || searchParams.get("branch3_video")?.trim() || DEFAULT_VIDEO_URL;
}

function getConfiguredEpisodeId(): string {
  const searchParams = new URLSearchParams(window.location.search);
  return searchParams.get("episodeId")?.trim() || searchParams.get("branch3_episode")?.trim() || DEFAULT_EPISODE_ID;
}

export function Branch3PlayerDemo({
  dramaId = DRAMA_ID,
  startSeconds = 0,
  onBack,
}: { dramaId?: string; startSeconds?: number; onBack?: () => void } = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const bubbleRef = useRef<HTMLElement | null>(null);
  const notifiedMarkersRef = useRef(new Set<string>());
  const viewerSessionIdRef = useRef<string>(getOrCreateViewerSessionId());
  const lastRuntimeActionRef = useRef<{
    eventId: string;
    marker: HighlightMarker;
  } | null>(null);
  const initialVideoUrl = useMemo(() => getConfiguredVideoUrl(), []);
  const configuredEpisodeId = useMemo(() => getConfiguredEpisodeId(), []);
  const initialMarkers = useMemo(
    () => selectEpisodeMarkers(STATIC_HIGHLIGHT_MARKERS, configuredEpisodeId),
    [configuredEpisodeId],
  );
  const initialEpisodeId = useMemo(
    () => resolveEpisodeId(STATIC_HIGHLIGHT_MARKERS, configuredEpisodeId),
    [configuredEpisodeId],
  );
  const [videoUrl, setVideoUrl] = useState(initialVideoUrl);
  const [allMarkers, setAllMarkers] = useState<HighlightMarker[]>(STATIC_HIGHLIGHT_MARKERS);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState(initialEpisodeId);
  const [episodePickerOpen, setEpisodePickerOpen] = useState(false);
  const [packStatus, setPackStatus] = useState<"loading" | "api" | "fallback">("loading");
  const [packError, setPackError] = useState("");
  const [durationSeconds, setDurationSeconds] = useState(FALLBACK_DURATION_SECONDS);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasVideoError, setHasVideoError] = useState(false);
  const [activeMarkerId, setActiveMarkerId] = useState<string>(initialMarkers[0].id);
  const [customOpen, setCustomOpen] = useState(false);
  const [customAction, setCustomAction] = useState("");
  const [result, setResult] = useState<ViewerResult | null>(null);
  const [stampText, setStampText] = useState("懂你❤");
  const [completedMarkerIds, setCompletedMarkerIds] = useState<Set<string>>(() => new Set());
  const { state: companionState, send: sendCompanionEvent } = useTomatoCompanionMachine();

  const markers = useMemo(() => selectEpisodeMarkers(allMarkers, selectedEpisodeId), [allMarkers, selectedEpisodeId]);
  const episodeOptions = useMemo(() => buildEpisodeOptions(allMarkers), [allMarkers]);
  const activeMarker = markers.find((marker) => marker.id === activeMarkerId) ?? markers[0] ?? allMarkers[0] ?? initialMarkers[0];
  // The window the idle companion is tappable for: the most-recent uncompleted window whose START
  // we have reached — DURING (within the window) OR AFTER (viewer missed it, companion idle again).
  // Before any window starts (currentTime < every startSeconds) this is null → tapping is a no-op.
  const tappableMarker = useMemo(() => {
    let candidate: HighlightMarker | undefined;
    for (const marker of markers) {
      if (currentTime >= marker.startSeconds && !completedMarkerIds.has(marker.id)) {
        if (!candidate || marker.startSeconds > candidate.startSeconds) {
          candidate = marker;
        }
      }
    }
    return candidate ?? null;
  }, [markers, currentTime, completedMarkerIds]);
  const nextEligibleMarker = markers.find((marker) => marker.noticeAtSeconds >= currentTime - 0.3);
  const visibleHook =
    companionState === "idle" ? tappableMarker ?? nextEligibleMarker ?? activeMarker : activeMarker;
  const showBubble =
    companionState === "stand_bubble" ||
    companionState === "thinking" ||
    companionState === "verdict" ||
    companionState === "error";

  useEffect(() => {
    const controller = new AbortController();
    listDramaMoments(dramaId, { signal: controller.signal })
      .then((summaries) => {
        const hydratedMarkers = mapMomentSummariesToMarkers(summaries);
        if (hydratedMarkers.length === 0) {
          setPackStatus("fallback");
          setPackError("后端没有返回可用节点，已使用本地兜底节点。");
          return;
        }
        const nextEpisodeId = resolveEpisodeId(hydratedMarkers, configuredEpisodeId);
        notifiedMarkersRef.current.clear();
        setAllMarkers(hydratedMarkers);
        setSelectedEpisodeId(nextEpisodeId);
        setPackStatus("api");
        setPackError("");
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) {
          return;
        }
        setPackStatus("fallback");
        setPackError(error instanceof Error ? error.message : "Deadman API 暂时不可用，已使用本地兜底节点。");
      });
    return () => controller.abort();
  }, [configuredEpisodeId, initialVideoUrl]);

  useEffect(() => {
    const nextMarkers = selectEpisodeMarkers(allMarkers, selectedEpisodeId);
    const nextMarker = nextMarkers[0];
    if (!nextMarker) {
      return;
    }
    notifiedMarkersRef.current.clear();
    setActiveMarkerId(nextMarker.id);
    setCompletedMarkerIds(new Set());
    setCustomOpen(false);
    setCustomAction("");
    setEpisodePickerOpen(false);
    setResult(null);
    setStampText("懂你❤");
    setCurrentTime(0);
    setDurationSeconds(FALLBACK_DURATION_SECONDS);
    setHasVideoError(false);
    setIsPlaying(false);
    if (videoRef.current) {
      if (!videoRef.current.paused) {
        try {
          videoRef.current.pause();
        } catch {
          // Media APIs are optional in some test/browser shells; selection reset can still proceed.
        }
      }
      videoRef.current.currentTime = 0;
    }
    if (initialVideoUrl === DEFAULT_VIDEO_URL) {
      setVideoUrl(nextMarker.runtimeVideoUrl || DEFAULT_VIDEO_URL);
    }
    sendCompanionEvent({ type: "RESET" });
  }, [allMarkers, initialVideoUrl, selectedEpisodeId, sendCompanionEvent]);

  // One-time seek to the highlight the Stage list handed us (optional; 0 = normal start).
  // Catalog entry passes startSeconds=0 → no seek (the autoplay effect below starts from 0);
  // the Studio 发布 deep-link (?seek=N, App.tsx) passes startSeconds=N → one-time jump to N.
  const didInitialSeekRef = useRef(false);
  useEffect(() => {
    if (didInitialSeekRef.current || !startSeconds || startSeconds <= 0) return;
    const video = videoRef.current;
    if (!video) return;
    const seek = () => {
      try {
        video.currentTime = startSeconds;
      } catch {
        // Media APIs are optional in some test/browser shells.
      }
      setCurrentTime(startSeconds);
      didInitialSeekRef.current = true;
    };
    if (video.readyState >= 1) seek();
    else video.addEventListener("loadedmetadata", seek, { once: true });
  }, [startSeconds]);

  // Best-effort autoplay on entry (the catalog tap / deep-link nav is the user gesture).
  // One-shot per mount so the selection-reset effect's pause()/isPlaying(false) does not fight it,
  // and so the viewer's own pause is respected thereafter. Silently no-ops if the browser blocks
  // autoplay (muted/policy) — the viewer can still tap ▶.
  const didAutoplayRef = useRef(false);
  useEffect(() => {
    if (didAutoplayRef.current || !videoUrl || hasVideoError) return;
    const video = videoRef.current;
    if (!video || typeof video.play !== "function") return;
    didAutoplayRef.current = true;
    try {
      const playResult = video.play();
      if (playResult && typeof playResult.catch === "function") {
        playResult.catch(() => setIsPlaying(false));
      }
    } catch {
      setIsPlaying(false);
    }
  }, [videoUrl, hasVideoError]);

  useEffect(() => {
    void sendRuntimeEvent({
      viewer_session_id: viewerSessionIdRef.current,
      event_id: createRuntimeEventId(),
      event_type: "session_start",
      drama_id: dramaId,
      episode_id: activeMarker.episodeId,
      playback_time_seconds: currentTime,
      moment_id: activeMarker.momentId,
      companion_state: companionState,
    }).catch(() => {
      // Session startup is non-blocking; action submit still surfaces runtime errors.
    });
    // Start once on mount. Later marker changes are sent through notice/tap/action events.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (companionState !== "runout") {
      return;
    }
    const timer = window.setTimeout(() => sendCompanionEvent({ type: "RUNOUT_END" }), 680);
    return () => window.clearTimeout(timer);
  }, [companionState, sendCompanionEvent]);

  useEffect(() => {
    if (companionState !== "dismissed") {
      return;
    }
    const timer = window.setTimeout(() => sendCompanionEvent({ type: "DISMISSED_END" }), 280);
    return () => window.clearTimeout(timer);
  }, [companionState, sendCompanionEvent]);

  function activateMarker(marker: HighlightMarker, shouldSeek: boolean) {
    setActiveMarkerId(marker.id);
    setCustomOpen(false);
    setCustomAction("");
    sendCompanionEvent({ type: "TIMELINE_NOTICE", marker: marker.marker === "!" ? "exclaim" : "question" });
    void sendRuntimeEvent({
      viewer_session_id: viewerSessionIdRef.current,
      event_id: createRuntimeEventId(),
      event_type: "moment_notice",
      drama_id: dramaId,
      episode_id: marker.episodeId,
      playback_time_seconds: marker.timeSeconds,
      moment_id: marker.momentId,
      companion_state: companionState,
    }).catch(() => {
      // Notice is advisory; the visible companion can still use pack timing locally.
    });
    if (shouldSeek && videoRef.current) {
      videoRef.current.currentTime = marker.timeSeconds;
      setCurrentTime(marker.timeSeconds);
    }
  }

  function pauseForCompanionChoice() {
    if (videoRef.current && !videoRef.current.paused) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }

  function handleLoadedMetadata() {
    const mediaDuration = videoRef.current?.duration ?? FALLBACK_DURATION_SECONDS;
    setDurationSeconds(Number.isFinite(mediaDuration) && mediaDuration > 0 ? mediaDuration : FALLBACK_DURATION_SECONDS);
    setHasVideoError(false);
  }

  function handleTimeUpdate() {
    const nextTime = videoRef.current?.currentTime ?? 0;
    setCurrentTime(nextTime);
    syncCompanionToPlaybackWindow(nextTime);
  }

  function syncCompanionToPlaybackWindow(nextTime: number, shouldRenotice = false) {
    const reachedMarker = findMarkerInWindow(markers, nextTime);
    if (!reachedMarker) {
      if (
        (companionState === "notice_question" || companionState === "notice_exclaim") &&
        !showBubble
      ) {
        sendCompanionEvent({ type: "RESET" });
      }
      return;
    }
    if (completedMarkerIds.has(reachedMarker.id)) {
      if (
        (companionState === "notice_question" || companionState === "notice_exclaim") &&
        !showBubble
      ) {
        sendCompanionEvent({ type: "RESET" });
      }
      return;
    }
    setActiveMarkerId(reachedMarker.id);
    if (!shouldRenotice && notifiedMarkersRef.current.has(reachedMarker.id)) {
      return;
    }
    notifiedMarkersRef.current.add(reachedMarker.id);
    activateMarker(reachedMarker, false);
  }

  function handleSeek(event: ChangeEvent<HTMLInputElement> | FormEvent<HTMLInputElement>) {
    const nextTime = Number(event.currentTarget.value);
    if (!Number.isFinite(nextTime)) {
      return;
    }
    if (videoRef.current) {
      videoRef.current.currentTime = nextTime;
    }
    setCurrentTime(nextTime);
    syncCompanionToPlaybackWindow(nextTime, true);
  }

  function togglePlayback() {
    const video = videoRef.current;
    if (!videoUrl || hasVideoError) {
      setIsPlaying((playing) => !playing);
      return;
    }
    if (!video || hasVideoError) {
      return;
    }
    if (video.paused) {
      try {
        const playResult = video.play();
        if (playResult && typeof playResult.catch === "function") {
          playResult.catch(() => setIsPlaying(false));
        }
      } catch {
        setIsPlaying(false);
      }
      return;
    }
    video.pause();
  }

  function handleEpisodeSelect(episodeId: string) {
    if (episodeId === selectedEpisodeId) {
      setEpisodePickerOpen(false);
      return;
    }
    setSelectedEpisodeId(episodeId);
  }

  function handleCompanionTap(state: TomatoCompanionState) {
    if (state === "idle") {
      // Tappable from the nearest started window onward (during OR after a missed window).
      // No-op before any window has started.
      if (!tappableMarker) {
        return;
      }
      setActiveMarkerId(tappableMarker.id);
      setCustomOpen(false);
      setCustomAction("");
      void sendCompanionTap(tappableMarker);
      pauseForCompanionChoice();
      sendCompanionEvent({ type: "TAP" });
      return;
    }
    if (state === "notice_question" || state === "notice_exclaim") {
      void sendCompanionTap(activeMarker);
      pauseForCompanionChoice();
      sendCompanionEvent({ type: "TAP" });
      return;
    }
    if (state === "verdict" || state === "error") {
      sendCompanionEvent({ type: "DISMISS" });
    }
  }

  function handleCompanionTransitionDone(state: TomatoCompanionState) {
    if (state === "runout") {
      sendCompanionEvent({ type: "RUNOUT_END" });
      return;
    }
    if (state === "dismissed") {
      sendCompanionEvent({ type: "DISMISSED_END" });
    }
  }

  async function submitAction(
    actionText: string,
    source: DeadmanJudgmentAction["source"],
    optionIndex?: number,
    option?: HighlightOption,
  ) {
    const normalizedAction = actionText.trim();
    if (!normalizedAction || companionState === "thinking") {
      return;
    }
    setResult(null);
    setStampText(buildStampTextForAction(option, source));
    sendCompanionEvent({ type: "SUBMIT" });
    const eventId = createRuntimeEventId();
    lastRuntimeActionRef.current = { eventId, marker: activeMarker };
    try {
      const runtimeResponse = await sendRuntimeEvent({
        viewer_session_id: viewerSessionIdRef.current,
        event_id: eventId,
        event_type: "user_action",
        drama_id: dramaId,
        episode_id: activeMarker.episodeId,
        playback_time_seconds: currentTime,
        moment_id: activeMarker.momentId,
        companion_state: companionState,
        action: buildJudgmentAction(source, normalizedAction, optionIndex, option),
      });
      applyRuntimeResponse(runtimeResponse);
    } catch (error) {
      setResult(buildApiFailureResult(error));
      sendCompanionEvent({ type: "RESULT_ERROR" });
    }
  }

  function handleCustomSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitAction(customAction, "custom");
  }

  function handleCloseBubble() {
    setCustomOpen(false);
    setCustomAction("");
    void sendRuntimeEvent({
      viewer_session_id: viewerSessionIdRef.current,
      event_id: createRuntimeEventId(),
      event_type: "continue_watching",
      drama_id: dramaId,
      episode_id: activeMarker.episodeId,
      playback_time_seconds: currentTime,
      moment_id: activeMarker.momentId,
      companion_state: companionState,
    }).catch(() => {
      // Continue watching should never be blocked by runtime telemetry.
    });
    sendCompanionEvent({ type: "DISMISS" });
  }

  function handleDevicePointerDown(event: PointerEvent<HTMLElement>) {
    if (!showBubble || companionState === "thinking") {
      return;
    }
    const bubble = bubbleRef.current;
    if (event.target instanceof Node && bubble?.contains(event.target)) {
      return;
    }
    handleCloseBubble();
  }

  async function sendCompanionTap(marker: HighlightMarker) {
    await sendRuntimeEvent({
      viewer_session_id: viewerSessionIdRef.current,
      event_id: createRuntimeEventId(),
      event_type: "companion_tap",
      drama_id: dramaId,
      episode_id: marker.episodeId,
      playback_time_seconds: currentTime,
      moment_id: marker.momentId,
      companion_state: companionState,
    });
  }

  async function retryLastRuntimeAction() {
    const retryContext = lastRuntimeActionRef.current;
    if (!retryContext || companionState === "thinking") {
      sendCompanionEvent({ type: "RETRY" });
      return;
    }
    setResult(null);
    sendCompanionEvent({ type: "RETRY" });
    sendCompanionEvent({ type: "SUBMIT" });
    try {
      const runtimeResponse = await sendRuntimeEvent({
        viewer_session_id: viewerSessionIdRef.current,
        event_id: retryContext.eventId,
        event_type: "runtime_retry",
        drama_id: dramaId,
        episode_id: retryContext.marker.episodeId,
        playback_time_seconds: currentTime,
        moment_id: retryContext.marker.momentId,
        companion_state: companionState,
      });
      applyRuntimeResponse(runtimeResponse);
    } catch (error) {
      setResult(buildApiFailureResult(error));
      sendCompanionEvent({ type: "RESULT_ERROR" });
    }
  }

  function applyRuntimeResponse(runtimeResponse: DeadmanRuntimeResponse) {
    if (runtimeResponse.status === "error") {
      setResult(buildRuntimeErrorResult(runtimeResponse));
      sendCompanionEvent({ type: "RESULT_ERROR" });
      return;
    }
    if (runtimeResponse.result_surface?.stamp) {
      setStampText(runtimeResponse.result_surface.stamp);
    } else if (runtimeResponse.judgment?.verdict.stance) {
      setStampText((current) => current || buildStampTextForStance(runtimeResponse.judgment?.verdict.stance));
    }
    setResult(buildRuntimeResult(runtimeResponse));
    setCompletedMarkerIds((current) => {
      const next = new Set(current);
      next.add(activeMarker.id);
      return next;
    });
    sendCompanionEvent({ type: "RESULT_READY" });
  }

  return (
    <main className="branch3-player-app">
      <section
        aria-label="看剧搭子播放器"
        className="branch3-player__device"
        onPointerDown={handleDevicePointerDown}
        role="region"
      >
        <div className="branch3-player__video-layer">
          {!videoUrl || hasVideoError ? (
            <div className="branch3-player__poster" aria-hidden="true">
              <div className="branch3-player__poster-light" />
              <div className="branch3-player__poster-room">
                <span className="branch3-player__poster-window" />
                <span className="branch3-player__poster-door" />
                <span className="branch3-player__poster-pot" />
                <span className="branch3-player__poster-rabbit" />
                <span className="branch3-player__poster-hand branch3-player__poster-hand--left" />
                <span className="branch3-player__poster-hand branch3-player__poster-hand--right" />
              </div>
              <div className="branch3-player__placeholder-tag">
                短剧画面
                <br />
                荒年 · 第12集
              </div>
              <div className="branch3-player__subtitle">
                <span>四蛋把兔子拎回来了。</span>
                <strong>这顿肉要是真的下锅，谁先吃？</strong>
              </div>
            </div>
          ) : null}
          <video
            aria-label="短剧 MP4 播放器"
            className="branch3-player__video"
            onDurationChange={handleLoadedMetadata}
            onEnded={() => setIsPlaying(false)}
            onError={() => {
              setHasVideoError(true);
              setIsPlaying(false);
            }}
            onLoadedMetadata={handleLoadedMetadata}
            onPause={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            onTimeUpdate={handleTimeUpdate}
            playsInline
            preload="metadata"
            ref={videoRef}
            src={videoUrl || undefined}
          />
          <div className="branch3-player__scrim" aria-hidden="true" />
        </div>

        <header className="branch3-player__topbar">
          <div className="branch3-player__topbar-left">
            {onBack ? (
              <button
                aria-label="返回短剧目录"
                className="branch3-player__back"
                onClick={onBack}
                type="button"
              >
                ‹
              </button>
            ) : null}
            <div>
              <p>看剧搭子 · 在场</p>
              <strong>{activeMarker.episodeTitle || DRAMA_TITLE}</strong>
            </div>
          </div>
        </header>

        {episodePickerOpen ? (
          <section
            aria-label="选择演示集"
            className="branch3-player__episode-sheet"
            id="branch3-episode-picker"
          >
            <div className="branch3-player__episode-sheet-head">
              <strong>演示集</strong>
              <span>来自导入内容包</span>
            </div>
            <div className="branch3-player__episode-list">
              {episodeOptions.map((episode) => (
                <button
                  aria-pressed={episode.episodeId === selectedEpisodeId}
                  className={episode.episodeId === selectedEpisodeId ? "is-active" : ""}
                  key={episode.episodeId}
                  onClick={() => handleEpisodeSelect(episode.episodeId)}
                  type="button"
                >
                  <strong>{episode.label}</strong>
                  <span>{episode.hook}</span>
                  <em>
                    {formatTime(episode.firstNoticeAtSeconds)} · {episode.markerCount} 个搭子点
                  </em>
                </button>
              ))}
            </div>
          </section>
        ) : null}

        {!showBubble ? (
          <div className="branch3-player__hook" data-testid="branch3-hook">
            <span>{visibleHook.marker === "!" ? "火气点" : "憋住点"}</span>
            <strong>{buildEmotionHook(visibleHook)}</strong>
          </div>
        ) : null}

        {!showBubble ? (
          <TomatoCompanion
            className="branch3-player__companion branch3-player__companion--edge"
            onTap={handleCompanionTap}
            onTransitionDone={handleCompanionTransitionDone}
            state={companionState}
          />
        ) : null}

        {showBubble ? (
          <section
            className={`branch3-player__bubble ${companionState === "verdict" ? "warm" : ""} ${companionState === "error" ? "is-error" : ""}`.trim()}
            aria-label="看剧搭子互动气泡"
            data-panel-state={companionState}
            ref={bubbleRef}
          >
            <TomatoCompanion
              className="branch3-player__companion branch3-player__companion--perch"
              state={companionState}
              stampText={stampText}
            />

            {companionState === "verdict" && result?.kind === "result" ? (
              <ResultPanel result={result} onClose={handleCloseBubble} />
            ) : companionState === "error" && result?.kind === "error" ? (
              <ErrorPanel result={result} onRetry={() => void retryLastRuntimeAction()} onClose={handleCloseBubble} />
            ) : companionState === "thinking" ? (
              <div className="branch3-player__panel-fade" aria-live="polite">
                <div className="branch3-player__label branch3-player__label--hot">搭子接话中</div>
                <div className="branch3-player__thinking-row">
                  <span className="branch3-player__dots" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className="branch3-player__spoken">替你把这句说出口...</span>
                </div>
              </div>
            ) : (
              <form className="branch3-player__quick-form" onSubmit={handleCustomSubmit}>
                <div className="branch3-player__label branch3-player__label--hot">
                  搭子凑过来
                </div>
                <p className="branch3-player__question branch3-player__spoken">{buildCompanionLead(activeMarker)}</p>
                <div className="branch3-player__quick-replies">
                  {activeMarker.options.map((option, optionIndex) => (
                    <button
                      key={option.label}
                      onClick={() => {
                        setCustomAction(option.displayText || option.text);
                        void submitAction(
                          option.displayText || option.text,
                          option.candidateId ? "preset_candidate" : "preset",
                          optionIndex,
                          option,
                        );
                      }}
                      type="button"
                    >
                      <strong>{option.displayText || option.text}</strong>
                    </button>
                  ))}
                </div>
                {!customOpen ? (
                  <button className="branch3-player__custom-toggle" onClick={() => setCustomOpen(true)} type="button">
                    <span>✎</span>
                    我有不同想法
                  </button>
                ) : (
                  <div className="branch3-player__custom-action">
                    <input
                      aria-label="自定义给搭子的动作"
                      autoFocus
                      onChange={(event) => setCustomAction(event.target.value)}
                      placeholder="把你憋着的那句写出来..."
                      type="text"
                      value={customAction}
                    />
                    <button
                      className="branch3-player__submit"
                      disabled={!customAction.trim()}
                      type="submit"
                    >
                      送
                    </button>
                  </div>
                )}
                {packStatus === "fallback" && packError ? (
                  <span className="branch3-player__api-note" role="status">
                    {packError}
                  </span>
                ) : null}
              </form>
            )}
          </section>
        ) : null}

        <section className={`branch3-player__controls ${showBubble ? "is-hidden" : ""}`.trim()} aria-label="播放器控制">
          <div className="branch3-player__progress-shell">
            <div className="branch3-player__markers" aria-label="高光时间点">
              {markers.map((marker) => (
                <button
                  aria-label={`${formatTime(marker.timeSeconds)} ${marker.hook}`}
                  className={marker.id === activeMarker.id ? "is-active" : ""}
                  data-testid="branch3-highlight-marker"
                  key={marker.id}
                  onClick={() => activateMarker(marker, true)}
                  style={{ left: markerOffset(marker.noticeAtSeconds, durationSeconds) }}
                  type="button"
                >
                  {marker.marker}
                </button>
              ))}
            </div>
            <input
              aria-label="播放进度"
              max={durationSeconds}
              min={0}
              onChange={handleSeek}
              onInput={handleSeek}
              step={0.1}
              type="range"
              value={Math.min(currentTime, durationSeconds)}
            />
          </div>
          <div className="branch3-player__transport">
            <button disabled={hasVideoError && Boolean(videoUrl)} onClick={togglePlayback} type="button">
              {isPlaying ? "❚❚" : "▶"}
            </button>
            <span>
              {formatTime(currentTime)} / {formatTime(durationSeconds)}
            </span>
            <button
              aria-controls="branch3-episode-picker"
              aria-expanded={episodePickerOpen}
              className="branch3-player__episode-trigger"
              onClick={() => setEpisodePickerOpen((open) => !open)}
              type="button"
            >
              <span>{formatEpisodeLabel(selectedEpisodeId)}</span>
              <i aria-hidden="true">⌄</i>
            </button>
          </div>
        </section>
      </section>
    </main>
  );
}

function markerOffset(timeSeconds: number, durationSeconds: number): string {
  const safeDuration = Math.max(durationSeconds, FALLBACK_DURATION_SECONDS);
  const rawPercent = (timeSeconds / safeDuration) * 100;
  return `${Math.min(96, Math.max(4, rawPercent))}%`;
}

function buildEmotionHook(marker: HighlightMarker): string {
  return marker.hook;
}

function buildCompanionLine(marker: HighlightMarker): string {
  if (marker.type === "resource") {
    return "四蛋这一下太戳了。肉能救急，但孩子不能又被晾在一边。";
  }
  if (marker.type === "relationship") {
    return "这桌人真会欺负老实人。先别讲大道理，这口饭就不能这么咽。";
  }
  if (marker.type === "system") {
    return "外挂都亮了还装没看见？可以忍，但别把命也忍没了。";
  }
  if (marker.type === "evidence") {
    return "这帽子扣得太脏了。要反打可以，但证据得比火气先上桌。";
  }
  if (marker.type === "exposure") {
    return "白米一露，屋里就不只是饿了。现在最怕的是全家一起追问。";
  }
  return `这段我真忍不了。${marker.hook}`;
}

function buildCompanionLead(marker: HighlightMarker): string {
  if (marker.companionLead) {
    return marker.companionLead;
  }
  if (marker.type === "resource") {
    return "我刚刚真想替四蛋说一句。";
  }
  if (marker.type === "relationship") {
    return "这桌饭看得人火气上来了。";
  }
  if (marker.type === "system") {
    return "这系统一亮，我也忍不住想点一下。";
  }
  if (marker.type === "evidence") {
    return "这帽子扣得太随便了。";
  }
  if (marker.type === "exposure") {
    return "这袋米露出来，我都替她绷住了。";
  }
  return "这段我也有句话卡在嘴边。";
}

function buildCompactVoiceTake(text: string): string {
  const compact = text
    .replace(/^今晚/, "")
    .replace(/^先/, "")
    .replace(/^把/, "")
    .replace(/^当场/, "")
    .replace(/[，。！？,.!?].*$/, "")
    .trim();
  if (!compact) {
    return text.length > 12 ? `${text.slice(0, 12)}...` : text;
  }
  return compact.length > 12 ? `${compact.slice(0, 12)}...` : compact;
}

function buildStampTextForAction(option: HighlightOption | undefined, source: DeadmanJudgmentAction["source"]): string {
  if (source === "custom") {
    return "懂你❤";
  }
  return option?.stampText || "懂你❤";
}

function buildJudgmentAction(
  source: DeadmanJudgmentAction["source"],
  text: string,
  optionIndex?: number,
  option?: HighlightOption,
): DeadmanJudgmentAction {
  if (source === "preset_candidate") {
    return {
      source,
      text,
      option_index: null,
      candidate_id: option?.candidateId || null,
      action_payload: option?.actionPayload || null,
    };
  }
  return {
    source,
    text,
    option_index: source === "preset" ? optionIndex ?? null : null,
  };
}

function buildStampTextForStance(stance: DeadmanJudgmentResponse["verdict"]["stance"] | undefined): string {
  if (stance === "caution") {
    return "我懂";
  }
  if (stance === "reject_softly") {
    return "抱一下";
  }
  return "懂你❤";
}

function formatEpisodeLabel(episodeId: string): string {
  const match = episodeId.match(/ep(\d+)/i);
  if (match) return `EP${String(Number(match[1])).padStart(2, "0")}`;
  return episodeId.startsWith("up_") ? "样片" : "本集"; // uploaded sample / unnumbered episode
}

function formatTime(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function mapMomentSummariesToMarkers(summaries: DeadmanMomentSummary[]): HighlightMarker[] {
  return summaries
    .filter((summary) => {
      const hasExchangeCandidates =
        Array.isArray(summary.companion_exchange?.reply_candidates) &&
        summary.companion_exchange.reply_candidates.length > 0;
      const hasMouthpieceCandidates =
        Array.isArray(summary.mouthpiece_candidates) && summary.mouthpiece_candidates.length > 0;
      const hasLegacyOptions = Array.isArray(summary.default_options) && summary.default_options.length > 0;
      // A pre-promote SCAFFOLD moment (empty companion_exchange) still carries a valid interaction
      // window + runtime_video_url, so keep it so the VIDEO is playable — e.g. the in-graph review
      // gate previewing the window of an un-promoted upload. Curated viewer dramas always have
      // candidates, so they're unaffected; this only rescues otherwise-dropped scaffold moments.
      const iw = summary.interaction_window;
      const hasWindow = !!iw && (iw.start_seconds != null || iw.notice_at_seconds != null);
      return Boolean(summary.moment_id) && (hasExchangeCandidates || hasMouthpieceCandidates || hasLegacyOptions || hasWindow);
    })
    .map((summary, index) => {
      const fallback = STATIC_HIGHLIGHT_MARKERS[index % STATIC_HIGHLIGHT_MARKERS.length];
      const viewerTemplate = STATIC_HIGHLIGHT_MARKERS.find((marker) => marker.momentId === summary.moment_id);
      const window = readInteractionWindow(summary, index);
      const options = buildHighlightOptions(summary, viewerTemplate);
      return {
        id: summary.moment_id,
        momentId: summary.moment_id,
        episodeId: summary.source_drama?.episode_id || fallback.episodeId,
        timeSeconds: window.startSeconds,
        noticeAtSeconds: window.noticeAtSeconds,
        startSeconds: window.startSeconds,
        endSeconds: window.endSeconds,
        timingSource: window.timingSource,
        episodeTitle: summary.source_drama?.title,
        runtimeVideoUrl: summary.source_drama?.runtime_video_url,
        type: summary.action_type || fallback.type,
        marker: summary.companion_exchange?.notice_marker === "?" || summary.notice_marker === "?" ? "?" : "!",
        hook: summary.companion_exchange?.scene_signal || summary.hook || viewerTemplate?.hook || fallback.hook,
        companionLead: summary.companion_exchange?.companion_lead || summary.companion_lead || undefined,
        // authored options when present, else the matching viewer template — but NEVER leak a
        // different drama's fallback options onto a candidate-less scaffold (the review-gate preview).
        options: options && options.length > 0 ? options : viewerTemplate?.options ?? [],
        resultMedia: summary.result_media,
      };
    });
}

function buildHighlightOptions(
  summary: DeadmanMomentSummary,
  viewerTemplate: HighlightMarker | undefined,
): HighlightOption[] | undefined {
  const exchangeCandidates =
    summary.companion_exchange?.reply_candidates?.slice(0, 3).filter(isValidMouthpieceCandidate) || [];
  const candidates =
    exchangeCandidates.length > 0
      ? exchangeCandidates
      : summary.mouthpiece_candidates?.slice(0, 3).filter(isValidMouthpieceCandidate) || [];
  if (candidates.length > 0) {
    return candidates.map((candidate, optionIndex) => ({
      label: optionLabel(optionIndex),
      text: candidate.display_text,
      displayText: candidate.display_text,
      stampText: viewerTemplate?.options[optionIndex]?.stampText,
      candidateId: candidate.candidate_id,
      actionPayload: candidate.action_payload,
      emotionRole: candidate.emotion_role,
      semanticRole: candidate.semantic_role,
      requiresReview: Boolean(candidate.requires_review),
    }));
  }
  return summary.default_options?.slice(0, 3).map((text, optionIndex) => ({
    label: optionLabel(optionIndex),
    text,
    displayText: viewerTemplate?.options[optionIndex]?.displayText || buildCompactVoiceTake(text),
    stampText: viewerTemplate?.options[optionIndex]?.stampText,
  }));
}

function isValidMouthpieceCandidate(candidate: DeadmanMouthpieceCandidate): boolean {
  return Boolean(candidate.candidate_id && candidate.display_text && candidate.action_payload);
}

function buildEpisodeOptions(markers: HighlightMarker[]): EpisodeOption[] {
  const episodes = new Map<string, EpisodeOption>();
  markers.forEach((marker) => {
    const existing = episodes.get(marker.episodeId);
    if (existing) {
      existing.markerCount += 1;
      if (marker.noticeAtSeconds < existing.firstNoticeAtSeconds) {
        existing.firstNoticeAtSeconds = marker.noticeAtSeconds;
        existing.hook = marker.hook;
      }
      if (!existing.runtimeVideoUrl && marker.runtimeVideoUrl) {
        existing.runtimeVideoUrl = marker.runtimeVideoUrl;
      }
      return;
    }
    episodes.set(marker.episodeId, {
      episodeId: marker.episodeId,
      label: formatEpisodeLabel(marker.episodeId),
      title: marker.episodeTitle || DRAMA_TITLE,
      hook: marker.hook,
      markerCount: 1,
      firstNoticeAtSeconds: marker.noticeAtSeconds,
      runtimeVideoUrl: marker.runtimeVideoUrl,
    });
  });
  return Array.from(episodes.values());
}

function resolveEpisodeId(markers: HighlightMarker[], requestedEpisodeId: string): string {
  if (markers.length === 0) {
    return "";
  }
  if (requestedEpisodeId && markers.some((marker) => marker.episodeId === requestedEpisodeId)) {
    return requestedEpisodeId;
  }
  return markers[0].episodeId;
}

function selectEpisodeMarkers(markers: HighlightMarker[], requestedEpisodeId: string): HighlightMarker[] {
  if (markers.length === 0) {
    return [];
  }
  const selectedEpisodeId = resolveEpisodeId(markers, requestedEpisodeId);
  return markers.filter((marker) => marker.episodeId === selectedEpisodeId);
}

function readInteractionWindow(
  summary: DeadmanMomentSummary,
  index: number,
): Pick<HighlightMarker, "noticeAtSeconds" | "startSeconds" | "endSeconds" | "timingSource"> {
  const window = summary.interaction_window;
  const notice = Number(window?.notice_at_seconds);
  const start = Number(window?.start_seconds);
  const end = Number(window?.end_seconds);
  if (Number.isFinite(notice) && Number.isFinite(start) && Number.isFinite(end) && notice <= start && start <= end) {
    return {
      noticeAtSeconds: Math.max(0, notice),
      startSeconds: Math.max(0, start),
      endSeconds: Math.max(start + 0.1, end),
      timingSource: window?.source || "pack_interaction_window",
    };
  }
  // Temporary compatibility path for older packs that have not been republished with interaction_window.
  const fallbackStart = readMomentStartSeconds(summary, index);
  return {
    noticeAtSeconds: fallbackStart,
    startSeconds: fallbackStart,
    endSeconds: fallbackStart + FALLBACK_WINDOW_SECONDS,
    timingSource: "legacy_source_drama_or_local_fallback",
  };
}

function readMomentStartSeconds(summary: DeadmanMomentSummary, index: number): number {
  const timeRange = summary.source_drama?.time_range_seconds;
  const start = Array.isArray(timeRange) ? Number(timeRange[0]) : Number.NaN;
  if (Number.isFinite(start) && start >= 0) {
    return start;
  }
  return FALLBACK_MARKER_TIMES[index] ?? FALLBACK_MARKER_TIMES[FALLBACK_MARKER_TIMES.length - 1];
}

function findMarkerInWindow(markers: HighlightMarker[], timeSeconds: number): HighlightMarker | undefined {
  return markers.find((marker) => timeSeconds >= marker.noticeAtSeconds && timeSeconds <= marker.endSeconds);
}

function optionLabel(index: number): HighlightOption["label"] {
  if (index === 1) {
    return "B";
  }
  if (index === 2) {
    return "C";
  }
  return "A";
}

function buildJudgmentResult(judgment: DeadmanJudgmentResponse): StaticResult {
  return {
    kind: "result",
    text: buildNarrativeResultText(judgment),
    microCue: buildMicroCue(judgment),
    media: judgment.media,
  };
}

function buildRuntimeResult(runtimeResponse: DeadmanRuntimeResponse): StaticResult {
  if (runtimeResponse.result_surface) {
    return {
      kind: "result",
      text: compactCompanionResultText(runtimeResponse.result_surface.text),
      microCue: compactMicroCue(runtimeResponse.result_surface.micro_cue?.text),
      continueLabel: runtimeResponse.result_surface.continue_label,
      media: runtimeResponse.judgment?.media,
    };
  }
  if (runtimeResponse.judgment) {
    return buildJudgmentResult(runtimeResponse.judgment);
  }
  return {
    kind: "result",
    text: runtimeResponse.companion.utterance || "这手可以聊，搭子先接住了。",
  };
}

function buildRuntimeErrorResult(runtimeResponse: DeadmanRuntimeResponse): ErrorResult {
  const code = runtimeResponse.error?.code || "runtime_error";
  return {
    kind: "error",
    title: "搭子卡住了",
    message: runtimeResponse.companion.utterance || "这次我卡住了，刚才那手先收一下。可以重试，或者继续看。",
    detail: `接口状态：runtime/${code}`,
    media: {
      status: "not_available",
      image_url: "",
      source: "runtime_failure",
      prompt: "",
      fallback_text: "接口失败，本次没有结果图。",
    },
  };
}

function buildApiFailureResult(error: unknown): ErrorResult {
  const message =
    error instanceof DeadmanApiError
      ? `${error.status}/${error.code}`
      : error instanceof Error
        ? error.name
        : "未知接口错误";
  return {
    kind: "error",
    title: "搭子卡住了",
    message: "这次我卡住了，刚才那手先收一下。可以重试，或者继续看。",
    detail: `接口状态：${message}`,
    media: {
      status: "not_available",
      image_url: "",
      source: "api_failure",
      prompt: "",
      fallback_text: "接口失败，本次没有结果图。",
    },
  };
}

function buildNarrativeResultText(judgment: DeadmanJudgmentResponse): string {
  const parts = [judgment.verdict.summary, judgment.consequence.text]
    .map((part) => sanitizeViewerCopy(part))
    .filter(Boolean);
  const narrative = parts.join(" ");
  return narrative || "这手可以聊，关键是别把话说满，先看这几个人会怎么接。";
}

function buildMicroCue(judgment: DeadmanJudgmentResponse): string | undefined {
  const stats = judgment.aggregate_stats;
  if (stats?.choices?.length) {
    const selectedChoice = stats.choices.find((choice) => choice.selected);
    if (selectedChoice?.percent) {
      return `有${selectedChoice.percent}%其他观众也这么想。`;
    }
  }
  if (judgment.consequence.watch_flow_fit === "low") {
    return "这手爽是爽，搭子建议收一点。";
  }
  return undefined;
}

function compactCompanionResultText(rawText: string): string {
  const cleanText = sanitizeViewerCopy(rawText);
  if (!cleanText) {
    return "这手可以聊，搭子先接住了。";
  }
  return cleanText.length > 58 ? `${cleanText.slice(0, 58)}...` : cleanText;
}

function compactMicroCue(rawText: string | undefined): string | undefined {
  if (!rawText) {
    return undefined;
  }
  const cleanText = sanitizeViewerCopy(rawText);
  if (!cleanText) {
    return undefined;
  }
  return cleanText.length > 28 ? `${cleanText.slice(0, 28)}...` : cleanText;
}

function sanitizeViewerCopy(value: string): string {
  const forbiddenPatterns = [
    /原剧情/g,
    /剧情结论/g,
    /不改写[^。！？.!?]*/g,
    /不改变[^。！？.!?]*/g,
    /没有任何影响/g,
    /不会影响[^。！？.!?]*/g,
    /后续主线/g,
    /主线/g,
    /分支剧情/g,
    /后面剧集/g,
    /未来分支/g,
  ];
  const sentences = value
    .replace(/([。！？.!?])/g, "$1\n")
    .split("\n")
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .filter((sentence) => !forbiddenPatterns.some((pattern) => {
      pattern.lastIndex = 0;
      return pattern.test(sentence);
    }));
  return sentences.join("");
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function ResultPanel({ result, onClose }: { result: StaticResult; onClose: () => void }) {
  return (
    <div className="branch3-player__result" aria-live="polite">
      <strong>我接住你咯</strong>
      <p>{result.text}</p>
      {result.microCue ? <span className="branch3-player__aggregate">{result.microCue}</span> : null}
      <div className="branch3-player__result-actions">
        <button onClick={onClose} type="button">
          {result.continueLabel || "继续看"} ▷
        </button>
        <button onClick={onClose} type="button">
          分享
        </button>
      </div>
    </div>
  );
}

function ErrorPanel({
  result,
  onRetry,
  onClose,
}: {
  result: ErrorResult;
  onRetry: () => void;
  onClose: () => void;
}) {
  return (
    <div className="branch3-player__error" role="alert">
      <strong>{result.title}</strong>
      <p>{result.message}</p>
      <span>{result.detail}</span>
      <ResultMedia media={result.media} />
      <div className="branch3-player__error-actions">
        <button onClick={onRetry} type="button">
          重试
        </button>
        <button onClick={onClose} type="button">
          继续看
        </button>
      </div>
    </div>
  );
}

function ResultMedia({ media }: { media?: ViewerResult["media"] }) {
  if (!media) {
    return null;
  }
  if (media.image_url) {
    return (
      <figure className="branch3-player__result-media">
        <img alt="看剧搭子结果图" src={media.image_url} />
        <figcaption>{media.prompt || "预生成结果图"}</figcaption>
      </figure>
    );
  }
  return (
    <div className="branch3-player__result-media branch3-player__result-media--fallback" role="status">
      <strong>结果图像位</strong>
      <span>{media.fallback_text || imageFallbackText(media.status)}</span>
    </div>
  );
}

function imageFallbackText(status: string | undefined): string {
  if (status === "placeholder") {
    return "P0 先保留图像槽位，这次显示文字后果。";
  }
  if (status === "not_available") {
    return "实时图像生成未配置，这次显示文字后果。";
  }
  return "结果图暂不可用，这次显示文字后果。";
}
