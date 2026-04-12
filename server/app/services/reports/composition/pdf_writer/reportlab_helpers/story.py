"""리포트 영역의 story 서비스를 제공한다."""
from __future__ import annotations

from datetime import datetime
from xml.sax.saxutils import escape

from server.app.services.reports.composition.pdf_writer.header import extract_report_header
from server.app.services.reports.composition.pdf_writer.reportlab_helpers.page import is_ordered_line


def build_report_story(*, title: str, lines: list[str], styles: dict[str, object]):
    """ReportLab story를 구성한다."""

    from reportlab.lib import colors
    from reportlab.platypus import HRFlowable, Paragraph, Spacer

    header = extract_report_header(lines=lines, fallback_title=title)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    story = [
        Spacer(1, 18),
        Paragraph(escape(header.title), styles["title"]),
        Paragraph(f"생성 시각: {generated_at}", styles["subtitle"]),
    ]
    for meta_line in header.metadata_lines:
        story.append(Paragraph(escape(meta_line.lstrip("- ").strip()), styles["subtitle"]))
    story.extend(
        [
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D1D5DB")),
            Spacer(1, 14),
        ]
    )

    in_transcript_section = False
    for raw_line in header.remaining_lines:
        line = raw_line.rstrip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            story.append(Paragraph(escape(heading), styles["section"]))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=colors.HexColor("#E5E7EB"),
                    spaceAfter=8,
                )
            )
            in_transcript_section = heading == "참고 서사"
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:].strip()), styles["subsection"]))
            continue

        if line.startswith("  - "):
            story.append(Paragraph(escape(line[4:].strip()), styles["meta"]))
            continue

        if is_ordered_line(line):
            story.append(Paragraph(escape(line), styles["ordered"]))
            continue

        if line.startswith("- "):
            content = line[2:].strip()
            style = styles["transcript"] if in_transcript_section else styles["bullet"]
            story.append(Paragraph(escape(content), style))
            continue

        story.append(Paragraph(escape(line), styles["body"]))

    return header, story
