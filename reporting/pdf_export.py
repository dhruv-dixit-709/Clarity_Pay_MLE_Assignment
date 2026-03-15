from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer


def _inline_markdown_to_html(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", escaped)
    return escaped


def _build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        spaceAfter=8,
    )
    bullet = ParagraphStyle(
        "ReportBullet",
        parent=body,
        leftIndent=14,
        firstLineIndent=-10,
    )
    metadata = ParagraphStyle(
        "MetadataBody",
        parent=body,
        fontSize=9,
        leading=12,
    )
    heading1 = ParagraphStyle(
        "ReportHeading1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )
    heading2 = ParagraphStyle(
        "ReportHeading2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceAfter=10,
    )
    heading3 = ParagraphStyle(
        "ReportHeading3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceAfter=8,
    )
    return {
        "body": body,
        "bullet": bullet,
        "metadata": metadata,
        "heading1": heading1,
        "heading2": heading2,
        "heading3": heading3,
    }


def markdown_to_flowables(markdown_text: str) -> list:
    styles = _build_styles()
    flowables: list = []
    code_block: list[str] = []
    in_code_block = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                flowables.append(Preformatted("\n".join(code_block), styles["metadata"]))
                flowables.append(Spacer(1, 0.1 * inch))
                code_block = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_block.append(line)
            continue

        if not stripped:
            flowables.append(Spacer(1, 0.08 * inch))
            continue

        if stripped.startswith("# "):
            flowables.append(Paragraph(_inline_markdown_to_html(stripped[2:]), styles["heading1"]))
            continue
        if stripped.startswith("## "):
            flowables.append(Paragraph(_inline_markdown_to_html(stripped[3:]), styles["heading2"]))
            continue
        if stripped.startswith("### "):
            flowables.append(Paragraph(_inline_markdown_to_html(stripped[4:]), styles["heading3"]))
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            flowables.append(Paragraph(f"&bull; {_inline_markdown_to_html(stripped[2:])}", styles["bullet"]))
            continue
        if re.match(r"^\d+\.\s", stripped):
            flowables.append(Paragraph(_inline_markdown_to_html(stripped), styles["bullet"]))
            continue

        flowables.append(Paragraph(_inline_markdown_to_html(stripped), styles["body"]))

    if code_block:
        flowables.append(Preformatted("\n".join(code_block), styles["metadata"]))

    return flowables


def _page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(7.5 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def write_underwriting_report_pdf(
    markdown_text: str,
    output_path: str | Path,
    traceback_metadata: dict[str, object],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Underwriting Report",
        author="Merchant Underwriting Pipeline",
    )
    styles = _build_styles()
    story = markdown_to_flowables(markdown_text)
    story.append(PageBreak())
    story.append(Paragraph("Traceback Metadata", styles["heading1"]))

    for key, value in traceback_metadata.items():
        if isinstance(value, list):
            value_text = ", ".join(str(item) for item in value)
        else:
            value_text = str(value)
        story.append(Paragraph(f"<b>{escape(str(key))}:</b> {escape(value_text)}", styles["metadata"]))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return path
