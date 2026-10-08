"""
Document Exporters for Courtroom Transcripts.

Provides one-click export to:
1. Microsoft Word (.docx) using python-docx
2. Court-formatted PDF using ReportLab with multi-page automatic pagination and running headers/footers
"""

from datetime import datetime
import io
from typing import Any, Dict, Optional

# python-docx imports
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

import os
import re

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Register Devanagari font for Hindi & Marathi PDF rendering
DEVANAGARI_FONT_REGISTERED = False
_CANDIDATE_FONTS = [
    ("/System/Library/Fonts/Supplemental/DevanagariMT.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 0),
    ("/System/Library/Fonts/Kohinoor.ttc", 0),
    ("/Library/Fonts/NotoSansDevanagari-Regular.ttf", None),
    ("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None),
    ("/usr/share/fonts/truetype/freefont/FreeSerif.ttf", None),
]
for font_path, sub_idx in _CANDIDATE_FONTS:
    if os.path.exists(font_path):
        try:
            if sub_idx is not None:
                pdfmetrics.registerFont(TTFont("Devanagari", font_path, subfontIndex=sub_idx))
            else:
                pdfmetrics.registerFont(TTFont("Devanagari", font_path))
            DEVANAGARI_FONT_REGISTERED = True
            break
        except Exception:
            continue


def export_to_docx(transcript: str, metadata: Optional[Dict[str, Any]] = None) -> io.BytesIO:
    """
    Generates a structured Microsoft Word document (.docx) for courtroom records.
    
    Structure:
        COURT PROCEEDINGS
        Speech-to-Text Draft
        Date: <date> | Language: <lang> | Words: <count>
        --------------------------------
        <transcript paragraphs>
        --------------------------------
        Generated using CourtScribe AI
        Demo — Human verification required
    """
    meta = metadata or {}
    now_str = meta.get("date") or datetime.now().strftime("%d %B %Y, %I:%M %p")
    language = meta.get("language", "Indian English (Courtroom Stenography)")
    title = meta.get("title", "COURT PROCEEDINGS / JUDGE'S DICTATION")
    subtitle = meta.get("subtitle", "Official Judicial Stenographer Record (Indian English)")

    doc = Document()

    # Set 0.8 inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run(title)
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)  # Dark Navy
    p_title.paragraph_format.space_after = Pt(2)

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(subtitle)
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(11)
    run_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)  # Slate
    p_sub.paragraph_format.space_after = Pt(12)

    # Metadata summary box
    word_count = len(transcript.split()) if transcript else 0
    table = doc.add_table(rows=2, cols=2)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table.autofit = False

    # Widths
    for row in table.rows:
        row.cells[0].width = Inches(3.4)
        row.cells[1].width = Inches(3.4)

    r0c0 = table.cell(0, 0).paragraphs[0]
    r0c0.add_run(f"Date & Time: {now_str}").font.size = Pt(9.5)
    
    r0c1 = table.cell(0, 1).paragraphs[0]
    r0c1.add_run(f"Language Mode: {language}").font.size = Pt(9.5)

    r1c0 = table.cell(1, 0).paragraphs[0]
    r1c0.add_run(f"Word Count: {word_count} words").font.size = Pt(9.5)

    r1c1 = table.cell(1, 1).paragraphs[0]
    r1c1.add_run("Status: Uncertified Draft").font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Divider
    p_div1 = doc.add_paragraph()
    p_div1.paragraph_format.space_after = Pt(12)
    run_div1 = p_div1.add_run("—" * 58)
    run_div1.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    # Transcript Body
    text_content = transcript.strip() if transcript and transcript.strip() else "[No transcription recorded.]"
    paragraphs = text_content.split("\n\n")

    for para_text in paragraphs:
        cleaned_para = para_text.strip()
        if not cleaned_para:
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        
        # Handle internal single newlines inside paragraph
        lines = cleaned_para.split("\n")
        for idx, line in enumerate(lines):
            run = p.add_run(line.strip())
            run.font.name = "Calibri"
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
            if idx < len(lines) - 1:
                p.add_run("\n")

    # Bottom Divider
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    p_div2 = doc.add_paragraph()
    p_div2.paragraph_format.space_after = Pt(8)
    run_div2 = p_div2.add_run("—" * 58)
    run_div2.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    # Footer note
    p_foot = doc.add_paragraph()
    p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_foot1 = p_foot.add_run("Generated using CourtScribe AI\n")
    run_foot1.font.name = "Calibri"
    run_foot1.font.size = Pt(9)
    run_foot1.font.bold = True
    run_foot1.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    run_foot2 = p_foot.add_run("Demo — Human verification required before official court record.")
    run_foot2.font.name = "Calibri"
    run_foot2.font.size = Pt(8.5)
    run_foot2.font.italic = True
    run_foot2.font.color.rgb = RGBColor(0xA0, 0xAE, 0xC0)

    # Save to buffer
    docx_io = io.BytesIO()
    doc.save(docx_io)
    docx_io.seek(0)
    return docx_io


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and draw
    professional running headers and 'Page X of Y' footers on all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, A4[1] - 36, "COURT PROCEEDINGS — TRANSCRIPT DRAFT")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, A4[1] - 42, A4[0] - 54, A4[1] - 42)

        # Running Footer (all pages)
        footer_y = 36
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, footer_y + 12, A4[0] - 54, footer_y + 12)

        disclaimer = "CourtScribe AI Demo — Unofficial Record (Human verification required)"
        self.drawString(54, footer_y, disclaimer)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 54, footer_y, page_str)

        self.restoreState()


def export_to_pdf(transcript: str, metadata: Optional[Dict[str, Any]] = None) -> io.BytesIO:
    """
    Generates a professional, text-based PDF using ReportLab.
    Ensures A4 dimensions, proper margins, court-style header,
    structured metadata, multi-page paragraph flow, and page numbering.
    """
    meta = metadata or {}
    now_str = meta.get("date") or datetime.now().strftime("%d %B %Y, %I:%M %p")
    language = meta.get("language", "Indian English (Courtroom Stenography)")
    title = meta.get("title", "COURT PROCEEDINGS / JUDGE'S DICTATION")
    subtitle = meta.get("subtitle", "Official Judicial Stenographer Record (Indian English)")

    pdf_buffer = io.BytesIO()
    # 54 points = 0.75 inch margin
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Check if Devanagari font is needed
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", transcript or "")) or language in ("Hindi", "Marathi")
    use_dev = has_devanagari and DEVANAGARI_FONT_REGISTERED
    body_font = "Devanagari" if use_dev else "Helvetica"

    # Custom styles
    title_style = ParagraphStyle(
        "CourtTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Centered
        textColor=colors.HexColor("#1B365D"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "CourtSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        alignment=1,  # Centered
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=14,
    )

    body_style = ParagraphStyle(
        "CourtBody",
        parent=styles["Normal"],
        fontName=body_font,
        fontSize=10.5 if use_dev else 10,
        leading=16 if use_dev else 15,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=10,
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2D3748"),
    )

    meta_val_style = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#4A5568"),
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(subtitle, subtitle_style))
    story.append(Spacer(1, 4))

    # Metadata Table
    word_count = len(transcript.split()) if transcript else 0
    table_data = [
        [
            Paragraph(f"<b>Hearing Date:</b> {now_str}", meta_val_style),
            Paragraph(f"<b>Language:</b> {language}", meta_val_style),
        ],
        [
            Paragraph(f"<b>Word Count:</b> {word_count} words", meta_val_style),
            Paragraph("<b>Classification:</b> Uncertified Draft Record", meta_val_style),
        ],
    ]

    meta_table = Table(table_data, colWidths=[240, 240])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Divider line
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=14))

    # Transcript Paragraphs
    text_content = transcript.strip() if transcript and transcript.strip() else "[No transcription recorded.]"
    paragraphs = text_content.split("\n\n")

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
        # Convert internal single newlines to HTML breaks for ReportLab
        html_para = para_clean.replace("\n", "<br/>")
        story.append(Paragraph(html_para, body_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_buffer.seek(0)
    return pdf_buffer
