"""리포트 영역의 transcript correction store 서비스를 제공한다."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field

from server.app.infrastructure.artifacts import LocalArtifactStore


@dataclass(frozen=True)
class TranscriptCorrectionItem:
    """단일 발화 보정 결과."""

    utterance_id: str
    raw_text: str
    corrected_text: str
    changed: bool
    risk_flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TranscriptCorrectionDocument:
    """세션 단위 transcript 보정 결과."""

    session_id: str
    source_version: int
    model: str
    items: list[TranscriptCorrectionItem] = field(default_factory=list)


class TranscriptCorrectionStore:
    """노트 transcript 보정 artifact를 저장/조회한다."""

    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifact_store = artifact_store

    def save(self, document: TranscriptCorrectionDocument) -> None:
        """보정 문서를 JSON artifact로 저장한다."""

        target_path = self._resolve_path(document.session_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": document.session_id,
            "source_version": document.source_version,
            "model": document.model,
            "items": [asdict(item) for item in document.items],
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
    ) -> TranscriptCorrectionDocument | None:
        """저장된 보정 문서를 읽는다."""

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

        raw_items = payload.get("items") or []
        items = [
            TranscriptCorrectionItem(
                utterance_id=str(item.get("utterance_id") or ""),
                raw_text=str(item.get("raw_text") or ""),
                corrected_text=str(item.get("corrected_text") or ""),
                changed=bool(item.get("changed", False)),
                risk_flags=[
                    str(flag).strip()
                    for flag in (item.get("risk_flags") or [])
                    if str(flag).strip()
                ],
            )
            for item in raw_items
            if str(item.get("utterance_id") or "").strip()
        ]
        return TranscriptCorrectionDocument(
            session_id=str(payload.get("session_id") or session_id),
            source_version=source_version,
            model=str(payload.get("model") or ""),
            items=items,
        )

    def load_map(
        self,
        *,
        session_id: str,
        expected_source_version: int | None = None,
    ) -> dict[str, TranscriptCorrectionItem]:
        """발화 ID 기준 보정 맵을 읽는다."""

        document = self.load(
            session_id=session_id,
            expected_source_version=expected_source_version,
        )
        if document is None:
            return {}
        return {
            item.utterance_id: item
            for item in document.items
            if item.changed and item.corrected_text.strip()
        }

    def delete(self, session_id: str) -> None:
        """세션 보정 artifact를 삭제한다."""

        target_dir = self._artifact_store.resolve_path(
            f"transcript_corrections/{session_id}"
        )
        shutil.rmtree(target_dir, ignore_errors=True)

    def _resolve_path(self, session_id: str):
        artifact_id = f"transcript_corrections/{session_id}/canonical.json"
        return self._artifact_store.resolve_path(artifact_id)
