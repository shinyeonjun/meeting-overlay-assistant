/** transcript 본문과 회의록 생성/산출물 액션을 함께 렌더링한다. */
import React, { useEffect, useMemo, useRef } from "react";
import { Loader } from "lucide-react";

import useDraftTranscriptTyping from "../hooks/useDraftTranscriptTyping.js";
import WorkspaceTranscriptStatus from "./WorkspaceTranscriptStatus.jsx";
import {
  buildEmptyState,
  buildTranscriptRows,
  canPlayTranscriptRow,
} from "./WorkspaceTranscriptPanel.helpers.js";
import {
  ReportWorkflowBanner,
  TranscriptHeader,
  TranscriptEmptyState,
  TranscriptInitialLoadingState,
  TranscriptRow,
} from "./WorkspaceTranscriptPanel.parts.jsx";

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
      <TranscriptHeader
        canDownloadRecording={canDownloadRecording}
        canRegenerateReport={canRegenerateReport}
        downloadHref={downloadHref}
        onGenerateReport={onGenerateReport}
        processingAction={processingAction}
        reportArtifactUrls={reportArtifactUrls}
        session={session}
        workflow={workflow}
      />

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
            <TranscriptRow
              active={activeClipId === row.id}
              canPlay={canPlayTranscriptRow(row)}
              key={row.id}
              onPlay={onPlayTranscriptClip}
              row={row}
            />
          ))
        ) : showTranscriptProgressHero ? null : showInitialTranscriptLoading ? (
          <TranscriptInitialLoadingState />
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
