"""세션 요청 스키마"""

from pydantic import BaseModel, Field, model_validator


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
