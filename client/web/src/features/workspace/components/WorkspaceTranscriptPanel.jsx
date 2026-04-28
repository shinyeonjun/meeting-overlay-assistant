/** transcript 본문과 회의록 생성/산출물 액션을 함께 렌더링한다. */
import React, { useEffect, useMemo, useRef } from "react";
import { ExternalLink, FileDown, Loader, RefreshCcw, Sparkles } from "lucide-react";

import useDraftTranscriptTyping from "../hooks/useDraftTranscriptTyping.js";
import WorkspaceTranscriptStatus from "./WorkspaceTranscriptStatus.jsx";

const BADGE_COPY = {
  context: { label: "CONTEXT", tone: "context" },
  decision: { label: "DECISION", tone: "decision" },
  action_item: { label: "ACTION ITEM", tone: "action" },
  question: { label: "QUESTION", tone: "question" },
  risk: { label: "RISK", tone: "risk" },
};

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

function canPlayTranscriptRow(row) {
  return Number.isFinite(row?.startMs) && Number.isFinite(row?.endMs) && row.endMs > row.startMs;
}

function buildTranscriptRows({ overview, reportDetail, transcriptItems }) {
  const speakerTranscript =
    transcriptItems?.length > 0 ? transcriptItems : (reportDetail?.speaker_transcript ?? []);
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
        isDraft: item.transcript_source === "post_processing_draft",
        badge,
        startMs: Number(item.start_ms ?? 0),
        endMs: Number(item.end_ms ?? 0),
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
    startMs: null,
    endMs: null,
  }));
}

function buildEmptyState(workflow) {
  if (workflow.pipelineStage === "post_processing" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "노트 생성을 이어가지 못했습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "노트 다시 만들기",
    };
  }

  if (workflow.pipelineStage === "note_correction" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "노트 보정이 멈췄습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "노트 다시 만들기",
    };
  }

  if (workflow.pipelineStage === "report_generation" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "회의록 생성을 이어가지 못했습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "회의록 다시 생성",
    };
  }

  if (workflow.pipelineStage === "recovery") {
    return {
      tone: "failed",
      title: "회의가 비정상 종료되었습니다",
      progressLabel: "복구 필요",
      actionLabel: "노트 만들기",
    };
  }

  if (workflow.pipelineStage === "post_processing") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의 정리에 실패했습니다",
        progressLabel: "정리 실패",
        actionLabel: "노트 다시 만들기",
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

  if (workflow.pipelineStage === "note_correction") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "노트 보정에 실패했습니다",
        progressLabel: "보정 실패",
        actionLabel: "노트 다시 만들기",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "노트를 다듬고 있습니다",
        progressLabel: "보정 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "노트 보정을 준비하고 있습니다",
      progressLabel: "보정 대기",
      actionLabel: null,
    };
  }

  if (workflow.pipelineStage === "report_generation") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의록 생성에 실패했습니다",
        progressLabel: "회의록 실패",
        actionLabel: "회의록 다시 생성",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "회의록을 작성하고 있습니다",
        progressLabel: "회의록 생성 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "회의록 생성을 기다리고 있습니다",
      progressLabel: "회의록 대기",
      actionLabel: "회의록 생성",
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
    title: "아직 표시할 회의 내용이 없습니다",
    progressLabel: "준비 중",
    actionLabel: null,
  };
}

function TranscriptEmptyState({
  canDownloadRecording,
  downloadHref,
  emptyState,
  processingAction,
  onPrimaryAction,
  workflow,
}) {
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

        {emptyState.actionLabel || canDownloadRecording ? (
          <div className="caps-transcript-actions">
            {emptyState.actionLabel ? (
              <button
                className="caps-generate-button"
                disabled={processingAction || workflow.status === "processing"}
                onClick={onPrimaryAction}
                type="button"
              >
                {processingAction ? (
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

            {canDownloadRecording && downloadHref ? (
              <a className="caps-transcript-button" href={downloadHref}>
                <FileDown size={14} />
                원본 다운로드
              </a>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function resolveReportActionCopy(reportWorkflow, reportStatus) {
  const warningReason = String(reportStatus?.warning_reason ?? "").toLowerCase();
  if (warningReason === "report_generation_fallback") {
    return {
      actionLabel: "회의록 다시 만들기",
      description:
        reportStatus?.latest_job_error_message ||
        "PDF는 만들었지만 AI 회의록 분석이 완료되지 않아 기본 회의록으로 생성했습니다.",
      tone: "warning",
      title: "기본 회의록으로 생성됐습니다",
    };
  }

  if (reportWorkflow?.pipelineStage !== "report_generation") {
    return null;
  }

  const errorMessage =
    reportStatus?.latest_job_error_message ||
    reportStatus?.warning_reason ||
    "회의록 생성 작업이 완료되지 않았습니다. 다시 생성해 보세요.";

  if (reportWorkflow.status === "failed") {
    return {
      actionLabel: "회의록 다시 생성",
      description: errorMessage,
      tone: "failed",
      title: "회의록 생성에 실패했습니다",
    };
  }

  if (reportWorkflow.status === "processing") {
    return {
      actionLabel: null,
      description: "완료되면 PDF 다운로드와 HTML 미리보기가 활성화됩니다.",
      tone: "processing",
      title: "회의록을 만드는 중입니다",
    };
  }

  if (reportWorkflow.status === "pending") {
    return {
      actionLabel: "회의록 생성",
      description: "정리된 노트를 바탕으로 PDF, HTML, Markdown 회의록을 만듭니다.",
      tone: "pending",
      title: "다운로드할 회의록을 만들 수 있습니다",
    };
  }

  return null;
}

function ReportWorkflowBanner({
  processingAction,
  reportStatus,
  reportWorkflow,
  onGenerateReport,
}) {
  const copy = resolveReportActionCopy(reportWorkflow, reportStatus);
  if (!copy) {
    return null;
  }

  const isProcessing = copy.tone === "processing";
  return (
    <div className={`caps-report-workflow-banner ${copy.tone}`}>
      <div>
        <span className={`caps-transcript-empty-pill ${copy.tone}`}>
          {isProcessing ? <Loader size={13} className="spinner" /> : null}
          {reportWorkflow.label}
        </span>
        <strong>{copy.title}</strong>
        <p>{copy.description}</p>
      </div>
      {copy.actionLabel ? (
        <button
          className="caps-generate-button"
          disabled={processingAction}
          onClick={onGenerateReport}
          type="button"
        >
          {processingAction ? (
            <>
              <Loader size={15} className="spinner" />
              처리 중
            </>
          ) : (
            <>
              <Sparkles size={15} />
              {copy.actionLabel}
            </>
          )}
        </button>
      ) : null}
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

/**
 * transcript 패널은 진행 카드와 draft transcript를 함께 보여준다.
 * draft row는 새로 들어올 때마다 타이핑처럼 풀어 보여서 생성 중인 감각을 만든다.
 */
export default function WorkspaceTranscriptPanel({
  actionError,
  actionNotice,
  activeClipId,
  canDownloadRecording,
  downloadHref,
  onGenerateReport,
  onPlayTranscriptClip,
  onPrimaryAction,
  overview,
  processingAction,
  reportArtifactUrls,
  reportDetail,
  reportStatus,
  reportWorkflow,
  session,
  showTranscriptProgressHero,
  transcript,
  transcriptLoading,
  visibleLatestReport,
  workflow,
}) {
  const transcriptRows = useMemo(
    () => buildTranscriptRows({ overview, reportDetail, transcriptItems: transcript?.items }),
    [overview, reportDetail, transcript?.items],
  );
  const animatedRows = useDraftTranscriptTyping(transcriptRows);
  const emptyState = useMemo(() => buildEmptyState(workflow), [workflow]);
  const showCompactTranscriptStatus =
    showTranscriptProgressHero && animatedRows.length > 0;
  const showInitialTranscriptLoading =
    transcriptLoading && animatedRows.length === 0 && !showTranscriptProgressHero;
  const showTranscriptAppendLoading =
    transcriptLoading && animatedRows.length > 0 && !showTranscriptProgressHero;
  const showReportWorkflowBanner =
    (animatedRows.length > 0 || visibleLatestReport) &&
    ((reportWorkflow?.pipelineStage === "report_generation" &&
      ["pending", "processing", "failed"].includes(reportWorkflow.status)) ||
      reportStatus?.warning_reason === "report_generation_fallback");
  const canRegenerateReport =
    Boolean(visibleLatestReport?.id) &&
    !["pending", "processing"].includes(reportWorkflow?.status);
  const scrollRef = useRef(null);
  const latestRowId = animatedRows[animatedRows.length - 1]?.id ?? null;

  useEffect(() => {
    if (!showCompactTranscriptStatus || !scrollRef.current) {
      return;
    }
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [latestRowId, showCompactTranscriptStatus]);

  return (
    <section className="caps-transcript-panel">
      <div className="caps-transcript-header">
        <div>
          <div className="caps-transcript-meta">
            <span className="caps-transcript-mode">{formatModeLabel(session.mode)}</span>
            <span>
              {formatMeetingDate(session.started_at)} · {workflow.category === "running" ? "실시간 회의" : "회의 노트"}
            </span>
          </div>
          <h1>{session.title || "제목 없는 회의"}</h1>
        </div>

        <div className="caps-transcript-actions">
          {reportArtifactUrls?.downloadHref ? (
            <a className="caps-transcript-button primary" href={reportArtifactUrls.downloadHref}>
              <FileDown size={14} />
              {reportArtifactUrls.downloadLabel}
            </a>
          ) : null}
          {reportArtifactUrls?.htmlHref ? (
            <a
              className="caps-transcript-button"
              href={reportArtifactUrls.htmlHref}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink size={14} />
              {reportArtifactUrls.previewLabel}
            </a>
          ) : null}
          {canRegenerateReport ? (
            <button
              className="caps-transcript-button"
              disabled={processingAction}
              onClick={onGenerateReport}
              type="button"
            >
              {processingAction ? (
                <Loader size={14} className="spinner" />
              ) : (
                <RefreshCcw size={14} />
              )}
              {processingAction ? "만드는 중" : "회의록 다시 만들기"}
            </button>
          ) : null}
          {canDownloadRecording && downloadHref ? (
            <a className="caps-transcript-button muted" href={downloadHref}>
              <FileDown size={14} />
              원본 다운
            </a>
          ) : null}
        </div>
      </div>

      {showReportWorkflowBanner ? (
        <ReportWorkflowBanner
          onGenerateReport={onGenerateReport}
          processingAction={processingAction}
          reportStatus={reportStatus}
          reportWorkflow={reportWorkflow}
        />
      ) : null}
      {actionError ? <div className="caps-inline-alert">{actionError}</div> : null}
      {actionNotice ? <div className="caps-inline-notice">{actionNotice}</div> : null}
      {showTranscriptAppendLoading ? (
        <div className="caps-inline-notice">
          <Loader size={14} className="spinner" />
          노트를 이어서 불러오는 중입니다.
        </div>
      ) : null}

      <div ref={scrollRef} className="caps-transcript-scroll">
        {showTranscriptProgressHero ? (
          <WorkspaceTranscriptStatus
            actionNotice={actionNotice}
            compact={showCompactTranscriptStatus}
            draftCount={animatedRows.length}
            workflow={workflow}
          />
        ) : null}

        {animatedRows.length > 0 ? (
          animatedRows.map((row) => (
            <button
              key={row.id}
              className={`caps-transcript-row ${row.isDraft ? "draft" : ""} ${canPlayTranscriptRow(row) ? "clickable" : ""} ${activeClipId === row.id ? "active" : ""} ${row.isTyping ? "typing" : ""}`}
              onClick={() => onPlayTranscriptClip(row)}
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
                    <span>{row.isTyping ? "초안 작성 중" : "초안"}</span>
                  </div>
                ) : null}
                <p className="caps-transcript-text">
                  {row.displayText}
                  {row.isTyping ? <span className="caps-transcript-caret" aria-hidden="true" /> : null}
                </p>
              </div>
            </button>
          ))
        ) : showTranscriptProgressHero ? null : showInitialTranscriptLoading ? (
          <div className="caps-transcript-empty loading">
            <div className="caps-transcript-empty-card">
              <div className="caps-transcript-empty-head">
                <span className="caps-transcript-empty-pill processing">
                  <Loader size={13} className="spinner" />
                  노트 불러오는 중
                </span>
                <h3>회의 노트를 불러오는 중입니다</h3>
              </div>
              <div className="caps-transcript-empty-skeletons" aria-hidden="true">
                <div className="session-preview-skeleton short" />
                <div className="session-preview-skeleton long" />
                <div className="session-preview-skeleton medium" />
              </div>
            </div>
          </div>
        ) : (
          <TranscriptEmptyState
            canDownloadRecording={canDownloadRecording}
            downloadHref={downloadHref}
            emptyState={emptyState}
            onPrimaryAction={onPrimaryAction}
            processingAction={processingAction}
            workflow={workflow}
          />
        )}
      </div>
    </section>
  );
}
