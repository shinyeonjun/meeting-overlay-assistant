"""LLM 기반 Markdown 리포트 정제기."""

from __future__ import annotations

from backend.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)


class LLMMarkdownReportRefiner(ReportRefiner):
    """구조화된 이벤트와 화자 정보를 더 자연스러운 Markdown으로 정제한다."""

    def __init__(self, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        prompt = self._build_prompt(refinement_input)
        try:
            refined_markdown = self._completion_client.complete(prompt).strip()
        except Exception:
            return refinement_input.raw_markdown

        return refined_markdown or refinement_input.raw_markdown

    def _build_prompt(self, refinement_input: ReportRefinementInput) -> str:
        event_block = "\n".join(f"- {line}" for line in refinement_input.event_lines) or "- 없음"
        transcript_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_transcript_lines) or "- 없음"
        )
        speaker_event_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_event_lines) or "- 없음"
        )

        return (
            "당신은 회의 리포트를 정리하는 전문가다.\n"
            "아래 자료를 바탕으로 읽기 좋은 Markdown 회의록을 다시 작성하라.\n"
            "반드시 Markdown만 반환하고, 설명 문장은 붙이지 마라.\n"
            "섹션 순서는 반드시 다음을 지켜라.\n"
            "1. # Session Report: {session_id}\n"
            "2. ## Snapshot\n"
            "3. ## Questions\n"
            "4. ## Decisions\n"
            "5. ## Action Items\n"
            "6. ## Risks\n"
            "7. ## Speaker Notes\n"
            "8. ## Speaker-attributed Events\n"
            "\n"
            "규칙:\n"
            "- 내용이 없으면 '없음'이라고만 적어라.\n"
            "- Action Items에는 담당자와 기한이 있으면 함께 적어라.\n"
            "- Speaker Notes는 화자 label 기준으로 묶어라.\n"
            "- 과장하거나 없는 사실을 추가하지 마라.\n"
            "- 원문의 의미를 유지하되, 중복은 줄이고 읽기 쉽게 정리하라.\n"
            "\n"
            f"세션 ID: {refinement_input.session_id}\n"
            "\n"
            "[원본 Markdown]\n"
            f"{refinement_input.raw_markdown}\n"
            "\n"
            "[이벤트]\n"
            f"{event_block}\n"
            "\n"
            "[화자 전사]\n"
            f"{transcript_block}\n"
            "\n"
            "[화자-이벤트 연결]\n"
            f"{speaker_event_block}\n"
        ).format(session_id=refinement_input.session_id)
