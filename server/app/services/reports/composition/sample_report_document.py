"""회의록 템플릿 디자인 확인용 샘플 문서."""

from __future__ import annotations

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    ReportSection,
)


def build_sample_report_document() -> ReportDocumentV1:
    """디자인 확인용 샘플 문서를 만든다."""

    return ReportDocumentV1(
        title="CAPS 회의록 품질 개선 회의",
        metadata=(
            ReportMetaField("회의제목", "고객중심과 외부지향 회사전략 인식 제고 회의"),
            ReportMetaField("일시", "2026-04-25 10:00 - 10:45"),
            ReportMetaField("장소", "본사 4층 회의실"),
            ReportMetaField("작성자", "기획팀 박민수 대리"),
            ReportMetaField("작성일", "2026-04-25"),
            ReportMetaField("참석자", "기획팀 박민수 과장, 이지현 대리 / 개발팀 김성준 대리"),
        ),
        summary=(
            "고객중심과 외부지향 회사전략에 대한 구성원 인식을 높이기 위한 회의록이다.",
        ),
        sections=(
            ReportSection(
                title="현재 회사전략에 대한 사원들의 이해도 점검",
                background=(
                    ReportListItem(
                        "고객중심과 외부지향 회사전략에 대한 구성원 이해도를 확인할 필요가 있었다.",
                    ),
                ),
                opinions=(
                    ReportListItem(
                        "고객중심은 고객의 입장에서 고객이 좋아할 만한 서비스를 제공하는 방향으로 이해한다.",
                    ),
                    ReportListItem(
                        "외부지향은 살아있는 서비스를 외부에 잘 알리는 활동으로 정리한다.",
                    ),
                ),
                review=(
                    ReportListItem(
                        "회사전략이 현장 업무에서 구체적으로 인식되고 있는지 점검했다.",
                    ),
                ),
                direction=(
                    ReportListItem(
                        "회사전략을 구성원이 이해할 수 있도록 인식 제고 방안을 마련한다.",
                    ),
                ),
            ),
            ReportSection(
                title="인식 제고를 위한 개선방안",
                background=(
                    ReportListItem(
                        "회사전략을 개인 업무에서 실천할 수 있는 방안이 필요하다는 점을 확인했다.",
                    ),
                ),
                opinions=(
                    ReportListItem(
                        "회사 전략을 바탕으로 개인이 실천할 수 있는 작은 업무부터 실행한다.",
                    ),
                ),
                review=(
                    ReportListItem(
                        "구성원이 회사전략을 인지할 수 있도록 구체적인 실행방안을 마련한다.",
                    ),
                ),
                direction=(
                    ReportListItem(
                        "사원 의견을 취합한 뒤 다음 회의에서 개선방안을 구체화한다.",
                    ),
                ),
            ),
        ),
        agenda=(ReportListItem("고객중심과 외부지향 회사전략에 대한 인식제고"),),
        decisions=(
            ReportListItem(
                "회사전략에 대한 사원들의 의견을 취합 및 수렴한다.",
            ),
            ReportListItem(
                "다음 주 목요일 개선방안에 대한 구체적 절차를 의논한다.",
            ),
        ),
        action_items=(
            ReportActionItem(
                task="10/4(목) 10:00시 4층 회의실에서 후속 회의를 진행한다.",
            ),
        ),
    )
