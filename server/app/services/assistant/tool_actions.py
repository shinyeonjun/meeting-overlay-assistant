"""챗봇 tool action 안전 계약."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AssistantToolActionProposal:
    """사용자 확인이 필요한 챗봇 action 제안."""

    name: str
    title: str
    description: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    requires_confirmation: bool = True


@dataclass(frozen=True)
class AssistantToolExecutionResult:
    """챗봇 action 실행 시도 결과."""

    action_id: str
    status: str
    message: str


class AssistantToolActionRegistry:
    """실험 플래그와 사용자 확인을 강제하는 action registry."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        require_confirmation: bool = True,
    ) -> None:
        self._enabled = enabled
        self._require_confirmation = require_confirmation

    def propose(
        self,
        *,
        name: str,
        title: str,
        description: str,
        payload: dict[str, Any] | None = None,
        requires_confirmation: bool = True,
    ) -> AssistantToolActionProposal:
        """LLM이 직접 실행하지 못하도록 action을 제안 객체로만 만든다."""

        return AssistantToolActionProposal(
            name=name,
            title=title,
            description=description,
            payload=dict(payload or {}),
            requires_confirmation=requires_confirmation or self._require_confirmation,
        )

    def execute(
        self,
        proposal: AssistantToolActionProposal,
        *,
        confirmed: bool,
    ) -> AssistantToolExecutionResult:
        """사용자 확인 전에는 어떤 변경 action도 실행하지 않는다."""

        if not self._enabled:
            return AssistantToolExecutionResult(
                action_id=proposal.id,
                status="disabled",
                message="assistant tool calling이 비활성화되어 있습니다.",
            )
        if proposal.requires_confirmation and not confirmed:
            return AssistantToolExecutionResult(
                action_id=proposal.id,
                status="confirmation_required",
                message="사용자 확인이 필요합니다.",
            )
        return AssistantToolExecutionResult(
            action_id=proposal.id,
            status="not_implemented",
            message="action 실행기는 아직 연결되지 않았습니다.",
        )
