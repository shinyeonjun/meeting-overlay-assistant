import React from "react";
import { FileDown, Loader, Sparkles } from "lucide-react";

import { BADGE_COPY } from "./workspace-canvas-model.js";

/** 워크스페이스 회의 화면의 표시 전용 하위 컴포넌트(상태를 갖지 않는다). */

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

export function TranscriptProgressHero({ workflow, draftCount, actionNotice }) {
  const isProcessing = workflow.status === "processing";
  const title = actionNotice
    ? "새 노트를 다시 만들고 있습니다"
    : isProcessing
      ? "회의를 정리하고 있습니다"
      : "새 노트를 만들 준비를 하고 있습니다";
  const description =
    actionNotice
      ? actionNotice
      : draftCount > 0
        ? `초안 ${draftCount}개가 쌓였습니다. 아래에서 바로 확인할 수 있습니다.`
        : "발화가 정리되는 대로 아래에 초안 노트가 채워집니다.";

  return (
    <div className="caps-transcript-empty caps-transcript-progress">
      <div className="caps-transcript-empty-card">
        <div className="caps-transcript-empty-head">
          <span className="caps-transcript-empty-pill processing">
            <Loader size={13} className="spinner" />
            정리 중
          </span>
          <h3>{title}</h3>
          <p>{description}</p>
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
