import io
from typing import Any, List
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def generate_excel_report(title: str, headers: List[str], rows: List[List[Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "AKTP Report"

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(headers)))
    title_cell = ws.cell(row=1, column=1, value=f"AK TUITION (AKTP PORTAL) — {title}")
    title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="0A2463")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    header_fill = PatternFill("solid", fgColor="1E40AF")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=2, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    alt_fill = PatternFill("solid", fgColor="EFF6FF")
    for row_idx, row in enumerate(rows, start=3):
        for col_idx, val in enumerate(row, start=1):
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            if row_idx % 2 == 1:
                c.fill = alt_fill
            c.alignment = Alignment(vertical="center")

    for col_idx, col in enumerate(ws.columns, start=1):
        max_len = 0
        col_letter = get_column_letter(col_idx)
        for cell in col:
            if cell.row == 1:
                continue
            val = str(cell.value or "")
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 45)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
