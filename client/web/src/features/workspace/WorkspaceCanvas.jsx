import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  FileText,
  Loader,
  Pause,
  Play,
  SendHorizontal,
  Sparkles,
} from "lucide-react";

import {
  fetchSessionOverview,
  fetchSessionTranscript,
} from "../../services/session-api.js";
import {
  enqueueReportGenerationJob,
  fetchFinalReportStatus,
  fetchLatestReport,
  fetchReportDetail,
  fetchReportGenerationJob,
} from "../../services/report-api.js";
import {
  getReportStatusLabel,
  getReportStatusTone,
  isLiveSession,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import { buildApiUrl } from "../../config/runtime.js";
import "./workspace-canvas.css";

const BADGE_COPY = {
  context: { label: "CONTEXT", tone: "context" },
  decision: { label: "DECISION", tone: "decision" },
  action_item: { label: "ACTION ITEM", tone: "action" },
  question: { label: "QUESTION", tone: "question" },
  risk: { label: "RISK", tone: "risk" },
};

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function formatMeetingDate(value) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "short",
    });
  } catch {
    return value;
  }
}

function formatTranscriptTime(startMs) {
  const totalSeconds = Math.max(0, Math.floor(Number(startMs || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const hours = Math.floor(minutes / 60);
  const minuteValue = minutes % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minuteValue).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minuteValue).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatAudioClock(totalSeconds) {
  const safeSeconds = Number.isFinite(totalSeconds) ? Math.max(0, Math.floor(totalSeconds)) : 0;
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatModeLabel(mode) {
  switch (String(mode ?? "").toLowerCase()) {
    case "strategy":
      return "전략 회의";
    case "review":
      return "리뷰 회의";
    case "daily":
      return "데일리";
    default:
      return "일반 회의";
  }
}

function formatEventState(state) {
  switch (String(state ?? "").toLowerCase()) {
    case "open":
    case "active":
      return "진행 중";
    case "resolved":
      return "해결";
    case "closed":
      return "종료";
    case "completed":
      return "완료";
    case "pending":
      return "대기";
    default:
      return state || "확인 필요";
  }
}

function buildTranscriptRows({ overview, reportDetail, transcriptItems }) {
  const speakerTranscript =
    transcriptItems?.length > 0
      ? transcriptItems
      : (reportDetail?.speaker_transcript ?? []);
  const speakerEvents = reportDetail?.speaker_events ?? [];

  if (speakerTranscript.length > 0) {
    const queueBySpeaker = new Map();
    for (const event of speakerEvents) {
      const key = event.speaker_label || "__default";
      const queue = queueBySpeaker.get(key) ?? [];
      queue.push(event);
      queueBySpeaker.set(key, queue);
    }

    return speakerTranscript.map((item, index) => {
      const key = item.speaker_label || "__default";
      const queue = queueBySpeaker.get(key) ?? [];
      const badge = queue.length > 0 ? queue.shift() : null;
      return {
        id: `${item.speaker_label}-${item.start_ms}-${index}`,
        speaker: item.speaker_label || "참석자",
        time: formatTranscriptTime(item.start_ms),
        text: item.text,
        badge,
      };
    });
  }

  const fallbackEvents = [
    ...(overview?.decisions ?? []).map((item) => ({ ...item, event_type: "decision" })),
    ...(overview?.action_items ?? []).map((item) => ({ ...item, event_type: "action_item" })),
    ...(overview?.questions ?? []).map((item) => ({ ...item, event_type: "question" })),
    ...(overview?.risks ?? []).map((item) => ({ ...item, event_type: "risk" })),
  ];

  return fallbackEvents.slice(0, 8).map((item, index) => ({
    id: item.id,
    speaker: item.speaker_label || "회의 메모",
    time: formatTranscriptTime(index * 90 * 1000),
    text: item.title,
    badge: {
      speaker_label: item.speaker_label,
      event_type: item.event_type,
      title: item.title,
      state: item.state,
    },
  }));
}

function buildAssistantMessages({ actionItems, currentTopic, decisions }) {
  const assistantIntro = {
    role: "assistant",
    text: "회의 내용을 기준으로 궁금한 점을 바로 물어볼 수 있습니다.",
  };

  if (actionItems.length > 0) {
    return [
      assistantIntro,
      {
        role: "user",
        text: "가장 먼저 챙겨야 할 액션이 뭐야?",
      },
      {
        role: "assistant",
        text: `${actionItems[0].title}${actionItems[0].speaker_label ? `, 담당은 ${actionItems[0].speaker_label}` : ""}`,
        linkText: "근거 보기",
      },
    ];
  }

  if (decisions.length > 0) {
    return [
      assistantIntro,
      {
        role: "user",
        text: "이번 회의에서 확정된 핵심 결정은 뭐야?",
      },
      {
        role: "assistant",
        text: decisions[0].title,
        linkText: "회의 근거 보기",
      },
    ];
  }

  return [
    assistantIntro,
    {
      role: "assistant",
      text: currentTopic || "아직 정리된 회의 요약이 없습니다.",
    },
  ];
}

function buildEmptyState(workflow) {
  if (workflow.pipelineStage === "post_processing") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의 정리에 실패했습니다",
        progressLabel: "정리 실패",
        actionLabel: null,
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "회의를 정리하고 있습니다",
        progressLabel: "정리 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "회의 정리를 준비하고 있습니다",
      progressLabel: "정리 대기",
      actionLabel: null,
    };
  }

  if (workflow.pipelineStage === "report_generation") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "리포트 생성에 실패했습니다",
        progressLabel: "리포트 실패",
        actionLabel: "리포트 다시 생성",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "리포트를 작성하고 있습니다",
        progressLabel: "리포트 작성 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "리포트 생성을 기다리고 있습니다",
      progressLabel: "리포트 대기",
      actionLabel: "리포트 다시 생성",
    };
  }

  if (workflow.category === "running") {
    return {
      tone: "live",
      title: "회의가 진행 중입니다",
      progressLabel: "실시간 회의",
      actionLabel: null,
    };
  }

  return {
    tone: "default",
    title: "아직 표시할 transcript가 없습니다",
    progressLabel: "준비 중",
    actionLabel: null,
  };
}

function TranscriptEmptyState({ emptyState, canRetryReport, generating, onGenerateReport, workflow }) {
  const isProcessing = emptyState.tone === "processing";
  const showSkeleton = ["processing", "pending", "live"].includes(emptyState.tone);

  return (
    <div className={`caps-transcript-empty ${emptyState.tone}`}>
      <div className="caps-transcript-empty-card">
        <div className="caps-transcript-empty-head">
          <span className={`caps-transcript-empty-pill ${emptyState.tone}`}>
            {isProcessing ? <Loader size={13} className="spinner" /> : null}
            {emptyState.progressLabel}
          </span>
          <h3>{emptyState.title}</h3>
        </div>

        {showSkeleton ? (
          <div className="caps-transcript-empty-skeletons" aria-hidden="true">
            <div className="session-preview-skeleton short" />
            <div className="session-preview-skeleton long" />
            <div className="session-preview-skeleton medium" />
          </div>
        ) : null}

        {canRetryReport && emptyState.actionLabel ? (
          <button
            className="caps-generate-button"
            disabled={generating || workflow.status === "processing"}
            onClick={onGenerateReport}
            type="button"
          >
            {generating ? (
              <>
                <Loader size={15} className="spinner" />
                처리 중
              </>
            ) : (
              <>
                <Sparkles size={15} />
                {emptyState.actionLabel}
              </>
            )}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function TranscriptBadge({ badge }) {
  if (!badge) {
    return null;
  }

  const copy = BADGE_COPY[String(badge.event_type ?? "").toLowerCase()] ?? {
    label: String(badge.event_type ?? "EVENT").toUpperCase(),
    tone: "context",
  };

  return (
    <div className={`caps-transcript-tag ${copy.tone}`}>
      <span>{copy.label}</span>
    </div>
  );
}

export default function WorkspaceCanvas({
  onOpenDetail,
  onRefreshWorkspace,
  refreshToken,
  sessionId,
}) {
  const audioRef = useRef(null);
  const audioObjectUrlRef = useRef(null);
  const shouldSyncWorkspaceRef = useRef(false);
  const [overview, setOverview] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [reportStatus, setReportStatus] = useState(null);
  const [latestReport, setLatestReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [sessionReloadToken, setSessionReloadToken] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        if (overview == null || overview?.session?.id !== sessionId || reportStatus == null) {
          setLoading(true);
        }
        setError(null);
        setActionError(null);

        const [nextOverview, nextTranscript, nextReportStatus] = await Promise.all([
          fetchSessionOverview({ sessionId }),
          fetchSessionTranscript({ sessionId }),
          fetchFinalReportStatus({ sessionId }),
        ]);

        let nextLatestReport = null;
        let nextReportDetail = null;
        if (nextReportStatus.status === "completed" && nextReportStatus.latest_report_id) {
          nextLatestReport = await fetchLatestReport({ sessionId });
          nextReportDetail = await fetchReportDetail({
            sessionId,
            reportId: nextReportStatus.latest_report_id,
          });
        }

        if (!cancelled) {
          setOverview(nextOverview);
          setTranscript(nextTranscript);
          setReportStatus(nextReportStatus);
          setLatestReport(nextLatestReport);
          setReportDetail(nextReportDetail);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "회의 화면을 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [overview?.session?.id, refreshToken, reportStatus?.session_id, sessionId, sessionReloadToken]);

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
      setPlayingAudio(false);
    }

    function handleEnded() {
      setPlayingAudio(false);
    }

    function handleLoadedMetadata() {
      setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      setAudioCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
      setLoadingAudio(false);
    }

    function handleTimeUpdate() {
      setAudioCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
    }

    function handleWaiting() {
      setLoadingAudio(true);
    }

    function handleError() {
      setLoadingAudio(false);
      setPlayingAudio(false);
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
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (audioObjectUrlRef.current) {
        URL.revokeObjectURL(audioObjectUrlRef.current);
        audioObjectUrlRef.current = null;
      }
    };
  }, []);

  const session = overview?.session;
  const isLive = isLiveSession(session?.status);
  const workflow = useMemo(
    () => resolveWorkflowStatus(session, reportStatus),
    [reportStatus, session],
  );
  const transcriptRows = useMemo(
    () => buildTranscriptRows({ overview, reportDetail, transcriptItems: transcript?.items }),
    [overview, reportDetail, transcript?.items],
  );
  const oneLineSummary = useMemo(() => {
    if (latestReport?.content) {
      const firstLine = latestReport.content
        .split("\n")
        .map((line) => line.trim())
        .find(Boolean);
      if (firstLine) {
        return firstLine;
      }
    }
    return overview?.current_topic || session?.title || "회의 요약이 아직 없습니다.";
  }, [latestReport?.content, overview?.current_topic, session?.title]);
  const assistantMessages = useMemo(
    () =>
      buildAssistantMessages({
        actionItems: overview?.action_items ?? [],
        currentTopic: overview?.current_topic,
        decisions: overview?.decisions ?? [],
      }),
    [overview?.action_items, overview?.current_topic, overview?.decisions],
  );
  const emptyState = useMemo(() => buildEmptyState(workflow), [workflow]);
  const canRetryReport = !isLive && workflow.pipelineStage === "report_generation";
  const hidePreviousNote =
    ["post_processing", "report_generation"].includes(workflow.pipelineStage) &&
    (workflow.status === "pending" || workflow.status === "processing");
  const visibleTranscriptRows = hidePreviousNote ? [] : transcriptRows;
  const visibleLatestReport = hidePreviousNote ? null : latestReport;
  const summaryHeadline = hidePreviousNote
    ? (workflow.status === "processing"
        ? "새 노트를 만드는 중입니다."
        : "새 노트 생성을 준비하고 있습니다.")
    : oneLineSummary;

  useEffect(() => {
    const shouldPoll =
      !isLive &&
      ["post_processing", "report_generation"].includes(workflow.pipelineStage) &&
      ["pending", "processing"].includes(workflow.status);

    if (shouldPoll) {
      shouldSyncWorkspaceRef.current = true;
      const timerId = window.setTimeout(() => {
        setSessionReloadToken((current) => current + 1);
      }, 2500);
      return () => {
        window.clearTimeout(timerId);
      };
    }

    if (shouldSyncWorkspaceRef.current && ["completed", "failed"].includes(workflow.status)) {
      shouldSyncWorkspaceRef.current = false;
      void onRefreshWorkspace();
    }

    return undefined;
  }, [isLive, onRefreshWorkspace, workflow.pipelineStage, workflow.status]);

  async function handleGenerateReport() {
    try {
      setGenerating(true);
      setActionError(null);
      await enqueueReportGenerationJob({ sessionId });

      for (let attempt = 0; attempt < 25; attempt += 1) {
        const job = await fetchReportGenerationJob({ sessionId });
        if (job.status === "completed" || job.status === "failed") {
          break;
        }
        await sleep(1500);
      }

      const nextStatus = await fetchFinalReportStatus({ sessionId });
      setReportStatus(nextStatus);
      if (nextStatus.status === "completed" && nextStatus.latest_report_id) {
        const nextLatest = await fetchLatestReport({ sessionId });
        const nextDetail = await fetchReportDetail({
          sessionId,
          reportId: nextStatus.latest_report_id,
        });
        setLatestReport(nextLatest);
        setReportDetail(nextDetail);
      }
      await onRefreshWorkspace();
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "리포트 생성 요청에 실패했습니다.",
      );
    } finally {
      setGenerating(false);
    }
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

      if (!session?.recording_artifact_id) {
        setActionError("아직 연결된 녹음 파일이 없습니다.");
        return;
      }

      setLoadingAudio(true);
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
  }

  if (loading) {
    return (
      <div className="workspace-state-view">
        <Loader className="spinner" size={28} />
        <p>회의 화면을 불러오는 중입니다.</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="workspace-state-view error">
        <AlertCircle size={28} />
        <h3>회의 화면을 열 수 없습니다.</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div
      className={`caps-meeting-workspace animate-fade-in ${session?.recording_artifact_id ? "has-audio-player" : ""}`}
    >
      <audio ref={audioRef} hidden preload="metadata" />
      <section className="caps-transcript-panel">
        <div className="caps-transcript-header">
          <div>
            <div className="caps-transcript-meta">
              <span className="caps-transcript-mode">{formatModeLabel(session.mode)}</span>
              <span>
                {`${formatMeetingDate(session.started_at)} · ${isLive ? "실시간 회의" : "회의 노트"}`}
              </span>
            </div>
            <h1>{session.title || "제목 없는 회의"}</h1>
          </div>

          <div className="caps-transcript-actions">
            {visibleLatestReport ? (
              <button
                className="caps-transcript-button"
                onClick={() =>
                  onOpenDetail({
                    type: "report",
                    reportId: visibleLatestReport.id,
                    sessionId,
                  })
                }
                type="button"
              >
                <FileText size={14} />
                리포트 보기
              </button>
            ) : null}
            <button
              className="caps-transcript-button"
              onClick={handleToggleAudioPlayback}
              type="button"
            >
              {playingAudio ? <Pause size={14} /> : <Play size={14} />}
              오디오 재생
            </button>
          </div>
        </div>

        {actionError ? <div className="caps-inline-alert">{actionError}</div> : null}

        <div className="caps-transcript-scroll">
          {visibleTranscriptRows.length > 0 ? (
            visibleTranscriptRows.map((row) => (
              <div key={row.id} className="caps-transcript-row">
                <div className="caps-transcript-speaker">
                  <div className="caps-transcript-name">{row.speaker}</div>
                  <div className="caps-transcript-time">{row.time}</div>
                </div>

                <div className="caps-transcript-content">
                  <TranscriptBadge badge={row.badge} />
                  <p>{row.text}</p>
                </div>
              </div>
            ))
          ) : (
            <TranscriptEmptyState
              canRetryReport={canRetryReport}
              emptyState={emptyState}
              generating={generating}
              onGenerateReport={handleGenerateReport}
              workflow={workflow}
            />
          )}
        </div>
      </section>

      <aside className="caps-insight-panel">
        <div className="caps-summary-block">
          <div className="caps-summary-header">
            <h3>회의 요약</h3>
            <span className={`caps-status-badge ${getReportStatusTone(reportStatus, session)}`}>
              {getReportStatusLabel(reportStatus, session)}
            </span>
          </div>

          <div className="caps-summary-headline">{summaryHeadline}</div>

          {hidePreviousNote ? null : <div className="caps-summary-section">
            <p className="caps-summary-label">주요 결정 사항</p>
            <ul className="caps-summary-bullets">
              {(overview?.decisions ?? []).slice(0, 3).map((item) => (
                <li key={item.id}>{item.title}</li>
              ))}
              {(overview?.decisions ?? []).length === 0 ? <li>아직 정리된 결정이 없습니다.</li> : null}
            </ul>
          </div>}

          {hidePreviousNote ? null : <div className="caps-summary-section">
            <p className="caps-summary-label">후속 조치</p>
            <div className="caps-action-stack">
              {(overview?.action_items ?? []).slice(0, 3).map((item) => (
                <div key={item.id} className="caps-action-card">
                  <span>{item.title}</span>
                  <strong>{item.speaker_label || formatEventState(item.state)}</strong>
                </div>
              ))}
              {(overview?.action_items ?? []).length === 0 ? (
                <div className="caps-action-card empty">
                  <span>등록된 후속 조치가 없습니다.</span>
                </div>
              ) : null}
            </div>
          </div>}

          {hidePreviousNote ? null : <div className="caps-summary-section">
            <p className="caps-summary-label">미해결 질문 및 리스크</p>
            <div className="caps-risk-stack">
              {[...(overview?.questions ?? []), ...(overview?.risks ?? [])].slice(0, 2).map((item) => (
                <div key={item.id} className="caps-risk-card">
                  <AlertTriangle size={14} />
                  <span>{item.title}</span>
                </div>
              ))}
              {((overview?.questions ?? []).length + (overview?.risks ?? []).length) === 0 ? (
                <div className="caps-risk-card empty">
                  <AlertTriangle size={14} />
                  <span>열린 질문이나 리스크가 없습니다.</span>
                </div>
              ) : null}
            </div>
          </div>}
        </div>

        <div className="caps-assistant-block">
          <div className="caps-assistant-header">
            <Sparkles size={16} />
            <h3>AI 어시스턴트</h3>
          </div>

          <div className="caps-assistant-messages">
            {(hidePreviousNote
              ? [
                  {
                    role: "assistant",
                    text:
                      workflow.status === "processing"
                        ? "새 노트를 만드는 중입니다."
                        : "새 노트 생성을 준비하고 있습니다.",
                  },
                ]
              : assistantMessages
            ).map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`caps-chat-row ${message.role === "user" ? "user" : "assistant"}`}
              >
                <div className="caps-chat-bubble">
                  <p>{message.text}</p>
                  {message.linkText ? (
                    <button
                      className="caps-chat-link"
                      onClick={() =>
                        visibleLatestReport
                          ? onOpenDetail({
                              type: "report",
                              reportId: visibleLatestReport.id,
                              sessionId,
                            })
                          : null
                      }
                      type="button"
                    >
                      {message.linkText}
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <div className="caps-assistant-input">
            <input placeholder="AI에게 질문하기..." type="text" />
            <button type="button">
              <SendHorizontal size={15} />
            </button>
          </div>
        </div>
      </aside>

      {session?.recording_artifact_id ? (
        <div className="caps-audio-player">
          <div className="caps-audio-player-main">
            <button
              className="caps-audio-player-button"
              disabled={loadingAudio}
              onClick={handleToggleAudioPlayback}
              type="button"
            >
              {loadingAudio ? (
                <Loader className="spinner" size={16} />
              ) : playingAudio ? (
                <Pause size={16} />
              ) : (
                <Play size={16} />
              )}
            </button>

            <div className="caps-audio-player-copy">
              <strong>회의 녹음</strong>
              <span>{playingAudio ? "재생 중" : loadingAudio ? "불러오는 중" : "재생 준비"}</span>
            </div>
          </div>

          <div className="caps-audio-player-track">
            <span className="caps-audio-player-time">{formatAudioClock(audioCurrentTime)}</span>
            <input
              className="caps-audio-player-slider"
              max={audioDuration > 0 ? audioDuration : 0}
              min="0"
              onChange={handleSeekAudio}
              step="0.1"
              type="range"
              value={audioDuration > 0 ? Math.min(audioCurrentTime, audioDuration) : 0}
            />
            <span className="caps-audio-player-time">{formatAudioClock(audioDuration)}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
