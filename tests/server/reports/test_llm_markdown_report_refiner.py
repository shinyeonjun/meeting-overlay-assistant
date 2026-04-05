from __future__ import annotations

from server.app.services.reports.refinement.llm_markdown_report_refiner import (
    LLMMarkdownReportRefiner,
)
from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
)


class FakeCompletionClient:
    def __init__(self, response_text: str, should_raise: bool = False) -> None:
        self._response_text = response_text
        self._should_raise = should_raise

    def complete(self, prompt: str) -> str:
        if self._should_raise:
            raise RuntimeError("boom")
        return self._response_text


class TestLLMMarkdownReportRefiner:
    def test_llm_응답이_있으면_정제된_markdown을_반환한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient("# Session Report: s\n\n- Session ID: s\n\n## Snapshot\n- 정리됨")
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
                event_lines=["[question] 이거 맞아요?"],
            )
        )

        assert result.startswith("# 회의 리포트")
        assert "- 정리됨" in result
        assert "- 세션 ID: s" in result
        assert "## 회의 개요" in result
        assert "## 질문" in result
        assert "## Snapshot" not in result
        assert "- Session ID: s" not in result

    def test_llm_실패시_structured_fallback으로_정제한다(self):
        refiner = LLMMarkdownReportRefiner(FakeCompletionClient("", should_raise=True))

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의 리포트")
        assert "- 세션 ID: s" in result

    def test_llm_응답이_json이면_structured_fallback으로_정제한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient('{"title":"회의 리포트","summary":"정리됨"}')
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의 리포트")
        assert "- 세션 ID: s" in result

    def test_llm_응답에_필수_섹션이_빠지면_자동으로_보정한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient(
                "# Session Report: s\n\n"
                "## Snapshot\n"
                "- 정리됨\n\n"
                "## 질문\n"
                "- 이미 있는 질문\n"
            )
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의 리포트")
        assert result.count("## 질문") == 1
        assert "## 회의 개요" in result
        assert "## 결정 사항" in result
        assert "## 액션 아이템" in result
        assert "## 리스크" in result

    def test_llm_영문_섹션_제목을_한국_표준_헤더로_정규화한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient(
                "# Meeting Report\n\n"
                "Session ID: session-123\n\n"
                "## Decisions\n"
                "1. 배포 일정 확정\n\n"
                "## Next Steps\n"
                "- QA 재확인\n"
            )
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-123",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의 리포트")
        assert "- 세션 ID: session-123" in result
        assert "## 결정 사항" in result
        assert "## 액션 아이템" in result
        assert "## Decisions" not in result
        assert "## Next Steps" not in result

    def test_llm_응답의_목록_스타일을_섹션별_표준_형식으로_정규화한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient(
                "# Meeting Report\n\n"
                "- Session ID: session-123\n\n"
                "## Decisions\n"
                "- 배포 일정 확정\n"
                "* 롤백 계획 점검\n\n"
                "## Next Steps\n"
                "1. QA 재확인\n"
                "- API 문서 공유\n\n"
                "## Risks\n"
                "1. 일정 지연 가능성\n"
            )
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-123",
                raw_markdown="# raw",
            )
        )

        assert "## 결정 사항" in result
        assert "1. 배포 일정 확정" in result
        assert "2. 롤백 계획 점검" in result
        assert "## 액션 아이템" in result
        assert "- [ ] QA 재확인" in result
        assert "- [ ] API 문서 공유" in result
        assert "## 리스크" in result
        assert "- 일정 지연 가능성" in result
