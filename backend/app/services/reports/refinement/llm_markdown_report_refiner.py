"""LLM 기반 Markdown 리포트 정제기."""

from __future__ import annotations

from backend.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)
from backend.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class LLMMarkdownReportRefiner(ReportRefiner):
    """구조화된 리포트 입력을 LLM으로 사용자용 문서로 정제한다."""

    def __init__(self, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client
        self._fallback_refiner = StructuredMarkdownReportRefiner()

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        prompt = self._build_prompt(refinement_input)
        try:
            refined_markdown = self._completion_client.complete(prompt).strip()
        except Exception:
            return self._fallback_refiner.refine(refinement_input)

        if not refined_markdown:
            return self._fallback_refiner.refine(refinement_input)
        if not self._looks_like_markdown_report(refined_markdown):
            return self._fallback_refiner.refine(refinement_input)
        return refined_markdown

    def _build_prompt(self, refinement_input: ReportRefinementInput) -> str:
        event_block = "\n".join(f"- {line}" for line in refinement_input.event_lines) or "- 없음"
        transcript_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_transcript_lines)
            or "- 없음"
        )
        speaker_event_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_event_lines)
            or "- 없음"
        )

        return (
            "당신은 회의 리포트를 정리하는 전문 편집자다.\n"
            "아래 자료를 바탕으로 사용자가 바로 읽을 수 있는 한국어 Markdown 리포트를 작성하라.\n"
            "반드시 Markdown만 반환하고, 설명 문장이나 코드 블록은 추가하지 마라.\n"
            "\n"
            "섹션 순서는 반드시 아래를 따른다.\n"
            "1. # 회의 리포트\n"
            "2. - 세션 ID: ...\n"
            "3. ## 회의 개요\n"
            "4. ## 질문\n"
            "5. ## 결정 사항\n"
            "6. ## 액션 아이템\n"
            "7. ## 리스크\n"
            "8. ## 참고 전사\n"
            "9. ## 발화자 기반 인사이트\n"
            "\n"
            "규칙:\n"
            "- 내용이 없으면 '없음'이라고만 적는다.\n"
            "- 액션 아이템에 담당자나 기한이 있으면 함께 적는다.\n"
            "- 근거 문장이 있으면 항목 아래에 짧게 정리한다.\n"
            "- 참고 전사는 중복을 줄이고 핵심 발화만 정리한다.\n"
            "- 없는 사실을 추가하지 마라.\n"
            "- 같은 의미의 문장은 합치고 표현을 자연스럽게 다듬는다.\n"
            "- 질문, 결정 사항, 액션 아이템, 리스크는 서로 섞지 마라.\n"
            "\n"
            f"세션 ID: {refinement_input.session_id}\n"
            "\n"
            "[원본 Markdown]\n"
            f"{refinement_input.raw_markdown}\n"
            "\n"
            "[이벤트]\n"
            f"{event_block}\n"
            "\n"
            "[발화 전사]\n"
            f"{transcript_block}\n"
            "\n"
            "[발화자-이벤트 연결]\n"
            f"{speaker_event_block}\n"
        )

    @staticmethod
    def _looks_like_markdown_report(content: str) -> bool:
        stripped = content.lstrip()
        if not stripped:
            return False
        if stripped.startswith("{") or stripped.startswith("["):
            return False
        return "# 회의 리포트" in stripped
