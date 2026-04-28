"""회의록 조립 구성요소 패키지."""

from .markdown_report_builder import MarkdownReportBuilder
from .report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    ReportSection,
    report_document_to_dict,
)
from .html_report_template import (
    build_sample_report_document,
    render_report_html,
    render_sample_report_html,
)
from .report_document_mapper import (
    ReportSessionContext,
    build_report_document_v1,
)
from .report_markdown_renderer import (
    render_report_markdown,
)
from .speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)

__all__ = [
    "ReportActionItem",
    "ReportDocumentV1",
    "ReportListItem",
    "ReportMetaField",
    "ReportSection",
    "ReportSessionContext",
    "MarkdownReportBuilder",
    "SpeakerAttributedEvent",
    "SpeakerEventProjectionService",
    "build_sample_report_document",
    "build_report_document_v1",
    "render_report_html",
    "render_report_markdown",
    "render_sample_report_html",
    "report_document_to_dict",
]
