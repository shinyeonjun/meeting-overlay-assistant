"""회의 기록에 보여 줄 화자 이름 규칙.

화자 분리는 "SPEAKER_00"처럼 의미 없는 라벨만 준다. 화면과 리포트에는 처음 말한 순서대로
"화자 1", "화자 2"를 보여 주고, 사용자가 이름을 붙이면 그 이름을 쓴다.
발화 원문의 speaker_label은 바꾸지 않는다.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from server.app.domain.models.utterance import Utterance

# 라벨이 비어 있는 발화를 부를 때 쓰는 라벨. API로 이 화자에 이름을 붙일 때도 이 값을 쓴다.
UNASSIGNED_SPEAKER_LABEL = "speaker-unknown"
# 화자 분리를 하지 않았거나 구간을 못 맞춘 발화에 붙는 라벨.
# "화자-미분류"는 UnknownSpeakerDiarizer의 기본값이다. 설정으로 바꾼 라벨은 호출하는 쪽이 더한다.
BUILT_IN_UNASSIGNED_SPEAKER_LABELS = frozenset({UNASSIGNED_SPEAKER_LABEL, "화자-미분류"})

MAX_SPEAKER_NAME_LENGTH = 40


@dataclass(frozen=True)
class SpeakerSummary:
    """한 화자 라벨의 표시 이름과 발화 수."""

    speaker_label: str
    display_name: str
    default_name: str
    custom_name: str | None
    utterance_count: int


def build_unassigned_speaker_labels(*extra_labels: str | None) -> frozenset[str]:
    """기본 미분류 라벨에 설정으로 바꾼 라벨을 더한다."""

    extras = {label.strip() for label in extra_labels if label and label.strip()}
    return BUILT_IN_UNASSIGNED_SPEAKER_LABELS | extras


def normalize_speaker_label(speaker_label: str | None) -> str:
    """빈 라벨은 미분류 라벨로 맞춘다."""

    label = (speaker_label or "").strip()
    return label or UNASSIGNED_SPEAKER_LABEL


def normalize_speaker_name(display_name: str | None) -> str | None:
    """이름 안팎 공백을 정리한다. 빈 이름은 None(기본 이름으로 되돌림)이다."""

    name = " ".join((display_name or "").split())
    if not name:
        return None
    if len(name) > MAX_SPEAKER_NAME_LENGTH:
        raise ValueError(f"화자 이름은 {MAX_SPEAKER_NAME_LENGTH}자 이하로 입력해 주세요.")
    return name


def summarize_speakers(
    utterances: Iterable[Utterance],
    custom_names: Mapping[str, str],
    *,
    unassigned_labels: frozenset[str] = BUILT_IN_UNASSIGNED_SPEAKER_LABELS,
) -> list[SpeakerSummary]:
    """처음 말한 순서대로 화자 목록을 만든다."""

    counts: dict[str, int] = {}
    for utterance in sorted(utterances, key=lambda item: (item.start_ms, item.seq_num)):
        label = normalize_speaker_label(utterance.speaker_label)
        counts[label] = counts.get(label, 0) + 1

    assigned_labels = [label for label in counts if label not in unassigned_labels]
    default_names = {label: f"화자 {index}" for index, label in enumerate(assigned_labels, start=1)}
    # 화자 분리를 안 했으면 모두 한 라벨이다. 이때는 "참석자", 섞여 있으면 "미분류"로 부른다.
    unassigned_name = "미분류" if assigned_labels else "참석자"

    summaries: list[SpeakerSummary] = []
    for label, count in counts.items():
        default_name = default_names.get(label, unassigned_name)
        custom_name = custom_names.get(label)
        summaries.append(
            SpeakerSummary(
                speaker_label=label,
                display_name=custom_name or default_name,
                default_name=default_name,
                custom_name=custom_name,
                utterance_count=count,
            )
        )
    return summaries


def build_speaker_name_map(
    utterances: Iterable[Utterance],
    custom_names: Mapping[str, str],
    *,
    unassigned_labels: frozenset[str] = BUILT_IN_UNASSIGNED_SPEAKER_LABELS,
) -> dict[str, str]:
    """{speaker_label: 표시 이름}을 만든다."""

    return {
        summary.speaker_label: summary.display_name
        for summary in summarize_speakers(
            utterances,
            custom_names,
            unassigned_labels=unassigned_labels,
        )
    }
