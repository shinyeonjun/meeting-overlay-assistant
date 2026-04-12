"""리포트 영역의 prompt builder 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import ReportRefinementInput


def build_refinement_prompt(refinement_input: ReportRefinementInput) -> str:
    """리포트 정제용 프롬프트를 생성한다."""

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
        "당신은 회의 리포트를 정리하는 전문 에디터다.\n"
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
        "8. ## 참고 의사\n"
        "9. ## 발화자 기반 인사이트\n"
        "\n"
        "규칙:\n"
        "- 내용이 없으면 '없음'이라고만 적는다.\n"
        "- 액션 아이템에 담당자나 기한이 있으면 함께 적는다.\n"
        "- 근거 문장이 있으면 해당 항목 아래에 정리한다.\n"
        "- 참고 의사는 중복을 줄이고 핵심 발화만 정리한다.\n"
        "- 없는 사실은 추가하지 마라.\n"
        "- 같은 내용을 여러 문장으로 반복하지 말고 자연스럽게 압축해라.\n"
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
        "[발화와 이벤트 연결]\n"
        f"{speaker_event_block}\n"
    )

