from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class TestStructuredMarkdownReportRefiner:
    def test_이벤트_메타데이터를_사용자용_섹션으로_구성한다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-1",
                raw_markdown="# raw",
                events=[
                    ReportRefinementEvent(
                        event_type="decision",
                        title="출시를 3월 14일로 확정합니다.",
                        state="confirmed",
                        evidence_text="이번 주 금요일에 출시합시다.",
                        speaker_label="SPEAKER_00",
                        input_source="system_audio",
                    ),
                    ReportRefinementEvent(
                        event_type="action_item",
                        title="민수가 발표 체크리스트를 정리합니다.",
                        state="open",
                        evidence_text="민수가 발표 체크리스트를 정리합니다.",
                        speaker_label="SPEAKER_01",
                    ),
                    ReportRefinementEvent(
                        event_type="risk",
                        title="QA 시간이 부족할 수 있습니다.",
                        state="open",
                    ),
                ],
                speaker_transcript_lines=[
                    "[SPEAKER_00] 00:00-00:01 이번 주 금요일에 출시합시다."
                ],
                speaker_event_lines=[
                    "[decision] SPEAKER_00: 출시를 3월 14일로 확정합니다."
                ],
            )
        )

        assert result.startswith("# 회의록")
        assert "- 세션 ID: session-1" in result
        assert "## 회의 개요" in result
        assert "- 추출 이벤트: 3건" in result
        assert "## 결정 사항" in result
        assert "1. 출시를 3월 14일로 확정합니다." in result
        assert "## 액션 아이템" in result
        assert "- [ ] 민수가 발표 체크리스트를 정리합니다." in result
        assert "  - 발화자: SPEAKER_00" in result
        assert "  - 입력 소스: system_audio" in result
        assert "  - 근거: 민수가 발표 체크리스트를 정리합니다." in result
        assert "## 리스크" in result
        assert "## 참고 전사" in result
        assert "[SPEAKER_00] 00:00-00:01 이번 주 금요일에 출시합시다." in result
        assert "## 발화자 기반 인사이트" in result

    def test_같은_근거를_가진_질문은_하나만_남긴다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-dup",
                raw_markdown="# raw",
                events=[
                    ReportRefinementEvent(
                        event_type="question",
                        title="사파리 브라우저에서만 로그인 버튼이 비활성화되는 것 맞나요?",
                        state="open",
                        evidence_text="사파리 브라우저에서만 로그인 버튼이 비활성화되는 것 맞나요?",
                    ),
                    ReportRefinementEvent(
                        event_type="question",
                        title="사파리 브라우저에서 로그인 버튼 비활성화 확인 필요",
                        state="open",
                        evidence_text="사파리 브라우저에서만 로그인 버튼이 비활성화되는 것 맞나요?",
                    ),
                ],
            )
        )

        assert result.count("사파리 브라우저에서만 로그인 버튼이 비활성화되는 것 맞나요?") == 2
        assert "사파리 브라우저에서 로그인 버튼 비활성화 확인 필요" not in result

    def test_메타성_문장은_리스크와_질문에서_제거한다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-meta",
                raw_markdown="# raw",
                events=[
                    ReportRefinementEvent(
                        event_type="question",
                        title="여기서 질문 하나 더 있습니다.",
                        state="open",
                        evidence_text="여기서 질문 하나 더 있습니다.",
                    ),
                    ReportRefinementEvent(
                        event_type="risk",
                        title="추가 리스크도 있습니다.",
                        state="open",
                        evidence_text="추가 리스크도 있습니다.",
                    ),
                    ReportRefinementEvent(
                        event_type="risk",
                        title="배포 일정이 하루 밀릴 수 있습니다.",
                        state="open",
                        evidence_text="배포 일정이 하루 밀릴 수 있습니다.",
                    ),
                ],
                speaker_event_lines=[
                    "[question] SPEAKER_00: 여기서 질문 하나 더 있습니다.",
                    "[risk] SPEAKER_00: 추가 리스크도 있습니다.",
                    "[risk] SPEAKER_00: 배포 일정이 하루 밀릴 수 있습니다.",
                ],
            )
        )

        assert "여기서 질문 하나 더 있습니다." not in result
        assert "추가 리스크도 있습니다." not in result
        assert "배포 일정이 하루 밀릴 수 있습니다." in result

    def test_이벤트가_없으면_빈_섹션을_없음으로_채운다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-empty",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의록")
        assert result.count("- 없음") >= 6
