import { useCallback } from "react";

import { WORKSPACE_MODES } from "../../../app/workspace-modes.js";
import {
  deleteSession,
  renameSession,
  reprocessSession,
} from "../../../services/session-api.js";
import { enqueueReportGenerationJob } from "../../../services/report-api.js";

function showCommandError(error, fallbackMessage) {
  window.alert(error instanceof Error ? error.message : fallbackMessage);
}

function updateSessionInWorkspaceData(workspaceData, sessionId, nextSession) {
  if (!workspaceData) {
    return workspaceData;
  }
  return {
    ...workspaceData,
    sessions: (workspaceData.sessions ?? []).map((item) =>
      item.id === sessionId ? { ...item, ...nextSession } : item,
    ),
  };
}

function buildPendingReportStatus(sessionId, job, currentReportStatuses) {
  return {
    ...(currentReportStatuses[sessionId] ?? {}),
    session_id: sessionId,
    status: "processing",
    pipeline_stage: "report_generation",
    latest_job_status: job.status,
    latest_job_error_message: job.error_message ?? null,
  };
}

export default function useSessionCommands({
  detailView,
  onRefreshWorkspace,
  selectedSessionId,
  setActiveMode,
  setDetailView,
  setSelectedSessionId,
  setWorkspaceData,
}) {
  const openSession = useCallback((sessionId, targetMode = WORKSPACE_MODES.notes) => {
    if (!sessionId) {
      return;
    }
    setSelectedSessionId(sessionId);
    setActiveMode(targetMode);
  }, [setActiveMode, setSelectedSessionId]);

  const renameSelectedSession = useCallback(async (session) => {
    const nextTitle = window.prompt("회의 이름을 입력하세요.", session.title ?? "");
    if (nextTitle === null) {
      return;
    }

    const normalizedTitle = nextTitle.trim();
    if (!normalizedTitle || normalizedTitle === session.title) {
      return;
    }

    try {
      await renameSession({ sessionId: session.id, title: normalizedTitle });
      await onRefreshWorkspace();
    } catch (nextError) {
      showCommandError(nextError, "회의 이름을 바꾸지 못했습니다.");
    }
  }, [onRefreshWorkspace]);

  const deleteSelectedSession = useCallback(async (session) => {
    const confirmed = window.confirm(
      `"${session.title || "제목 없는 회의"}" 회의를 삭제할까요?\n\n녹음, 전사, 노트, 회의록 산출물이 함께 삭제될 수 있습니다.`,
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteSession({ sessionId: session.id });
      if (selectedSessionId === session.id) {
        setSelectedSessionId(undefined);
      }
      if (detailView?.sessionId === session.id) {
        setDetailView(null);
      }
      await onRefreshWorkspace();
    } catch (nextError) {
      showCommandError(nextError, "회의를 삭제하지 못했습니다.");
    }
  }, [
    detailView?.sessionId,
    onRefreshWorkspace,
    selectedSessionId,
    setDetailView,
    setSelectedSessionId,
  ]);

  const reprocessSelectedSession = useCallback(async (session) => {
    try {
      const refreshedSession = await reprocessSession({ sessionId: session.id });
      setSelectedSessionId(session.id);
      setActiveMode(WORKSPACE_MODES.notes);
      setWorkspaceData((current) =>
        updateSessionInWorkspaceData(current, session.id, refreshedSession),
      );
      await onRefreshWorkspace({ background: true });
    } catch (nextError) {
      showCommandError(nextError, "노트 재정리를 요청하지 못했습니다.");
    }
  }, [
    onRefreshWorkspace,
    setActiveMode,
    setSelectedSessionId,
    setWorkspaceData,
  ]);

  const generateReportForSession = useCallback(async (session) => {
    try {
      const job = await enqueueReportGenerationJob({ sessionId: session.id });
      setSelectedSessionId(session.id);
      setActiveMode(WORKSPACE_MODES.recaps);
      setWorkspaceData((current) => {
        if (!current) {
          return current;
        }

        const currentReportStatuses = current.reportStatuses ?? {};
        const nextReportStatus = buildPendingReportStatus(session.id, job, currentReportStatuses);

        return {
          ...current,
          report_statuses: {
            ...(current.report_statuses ?? {}),
            [session.id]: nextReportStatus,
          },
          reportStatuses: {
            ...currentReportStatuses,
            [session.id]: nextReportStatus,
          },
        };
      });
      await onRefreshWorkspace({ background: true });
    } catch (nextError) {
      showCommandError(nextError, "회의록 생성 요청이 실패했습니다.");
    }
  }, [
    onRefreshWorkspace,
    setActiveMode,
    setSelectedSessionId,
    setWorkspaceData,
  ]);

  return {
    deleteSelectedSession,
    generateReportForSession,
    openSession,
    renameSelectedSession,
    reprocessSelectedSession,
  };
}
