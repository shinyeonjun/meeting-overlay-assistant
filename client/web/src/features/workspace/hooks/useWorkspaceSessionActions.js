import { useCallback } from "react";

import { enqueueReportGenerationJob } from "../../../services/report-api.js";
import { reprocessSession } from "../../../services/session-api.js";
import {
  buildPostProcessingStatus,
  buildReportGenerationStatus,
} from "./useWorkspaceSessionData.helpers.js";

/** 워크스페이스 세션 화면의 사용자 액션 callback을 구성한다. */
export default function useWorkspaceSessionActions({
  latestReport,
  loadSessionData,
  onRefreshWorkspace,
  reportPipelineStage,
  sessionId,
  setActionError,
  setActionNotice,
  setLatestReport,
  setOverview,
  setProcessingAction,
  setReportDetail,
  setReportStatus,
  shouldSyncWorkspaceRef,
}) {
  const handleGenerateReport = useCallback(async () => {
    try {
      setProcessingAction(true);
      setActionError(null);
      const job = await enqueueReportGenerationJob({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setReportStatus((current) => buildReportGenerationStatus({ current, job, sessionId }));
      setActionNotice(
        latestReport
          ? "새 회의록 버전을 만드는 중입니다. 완료 전까지는 현재 PDF를 그대로 보여줍니다."
          : "회의록을 만드는 중입니다. 완료되면 PDF가 표시됩니다.",
      );

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
          : "회의록 생성 요청이 실패했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }, [
    latestReport,
    loadSessionData,
    onRefreshWorkspace,
    sessionId,
    setActionError,
    setActionNotice,
    setProcessingAction,
    setReportStatus,
    shouldSyncWorkspaceRef,
  ]);

  const handleReprocessNote = useCallback(async () => {
    try {
      setProcessingAction(true);
      setActionError(null);
      const nextSession = await reprocessSession({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setOverview((current) => ({
        ...(current ?? {}),
        session: nextSession,
      }));
      setReportStatus((current) =>
        buildPostProcessingStatus({ current, nextSession, sessionId }),
      );
      setActionNotice("재생성을 시작했습니다. 새 초안이 준비되는 대로 아래에 표시합니다.");
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
          : "노트 생성 요청을 처리하지 못했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }, [
    loadSessionData,
    onRefreshWorkspace,
    sessionId,
    setActionError,
    setActionNotice,
    setLatestReport,
    setOverview,
    setProcessingAction,
    setReportDetail,
    setReportStatus,
    shouldSyncWorkspaceRef,
  ]);

  const handlePrimaryAction = useCallback(async () => {
    if (reportPipelineStage === "report_generation") {
      await handleGenerateReport();
      return;
    }
    await handleReprocessNote();
  }, [handleGenerateReport, handleReprocessNote, reportPipelineStage]);

  const handleReportEdited = useCallback(async () => {
    setActionError(null);
    setActionNotice("편집한 회의록 PDF를 다시 만들었습니다.");
    await loadSessionData({
      background: true,
      includeOverview: true,
      includeTranscript: false,
      includeReportDetail: true,
    });
    await onRefreshWorkspace({ background: true, syncSession: false });
  }, [loadSessionData, onRefreshWorkspace, setActionError, setActionNotice]);

  return {
    handleGenerateReport,
    handlePrimaryAction,
    handleReportEdited,
    handleReprocessNote,
  };
}
