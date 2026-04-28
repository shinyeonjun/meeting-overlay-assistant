from server.app.services.assistant import AssistantToolActionRegistry


def test_assistant_tool_action은_기본적으로_제안만_만든다() -> None:
    registry = AssistantToolActionRegistry(enabled=False, require_confirmation=True)

    proposal = registry.propose(
        name="regenerate_report",
        title="회의록 다시 만들기",
        description="현재 세션의 회의록을 다시 생성합니다.",
        payload={"session_id": "session-1"},
    )
    result = registry.execute(proposal, confirmed=True)

    assert proposal.requires_confirmation is True
    assert proposal.payload == {"session_id": "session-1"}
    assert result.status == "disabled"


def test_assistant_tool_action은_사용자_확인_전에는_실행되지_않는다() -> None:
    registry = AssistantToolActionRegistry(enabled=True, require_confirmation=True)

    proposal = registry.propose(
        name="delete_session",
        title="회의 삭제",
        description="회의와 관련 산출물을 삭제합니다.",
    )
    result = registry.execute(proposal, confirmed=False)

    assert result.status == "confirmation_required"


def test_assistant_tool_action은_확인되어도_실행기_연결_전에는_noop이다() -> None:
    registry = AssistantToolActionRegistry(enabled=True, require_confirmation=True)

    proposal = registry.propose(
        name="share_report",
        title="회의록 공유",
        description="공유 링크를 생성합니다.",
    )
    result = registry.execute(proposal, confirmed=True)

    assert result.status == "not_implemented"
