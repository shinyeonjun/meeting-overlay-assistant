/** 워크스페이스 녹음 플레이어의 준비, 재생, 구간 반복 상태를 관리한다. */
import { useEffect, useRef, useState } from "react";

import { buildApiUrl } from "../../../config/runtime.js";

function canPlayTranscriptRow(row) {
  return Number.isFinite(row?.startMs) && Number.isFinite(row?.endMs) && row.endMs > row.startMs;
}

function hasLoadedAudioMetadata(audio) {
  return audio.readyState >= 1 && Number.isFinite(audio.duration);
}

function waitForAudioMetadata(audio) {
  if (hasLoadedAudioMetadata(audio)) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    function cleanup() {
      audio.removeEventListener("loadedmetadata", handleLoaded);
      audio.removeEventListener("error", handleError);
    }

    function handleLoaded() {
      cleanup();
      resolve();
    }

    function handleError() {
      cleanup();
      reject(new Error("녹음 정보를 불러오지 못했습니다."));
    }

    audio.addEventListener("loadedmetadata", handleLoaded);
    audio.addEventListener("error", handleError);
  });
}

/**
 * 녹음 메타데이터를 세션 진입 직후 준비하고,
 * 플레이어와 회의 내용 구간 재생을 같은 상태 머신으로 다룬다.
 */
export default function useWorkspaceAudioPlayback({ canDownloadRecording, sessionId }) {
  const audioRef = useRef(null);
  const activeClipRef = useRef(null);
  const metadataPromiseRef = useRef(null);
  const requestVersionRef = useRef(0);
  const playbackRequestIdRef = useRef(0);
  const preparedSourceUrlRef = useRef(null);

  const [playingAudio, setPlayingAudio] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
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
      setAudioReady(true);
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
      if (!audio.paused) {
        setLoadingAudio(true);
      }
    }

    function handleError() {
      setLoadingAudio(false);
      setPlayingAudio(false);
      setAudioReady(false);
      setActiveClip(null);
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

  function isActiveRequest(requestVersion) {
    return requestVersionRef.current === requestVersion;
  }

  function isActivePlaybackRequest(playbackRequestId) {
    return playbackRequestIdRef.current === playbackRequestId;
  }

  function prepareAudioSource(audio) {
    const nextSourceUrl = buildApiUrl(`/api/v1/sessions/${sessionId}/recording`);
    if (preparedSourceUrlRef.current !== nextSourceUrl || audio.getAttribute("src") !== nextSourceUrl) {
      preparedSourceUrlRef.current = nextSourceUrl;
      audio.src = nextSourceUrl;
      audio.load();
    }
  }

  function cancelPendingPlayback() {
    const audio = audioRef.current;
    playbackRequestIdRef.current += 1;
    setLoadingAudio(false);
    setPlayingAudio(false);
    setActiveClip(null);
    if (audio) {
      audio.pause();
    }
  }

  async function preloadAudioMetadata(audio, { requestVersion = requestVersionRef.current } = {}) {
    if (!canDownloadRecording) {
      throw new Error("아직 연결된 녹음 파일이 없습니다.");
    }

    if (hasLoadedAudioMetadata(audio)) {
      if (isActiveRequest(requestVersion)) {
        setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
        setAudioCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
        setAudioReady(true);
      }
      return;
    }

    prepareAudioSource(audio);

    if (!metadataPromiseRef.current) {
      metadataPromiseRef.current = waitForAudioMetadata(audio).finally(() => {
        metadataPromiseRef.current = null;
      });
    }

    try {
      await metadataPromiseRef.current;
      if (!isActiveRequest(requestVersion)) {
        return;
      }
      setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      setAudioCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
      setAudioReady(true);
    } catch (error) {
      if (!isActiveRequest(requestVersion)) {
        return;
      }
      setAudioReady(false);
      throw error;
    }
  }

  useEffect(() => {
    const audio = audioRef.current;
    requestVersionRef.current += 1;
    playbackRequestIdRef.current += 1;
    metadataPromiseRef.current = null;
    preparedSourceUrlRef.current = null;

    if (!audio) {
      return;
    }

    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    setLoadingAudio(false);
    setPlayingAudio(false);
    setAudioReady(false);
    setAudioCurrentTime(0);
    setAudioDuration(0);
    setActiveClip(null);

    if (!canDownloadRecording) {
      return;
    }

    const requestVersion = requestVersionRef.current;
    void preloadAudioMetadata(audio, { requestVersion }).catch(() => {});
  }, [canDownloadRecording, sessionId]);

  async function handleToggleAudioPlayback() {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    if (loadingAudio) {
      cancelPendingPlayback();
      return;
    }

    if (playingAudio) {
      audio.pause();
      setActiveClip(null);
      return;
    }

    try {
      const playbackRequestId = ++playbackRequestIdRef.current;
      setLoadingAudio(true);
      await preloadAudioMetadata(audio);
      if (!isActivePlaybackRequest(playbackRequestId)) {
        return;
      }
      if (activeClipRef.current && audio.currentTime >= activeClipRef.current.endTimeSeconds) {
        audio.currentTime = activeClipRef.current.startTimeSeconds;
        setAudioCurrentTime(activeClipRef.current.startTimeSeconds);
      }
      await audio.play();
      if (!isActivePlaybackRequest(playbackRequestId)) {
        audio.pause();
      }
    } catch {
      setLoadingAudio(false);
      setPlayingAudio(false);
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

    if (loadingAudio && activeClipRef.current?.id === row.id) {
      cancelPendingPlayback();
      return;
    }

    if (playingAudio && activeClipRef.current?.id === row.id) {
      audio.pause();
      setActiveClip(null);
      return;
    }

    try {
      const playbackRequestId = ++playbackRequestIdRef.current;
      setLoadingAudio(true);
      setActiveClip({
        id: row.id,
        startTimeSeconds,
        endTimeSeconds,
      });
      await preloadAudioMetadata(audio);
      if (!isActivePlaybackRequest(playbackRequestId)) {
        return;
      }
      audio.currentTime = startTimeSeconds;
      setAudioCurrentTime(startTimeSeconds);
      await audio.play();
      if (!isActivePlaybackRequest(playbackRequestId)) {
        audio.pause();
      }
    } catch {
      setLoadingAudio(false);
      setPlayingAudio(false);
      setActiveClip(null);
    }
  }

  function handleSeekAudio(event) {
    const audio = audioRef.current;
    if (!audio || !audioReady || audioDuration <= 0) {
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
    audioReady,
    audioRef,
    handlePlayTranscriptClip,
    handleSeekAudio,
    handleToggleAudioPlayback,
    loadingAudio,
    playingAudio,
  };
}
