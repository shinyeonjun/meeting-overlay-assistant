"""회의 기록의 화자 이름을 조회하고 바꾼다."""

from __future__ import annotations

from collections.abc import Iterable

from server.app.domain.models.speaker_names import (
    SpeakerSummary,
    build_speaker_name_map,
    normalize_speaker_label,
    normalize_speaker_name,
    summarize_speakers,
)
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import PostProcessingStatus
from server.app.repositories.contracts.speaker_name_repository import SpeakerNameRepository


class SpeakerNotFoundError(LookupError):
    """회의 기록에 없는 화자 라벨."""


class SpeakerNamesLockedError(RuntimeError):
    """회의 정리 중이라 화자 라벨이 바뀔 수 있어 이름을 바꿀 수 없다."""


class SpeakerNameService:
    """화자 라벨과 사용자가 붙인 이름을 묶는다.

    이름은 붙인 시점의 transcript 버전과 함께 저장한다. 회의를 다시 정리하면 버전이 올라가고
    라벨도 새로 매겨지므로, 옛 버전에서 붙인 이름은 쓰지 않는다.
    """

    def __init__(
        self,
        speaker_name_repository: SpeakerNameRepository,
        *,
        unassigned_labels: frozenset[str],
    ) -> None:
        self._repository = speaker_name_repository
        self._unassigned_labels = unassigned_labels

    def list_speakers(
        self,
        session: MeetingSession,
        utterances: Iterable[Utterance],
    ) -> list[SpeakerSummary]:
        return summarize_speakers(
            utterances,
            self._load_custom_names(session),
            unassigned_labels=self._unassigned_labels,
        )

    def build_name_map(
        self,
        session: MeetingSession,
        utterances: Iterable[Utterance],
    ) -> dict[str, str]:
        return build_speaker_name_map(
            utterances,
            self._load_custom_names(session),
            unassigned_labels=self._unassigned_labels,
        )

    def rename(
        self,
        session: MeetingSession,
        utterances: Iterable[Utterance],
        *,
        speaker_label: str,
        display_name: str | None,
    ) -> list[SpeakerSummary]:
        """이름을 붙인다. display_name이 비어 있으면 기본 이름으로 되돌린다."""

        if session.post_processing_status == PostProcessingStatus.PROCESSING:
            raise SpeakerNamesLockedError("회의 정리가 끝난 뒤에 화자 이름을 바꿀 수 있습니다.")

        items = list(utterances)
        label = normalize_speaker_label(speaker_label)
        if label not in {normalize_speaker_label(item.speaker_label) for item in items}:
            raise SpeakerNotFoundError("이 회의에 없는 화자입니다.")

        name = normalize_speaker_name(display_name)
        if name is None:
            self._repository.clear_name(session.id, label)
        else:
            self._repository.set_name(
                session.id,
                label,
                name,
                transcript_version=session.canonical_transcript_version,
            )
        return self.list_speakers(session, items)

    def _load_custom_names(self, session: MeetingSession) -> dict[str, str]:
        return self._repository.list_by_session(
            session.id,
            transcript_version=session.canonical_transcript_version,
        )
