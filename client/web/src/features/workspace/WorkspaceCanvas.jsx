/** 웹 워크스페이스의 워크스페이스 기능 화면을 렌더링한다. */
import React, { memo, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  FileDown,
  FileText,
  Loader,
  Pause,
  Play,
  SendHorizontal,
  Sparkles,
} from "lucide-react";

import { reprocessSession } from "../../services/session-api.js";
import { enqueueReportGenerationJob } from "../../services/report-api.js";
import {
  getReportStatusLabel,
  getReportStatusTone,
  isLiveSession,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import { buildApiUrl } from "../../config/runtime.js";
import "./workspace-canvas.css";
import {
  formatMeetingDate,
  formatTranscriptTime,
  formatAudioClock,
  formatModeLabel,
  formatEventState,
  buildTranscriptRows,
  canPlayTranscriptRow,
  buildAssistantMessages,
  buildEmptyState,
  hasRecordingAvailable,
} from "./workspace-canvas-model.js";
import {
  TranscriptBadge,
  TranscriptEmptyState,
  TranscriptProgressHero,
} from "./WorkspaceCanvasParts.jsx";
import {
  debugWorkspace,
  useWorkspaceAudioState,
  useWorkspaceSessionData,
  useWorkspaceSessionPolling,
} from "./use-workspace-canvas-state.js";


function WorkspaceCanvas({
  onOpenDetail,
  onRefreshWorkspace,
  refreshToken,
  sessionId,
}) {
  const [actionError, setActionError] = useState(null);
  const [processingAction, setProcessingAction] = useState(false);
  const {
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
  } = useWorkspaceSessionData({ refreshToken, sessionId, setActionError });

  const session = overview?.session;
  const canDownloadRecording = hasRecordingAvailable(session);
  const {
    activeClip,
    audioCurrentTime,
    audioDuration,
    audioRef,
    handlePlayTranscriptClip,
    handleSeekAudio,
    handleToggleAudioPlayback,
    loadingAudio,
    playingAudio,
  } = useWorkspaceAudioState({ canDownloadRecording, sessionId, setActionError });

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
  const downloadHref = canDownloadRecording
    ? buildApiUrl(`/api/v1/sessions/${sessionId}/recording?download=true`)
    : null;
  const hidePreviousNote =
    ["post_processing", "note_correction", "report_generation"].includes(workflow.pipelineStage) &&
    (workflow.status === "pending" || workflow.status === "processing");
  const visibleTranscriptRows = transcriptRows;
  const visibleLatestReport = hidePreviousNote ? null : latestReport;
  // 처리 중에는 상태 카드와 초안 rows를 함께 보여주고, 완료 시 최종 노트로 전환한다.
  const showTranscriptProgressHero =
    ["post_processing", "note_correction"].includes(workflow.pipelineStage) &&
    ["pending", "processing"].includes(workflow.status);
  const summaryHeadline = hidePreviousNote
    ? workflow.status === "processing"
      ? "새 노트를 만드는 중입니다."
      : "새 노트 생성을 준비하고 있습니다."
    : oneLineSummary;
  const clipLabel = activeClip
    ? `${formatAudioClock(activeClip.startTimeSeconds)} - ${formatAudioClock(activeClip.endTimeSeconds)} 구간 재생`
    : null;

  useEffect(() => {
    debugWorkspace("render", {
      hasLatestReport: Boolean(latestReport?.id),
      hasOverview: Boolean(session?.id),
      loading,
      pipelineStage: workflow?.pipelineStage ?? null,
      reportStatus: reportStatus?.status ?? null,
      sessionId,
      transcriptCount: transcript?.items?.length ?? 0,
      workflowStatus: workflow?.status ?? null,
    });
  }, [
    latestReport?.id,
    loading,
    reportStatus?.status,
    session?.id,
    sessionId,
    transcript?.items?.length,
    workflow?.pipelineStage,
    workflow?.status,
  ]);

  useWorkspaceSessionPolling({
    hasLoadedSessionRef,
    isLive,
    loadSessionData,
    loading,
    onRefreshWorkspace,
    reportStatus,
    session,
    shouldSyncWorkspaceRef,
    workflow,
  });

  async function handleGenerateReport() {
    try {
      setProcessingAction(true);
      setActionError(null);
      const job = await enqueueReportGenerationJob({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setReportStatus((current) => ({
        ...(current ?? {}),
        session_id: sessionId,
        status: "processing",
        pipeline_stage: "report_generation",
        latest_job_status: job.status,
        latest_job_error_message: job.error_message ?? null,
      }));

      await loadSessionData({
        background: true,
        includeOverview: false,
        includeTranscript: false,
        includeReportDetail: false,
      });
      await onRefreshWorkspace({ background: true, syncSession: false });
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "리포트 생성 요청에 실패했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }

  async function handleReprocessNote() {
    try {
      setProcessingAction(true);
      setActionError(null);
      const nextSession = await reprocessSession({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setOverview((current) => ({
        ...(current ?? {}),
        session: nextSession,
      }));
      setReportStatus((current) => ({
        ...(current ?? {}),
        session_id: sessionId,
        status: "pending",
        pipeline_stage: "post_processing",
        post_processing_status: nextSession.post_processing_status ?? "queued",
        latest_job_status: null,
        latest_job_error_message: null,
      }));
      setActionNotice("재생성을 시작했습니다. 새 초안이 준비되는 대로 아래에 표시됩니다.");
      setLatestReport(null);
      setReportDetail(null);
      await loadSessionData({
        background: true,
        includeOverview: false,
        includeTranscript: false,
        includeReportDetail: false,
      });
      await onRefreshWorkspace({ background: true, syncSession: false });
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "노트 생성을 요청하지 못했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }

  async function handlePrimaryAction() {
    if (emptyState.actionKind === "reprocess") {
      await handleReprocessNote();
      return;
    }
    if (emptyState.actionKind === "report") {
      await handleGenerateReport();
    }
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
      className={`caps-meeting-workspace animate-fade-in ${canDownloadRecording ? "has-audio-player" : ""}`}
    >
      <audio ref={audioRef} hidden preload="metadata" />

      <section className="caps-transcript-panel">
        <div className="caps-transcript-header">
          <div>
            <div className="caps-transcript-meta">
              <span className="caps-transcript-mode">{formatModeLabel(session.mode)}</span>
              <span>
                {formatMeetingDate(session.started_at)} · {isLive ? "실시간 회의" : "회의 노트"}
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
            {canDownloadRecording && downloadHref ? (
              <a className="caps-transcript-button" href={downloadHref}>
                <FileDown size={14} />
                원본 다운로드
              </a>
            ) : null}
          </div>
        </div>

        {actionError ? <div className="caps-inline-alert">{actionError}</div> : null}

        <div className="caps-transcript-scroll">
          {showTranscriptProgressHero ? (
            <TranscriptProgressHero
              workflow={workflow}
              draftCount={visibleTranscriptRows.length}
              actionNotice={actionNotice}
            />
          ) : null}
          {visibleTranscriptRows.length > 0 ? (
            visibleTranscriptRows.map((row) => (
              <button
                key={row.id}
                className={`caps-transcript-row ${row.isDraft ? "draft" : ""} ${canPlayTranscriptRow(row) ? "clickable" : ""} ${activeClip?.id === row.id ? "active" : ""}`}
                onClick={() => handlePlayTranscriptClip(row)}
                type="button"
              >
                <div className="caps-transcript-speaker">
                  <div className="caps-transcript-name">{row.speaker}</div>
                  <div className="caps-transcript-time">{row.time}</div>
                </div>

                <div className="caps-transcript-content">
                  <TranscriptBadge badge={row.badge} />
                  {row.isDraft ? (
                    <div className="caps-transcript-tag context">
                      <span>초안</span>
                    </div>
                  ) : null}
                  <p>{row.text}</p>
                </div>
              </button>
            ))
          ) : showTranscriptProgressHero ? null : (
            <TranscriptEmptyState
              canDownloadRecording={canDownloadRecording}
              downloadHref={downloadHref}
              emptyState={emptyState}
              onPrimaryAction={handlePrimaryAction}
              processingAction={processingAction}
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

          {!hidePreviousNote ? (
            <div className="caps-summary-section">
              <p className="caps-summary-label">주요 결정 사항</p>
              <ul className="caps-summary-bullets">
                {(overview?.decisions ?? []).slice(0, 3).map((item) => (
                  <li key={item.id}>{item.title}</li>
                ))}
                {(overview?.decisions ?? []).length === 0 ? (
                  <li>아직 정리된 결정이 없습니다.</li>
                ) : null}
              </ul>
            </div>
          ) : null}

          {!hidePreviousNote ? (
            <div className="caps-summary-section">
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
            </div>
          ) : null}

          {!hidePreviousNote ? (
            <div className="caps-summary-section">
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
            </div>
          ) : null}
        </div>

        {!hidePreviousNote ? (
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
        ) : null}
      </aside>

      {canDownloadRecording ? (
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
              <span>
                {clipLabel
                  ? clipLabel
                  : playingAudio
                  ? "재생 중"
                  : loadingAudio
                    ? "불러오는 중"
                    : "재생 준비"}
              </span>
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

export default memo(WorkspaceCanvas);
