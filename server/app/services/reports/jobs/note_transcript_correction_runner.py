"""노트 transcript 보정 문서 생성과 저장을 담당한다."""

from __future__ import annotations

from collections.abc import Callable

from server.app.services.reports.refinement import (
    NoteTranscriptCorrector,
    TranscriptCorrectionDocument,
    TranscriptCorrectionStore,
)


class NoteTranscriptCorrectionRunner:
    """corrector lazy-load와 보정 결과 저장을 캡슐화한다."""

    def __init__(
        self,
        *,
        note_transcript_corrector: (
            NoteTranscriptCorrector | Callable[[], NoteTranscriptCorrector | None] | None
        ) = None,
        transcript_correction_store: TranscriptCorrectionStore | None = None,
    ) -> None:
        self._note_transcript_corrector = (
            None if callable(note_transcript_corrector) else note_transcript_corrector
        )
        self._note_transcript_corrector_factory = (
            note_transcript_corrector if callable(note_transcript_corrector) else None
        )
        self._transcript_correction_store = transcript_correction_store

    @property
    def enabled(self) -> bool:
        """실제 보정 작업이 설정되어 있는지 반환한다."""

        return (
            self._note_transcript_corrector is not None
            or self._note_transcript_corrector_factory is not None
        )

    def build_and_save_document(
        self,
        *,
        session_id: str,
        source_version: int,
        utterances,
    ) -> TranscriptCorrectionDocument:
        """보정 문서를 생성하고 저장소가 있으면 저장한다."""

        document = self.build_document(
            session_id=session_id,
            source_version=source_version,
            utterances=utterances,
        )
        if self._transcript_correction_store is not None:
            self._transcript_correction_store.save(document)
        return document

    def build_document(
        self,
        *,
        session_id: str,
        source_version: int,
        utterances,
    ) -> TranscriptCorrectionDocument:
        """corrector 설정에 따라 보정 문서를 생성한다."""

        corrector = self._get_note_transcript_corrector()
        if corrector is None:
            return TranscriptCorrectionDocument(
                session_id=session_id,
                source_version=source_version,
                model="disabled",
                items=[],
            )
        return corrector.correct(
            session_id=session_id,
            source_version=source_version,
            utterances=utterances,
        )

    def _get_note_transcript_corrector(self) -> NoteTranscriptCorrector | None:
        if (
            self._note_transcript_corrector is None
            and self._note_transcript_corrector_factory is not None
        ):
            self._note_transcript_corrector = self._note_transcript_corrector_factory()
        return self._note_transcript_corrector
