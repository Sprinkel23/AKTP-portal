import io
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import BASE_DIR, DEFAULT_LOGO_PATH

NAVY = colors.HexColor("#0A2463")
ROYAL = colors.HexColor("#1E40AF")
GOLD = colors.HexColor("#D4AF37")
GOLD_LIGHT = colors.HexColor("#FEF9E7")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")


def resolve_logo_path(settings_logo_path: Optional[str] = None) -> Optional[Path]:
    if settings_logo_path:
        candidate = Path(settings_logo_path)
        if not candidate.is_absolute():
            # handle /uploads/... or /assets/...
            rel = settings_logo_path.lstrip("/")
            candidate = BASE_DIR / rel
        if candidate.exists():
            return candidate
    if DEFAULT_LOGO_PATH.exists():
        return DEFAULT_LOGO_PATH
    return None


def resolve_signature_path(sig_path: Optional[str] = None) -> Optional[Path]:
    if not sig_path:
        return None
    candidate = Path(sig_path)
    if not candidate.is_absolute():
        candidate = BASE_DIR / sig_path.lstrip("/")
    return candidate if candidate.exists() else None


def _draw_official_seal(c: canvas.Canvas, cx: float, cy: float, radius: float = 28):
    c.saveState()
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.5)
    c.circle(cx, cy, radius, stroke=1, fill=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.0)
    c.circle(cx, cy, radius - 4, stroke=1, fill=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(cx, cy + 9, "AK TUITION")
    c.setFont("Helvetica-Bold", 5.5)
    c.drawCentredString(cx, cy, "OFFICIAL SEAL")
    c.setFillColor(ROYAL)
    c.setFont("Helvetica", 5)
    c.drawCentredString(cx, cy - 9, "VERIFIED PORTAL")
    c.restoreState()


def generate_marks_card_pdf(
    *,
    tuition_name: str,
    tagline: str,
    director_name: str,
    director_designation: str,
    logo_path: Optional[str],
    signature_path: Optional[str],
    academic_year: str,
    exam_name: str,
    exam_date: str,
    student_name: str,
    student_code: str,
    class_name: str,
    section: str,
    subjects: List[dict],
    total_max: float,
    total_obtained: float,
    percentage: float,
    overall_grade: str,
    result_status: str,
    teacher_remarks: str,
    class_rank: Optional[int] = None,
    class_total_students: Optional[int] = None,
) -> bytes:
    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)

    # White background
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Double decorative Navy & Gold border
    c.setStrokeColor(NAVY)
    c.setLineWidth(3.5)
    c.rect(14 * mm, 14 * mm, width - 28 * mm, height - 28 * mm, stroke=1, fill=0)

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    c.rect(17.5 * mm, 17.5 * mm, width - 35 * mm, height - 35 * mm, stroke=1, fill=0)

    # Corner accents
    for x0 in (14 * mm, width - 19 * mm):
        for y0 in (14 * mm, height - 19 * mm):
            c.setFillColor(GOLD)
            c.rect(x0, y0, 5 * mm, 5 * mm, fill=1, stroke=0)

    # Header band
    top_y = height - 24 * mm
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        # Preserve exact 1:1 circular aspect ratio without cropping/distorting
        c.drawImage(str(resolved_logo), 24 * mm, top_y - 24 * mm, width=26 * mm, height=26 * mm, mask="auto", preserveAspectRatio=True)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2 + 8 * mm, top_y - 5 * mm, tuition_name.upper())

    c.setFillColor(ROYAL)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(width / 2 + 8 * mm, top_y - 12 * mm, tagline)

    # Banner pill
    c.setFillColor(NAVY)
    c.roundRect(45 * mm, top_y - 25 * mm, width - 90 * mm, 9 * mm, 4, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, top_y - 21.8 * mm, "OFFICIAL EXAMINATION MARKS CARD")

    c.setFillColor(SLATE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, top_y - 32 * mm, f"Academic Year: {academic_year}   |   Examination: {exam_name}")

    # Divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(22 * mm, top_y - 36 * mm, width - 22 * mm, top_y - 36 * mm)

    # Student details box
    box_top = top_y - 41 * mm
    c.setFillColor(LIGHT_BLUE)
    c.setStrokeColor(ROYAL)
    c.setLineWidth(0.8)
    c.roundRect(22 * mm, box_top - 28 * mm, width - 44 * mm, 28 * mm, 4, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(26 * mm, box_top - 8 * mm, "Student Name:")
    c.drawString(26 * mm, box_top - 16 * mm, "Student ID:")
    c.drawString(26 * mm, box_top - 24 * mm, "Examination Date:")

    c.drawString(115 * mm, box_top - 8 * mm, "Class:")
    c.drawString(115 * mm, box_top - 16 * mm, "Section:")
    c.drawString(115 * mm, box_top - 24 * mm, "Publication:")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(58 * mm, box_top - 8 * mm, student_name)
    c.drawString(58 * mm, box_top - 16 * mm, student_code)
    c.drawString(58 * mm, box_top - 24 * mm, exam_date)

    c.drawString(140 * mm, box_top - 8 * mm, class_name)
    c.drawString(140 * mm, box_top - 16 * mm, section)
    c.setFillColor(colors.HexColor("#15803D"))
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(140 * mm, box_top - 24 * mm, "OFFICIAL PUBLISHED")

    # Subject Marks Table
    table_data = [["Sl. No.", "Subject", "Max Marks", "Marks Obtained", "Grade", "Remarks"]]
    for idx, row in enumerate(subjects, start=1):
        table_data.append([
            str(idx),
            row["subject"],
            f"{row['max_marks']:.0f}",
            f"{row['marks_obtained']:.1f}" if row["marks_obtained"] % 1 else f"{row['marks_obtained']:.0f}",
            row["grade"],
            row.get("remarks") or "-",
        ])

    tbl = Table(
        table_data,
        colWidths=[16 * mm, 52 * mm, 24 * mm, 28 * mm, 18 * mm, 28 * mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (4, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.6, ROYAL),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))

    table_y = box_top - 36 * mm
    tw, th = tbl.wrapOn(c, width - 44 * mm, 140 * mm)
    tbl.drawOn(c, 22 * mm, table_y - th)

    # Final Summary Box
    sum_top = table_y - th - 10 * mm
    c.setFillColor(GOLD_LIGHT)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.roundRect(22 * mm, sum_top - 32 * mm, width - 44 * mm, 32 * mm, 4, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(26 * mm, sum_top - 9 * mm, f"Total Maximum Marks: {total_max:.0f}")
    c.drawString(26 * mm, sum_top - 18 * mm, f"Total Marks Obtained: {total_obtained:.1f}")
    c.drawString(26 * mm, sum_top - 27 * mm, f"Teacher Remarks: {teacher_remarks[:65]}")

    c.drawString(115 * mm, sum_top - 9 * mm, f"Overall Percentage: {percentage:.2f}%")
    rank_text = f"#{class_rank} / {class_total_students}" if class_rank and class_total_students else "N/A"
    c.drawString(115 * mm, sum_top - 18 * mm, f"Overall Grade: {overall_grade}   |   Class Rank: {rank_text}")
    res_color = colors.HexColor("#15803D") if result_status == "PASS" else colors.HexColor("#B91C1C")
    c.setFillColor(res_color)
    c.drawString(115 * mm, sum_top - 27 * mm, f"Result Status: {result_status}")

    # Seal & Signature Footer
    footer_y = 32 * mm
    _draw_official_seal(c, 48 * mm, footer_y + 18 * mm, radius=13 * mm)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(24 * mm, footer_y - 4 * mm, f"Issued via AKTP PORTAL on {datetime.now().strftime('%d %b %Y')}")

    # Director signature block (never fabricate signature)
    sig_x = width - 78 * mm
    resolved_sig = resolve_signature_path(signature_path)
    if resolved_sig:
        c.drawImage(str(resolved_sig), sig_x + 5 * mm, footer_y + 13 * mm, width=42 * mm, height=16 * mm, mask="auto", preserveAspectRatio=True)
    else:
        c.setStrokeColor(MUTED)
        c.setDash(2, 2)
        c.line(sig_x, footer_y + 14 * mm, sig_x + 52 * mm, footer_y + 14 * mm)
        c.setDash()
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawCentredString(sig_x + 26 * mm, footer_y + 17 * mm, "Authorized Signature")

    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.line(sig_x, footer_y + 12 * mm, sig_x + 52 * mm, footer_y + 12 * mm)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(sig_x + 26 * mm, footer_y + 6 * mm, director_name)
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(sig_x + 26 * mm, footer_y + 1 * mm, director_designation)

    c.showPage()
    c.save()
    return buf.getvalue()


def generate_branded_table_pdf(
    *,
    title: str,
    subtitle: str,
    headers: List[str],
    rows: List[List[Any]],
    logo_path: Optional[str] = None,
    tuition_name: str = "AK TUITION",
    tagline: str = "Learn • Practise • Achieve",
    landscape_mode: bool = False,
    footer_note: str = "",
) -> bytes:
    buf = io.BytesIO()
    pagesize = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("AKTitle", parent=styles["Heading1"], textColor=NAVY, fontSize=16, spaceAfter=2, alignment=TA_LEFT)
    sub_style = ParagraphStyle("AKSub", parent=styles["Normal"], textColor=ROYAL, fontSize=9.5, spaceAfter=4, alignment=TA_LEFT)
    cell_style = ParagraphStyle("AKCell", parent=styles["Normal"], fontSize=8.5, leading=10.5, textColor=SLATE)
    hdr_style = ParagraphStyle("AKHdr", parent=styles["Normal"], fontSize=8.5, leading=10.5, textColor=colors.white, fontName="Helvetica-Bold")

    story = []
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        logo_img = RLImage(str(resolved_logo), width=18 * mm, height=18 * mm)
        header_tbl = Table(
            [[logo_img, [Paragraph(f"<b>{tuition_name}</b> — {tagline}", sub_style), Paragraph(title, title_style), Paragraph(subtitle, cell_style)]]],
            colWidths=[22 * mm, pagesize[0] - 54 * mm],
        )
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 1.5, GOLD),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(header_tbl)
    else:
        story.append(Paragraph(f"<b>{tuition_name}</b>", sub_style))
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(subtitle, cell_style))

    story.append(Spacer(1, 8 * mm))

    formatted_rows = [[Paragraph(str(h), hdr_style) for h in headers]]
    for r in rows:
        formatted_rows.append([Paragraph(str(val if val is not None else "-"), cell_style) for val in r])
    if len(formatted_rows) == 1:
        formatted_rows.append([Paragraph("No records found for selected filters.", cell_style)] + [Paragraph("", cell_style)] * (len(headers) - 1))

    avail_w = pagesize[0] - 32 * mm
    col_w = [avail_w / len(headers)] * len(headers)
    data_tbl = Table(formatted_rows, colWidths=col_w, repeatRows=1)
    data_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(data_tbl)

    if footer_note:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(footer_note, ParagraphStyle("AKFoot", parent=styles["Normal"], fontSize=8.5, textColor=MUTED)))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y %I:%M %p')} • AKTP PORTAL ({tuition_name})",
        ParagraphStyle("AKGen", parent=styles["Normal"], fontSize=8, textColor=MUTED, alignment=TA_RIGHT),
    ))

    doc.build(story)
    return buf.getvalue()


def generate_fee_receipt_pdf(
    *,
    tuition_name: str,
    tagline: str,
    address: str,
    phone: str,
    logo_path: Optional[str],
    receipt_number: str,
    payment_date: str,
    student_name: str,
    student_code: str,
    class_name: str,
    parent_name: str,
    payment_mode: str,
    reference_number: str,
    amount_paid: float,
    total_fees: float,
    total_paid_to_date: float,
    pending_amount: float,
    remarks: str,
) -> bytes:
    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(NAVY)
    c.setLineWidth(2.5)
    c.rect(18 * mm, height - 155 * mm, width - 36 * mm, 135 * mm, stroke=1, fill=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.rect(20 * mm, height - 153 * mm, width - 40 * mm, 131 * mm, stroke=1, fill=0)

    top_y = height - 26 * mm
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        c.drawImage(str(resolved_logo), 25 * mm, top_y - 20 * mm, width=20 * mm, height=20 * mm, mask="auto", preserveAspectRatio=True)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(50 * mm, top_y - 5 * mm, tuition_name)
    c.setFillColor(ROYAL)
    c.setFont("Helvetica", 9)
    c.drawString(50 * mm, top_y - 11 * mm, f"{tagline}  |  {phone}")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 8)
    c.drawString(50 * mm, top_y - 16 * mm, address)

    c.setFillColor(NAVY)
    c.roundRect(width - 72 * mm, top_y - 16 * mm, 46 * mm, 12 * mm, 3, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width - 49 * mm, top_y - 11.5 * mm, "OFFICIAL FEE RECEIPT")

    c.setStrokeColor(GOLD)
    c.line(24 * mm, top_y - 24 * mm, width - 24 * mm, top_y - 24 * mm)

    y = top_y - 34 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(26 * mm, y, f"Receipt No: {receipt_number}")
    c.drawRightString(width - 26 * mm, y, f"Payment Date: {payment_date}")

    y -= 10 * mm
    c.setFillColor(LIGHT_BLUE)
    c.roundRect(24 * mm, y - 24 * mm, width - 48 * mm, 26 * mm, 3, fill=1, stroke=0)
    c.setFillColor(SLATE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(28 * mm, y - 7 * mm, f"Student Name: {student_name} ({student_code})")
    c.drawString(28 * mm, y - 15 * mm, f"Class: {class_name}")
    c.drawString(28 * mm, y - 22 * mm, f"Parent / Guardian: {parent_name}")

    c.drawString(120 * mm, y - 7 * mm, f"Payment Mode: {payment_mode}")
    c.drawString(120 * mm, y - 15 * mm, f"Reference: {reference_number or 'N/A'}")
    c.drawString(120 * mm, y - 22 * mm, f"Remarks: {(remarks or '-')[:28]}")

    y -= 38 * mm
    summary_tbl = Table(
        [
            ["Total Annual Fee", "Amount Paid Now", "Total Paid To Date", "Pending Balance"],
            [f"Rs. {total_fees:,.2f}", f"Rs. {amount_paid:,.2f}", f"Rs. {total_paid_to_date:,.2f}", f"Rs. {pending_amount:,.2f}"],
        ],
        colWidths=[40 * mm, 40 * mm, 41 * mm, 41 * mm],
    )
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.7, ROYAL),
        ("BACKGROUND", (1, 1), (1, 1), GOLD_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    summary_tbl.wrapOn(c, width - 48 * mm, 30 * mm)
    summary_tbl.drawOn(c, 24 * mm, y - 14 * mm)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(26 * mm, height - 148 * mm, "System-generated receipt from AKTP PORTAL. Valid without physical stamp.")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 26 * mm, height - 148 * mm, "Authorized Signatory — AK Tuition")

    c.showPage()
    c.save()
    return buf.getvalue()


def generate_question_paper_pdf(
    *,
    tuition_name: str,
    logo_path: Optional[str],
    title: str,
    class_name: str,
    subject_name: str,
    duration_minutes: int,
    total_marks: float,
    instructions: str,
    evaluation_scheme: str,
    questions: List[dict],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    hdr_title = ParagraphStyle("QPHdr", parent=styles["Heading1"], textColor=NAVY, fontSize=15, alignment=TA_CENTER, spaceAfter=2)
    hdr_sub = ParagraphStyle("QPSub", parent=styles["Normal"], textColor=ROYAL, fontSize=10, alignment=TA_CENTER, spaceAfter=4)
    q_style = ParagraphStyle("QPQ", parent=styles["Normal"], textColor=colors.black, fontSize=10, leading=14, spaceAfter=4)
    opt_style = ParagraphStyle("QPOpt", parent=styles["Normal"], textColor=SLATE, fontSize=9.5, leftIndent=14, leading=13)
    sec_style = ParagraphStyle("QPSec", parent=styles["Heading3"], textColor=NAVY, fontSize=11, spaceBefore=8, spaceAfter=4)

    story = []
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        logo_img = RLImage(str(resolved_logo), width=18 * mm, height=18 * mm)
        top_tbl = Table([[logo_img, [Paragraph(tuition_name, hdr_title), Paragraph(title, hdr_sub)]]], colWidths=[22 * mm, 150 * mm])
        top_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 1.5, NAVY)]))
        story.append(top_tbl)
    else:
        story.append(Paragraph(tuition_name, hdr_title))
        story.append(Paragraph(title, hdr_sub))

    story.append(Spacer(1, 4 * mm))
    meta_tbl = Table(
        [[f"Class: {class_name}", f"Subject: {subject_name}", f"Duration: {duration_minutes} mins", f"Max Marks: {total_marks:.0f}"]],
        colWidths=[42 * mm, 48 * mm, 44 * mm, 40 * mm],
    )
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.8, ROYAL),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_tbl)

    if instructions:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(f"<b>General Instructions:</b> {instructions}", opt_style))
    if evaluation_scheme:
        story.append(Paragraph(f"<b>Evaluation Scheme:</b> {evaluation_scheme}", opt_style))

    type_labels = {
        "MCQ": "Multiple Choice Questions",
        "FILL_IN_BLANK": "Fill in the Blanks",
        "MATCH_FOLLOWING": "Match the Following",
        "ONE_MARK": "One-Mark Questions",
        "TWO_MARK": "Two-Mark Questions",
        "THREE_MARK": "Three-Mark Questions",
        "FOUR_MARK": "Four-Mark Questions",
        "FIVE_MARK": "Five-Mark Questions",
        "SIX_PLUS_MARK": "Six-Mark & Long Answer Questions",
    }

    current_type = None
    for idx, q in enumerate(questions, start=1):
        qt = q["question_type"]
        if qt != current_type:
            current_type = qt
            story.append(Paragraph(type_labels.get(qt, qt), sec_style))
        story.append(Paragraph(f"<b>Q{idx}.</b> {q['question_text']} <i>[{q['marks']:.0f} Mark(s)]</i>", q_style))
        if q.get("options"):
            for opt in q["options"]:
                story.append(Paragraph(f"({opt['option_label']}) {opt['option_text']}", opt_style))
        if q.get("match_pairs"):
            pair_rows = [["Column A", "Column B"]] + [[p.get("left", ""), p.get("right", "")] for p in q["match_pairs"]]
            ptbl = Table(pair_rows, colWidths=[70 * mm, 70 * mm])
            ptbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.5, SLATE),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(ptbl)
            story.append(Spacer(1, 2 * mm))

    doc.build(story)
    return buf.getvalue()
