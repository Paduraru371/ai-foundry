"""Generate downloadable answer documents for the admin chat."""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class GeneratedDocument:
    content: bytes
    media_type: str
    filename: str


def generate(
    kind: str,
    answer: str,
    metadata: dict | None = None,
    *,
    filename_stem: str = "libra-assist-answer",
) -> GeneratedDocument:
    kind = kind.lower()
    metadata = metadata or {}
    if kind == "pdf":
        content = _pdf(answer, metadata)
        media_type = "application/pdf"
    elif kind == "docx":
        content = _docx(answer, metadata)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif kind == "pptx":
        content = _pptx(answer, metadata)
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    elif kind == "json":
        content = json.dumps(
            {"answer": answer, "metadata": metadata},
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        media_type = "application/json"
    elif kind == "md":
        content = _text_document(answer, metadata, markdown=True).encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
    elif kind == "txt":
        content = _text_document(answer, metadata, markdown=False).encode("utf-8")
        media_type = "text/plain; charset=utf-8"
    else:
        raise ValueError(
            "Document type must be pdf, docx, pptx, txt, md, or json."
        )
    return GeneratedDocument(
        content=content,
        media_type=media_type,
        filename=f"{filename_stem}.{kind}",
    )


def _text_document(answer: str, metadata: dict, *, markdown: bool) -> str:
    title = "# Libra Assist answer" if markdown else "LIBRA ASSIST ANSWER"
    details = "\n".join(f"{key}: {value}" for key, value in metadata.items() if value)
    return f"{title}\n\n{details}\n\n{answer}".strip() + "\n"


def _answer_lines(answer: str) -> list[tuple[str, str]]:
    """Classify common Markdown lines so office exports preserve structure."""
    result: list[tuple[str, str]] = []
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            result.append(("space", ""))
            continue
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        bullet = re.match(r"^[-*•]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if heading:
            result.append(("heading", heading.group(1)))
        elif bullet:
            result.append(("bullet", bullet.group(1)))
        elif numbered:
            result.append(("numbered", numbered.group(1)))
        else:
            result.append(("paragraph", line))
    return result or [("paragraph", " ")]


def _docx(answer: str, metadata: dict) -> bytes:
    from docx import Document

    document = Document()
    document.add_heading("Libra Assist answer", 0)
    for key, value in metadata.items():
        if value:
            paragraph = document.add_paragraph()
            paragraph.add_run(f"{_label(key)}: ").bold = True
            paragraph.add_run(str(value))
    document.add_heading("Answer", level=1)
    for kind, text in _answer_lines(answer):
        if kind == "heading":
            document.add_heading(text, level=2)
        elif kind == "bullet":
            document.add_paragraph(text, style="List Bullet")
        elif kind == "numbered":
            document.add_paragraph(text, style="List Number")
        elif kind == "space":
            document.add_paragraph()
        else:
            document.add_paragraph(text)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _pdf(answer: str, metadata: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Libra Assist answer",
    )
    styles = getSampleStyleSheet()
    story = [Paragraph("Libra Assist answer", styles["Title"]), Spacer(1, 8)]
    for key, value in metadata.items():
        if value:
            story.append(Paragraph(
                f"<b>{escape(_label(key))}:</b> {escape(str(value))}",
                styles["BodyText"],
            ))
    story.extend([Spacer(1, 12), Paragraph("Answer", styles["Heading1"])])
    for kind, text in _answer_lines(answer):
        if kind == "heading":
            story.extend([Paragraph(escape(text), styles["Heading2"]), Spacer(1, 4)])
        elif kind == "bullet":
            story.extend([
                Paragraph(escape(text), styles["BodyText"], bulletText="•"),
                Spacer(1, 3),
            ])
        elif kind == "numbered":
            story.extend([
                Paragraph(escape(text), styles["BodyText"], bulletText="–"),
                Spacer(1, 3),
            ])
        elif kind == "space":
            story.append(Spacer(1, 5))
        else:
            story.extend([
                Paragraph(escape(text), styles["BodyText"]),
                Spacer(1, 6),
            ])
    document.build(story)
    return output.getvalue()


def _pptx(answer: str, metadata: dict) -> bytes:
    from lxml import etree
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    presentation = Presentation()
    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = "Libra Assist answer"
    subtitle = title_slide.placeholders[1]
    subtitle.text = "\n".join(
        f"{_label(key)}: {value}"
        for key, value in metadata.items()
        if value
    ) or "Generated answer"

    lines = [
        item
        for item in _answer_lines(answer)
        if item[0] != "space"
    ] or [("paragraph", " ")]
    for start in range(0, len(lines), 8):
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        title_box = slide.shapes.add_textbox(
            Inches(0.65), Inches(0.35), Inches(12), Inches(0.7)
        )
        title_frame = title_box.text_frame
        title_frame.text = "Answer" if start == 0 else "Answer — continued"
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.font.size = Pt(27)
        title_paragraph.font.bold = True
        title_paragraph.font.color.rgb = RGBColor(55, 31, 103)

        body_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(1.25), Inches(11.7), Inches(5.7)
        )
        body = body_box.text_frame
        body.word_wrap = True
        body.clear()
        for offset, (line_kind, text) in enumerate(lines[start:start + 8]):
            paragraph = body.paragraphs[0] if offset == 0 else body.add_paragraph()
            paragraph.text = (
                f"{start + offset + 1}. {text}"
                if line_kind == "numbered"
                else text
            )
            paragraph.font.size = Pt(21 if line_kind == "heading" else 18)
            paragraph.font.bold = line_kind == "heading"
            paragraph.space_after = Pt(10)
            paragraph.alignment = PP_ALIGN.LEFT
            if line_kind == "bullet":
                properties = paragraph._p.get_or_add_pPr()
                bullet = etree.Element(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}buChar"
                )
                bullet.set("char", "•")
                properties.insert(0, bullet)

    output = io.BytesIO()
    presentation.save(output)
    return output.getvalue()


def _label(value: str) -> str:
    return value.replace("_", " ").strip().title()
