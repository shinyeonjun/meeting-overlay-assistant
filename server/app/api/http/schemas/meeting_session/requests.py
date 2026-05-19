"""세션 요청 스키마."""

from pydantic import BaseModel, Field, model_validator


DEFAULT_PRIVACY_NOTICE_VERSION = "2026-05-v1"


class SessionCreateRequest(BaseModel):
    """세션 생성 요청."""

    title: str = Field(..., min_length=1)
    mode: str = Field(default="meeting")
    primary_input_source: str = Field(default="system_audio")
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    participants: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def apply_legacy_source_alias(cls, raw_value):
        if isinstance(raw_value, dict) and "primary_input_source" not in raw_value and "source" in raw_value:
            normalized = dict(raw_value)
            normalized["primary_input_source"] = normalized.pop("source")
            return normalized
        return raw_value


class SessionStartRequest(BaseModel):
    """세션 시작 전 녹음/전사/AI 처리 고지 확인 요청."""

    privacy_notice_acknowledged: bool = Field(...)
    privacy_notice_version: str = Field(
        default=DEFAULT_PRIVACY_NOTICE_VERSION,
        min_length=1,
        max_length=64,
    )


class SessionUpdateRequest(BaseModel):
    """세션 제목 수정 요청."""

    title: str = Field(..., min_length=1)
