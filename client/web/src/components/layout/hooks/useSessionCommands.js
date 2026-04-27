import { useCallback } from "react";

import { WORKSPACE_MODES } from "../../../app/workspace-modes.js";
import {
  deleteSession,
  renameSession,
  reprocessSession,
} from "../../../services/session-api.js";

export default function useSessionCommands({
  detailView,
  onRefreshWorkspace,
  selectedSessionId,
  setActiveMode,
  setDetailView,
  setSelectedSessionId,
  setWorkspaceData,
}) {
  const openSession = useCallback((sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveMode(WORKSPACE_MODES.meetings);
  }, [setActiveMode, setSelectedSessionId]);

  const renameSelectedSession = useCallback(async (session) => {
    const nextTitle = window.prompt("새 회의 이름을 입력하세요.", session.title ?? "");
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
      window.alert(
        nextError instanceof Error ? nextError.message : "회의 이름을 바꾸지 못했습니다.",
      );
    }
  }, [onRefreshWorkspace]);

  const deleteSelectedSession = useCallback(async (session) => {
    const confirmed = window.confirm(
      `"${session.title || "제목 없는 회의"}" 회의를 삭제할까요?`,
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
      window.alert(
        nextError instanceof Error ? nextError.message : "회의를 삭제하지 못했습니다.",
      );
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
      setActiveMode(WORKSPACE_MODES.meetings);
      setWorkspaceData((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          sessions: (current.sessions ?? []).map((item) =>
            item.id === session.id ? { ...item, ...refreshedSession } : item,
          ),
        };
      });
      await onRefreshWorkspace({ background: true });
    } catch (nextError) {
      window.alert(
        nextError instanceof Error ? nextError.message : "노트 생성을 요청하지 못했습니다.",
      );
    }
  }, [
    onRefreshWorkspace,
    setActiveMode,
    setSelectedSessionId,
    setWorkspaceData,
  ]);

  return {
    deleteSelectedSession,
    openSession,
    renameSelectedSession,
    reprocessSelectedSession,
  };
}
