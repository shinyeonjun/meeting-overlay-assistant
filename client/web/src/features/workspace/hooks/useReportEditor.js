import { useState } from "react";

import {
  fetchReportDocument,
  saveReportDocument,
} from "../../../services/report-api.js";
import { cloneEditableDocument } from "../components/ReportEditorPanel.helpers.js";

export default function useReportEditor({ onReportEdited, reportId, sessionId }) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [editDraft, setEditDraft] = useState(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState(null);

  async function openEditor() {
    if (!sessionId || !reportId) {
      return;
    }

    setEditorOpen(true);
    setEditError(null);
    setEditLoading(true);
    try {
      const payload = await fetchReportDocument({
        sessionId,
        reportId,
      });
      setEditDraft(cloneEditableDocument(payload.document));
    } catch (nextError) {
      setEditError(
        nextError instanceof Error
          ? nextError.message
          : "회의록 편집 데이터를 불러오지 못했습니다.",
      );
    } finally {
      setEditLoading(false);
    }
  }

  async function saveEditor() {
    if (!sessionId || !reportId || !editDraft) {
      return;
    }

    setEditError(null);
    setEditSaving(true);
    try {
      await saveReportDocument({
        sessionId,
        reportId,
        document: editDraft,
      });
      setEditorOpen(false);
      setEditDraft(null);
      await onReportEdited?.();
    } catch (nextError) {
      setEditError(
        nextError instanceof Error
          ? nextError.message
          : "회의록 편집본을 저장하지 못했습니다.",
      );
    } finally {
      setEditSaving(false);
    }
  }

  return {
    editDraft,
    editError,
    editLoading,
    editSaving,
    editorOpen,
    openEditor,
    saveEditor,
    setEditDraft,
    setEditorOpen,
  };
}
