/** WorkspaceTranscriptPanel의 표시 전용 하위 컴포넌트. */
import { ExternalLink, FileDown, Loader, RefreshCcw } from "lucide-react";

import {
  BADGE_COPY,
  formatMeetingDate,
  formatModeLabel,
  resolveReportActionCopy,
} from "./WorkspaceTranscriptPanel.helpers.js";

export function TranscriptHeader({
  canDownloadRecording,
  canRegenerateReport,
  downloadHref,
  onGenerateReport,
  processingAction,
  reportArtifactUrls,
  session,
  workflow,
}) {
  return (
    <div className="caps-transcript-header">
      <div>
        <div className="caps-transcript-meta">
          <span className="caps-transcript-mode">{formatModeLabel(session.mode)}</span>
          <span>
            {formatMeetingDate(session.started_at)} ·{" "}
            {workflow.category === "running" ? "실시간 회의" : "회의 노트"}
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
  );
}

export function TranscriptEmptyState({
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
                    <RefreshCcw size={15} />
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

export function ReportWorkflowBanner({
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
              <RefreshCcw size={15} />
              {copy.actionLabel}
            </>
          )}
        </button>
      ) : null}
    </div>
  );
}

export function TranscriptBadge({ badge }) {
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

export function TranscriptRow({ active, canPlay, onPlay, row }) {
  return (
    <button
      className={`caps-transcript-row ${row.isDraft ? "draft" : ""} ${
        canPlay ? "clickable" : ""
      } ${active ? "active" : ""} ${row.isTyping ? "typing" : ""}`}
      onClick={() => onPlay(row)}
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
  );
}

export function TranscriptInitialLoadingState() {
  return (
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
  );
}
