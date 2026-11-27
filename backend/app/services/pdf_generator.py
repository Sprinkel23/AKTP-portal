import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
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
MAROON = colors.HexColor("#7C1D24")
CREAM = colors.HexColor("#FFFDF7")
EMERALD = colors.HexColor("#15803D")
GOLD = colors.HexColor("#D4AF37")
GOLD_LIGHT = colors.HexColor("#FEF9E7")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")

_ONES = [
    "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
    "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
    "SEVENTEEN", "EIGHTEEN", "NINETEEN",
]
_TENS = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]


def _int_to_words(n: int) -> str:
    if n < 20:
        return _ONES[max(0, n)]
    if n < 100:
        return _TENS[n // 10] + (f" {_ONES[n % 10]}" if n % 10 else "")
    if n < 1000:
        return f"{_ONES[n // 100]} HUNDRED" + (f" {_int_to_words(n % 100)}" if n % 100 else "")
    if n < 100000:
        return f"{_int_to_words(n // 1000)} THOUSAND" + (f" {_int_to_words(n % 1000)}" if n % 1000 else "")
    return str(n)


def number_to_words(val: float) -> str:
    whole = int(val)
    frac = round(val - whole, 2)
    text = _int_to_words(whole)
    if frac >= 0.05:
        text += f" POINT {_ONES[int(round(frac * 10))] if int(round(frac * 10)) < 10 else int(round(frac * 100))}"
    return text


def result_division(percentage: float, any_fail: bool = False) -> str:
    if any_fail or percentage < 35:
        return "FAIL"
    if percentage >= 85:
        return "DISTINCTION"
    if percentage >= 60:
        return "FIRST CLASS"
    if percentage >= 50:
        return "SECOND CLASS"
    return "PASS CLASS"


def _doc_signature_hash(seed_str: str) -> str:
    return "AKTP-DSIG-" + hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:10].upper()


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
    examination_id: Optional[int] = None,
) -> bytes:
    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)

    # Parchment sheet background
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Double official Navy & Maroon/Gold border
    c.setStrokeColor(NAVY)
    c.setLineWidth(3.5)
    c.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm, stroke=1, fill=0)

    c.setStrokeColor(MAROON)
    c.setLineWidth(1.4)
    c.rect(15.5 * mm, 15.5 * mm, width - 31 * mm, height - 31 * mm, stroke=1, fill=0)

    # Corner accents
    for x0 in (12 * mm, width - 17 * mm):
        for y0 in (12 * mm, height - 17 * mm):
            c.setFillColor(GOLD)
            c.rect(x0, y0, 5 * mm, 5 * mm, fill=1, stroke=0)

    # Subtle diagonal institutional security watermark
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(34)
    c.setFillColor(colors.HexColor("#EEF2FF"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(0, 12, "AK TUITION • VERIFIED")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(0, -16, "OFFICIAL STATEMENT OF MARKS")
    c.restoreState()

    # Header band
    top_y = height - 22 * mm
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        c.drawImage(str(resolved_logo), 22 * mm, top_y - 24 * mm, width=24 * mm, height=24 * mm, mask="auto", preserveAspectRatio=True)

    c.setFillColor(MAROON)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(width / 2 + 8 * mm, top_y - 1 * mm, "DEPARTMENT OF ACADEMIC EXAMINATIONS • OFFICIAL RECORD")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 21)
    c.drawCentredString(width / 2 + 8 * mm, top_y - 8.5 * mm, tuition_name.upper())

    c.setFillColor(ROYAL)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2 + 8 * mm, top_y - 14.5 * mm, f"{tagline}  |  Director: {director_name}")

    # Banner pill
    c.setFillColor(NAVY)
    c.roundRect(42 * mm, top_y - 25.5 * mm, width - 84 * mm, 8.5 * mm, 3, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(width / 2, top_y - 22.3 * mm, "PROVISIONAL STATEMENT OF MARKS")

    sig_cert_id = _doc_signature_hash(f"{student_code}|{examination_id}|{total_obtained}|{percentage}")
    c.setFillColor(SLATE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, top_y - 31.5 * mm, f"Academic Year: {academic_year}   |   Examination: {exam_name}   |   Cert No: {sig_cert_id}")

    # Divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(20 * mm, top_y - 35 * mm, width - 20 * mm, top_y - 35 * mm)

    # Candidate Details Box
    box_top = top_y - 39 * mm
    c.setFillColor(colors.white)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.9)
    c.roundRect(20 * mm, box_top - 26 * mm, width - 40 * mm, 26 * mm, 3, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(24 * mm, box_top - 7.5 * mm, "Candidate Name:")
    c.drawString(24 * mm, box_top - 15 * mm, "Register No. (AK ID):")
    c.drawString(24 * mm, box_top - 22.5 * mm, "Exam Date:")

    c.drawString(114 * mm, box_top - 7.5 * mm, "Class / Batch:")
    c.drawString(114 * mm, box_top - 15 * mm, "Section:")
    c.drawString(114 * mm, box_top - 22.5 * mm, "Verification:")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(62 * mm, box_top - 7.5 * mm, student_name.upper())
    c.drawString(62 * mm, box_top - 15 * mm, f"{student_code}{section or ''}")
    c.setFont("Helvetica", 9)
    c.drawString(62 * mm, box_top - 22.5 * mm, exam_date)

    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(144 * mm, box_top - 7.5 * mm, class_name)
    c.drawString(144 * mm, box_top - 15 * mm, section)
    c.setFillColor(EMERALD)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(144 * mm, box_top - 22.5 * mm, "DIGITALLY VERIFIED")

    # Subject Marks Table (with Min Marks, Marks in Words, Subject Result)
    table_data = [["Sl.", "Subject", "Max", "Min", "Obtained", "Marks in Words", "Result", "Grade"]]
    any_fail = False
    for idx, row in enumerate(subjects, start=1):
        max_m = float(row["max_marks"])
        obt_m = float(row["marks_obtained"])
        min_m = round(max_m * 0.35)
        sub_pass = obt_m >= min_m
        if not sub_pass:
            any_fail = True
        table_data.append([
            str(idx),
            row["subject"],
            f"{max_m:.0f}",
            f"{min_m}",
            f"{obt_m:.1f}" if obt_m % 1 else f"{obt_m:.0f}",
            number_to_words(obt_m),
            "PASS" if sub_pass else "FAIL",
            row["grade"],
        ])

    tbl = Table(
        table_data,
        colWidths=[10 * mm, 38 * mm, 13 * mm, 13 * mm, 18 * mm, 46 * mm, 16 * mm, 16 * mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (4, -1), "CENTER"),
        ("ALIGN", (6, 1), (7, -1), "CENTER"),
        ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold"),
        ("FONTNAME", (6, 1), (7, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.6, NAVY),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))

    table_y = box_top - 32 * mm
    tw, th = tbl.wrapOn(c, width - 40 * mm, 135 * mm)
    tbl.drawOn(c, 20 * mm, table_y - th)

    # Grand Total & Classification Summary Box
    res_class = result_division(percentage, any_fail)
    sum_top = table_y - th - 8 * mm
    c.setFillColor(GOLD_LIGHT)
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.2)
    c.roundRect(20 * mm, sum_top - 35 * mm, width - 40 * mm, 35 * mm, 3, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(24 * mm, sum_top - 8.5 * mm, f"Total Max Marks: {total_max:.0f}")
    c.drawString(24 * mm, sum_top - 16.5 * mm, f"Grand Total Obtained: {total_obtained:g} ({number_to_words(total_obtained)})")
    c.drawString(24 * mm, sum_top - 24.5 * mm, f"Remarks: {teacher_remarks[:60]}")
    c.setFont("Helvetica", 8)
    c.setFillColor(SLATE)
    c.drawString(24 * mm, sum_top - 31.5 * mm, f"Verified Record ID: {sig_cert_id}")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(124 * mm, sum_top - 8.5 * mm, f"Percentage: {percentage:.2f}%")
    rank_text = f"#{class_rank} / {class_total_students}" if class_rank and class_total_students else "N/A"
    c.drawString(124 * mm, sum_top - 16.5 * mm, f"Grade: {overall_grade}  |  Rank: {rank_text}")
    res_color = EMERALD if res_class != "FAIL" else colors.HexColor("#B91C1C")
    c.setFillColor(res_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(124 * mm, sum_top - 25.5 * mm, f"RESULT: {res_class}")

    # Seal, Scannable QR Code & Digital Signature Footer
    footer_y = 29 * mm
    _draw_official_seal(c, 42 * mm, footer_y + 18 * mm, radius=13 * mm)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(22 * mm, footer_y - 4 * mm, f"Issued via AKTP PORTAL on {datetime.now().strftime('%d %b %Y')}")

    # Scannable Verification QR Code (center footer)
    qr_url = f"https://aktp-portal.netlify.app/results?code={student_code}&exam={examination_id or ''}"
    qr_widget = QrCodeWidget(qr_url)
    bounds = qr_widget.getBounds()
    qr_size = 22 * mm
    qr_w = bounds[2] - bounds[0]
    qr_h = bounds[3] - bounds[1]
    d = Drawing(qr_size, qr_size, transform=[qr_size / qr_w, 0, 0, qr_size / qr_h, 0, 0])
    d.add(qr_widget)
    qr_x = (width - qr_size) / 2
    qr_y = footer_y + 5 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm, 3, fill=0, stroke=1)
    renderPDF.draw(d, c, qr_x, qr_y)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(width / 2, footer_y - 0.5 * mm, "SCAN QR TO VERIFY RESULT")

    # Digitally Signed & Verified Block by G. Akash, B.E.
    sig_x = width - 80 * mm
    c.setFillColor(colors.HexColor("#F0FDF4"))
    c.setStrokeColor(EMERALD)
    c.setLineWidth(0.8)
    c.roundRect(sig_x - 2 * mm, footer_y + 1 * mm, 58 * mm, 31 * mm, 3, fill=1, stroke=1)

    resolved_sig = resolve_signature_path(signature_path)
    if resolved_sig:
        c.drawImage(str(resolved_sig), sig_x + 7 * mm, footer_y + 15.5 * mm, width=40 * mm, height=13 * mm, mask="auto", preserveAspectRatio=True)
    else:
        c.setFillColor(EMERALD)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(sig_x + 27 * mm, footer_y + 27.5 * mm, "DIGITALLY SIGNED & VERIFIED")
        c.setFillColor(NAVY)
        c.setFont("Times-BoldItalic", 12)
        c.drawCentredString(sig_x + 27 * mm, footer_y + 19.5 * mm, director_name)
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 6.2)
        c.drawCentredString(sig_x + 27 * mm, footer_y + 15 * mm, f"Ref: {sig_cert_id}")

    c.setStrokeColor(NAVY)
    c.setLineWidth(0.7)
    c.line(sig_x + 2 * mm, footer_y + 12.5 * mm, sig_x + 52 * mm, footer_y + 12.5 * mm)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(sig_x + 27 * mm, footer_y + 7.5 * mm, director_name)
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 7.8)
    c.drawCentredString(sig_x + 27 * mm, footer_y + 3 * mm, director_designation)

    c.showPage()
    c.save()
    return buf.getvalue()


def _build_digital_sig_flowable(
    styles,
    *,
    title: str,
    director_name: str,
    director_designation: str,
    signature_path: Optional[str],
    avail_w: float,
):
    cert = _doc_signature_hash(f"{title}|{director_name}|{datetime.now().strftime('%Y%m%d%H')}")
    left_p = Paragraph(
        f"<b>Digitally Signed &amp; Verified Document</b><br/>"
        f"Certificate Ref: <font color='#15803D'><b>{cert}</b></font><br/>"
        f"Issued via AKTP Official Academic System on {datetime.now().strftime('%d %b %Y %I:%M %p')}",
        ParagraphStyle("AKSigLeft", parent=styles["Normal"], fontSize=8, leading=11, textColor=SLATE),
    )
    resolved_sig = resolve_signature_path(signature_path)
    sig_parts = [
        Paragraph(
            "<font color='#15803D'><b>✓ DIGITALLY SIGNED &amp; VERIFIED</b></font>",
            ParagraphStyle("AKSigBadge", parent=styles["Normal"], fontSize=7.5, alignment=TA_CENTER),
        )
    ]
    if resolved_sig:
        sig_parts.append(RLImage(str(resolved_sig), width=32 * mm, height=11 * mm))
    else:
        sig_parts.append(
            Paragraph(
                f"<i><b>{director_name}</b></i>",
                ParagraphStyle("AKSigName", parent=styles["Normal"], fontSize=11, textColor=NAVY, alignment=TA_CENTER),
            )
        )
    sig_parts.append(
        Paragraph(
            f"<b>{director_name}</b><br/>{director_designation}",
            ParagraphStyle("AKSigDes", parent=styles["Normal"], fontSize=8, leading=10, textColor=NAVY, alignment=TA_CENTER),
        )
    )
    sig_tbl = Table([[left_p, sig_parts]], colWidths=[avail_w - 64 * mm, 64 * mm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (1, 0), (1, 0), 0.9, EMERALD),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F0FDF4")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return sig_tbl


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
    director_name: str = "G. Akash, B.E.",
    director_designation: str = "Director, AK Tuition",
    signature_path: Optional[str] = None,
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

    story.append(Spacer(1, 8 * mm))
    story.append(
        _build_digital_sig_flowable(
            styles,
            title=title,
            director_name=director_name,
            director_designation=director_designation,
            signature_path=signature_path,
            avail_w=avail_w,
        )
    )

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


def generate_salary_slip_pdf(
    *,
    tuition_name: str,
    tagline: str,
    address: str,
    phone: str,
    logo_path: Optional[str],
    slip_number: str,
    month_label: str,
    paid_date: str,
    teacher_name: str,
    teacher_code: str,
    bank_account_holder: str,
    bank_name: str,
    bank_account_number: str,
    bank_ifsc: str,
    upi_id: str,
    base_salary: float,
    bonus: float,
    deductions: float,
    net_amount: float,
    payment_mode: str,
    transaction_reference: str,
    remarks: str,
    director_name: str = "G. Akash, B.E.",
    director_designation: str = "Director, AK Tuition",
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.rect(18 * mm, height - 165 * mm, width - 36 * mm, 145 * mm)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.rect(20 * mm, height - 163 * mm, width - 40 * mm, 141 * mm)

    top_y = height - 32 * mm
    resolved_logo = resolve_logo_path(logo_path)
    if resolved_logo:
        c.drawImage(str(resolved_logo), 24 * mm, top_y - 16 * mm, width=20 * mm, height=20 * mm, mask="auto", preserveAspectRatio=True)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(48 * mm, top_y - 5 * mm, tuition_name)
    c.setFillColor(ROYAL)
    c.setFont("Helvetica", 9)
    c.drawString(48 * mm, top_y - 11 * mm, f"{tagline}  |  {phone}")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 8)
    c.drawString(48 * mm, top_y - 16 * mm, address)

    c.setFillColor(NAVY)
    c.roundRect(width - 76 * mm, top_y - 16 * mm, 50 * mm, 12 * mm, 2, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(width - 51 * mm, top_y - 11.5 * mm, "FACULTY SALARY SLIP")

    c.setStrokeColor(GOLD)
    c.line(24 * mm, top_y - 24 * mm, width - 24 * mm, top_y - 24 * mm)

    y = top_y - 33 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(26 * mm, y, f"Slip No: {slip_number}   |   Month: {month_label}")
    c.drawRightString(width - 26 * mm, y, f"Paid Date: {paid_date}")

    y -= 9 * mm
    c.setFillColor(LIGHT_BLUE)
    c.roundRect(24 * mm, y - 26 * mm, width - 48 * mm, 28 * mm, 2, fill=1, stroke=0)
    c.setFillColor(SLATE)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(28 * mm, y - 7 * mm, f"Faculty Name: {teacher_name} ({teacher_code})")
    c.drawString(28 * mm, y - 14 * mm, f"Bank / Holder: {bank_name or '-'} / {bank_account_holder or teacher_name}")
    c.drawString(28 * mm, y - 21 * mm, f"Account / IFSC: {bank_account_number or '-'} ({bank_ifsc or '-'})")

    c.drawString(120 * mm, y - 7 * mm, f"Payment Mode: {payment_mode}")
    c.drawString(120 * mm, y - 14 * mm, f"UPI ID: {upi_id or '-'}")
    c.drawString(120 * mm, y - 21 * mm, f"UTR / Ref: {(transaction_reference or 'PORTAL-VERIFIED')[:24]}")

    y -= 42 * mm
    summary_tbl = Table(
        [
            ["Base Salary", "Bonus / Allowance", "Deductions", "Net Salary Paid"],
            [f"Rs. {base_salary:,.2f}", f"Rs. {bonus:,.2f}", f"Rs. {deductions:,.2f}", f"Rs. {net_amount:,.2f}"],
        ],
        colWidths=[40 * mm, 41 * mm, 39 * mm, 42 * mm],
    )
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.7, ROYAL),
        ("BACKGROUND", (3, 1), (3, 1), GOLD_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    summary_tbl.wrapOn(c, width - 48 * mm, 30 * mm)
    summary_tbl.drawOn(c, 24 * mm, y - 14 * mm)

    if remarks:
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 8)
        c.drawString(26 * mm, y - 24 * mm, f"Remarks: {remarks[:95]}")

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(26 * mm, height - 157 * mm, "Digitally issued & verified salary slip from AKTP PORTAL.")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 26 * mm, height - 157 * mm, f"{director_name} — {director_designation}")

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
    director_name: str = "G. Akash, B.E.",
    director_designation: str = "Director, AK Tuition",
    signature_path: Optional[str] = None,
    watermark_text: Optional[str] = None,
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

    story.append(Spacer(1, 8 * mm))
    story.append(
        _build_digital_sig_flowable(
            styles,
            title=title,
            director_name=director_name,
            director_designation=director_designation,
            signature_path=signature_path,
            avail_w=A4[0] - 36 * mm,
        )
    )

    wm_label = (watermark_text or "").strip()

    def _draw_qp_watermark(canvas_obj, _doc):
        if not wm_label:
            return
        canvas_obj.saveState()
        canvas_obj.setFillColor(colors.HexColor("#E2E8F0"))
        try:
            canvas_obj.setFillAlpha(0.32)
        except Exception:
            pass
        canvas_obj.translate(A4[0] / 2.0, A4[1] / 2.0)
        canvas_obj.rotate(38)
        fsize = 44 if len(wm_label) <= 18 else 32
        canvas_obj.setFont("Helvetica-Bold", fsize)
        canvas_obj.drawCentredString(0, 0, wm_label.upper())
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_draw_qp_watermark, onLaterPages=_draw_qp_watermark)
    return buf.getvalue()
