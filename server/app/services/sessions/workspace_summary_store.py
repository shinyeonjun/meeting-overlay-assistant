"""워크스페이스 요약 artifact 저장/조회."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict
from datetime import UTC, datetime

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryActionItem,
    WorkspaceSummaryDocument,
    WorkspaceSummaryEvidence,
    WorkspaceSummaryStatus,
    WorkspaceSummaryTopic,
)


logger = logging.getLogger(__name__)


class WorkspaceSummaryStore:
    """세션별 우측 패널 요약 문서를 JSON artifact로 관리한다."""

    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifact_store = artifact_store

    def save(self, document: WorkspaceSummaryDocument) -> None:
        """요약 문서를 artifact로 저장한다."""

        target_path = self._resolve_path(document.session_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": document.session_id,
            "source_version": document.source_version,
            "model": document.model,
            "headline": document.headline,
            "summary": document.summary,
            "topics": [asdict(item) for item in document.topics],
            "decisions": document.decisions,
            "next_actions": [asdict(item) for item in document.next_actions],
            "open_questions": document.open_questions,
            "changed_since_last_meeting": document.changed_since_last_meeting,
            "evidence": [asdict(item) for item in document.evidence],
        }
        target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            self.save_status(
                session_id=document.session_id,
                source_version=document.source_version,
                status="completed",
                model=document.model,
            )
        except Exception:
            logger.exception(
                "노트 인사이트 상태 저장 실패: session_id=%s source_version=%s",
                document.session_id,
                document.source_version,
            )

    def save_status(
        self,
        *,
        session_id: str,
        source_version: int,
        status: str,
        model: str = "",
        error_message: str | None = None,
    ) -> None:
        """노트 인사이트 분석 상태를 artifact로 저장한다."""

        target_path = self._resolve_status_path(session_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "source_version": source_version,
            "status": status,
            "model": model,
            "error_message": error_message,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(
        self,
        *,
        session_id: str,
        expected_source_version: int | None = None,
    ) -> WorkspaceSummaryDocument | None:
        """저장된 요약 문서를 읽는다."""

        target_path = self._resolve_path(session_id)
        if not target_path.exists():
            return None

        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None

        source_version = int(payload.get("source_version") or 0)
        if expected_source_version is not None and source_version != expected_source_version:
            return None

        next_actions = [
            WorkspaceSummaryActionItem(
                title=str(item.get("title") or "").strip(),
                owner=(
                    str(item.get("owner")).strip()
                    if item.get("owner") not in {None, ""}
                    else None
                ),
                due_date=(
                    str(item.get("due_date")).strip()
                    if item.get("due_date") not in {None, ""}
                    else None
                ),
            )
            for item in (payload.get("next_actions") or [])
            if str(item.get("title") or "").strip()
        ]
        evidence = [
            WorkspaceSummaryEvidence(
                label=str(item.get("label") or "").strip(),
                start_ms=int(item.get("start_ms") or 0),
                end_ms=int(item.get("end_ms") or 0),
            )
            for item in (payload.get("evidence") or [])
            if str(item.get("label") or "").strip()
        ]
        topics = [
            WorkspaceSummaryTopic(
                title=str(item.get("title") or "").strip(),
                summary=str(item.get("summary") or "").strip(),
                start_ms=int(item.get("start_ms") or 0),
                end_ms=int(item.get("end_ms") or 0),
            )
            for item in (payload.get("topics") or [])
            if str(item.get("title") or "").strip()
        ]
        return WorkspaceSummaryDocument(
            session_id=str(payload.get("session_id") or session_id),
            source_version=source_version,
            model=str(payload.get("model") or ""),
            headline=str(payload.get("headline") or "").strip(),
            summary=[
                str(item).strip()
                for item in (payload.get("summary") or [])
                if str(item).strip()
            ],
            decisions=[
                str(item).strip()
                for item in (payload.get("decisions") or [])
                if str(item).strip()
            ],
            topics=topics,
            next_actions=next_actions,
            open_questions=[
                str(item).strip()
                for item in (payload.get("open_questions") or [])
                if str(item).strip()
            ],
            changed_since_last_meeting=[
                str(item).strip()
                for item in (payload.get("changed_since_last_meeting") or [])
                if str(item).strip()
            ],
            evidence=evidence,
        )

    def load_status(
        self,
        *,
        session_id: str,
        expected_source_version: int | None = None,
    ) -> WorkspaceSummaryStatus | None:
        """저장된 노트 인사이트 분석 상태를 읽는다."""

        target_path = self._resolve_status_path(session_id)
        if not target_path.exists():
            return None

        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None

        source_version = int(payload.get("source_version") or 0)
        if expected_source_version is not None and source_version != expected_source_version:
            return None

        error_message = payload.get("error_message")
        if error_message is not None:
            error_message = str(error_message).strip() or None

        return WorkspaceSummaryStatus(
            session_id=str(payload.get("session_id") or session_id),
            source_version=source_version,
            status=str(payload.get("status") or "").strip() or "unknown",
            model=str(payload.get("model") or "").strip(),
            error_message=error_message,
            updated_at=(
                str(payload.get("updated_at")).strip()
                if payload.get("updated_at") not in {None, ""}
                else None
            ),
        )

    def delete(self, session_id: str) -> None:
        """세션 요약 artifact를 제거한다."""

        target_dir = self._artifact_store.resolve_path(
            f"workspace_summaries/{session_id}"
        )
        shutil.rmtree(target_dir, ignore_errors=True)

    def _resolve_path(self, session_id: str):
        artifact_id = f"workspace_summaries/{session_id}/canonical.json"
        return self._artifact_store.resolve_path(artifact_id)

    def _resolve_status_path(self, session_id: str):
        artifact_id = f"workspace_summaries/{session_id}/status.json"
        return self._artifact_store.resolve_path(artifact_id)
