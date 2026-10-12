/** 워크스페이스 캔버스의 세션 데이터 로딩·폴링과 녹음 재생 상태를 훅으로 묶는다. */
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchSessionOverview, fetchSessionTranscript } from "../../services/session-api.js";
import {
  fetchFinalReportStatus,
  fetchLatestReport,
  fetchReportDetail,
} from "../../services/report-api.js";
import { buildApiUrl } from "../../config/runtime.js";
import {
  buildPollingPlan,
  canPlayTranscriptRow,
  isStaleWorkspaceResponse,
  shouldClearActionNoticeAfterLoad,
  shouldFetchLatestReport,
  waitForAudioMetadata,
} from "./workspace-canvas-model.js";

const WORKSPACE_DEBUG = import.meta.env.DEV;

export function debugWorkspace(event, payload = {}) {
  if (!WORKSPACE_DEBUG) {
    return;
  }
  console.debug("[CAPS][workspace]", event, payload);
}

export function useWorkspaceSessionData({ refreshToken, sessionId, setActionError }) {
  const overviewRef = useRef(null);
  const transcriptRef = useRef(null);
  const latestReportRef = useRef(null);
  const reportDetailRef = useRef(null);
  const isMountedRef = useRef(true);
  const shouldSyncWorkspaceRef = useRef(false);
  const hasLoadedSessionRef = useRef(false);
  const previousSessionIdRef = useRef(sessionId);
  const latestSessionIdRef = useRef(sessionId);
  const loadRequestIdRef = useRef(0);

  const [overview, setOverview] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [reportStatus, setReportStatus] = useState(null);
  const [latestReport, setLatestReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  const loadSessionData = useCallback(
    async ({
      background = false,
      includeOverview = true,
      includeTranscript = true,
      includeReportDetail = true,
    } = {}) => {
      debugWorkspace("load:start", {
        background,
        includeOverview,
        includeReportDetail,
        includeTranscript,
        sessionId,
      });
      if (!background) {
        setLoading(true);
        setError(null);
        setActionError(null);
      }
      const requestId = ++loadRequestIdRef.current;
      const requestedSessionId = sessionId;

      const nextReportStatus = await fetchFinalReportStatus({ sessionId });
      const nextOverviewPromise = includeOverview
        ? fetchSessionOverview({ sessionId })
        : Promise.resolve(overviewRef.current);
      const nextTranscriptPromise = includeTranscript
        ? fetchSessionTranscript({ sessionId })
        : Promise.resolve(transcriptRef.current);

      const [nextOverview, nextTranscript] = await Promise.all([
        nextOverviewPromise,
        nextTranscriptPromise,
      ]);

      let nextLatestReport = null;
      let nextReportDetail = null;
      if (shouldFetchLatestReport(nextReportStatus, includeReportDetail)) {
        nextLatestReport = await fetchLatestReport({ sessionId });
        nextReportDetail = await fetchReportDetail({
          sessionId,
          reportId: nextReportStatus.latest_report_id,
        });
      } else if (!includeReportDetail) {
        nextLatestReport = latestReportRef.current;
        nextReportDetail = reportDetailRef.current;
      }

      if (!isMountedRef.current) {
        debugWorkspace("load:skip-unmounted", {
          background,
          includeOverview,
          includeReportDetail,
          includeTranscript,
          sessionId,
        });
        return;
      }
      // 세션을 빠르게 전환하거나 background poll 응답이 늦게 도착한 경우
      // 오래된 응답이 현재 화면을 덮지 않도록 request/session 쌍을 확인한다.
      if (
        isStaleWorkspaceResponse({
          latestRequestId: loadRequestIdRef.current,
          latestSessionId: latestSessionIdRef.current,
          requestId,
          requestedSessionId,
        })
      ) {
        debugWorkspace("load:skip-stale", {
          requestId,
          requestedSessionId,
          sessionId: latestSessionIdRef.current,
        });
        return;
      }

      debugWorkspace("load:success", {
        background,
        fetchedOverview: includeOverview,
        fetchedReportDetail: includeReportDetail,
        fetchedTranscript: includeTranscript,
        latestJobStatus: nextReportStatus.latest_job_status ?? null,
        latestReportId: nextReportStatus.latest_report_id ?? null,
        reportStatus: nextReportStatus.status,
        sessionId,
        transcriptCount: nextTranscript?.items?.length ?? 0,
      });
      setOverview(nextOverview);
      setTranscript(nextTranscript);
      setReportStatus(nextReportStatus);
      setLatestReport(nextLatestReport);
      setReportDetail(nextReportDetail);
      if (shouldClearActionNoticeAfterLoad(nextReportStatus, nextOverview)) {
        setActionNotice(null);
      }
      hasLoadedSessionRef.current = true;

      if (!background) {
        setLoading(false);
      }
    },
    [sessionId],
  );

  useEffect(() => {
    overviewRef.current = overview;
  }, [overview]);

  useEffect(() => {
    transcriptRef.current = transcript;
  }, [transcript]);

  useEffect(() => {
    latestReportRef.current = latestReport;
  }, [latestReport]);

  useEffect(() => {
    reportDetailRef.current = reportDetail;
  }, [reportDetail]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    latestSessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    const sameSession = previousSessionIdRef.current === sessionId;
    const shouldLoadInBackground = hasLoadedSessionRef.current && sameSession;
    previousSessionIdRef.current = sessionId;

    async function loadSession() {
      try {
        debugWorkspace("effect:load-session", {
          refreshToken,
          sameSession,
          sessionId,
          shouldLoadInBackground,
        });
        await loadSessionData({ background: shouldLoadInBackground });
      } catch (nextError) {
        debugWorkspace("load:error", {
          background: shouldLoadInBackground,
          message: nextError instanceof Error ? nextError.message : String(nextError),
          sessionId,
        });
        if (cancelled || latestSessionIdRef.current !== sessionId) {
          return;
        }
        if (!shouldLoadInBackground) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "회의 화면을 불러오지 못했습니다.",
          );
          setLoading(false);
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [loadSessionData, refreshToken, sessionId]);

  useEffect(() => {
    hasLoadedSessionRef.current = false;
    setActionNotice(null);
  }, [sessionId]);

  return {
    actionNotice,
    error,
    hasLoadedSessionRef,
    latestReport,
    loading,
    loadSessionData,
    overview,
    reportDetail,
    reportStatus,
    setActionNotice,
    setLatestReport,
    setOverview,
    setReportDetail,
    setReportStatus,
    shouldSyncWorkspaceRef,
    transcript,
  };
}

export function useWorkspaceSessionPolling({
  hasLoadedSessionRef,
  isLive,
  loadSessionData,
  loading,
  onRefreshWorkspace,
  reportStatus,
  session,
  shouldSyncWorkspaceRef,
  workflow,
}) {
  useEffect(() => {
    if (loading || !hasLoadedSessionRef.current || !session || reportStatus == null) {
      return undefined;
    }

    const pollingPlan = buildPollingPlan({ isLive, reportStatus, workflow });

    if (pollingPlan) {
      shouldSyncWorkspaceRef.current = true;
      const timerId = window.setTimeout(() => {
        void loadSessionData({
          background: true,
          ...pollingPlan.loadOptions,
        }).catch(() => {});
      }, pollingPlan.intervalMs);
      return () => {
        window.clearTimeout(timerId);
      };
    }

    if (shouldSyncWorkspaceRef.current && ["completed", "failed"].includes(workflow.status)) {
      shouldSyncWorkspaceRef.current = false;
      void onRefreshWorkspace({ background: true, syncSession: false });
    }

    return undefined;
  }, [
    isLive,
    loadSessionData,
    loading,
    onRefreshWorkspace,
    reportStatus,
    session,
    workflow.pipelineStage,
    workflow.status,
  ]);
}

export function useWorkspaceAudioState({ canDownloadRecording, sessionId, setActionError }) {
  const audioRef = useRef(null);
  const audioObjectUrlRef = useRef(null);
  const activeClipRef = useRef(null);

  const [playingAudio, setPlayingAudio] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [activeClip, setActiveClip] = useState(null);

  useEffect(() => {
    activeClipRef.current = activeClip;
  }, [activeClip]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return undefined;
    }

    function handlePlay() {
      setLoadingAudio(false);
      setPlayingAudio(true);
    }

    function handlePause() {
      setLoadingAudio(false);
      setPlayingAudio(false);
    }

    function handleEnded() {
      setLoadingAudio(false);
      setPlayingAudio(false);
    }

    function handleLoadedMetadata() {
      setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      setAudioCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
      setLoadingAudio(false);
    }

    function handleTimeUpdate() {
      const nextCurrentTime = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
      const clip = activeClipRef.current;
      if (clip && nextCurrentTime >= clip.endTimeSeconds) {
        audio.currentTime = clip.endTimeSeconds;
        setLoadingAudio(false);
        audio.pause();
        setAudioCurrentTime(clip.endTimeSeconds);
        return;
      }
      setAudioCurrentTime(nextCurrentTime);
    }

    function handleWaiting() {
      setLoadingAudio(true);
    }

    function handleError() {
      setLoadingAudio(false);
      setPlayingAudio(false);
      setActiveClip(null);
      setActionError("녹음 파일을 재생하지 못했습니다.");
    }

    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("waiting", handleWaiting);
    audio.addEventListener("error", handleError);
    return () => {
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("waiting", handleWaiting);
      audio.removeEventListener("error", handleError);
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    if (audioObjectUrlRef.current) {
      URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = null;
    }
    setLoadingAudio(false);
    setPlayingAudio(false);
    setAudioCurrentTime(0);
    setAudioDuration(0);
    setActiveClip(null);
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (audioObjectUrlRef.current) {
        URL.revokeObjectURL(audioObjectUrlRef.current);
        audioObjectUrlRef.current = null;
      }
    };
  }, []);

  async function ensureAudioSourceLoaded(audio) {
    if (!canDownloadRecording) {
      throw new Error("아직 연결된 녹음 파일이 없습니다.");
    }

    if (!audioObjectUrlRef.current) {
      const response = await fetch(buildApiUrl(`/api/v1/sessions/${sessionId}/recording`));
      if (!response.ok) {
        throw new Error(`녹음 파일을 불러오지 못했습니다. (${response.status})`);
      }

      const audioBlob = await response.blob();
      if (audioObjectUrlRef.current) {
        URL.revokeObjectURL(audioObjectUrlRef.current);
      }
      audioObjectUrlRef.current = URL.createObjectURL(audioBlob);
      audio.src = audioObjectUrlRef.current;
      audio.load();
    }

    await waitForAudioMetadata(audio);
  }

  async function handleToggleAudioPlayback() {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    try {
      setActionError(null);
      if (playingAudio) {
        audio.pause();
        return;
      }

      setLoadingAudio(true);
      await ensureAudioSourceLoaded(audio);
      if (activeClipRef.current && audio.currentTime >= activeClipRef.current.endTimeSeconds) {
        audio.currentTime = activeClipRef.current.startTimeSeconds;
        setAudioCurrentTime(activeClipRef.current.startTimeSeconds);
      }
      await audio.play();
    } catch (nextError) {
      setLoadingAudio(false);
      setPlayingAudio(false);
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "녹음 파일을 재생하지 못했습니다.",
      );
    }
  }

  async function handlePlayTranscriptClip(row) {
    if (!canPlayTranscriptRow(row)) {
      return;
    }

    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    const startTimeSeconds = row.startMs / 1000;
    const endTimeSeconds = row.endMs / 1000;

    try {
      setActionError(null);
      setLoadingAudio(true);
      setActiveClip({
        id: row.id,
        startTimeSeconds,
        endTimeSeconds,
      });
      await ensureAudioSourceLoaded(audio);
      audio.currentTime = startTimeSeconds;
      setAudioCurrentTime(startTimeSeconds);
      await audio.play();
    } catch (nextError) {
      setLoadingAudio(false);
      setPlayingAudio(false);
      setActiveClip(null);
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "선택한 발화 구간을 재생하지 못했습니다.",
      );
    }
  }

  function handleSeekAudio(event) {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    const nextValue = Number(event.target.value);
    if (!Number.isFinite(nextValue)) {
      return;
    }

    audio.currentTime = nextValue;
    setAudioCurrentTime(nextValue);
    setActiveClip(null);
  }

  return {
    activeClip,
    audioCurrentTime,
    audioDuration,
    audioRef,
    handlePlayTranscriptClip,
    handleSeekAudio,
    handleToggleAudioPlayback,
    loadingAudio,
    playingAudio,
  };
}
