"""setup_server 출력 문구를 만드는 순수 포맷 helper."""

from __future__ import annotations

def _bool_to_korean(value: object) -> str:
    return "예" if bool(value) else "아니오"


def _state_word(
    value: bool,
    *,
    true_label: str = "정상",
    false_label: str = "실패",
) -> str:
    return true_label if value else false_label


def _optional_state_word(
    value: object,
    *,
    true_label: str = "정상",
    false_label: str = "실패",
    none_label: str = "미수집",
) -> str:
    if value is None:
        return none_label
    return true_label if bool(value) else false_label


def _doctor_check(label: str, status: str, detail: str) -> dict[str, str]:
    return {"label": label, "status": status, "detail": detail}


def _doctor_status_text(status: str) -> str:
    mapping = {
        "ok": "정상",
        "warn": "경고",
        "fail": "실패",
        "pending": "미수집",
    }
    return mapping.get(status, status)


def _switch_word(value: bool) -> str:
    return "켜짐" if value else "꺼짐"


def _count_word(value: object, *, suffix: str = "건", zero_label: str | None = None) -> str:
    numeric = int(value or 0)
    if numeric == 0 and zero_label is not None:
        return zero_label
    return f"{numeric}{suffix}"


def _format_optional_bool(value: object) -> str:
    if value is None:
        return "미수집"
    return _state_word(bool(value), true_label="정상", false_label="대기")


def _format_optional_number(value: object, *, suffix: str = "") -> str:
    if value is None:
        return "미수집"
    return f"{value}{suffix}"


def _shorten(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def _build_audio_activity_summary(audio_pipeline: dict[str, object]) -> dict[str, str]:
    error_count = int(audio_pipeline.get("error_count") or 0)
    backpressure_count = int(audio_pipeline.get("backpressure_count") or 0)
    late_final_count = int(audio_pipeline.get("late_final_count") or 0)
    final_count = int(audio_pipeline.get("recent_final_count") or 0)
    utterance_count = int(audio_pipeline.get("recent_utterance_count") or 0)
    event_count = int(audio_pipeline.get("recent_event_count") or 0)

    if error_count > 0:
        return {"message": "현재 상태: 오류 감지", "style": "bold red"}
    if backpressure_count > 0 or late_final_count > 0:
        return {"message": "현재 상태: 지연 경고", "style": "bold yellow"}
    if final_count == 0 and utterance_count == 0 and event_count == 0:
        return {"message": "현재 상태: 최근 처리 없음", "style": "dim cyan"}
    return {"message": "현재 상태: 정상 수집 중", "style": "green"}
