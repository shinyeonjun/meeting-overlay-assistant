from __future__ import annotations

from server.app.services.live_questions.models import LiveQuestionUtterance
from server.app.services.live_questions.question_lane_filter import QuestionLaneFilter


def _utterance(utterance_id: str, text: str) -> LiveQuestionUtterance:
    return LiveQuestionUtterance(
        id=utterance_id,
        text=text,
        speaker_label=None,
        timestamp_ms=1000,
        confidence=0.9,
    )


def test_question_lane_filter_discards_plain_status_window() -> None:
    filter_ = QuestionLaneFilter(max_window_size=3)

    selected = filter_.select_window(
        [
            _utterance("u-1", "오늘은 배포 일정을 먼저 공유하겠습니다."),
            _utterance("u-2", "그다음 비용 검토로 넘어가겠습니다."),
        ]
    )

    assert selected == []


def test_question_lane_filter_sends_recent_context_for_direct_question() -> None:
    filter_ = QuestionLaneFilter(max_window_size=3)
    utterances = [
        _utterance("u-1", "오늘은 배포 일정을 먼저 공유하겠습니다."),
        _utterance("u-2", "다음 주 릴리즈 후보가 있습니다."),
        _utterance("u-3", "그럼 최종 배포 일정은 언제 확정되나요?"),
    ]

    selected = filter_.select_window(utterances)

    assert [item.id for item in selected] == ["u-1", "u-2", "u-3"]


def test_question_lane_filter_sends_request_like_question_candidate() -> None:
    filter_ = QuestionLaneFilter(max_window_size=3)

    selected = filter_.select_window(
        [
            _utterance("u-1", "관련 로그는 방금 올렸습니다."),
            _utterance("u-2", "그 부분 확인 좀 해주세요."),
        ]
    )

    assert [item.id for item in selected] == ["u-1", "u-2"]


def test_question_lane_filter_sends_candidate_when_stt_loses_question_mark() -> None:
    filter_ = QuestionLaneFilter(max_window_size=3)

    selected = filter_.select_window(
        [
            _utterance("u-1", "이번 배포 범위도 같이 알 수 있을까요"),
            _utterance("u-2", "비용 확정되는지 봐주세요"),
        ]
    )

    assert [item.id for item in selected] == ["u-1", "u-2"]
