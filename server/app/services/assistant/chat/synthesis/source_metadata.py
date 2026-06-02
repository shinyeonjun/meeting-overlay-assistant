"""assistant 답변 근거 메타데이터 렌더링."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult


def render_source_metadata(source: RetrievalSearchResult) -> str:
    """검색 근거의 메타데이터를 프롬프트용 문자열로 렌더링한다."""

    metadata = []
    if source.source_type:
        metadata.append(f"유형={source.source_type}")
    source_kind = _metadata_value(source, "source_kind")
    if source_kind:
        metadata.append(f"소스성격={source_kind}")
    section_role = _metadata_value(source, "section_role")
    if section_role:
        metadata.append(f"섹션역할={section_role}")
    heading_path = _metadata_value(source, "heading_path")
    if heading_path:
        metadata.append(f"섹션경로={heading_path}")
    if source.session_id:
        metadata.append(f"세션={source.session_id}")
    if source.report_id:
        metadata.append(f"회의록={source.report_id}")
    if source.speaker_label:
        metadata.append(f"발화자={source.speaker_label}")
    if source.start_ms is not None or source.end_ms is not None:
        metadata.append(f"시간={_format_ms(source.start_ms)}-{_format_ms(source.end_ms)}")
    if source.source_ref:
        metadata.append(f"참조={source.source_ref}")
    return ", ".join(metadata) if metadata else "-"


def _metadata_value(source: RetrievalSearchResult, key: str) -> str:
    metadata = source.metadata_json or {}
    value = metadata.get(key)
    if isinstance(value, list):
        return " > ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value is not None else ""


def _format_ms(value: int | None) -> str:
    if value is None:
        return "?"
    total_seconds = max(int(value // 1000), 0)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"
