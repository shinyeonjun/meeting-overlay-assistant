"""화자 표시 이름 규칙 테스트."""

import pytest

from server.app.domain.models.speaker_names import (
    build_speaker_name_map,
    build_unassigned_speaker_labels,
    normalize_speaker_name,
    summarize_speakers,
)
from server.app.domain.models.utterance import Utterance


def _utterance(seq_num, start_ms, speaker_label):
    return Utterance.create(
        session_id="session-1",
        seq_num=seq_num,
        start_ms=start_ms,
        end_ms=start_ms + 500,
        text="발화",
        confidence=0.9,
        speaker_label=speaker_label,
    )


def test_처음_말한_시각_순서로_화자_번호를_붙인다():
    utterances = [
        _utterance(1, 5000, "SPEAKER_00"),
        _utterance(2, 1000, "SPEAKER_02"),
        _utterance(3, 9000, "SPEAKER_00"),
    ]

    assert build_speaker_name_map(utterances, {}) == {
        "SPEAKER_02": "화자 1",
        "SPEAKER_00": "화자 2",
    }


def test_분리된_화자와_미분류가_섞이면_미분류로_부른다():
    utterances = [
        _utterance(1, 0, "SPEAKER_00"),
        _utterance(2, 1000, None),
        _utterance(3, 2000, "speaker-unknown"),
    ]

    summaries = summarize_speakers(utterances, {})

    assert [(item.speaker_label, item.display_name, item.utterance_count) for item in summaries] == [
        ("SPEAKER_00", "화자 1", 1),
        ("speaker-unknown", "미분류", 2),
    ]


def test_사용자가_붙인_이름이_기본_이름보다_먼저다():
    utterances = [_utterance(1, 0, "SPEAKER_00"), _utterance(2, 1000, "SPEAKER_01")]

    summaries = summarize_speakers(utterances, {"SPEAKER_01": "이서연"})

    assert [(item.display_name, item.default_name, item.custom_name) for item in summaries] == [
        ("화자 1", "화자 1", None),
        ("이서연", "화자 2", "이서연"),
    ]


def test_이름은_공백을_정리하고_빈_이름은_되돌림으로_본다():
    assert normalize_speaker_name("  김   민수 ") == "김 민수"
    assert normalize_speaker_name("   ") is None
    assert normalize_speaker_name(None) is None
    with pytest.raises(ValueError):
        normalize_speaker_name("가" * 41)


def test_설정으로_바꾼_미분류_라벨도_미분류로_본다():
    utterances = [_utterance(1, 0, "SPEAKER_00"), _utterance(2, 1000, "unknown-voice")]

    names = build_speaker_name_map(
        utterances,
        {},
        unassigned_labels=build_unassigned_speaker_labels("unknown-voice", None, "  "),
    )

    assert names == {"SPEAKER_00": "화자 1", "unknown-voice": "미분류"}
