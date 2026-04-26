"""회의록 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


@dataclass(frozen=True)
class Report:
    """세션 결과 문서 엔티티."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_path: str
    generated_at: str
    insight_source: str
    generated_by_user_id: str | None = None
    file_artifact_id: str | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        report_type: str,
        version: int,
        file_path: str,
        *,
        file_artifact_id: str | None = None,
        insight_source: str,
        generated_by_user_id: str | None = None,
    ) -> "Report":
        """새 회의록을 생성한다."""

        return cls(
            id=generate_uuid_str(),
            session_id=session_id,
            report_type=report_type,
            version=version,
            file_path=file_path,
            generated_at=datetime.now(timezone.utc).isoformat(),
            insight_source=insight_source,
            generated_by_user_id=generated_by_user_id,
            file_artifact_id=file_artifact_id,
        )
