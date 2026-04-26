"""리포트 조립 구성요소 패키지."""

from .markdown_report_builder import MarkdownReportBuilder
from .html_report_template import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    build_sample_report_document,
    render_report_html,
    render_sample_report_html,
)
from .report_document_mapper import build_report_document_v1, render_report_markdown
from .speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)

__all__ = [
    "ReportActionItem",
    "ReportDocumentV1",
    "ReportListItem",
    "ReportMetaField",
    "MarkdownReportBuilder",
    "SpeakerAttributedEvent",
    "SpeakerEventProjectionService",
    "build_sample_report_document",
    "build_report_document_v1",
    "render_report_html",
    "render_report_markdown",
    "render_sample_report_html",
]
