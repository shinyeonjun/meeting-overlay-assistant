import React, { useMemo } from "react";
import {
  FileDown,
  Loader,
  Pencil,
  RefreshCcw,
} from "lucide-react";

import {
  formatDateTime,
  getMeetingStatusLabel,
  getMeetingStatusTone,
} from "../../../app/workspace-model.js";
import useReportEditor from "../hooks/useReportEditor.js";
import {
  buildAgenda,
  buildRecapModel,
  getSessionSourceLabel,
  getTranscriptMeta,
} from "./WorkspaceRecapView.helpers.js";
import {
  MinutesFallbackDocument,
  ToolbarLink,
} from "./WorkspaceRecapView.parts.jsx";
import ReportEditorPanel from "./ReportEditorPanel.jsx";

export default function WorkspaceRecapView({
  actionError,
  actionNotice,
  onGenerateReport,
  onReportEdited,
  overview,
  processingAction,
  reportArtifactUrls,
  reportDetail,
  reportStatus,
  reportWorkflow,
  session,
  visibleLatestReport,
}) {
  const recap = useMemo(
    () => buildRecapModel(overview, visibleLatestReport),
    [overview, visibleLatestReport],
  );
  const meta = useMemo(() => getTranscriptMeta(reportDetail), [reportDetail]);
  const transcriptSegments = useMemo(
    () => (reportDetail?.speaker_transcript ?? []).slice(0, 10),
    [reportDetail],
  );
  const statusTone = getMeetingStatusTone(reportStatus, session);
  const isReportProcessing = processingAction || reportWorkflow?.status === "processing";
  const hasReport = Boolean(visibleLatestReport?.id);
  const agenda = buildAgenda(recap, session);
  const sourceLabel = getSessionSourceLabel(session);
  const sessionTitle = session?.title || "제목 없는 회의";
  const startedAtLabel = formatDateTime(session?.started_at);
  const pdfPreviewHref = reportArtifactUrls?.previewHref;
  const {
    editDraft,
    editError,
    editLoading,
    editSaving,
    editorOpen,
    openEditor,
    saveEditor,
    setEditDraft,
    setEditorOpen,
  } = useReportEditor({
    onReportEdited,
    reportId: visibleLatestReport?.id,
    sessionId: session?.id,
  });

  return (
    <div className="caps-minutes-workspace animate-fade-in">
      <div className="caps-minutes-toolbar">
        <div className="caps-minutes-toolbar-title">
          <span className={`caps-status-badge ${statusTone}`}>
            {getMeetingStatusLabel(reportStatus, session)}
          </span>
          <div>
            <strong>{sessionTitle}</strong>
            <p>회의록 문서를 바로 확인하고 PDF로 내려받습니다.</p>
          </div>
        </div>

        <div className="caps-minutes-toolbar-actions">
          <button
            className="caps-minutes-toolbar-button"
            disabled={isReportProcessing}
            onClick={onGenerateReport}
            type="button"
          >
            {isReportProcessing ? <Loader className="spinner" size={16} /> : <RefreshCcw size={16} />}
            {isReportProcessing ? "생성 중" : hasReport ? "회의록 다시 만들기" : "회의록 만들기"}
          </button>
          <ToolbarLink href={reportArtifactUrls?.downloadHref} primary>
            <FileDown size={16} />
            PDF 다운로드
          </ToolbarLink>
          <button
            className="caps-minutes-toolbar-button"
            disabled={!visibleLatestReport?.id || isReportProcessing || editLoading || editSaving}
            onClick={openEditor}
            type="button"
          >
            {editLoading ? <Loader className="spinner" size={16} /> : <Pencil size={16} />}
            편집
          </button>
        </div>
      </div>

      {actionError ? <div className="caps-inline-alert caps-minutes-feedback">{actionError}</div> : null}
      {actionNotice ? (
        <div className="caps-inline-notice caps-minutes-feedback">{actionNotice}</div>
      ) : null}

      <div className="caps-minutes-page-shell">
        {pdfPreviewHref ? (
          <>
            <iframe
              className="caps-minutes-pdf-frame"
              loading="lazy"
              src={pdfPreviewHref}
              title="회의록 PDF 문서"
            />
            {isReportProcessing ? (
              <div className="caps-minutes-generation-badge">
                <Loader className="spinner" size={14} />
                새 버전 생성 중
              </div>
            ) : null}
          </>
        ) : isReportProcessing ? (
          <div className="caps-minutes-processing-state">
            <Loader className="spinner" size={24} />
            <strong>회의록을 만드는 중입니다.</strong>
            <p>생성이 끝나면 PDF 문서가 이 화면에 표시됩니다.</p>
          </div>
        ) : (
          <MinutesFallbackDocument
            agenda={agenda}
            meta={meta}
            recap={recap}
            sessionTitle={sessionTitle}
            sourceLabel={sourceLabel}
            startedAtLabel={startedAtLabel}
            transcriptSegments={transcriptSegments}
          />
        )}
      </div>

      {editorOpen ? (
        <>
          <button
            aria-label="회의록 편집 닫기"
            className="caps-minutes-editor-backdrop"
            onClick={() => setEditorOpen(false)}
            type="button"
          />
          <ReportEditorPanel
            document={editDraft}
            error={editError}
            loading={editLoading}
            onChange={setEditDraft}
            onClose={() => setEditorOpen(false)}
            onSave={saveEditor}
            saving={editSaving}
          />
        </>
      ) : null}
    </div>
  );
}
