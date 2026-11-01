"""
Inventory export to Excel (.xlsx) and PDF, laid out like the inventory page: one row per pair with
its photo, condition, what you paid, and current StockX bid, ask, last sale and net payout.
"""

import hashlib
import io
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CONDITION_LABELS = {
    "deadstock": "DS", "vnds": "Not DS", "used_like_new": "Used · like new",
    "used_good": "Used", "used_fair": "Used · fair", "used_beat": "Beat",
}
BOX_LABELS = {
    "original_good": "Original", "original_damaged": "Damaged", "replacement": "Not original", "no_box": "No box",
}
STATUS_LABELS = {"for_sale": "In stock", "sold": "Sold"}
FEE_NOTE = ("Net if sold now = highest StockX bid minus 9% transaction fee, 3% payment processing and $5 shipping. "
            "Shown only for DS pairs in their original box, since StockX accepts nothing else. "
            "Prices come from your last StockX sync of each pair.")

INK = "15171E"
MUTED = "6B7280"
ZEBRA = "F6F7F9"
POSITIVE = "047857"
NEGATIVE = "BE123C"


def _sorted_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same order as the inventory page: highest net payout first, then synced pairs."""
    return sorted(items, key=lambda i: (-(i["net_payout_now"] if i["net_payout_now"] is not None else -1), not i["synced"]))


def _short_date(value: Optional[str]) -> str:
    if not value:
        return ""
    return date.fromisoformat(value[:10]).strftime("%b %-d, %Y")


def _thumbnail(url: Optional[str], cache_dir: Path) -> Optional[Path]:
    """Downloads a product photo once, as a small PNG on white. Returns None if it can't be fetched."""
    if not url:
        return None
    path = cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".png")
    if path.exists():
        return path
    try:
        resp = httpx.get(url, timeout=8, follow_redirects=True)
        resp.raise_for_status()
        img = PILImage.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail((240, 170))
        canvas = PILImage.new("RGB", img.size, "white")
        canvas.paste(img, mask=img.split()[3])
        cache_dir.mkdir(parents=True, exist_ok=True)
        canvas.save(path, "PNG")
        return path
    except Exception:
        return None


def _rows(items: List[Dict[str, Any]], status: str) -> List[Dict[str, Any]]:
    rows = []
    for i in _sorted_items(items):
        sold = status == "sold"
        profit = (round(i["sold_price"] - i["purchase_price"], 2)
                  if sold and i.get("sold_price") is not None and i["purchase_price"] else i["profit_now"])
        rows.append({
            "item": i,
            "name": i["title"],
            "sku": i["sku"],
            "size": i["size"],
            "condition": CONDITION_LABELS.get(i["condition"], i["condition"]),
            "box": BOX_LABELS.get(i["box_condition"], i["box_condition"]),
            "paid": i["purchase_price"],
            "bid": i["highest_bid"],
            "ask": i["lowest_ask"],
            "last_sale": i["last_sale"],
            "last_sale_date": _short_date(i["last_sale_date"]),
            "net": i.get("sold_price") if sold else i["net_payout_now"],
            "profit": profit,
            "note": (i.get("sold_platform") or "") if sold else ("" if i["stockx_eligible"] else "Not accepted on StockX"),
        })
    return rows


def _columns(status: str):
    net_label = "Sold for" if status == "sold" else "Net if sold now"
    note_label = "Sold on" if status == "sold" else "Note"
    # key, header, width (Excel chars), is money
    return [
        ("photo", "", 12, False), ("name", "Sneaker", 40, False), ("sku", "Style code", 14, False),
        ("size", "Size", 11, False), ("condition", "Condition", 13, False), ("box", "Box", 12, False),
        ("paid", "Paid", 11, True), ("bid", "Highest bid", 12, True), ("ask", "Lowest ask", 12, True),
        ("last_sale", "Last sale", 11, True), ("last_sale_date", "Sale date", 13, False),
        ("net", net_label, 15, True), ("profit", "Profit", 11, True), ("note", note_label, 22, False),
    ]


# ---------------------------------------------------------------- Excel

def export_xlsx(valuation: Dict[str, Any], status: str, image_cache: Path) -> bytes:
    rows, totals, cols = _rows(valuation["items"], status), valuation["totals"], _columns(status)
    wb = Workbook()
    ws = wb.active
    ws.title = STATUS_LABELS[status]
    ws.sheet_view.showGridLines = False

    money = '"$"#,##0.00;[Red]-"$"#,##0.00;"–"'
    thin = Side(style="thin", color="E2E5EA")
    last_col = get_column_letter(len(cols))

    ws["A1"] = "mySNKRS Inventory"
    ws["A1"].font = Font(size=18, bold=True, color=INK)
    ws["A2"] = f"{STATUS_LABELS[status]} · {len(rows)} pairs · exported {date.today().strftime('%b %-d, %Y')}"
    ws["A2"].font = Font(size=10, color=MUTED)

    # Summary tiles
    summary = [
        ("Pairs", len(rows), None),
        ("Sold for" if status == "sold" else "Net if sold now", sum(r["net"] or 0 for r in rows), money),
        ("Paid", sum(r["paid"] or 0 for r in rows), money),
        ("Profit", sum(r["profit"] or 0 for r in rows if r["profit"] is not None), money),
    ]
    for n, (label, value, fmt) in enumerate(summary):
        col = 2 + n * 3
        ws.cell(row=4, column=col, value=label).font = Font(size=9, color=MUTED)
        cell = ws.cell(row=5, column=col, value=value)
        cell.font = Font(size=14, bold=True, color=INK)
        cell.alignment = Alignment(horizontal="left")
        if fmt:
            cell.number_format = money

    header_row = 7
    for c, (_, header, width, is_money) in enumerate(cols, start=1):
        cell = ws.cell(row=header_row, column=c, value=header)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=INK)
        cell.alignment = Alignment(horizontal="right" if is_money else "left", vertical="center", indent=0 if is_money else 1)
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[header_row].height = 24

    for n, r in enumerate(rows):
        row = header_row + 1 + n
        ws.row_dimensions[row].height = 46
        fill = PatternFill("solid", fgColor=ZEBRA) if n % 2 else None
        for c, (key, _, _, is_money) in enumerate(cols, start=1):
            cell = ws.cell(row=row, column=c, value=None if key == "photo" else r[key])
            cell.alignment = Alignment(vertical="center", horizontal="right" if is_money else "left",
                                       wrap_text=key == "name", indent=0 if is_money else 1)
            cell.border = Border(bottom=thin)
            cell.font = Font(size=10, color=INK, bold=key in ("name", "net"))
            if key in ("sku", "last_sale_date", "note"):
                cell.font = Font(size=9, color=MUTED)
            if is_money:
                cell.number_format = money
            if key == "profit" and r["profit"]:
                cell.font = Font(size=10, color=POSITIVE if r["profit"] > 0 else NEGATIVE)
            if fill:
                cell.fill = fill
        thumb = _thumbnail(r["item"].get("image_url"), image_cache)
        if thumb:
            img = XLImage(str(thumb))
            img.height, img.width = 52, round(52 * img.width / img.height)
            ws.add_image(img, f"A{row}")

    # Totals row with live formulas, so edits in Excel still add up
    first, last = header_row + 1, header_row + len(rows)
    total_row = last + 1
    ws.cell(row=total_row, column=2, value="Total").font = Font(bold=True, color=INK)
    for c, (key, _, _, _) in enumerate(cols, start=1):
        if key in ("paid", "net", "profit"):
            letter = get_column_letter(c)
            cell = ws.cell(row=total_row, column=c, value=f"=SUM({letter}{first}:{letter}{last})" if rows else 0)
            cell.number_format = money
            cell.font = Font(bold=True, color=INK)
            cell.alignment = Alignment(horizontal="right")
    for c in range(1, len(cols) + 1):
        ws.cell(row=total_row, column=c).border = Border(top=Side(style="medium", color=INK))
    ws.row_dimensions[total_row].height = 24

    note = ws.cell(row=total_row + 2, column=2, value=FEE_NOTE)
    note.font = Font(size=9, italic=True, color=MUTED)
    ws.merge_cells(start_row=total_row + 2, start_column=2, end_row=total_row + 2, end_column=len(cols))
    note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[total_row + 2].height = 30

    ws.freeze_panes = ws.cell(row=header_row + 1, column=3)
    if rows:
        ws.auto_filter.ref = f"B{header_row}:{last_col}{last}"
    ws.print_title_rows = f"{header_row}:{header_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ---------------------------------------------------------------- PDF

def _money(v: Optional[float]) -> str:
    if v is None:
        return "–"
    s = f"${abs(v):,.2f}".replace(".00", "")
    return f"-{s}" if v < 0 else s


def export_pdf(valuation: Dict[str, Any], status: str, image_cache: Path) -> bytes:
    rows = _rows(valuation["items"], status)
    ink, muted = colors.HexColor("#" + INK), colors.HexColor("#" + MUTED)

    name_style = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=ink)
    sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=7, leading=9, textColor=muted)
    cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10, textColor=ink)

    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(letter), leftMargin=0.45 * inch, rightMargin=0.45 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.6 * inch, title="mySNKRS Inventory")

    story = [
        Paragraph("mySNKRS Inventory", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=ink)),
        Paragraph(f"{STATUS_LABELS[status]} · {len(rows)} pairs · exported {date.today().strftime('%b %-d, %Y')}", sub_style),
        Spacer(1, 12),
    ]

    # Summary tiles
    net_total = sum(r["net"] or 0 for r in rows)
    paid_total = sum(r["paid"] or 0 for r in rows)
    profits = [r["profit"] for r in rows if r["profit"] is not None]
    tiles = [
        ("Pairs", str(len(rows))),
        ("Sold for" if status == "sold" else "Net if sold now on StockX", _money(net_total)),
        ("Paid", _money(paid_total) if paid_total else "–"),
        ("Profit", _money(sum(profits)) if profits else "–"),
    ]
    tile_cells = [[Paragraph(label, sub_style) for label, _ in tiles],
                  [Paragraph(value, ParagraphStyle("v", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=ink)) for _, value in tiles]]
    tile_table = Table(tile_cells, colWidths=[doc.width / 4] * 4)
    tile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#" + ZEBRA)),
        ("LINEAFTER", (0, 0), (-2, -1), 6, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
    ]))
    story += [tile_table, Spacer(1, 14)]

    # Main table: photo · sneaker (name + code) · size · condition · paid · bid · ask · last sale · net · profit
    headers = ["", "Sneaker", "Size", "Condition", "Paid", "Bid", "Ask", "Last sale",
               "Sold for" if status == "sold" else "Net now", "Profit"]
    widths = [0.75, 3.05, 0.95, 1.05, 0.6, 0.6, 0.6, 0.85, 0.75, 0.7]
    scale = doc.width / (sum(widths) * inch)
    widths = [w * inch * scale for w in widths]

    data = [headers]
    profit_colors = []
    for n, r in enumerate(rows, start=1):
        thumb = _thumbnail(r["item"].get("image_url"), image_cache)
        photo = ""
        if thumb:
            w, h = PILImage.open(thumb).size
            photo = RLImage(str(thumb), width=0.62 * inch, height=0.62 * inch * h / w)
        sneaker = [Paragraph(_escape(r["name"]), name_style), Paragraph(_escape(r["sku"]), sub_style)]
        condition = [Paragraph(r["condition"], cell_style)]
        if r["box"] != "Original":
            condition.append(Paragraph(f"{r['box']} box" if r["box"] != "No box" else "No box", sub_style))
        last = [Paragraph(_money(r["last_sale"]), ParagraphStyle("r", parent=cell_style, alignment=2))]
        if r["last_sale_date"]:
            last.append(Paragraph(r["last_sale_date"], ParagraphStyle("rs", parent=sub_style, alignment=2)))
        net = _money(r["net"]) if r["net"] is not None else ""
        if r["net"] is None and r["note"] and status != "sold":
            net = Paragraph("Not on StockX", ParagraphStyle("ns", parent=sub_style, alignment=2))
        data.append([photo, sneaker, r["size"], condition, _money(r["paid"]), _money(r["bid"]), _money(r["ask"]),
                     last, net, _money(r["profit"])])
        if r["profit"]:
            profit_colors.append(("TEXTCOLOR", (9, n), (9, n), colors.HexColor("#" + (POSITIVE if r["profit"] > 0 else NEGATIVE))))

    data.append(["", Paragraph("Total", name_style), "", "", _money(paid_total) if paid_total else "–", "", "", "",
                 _money(net_total), _money(sum(profits)) if profits else "–"])

    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), ink),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), ink),
        ("FONT", (8, 1), (8, -1), "Helvetica-Bold", 8.5),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#E2E5EA")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, ink),
        ("FONT", (4, -1), (-1, -1), "Helvetica-Bold", 9),
    ]
    style += [("BACKGROUND", (0, n), (-1, n), colors.HexColor("#" + ZEBRA)) for n in range(2, len(rows) + 1, 2)]
    table.setStyle(TableStyle(style + profit_colors))
    story += [table, Spacer(1, 10), Paragraph(FEE_NOTE, sub_style)]

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(muted)
        canvas.drawString(doc_.leftMargin, 0.35 * inch, "mySNKRS · prices from your StockX syncs")
        canvas.drawRightString(doc_.pagesize[0] - doc_.rightMargin, 0.35 * inch, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()


def _escape(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
