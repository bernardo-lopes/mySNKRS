"""
Parses StockX product page text (bid, ask, and the Market Data > Sales list) into structured data.

The text comes from the SNKRS sync bookmark (document.body.innerText of the StockX page in your
own browser) or from a manual copy/paste of the page or of the seller sales table.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

_PRICE = r"\$\s?([\d,]+(?:\.\d+)?)"

# Product page Sales panel: "10/25/26" date header, then rows of "$36 / New / US W 11.5 / 3:51 AM".
# Rows sold on the same day share one date header. Hidden prices show as "--".
_DATE_HEADER = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
_ROW_PRICE = re.compile(r"^(?:" + _PRICE + r"|--)$")
_ROW_TIME = re.compile(r"^(\d{1,2}):(\d{2})\s?([AP]M)$")

# Seller sell-page table: "Oct 25, 2026  03:51 AM  11.5W  $36" (tabs or newlines between cells)
_SELLER_ROW = re.compile(
    r"([A-Z][a-z]{2} \d{1,2}, \d{4})\s+(\d{1,2}:\d{2}\s?[AP]M)\s+([\w .']+?)\s+" + _PRICE
)

_BID_PATTERNS = [r"Sell Now for\s*" + _PRICE, r"Highest Bid\s*" + _PRICE, _PRICE + r"\s*Sell Now"]
_ASK_PATTERNS = [r"Buy Now for\s*" + _PRICE, r"Standard Lowest Ask\s*" + _PRICE, r"Lowest Ask\s*" + _PRICE]


def size_key(label: str) -> Optional[str]:
    """Normalizes StockX size labels ("US W 11.5", "US Women's 11.5", "11.5W", "US M 10", "10") to "W11.5" / "M10"."""
    raw = label.strip().upper().replace("’", "'")
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return None
    num = m.group(1).rstrip("0").rstrip(".") if "." in m.group(1) else m.group(1)
    if "EU" in raw or "UK" in raw or "CM" in raw or "KR" in raw:
        return None
    if re.match(r"^US\s?(?:M\b|MEN'?S)", raw):  # unisex: "US Men's 10 / Fits Women's 11"
        return "M" + num
    women = bool(re.search(r"US\s?W\b|WOMEN|\d(?:\.\d+)?\s?W\b", raw))
    youth = bool(re.search(r"\d(?:\.\d+)?\s?Y\b|US\s?Y\b|GS\b", raw))
    return ("W" if women else "Y" if youth else "M") + num


def size_aliases(label: str) -> List[str]:
    """Every size key a label covers. Unisex pairs read "US Men's 10 / Fits Women's 11", and StockX
    lists their sales under the women's size, so both "M10" and "W11" mean the same pair."""
    keys = [size_key(part) for part in label.split("/")]
    return [k for k in keys if k]


def _money(s: str) -> float:
    return float(s.replace(",", ""))


def _first(patterns: List[str], text: str) -> Optional[float]:
    for p in patterns:
        m = re.search(p, text)
        if m:
            return _money(m.group(1))
    return None


def _parse_sales_panel(lines: List[str]) -> List[Dict[str, Any]]:
    sales = []
    day: Optional[datetime] = None
    i = 0
    while i < len(lines):
        d = _DATE_HEADER.match(lines[i])
        if d:
            day = datetime(2000 + int(d.group(3)), int(d.group(1)), int(d.group(2)))
            i += 1
            continue
        p = _ROW_PRICE.match(lines[i])
        if p and day and i + 3 < len(lines):
            size_label, t = lines[i + 2], _ROW_TIME.match(lines[i + 3])
            if t:
                hour = int(t.group(1)) % 12 + (12 if t.group(3) == "PM" else 0)
                if p.group(1):  # "--" means StockX hides the price; skip it
                    sales.append({
                        "sold_at": day.replace(hour=hour, minute=int(t.group(2))).strftime("%Y-%m-%dT%H:%M"),
                        "price": _money(p.group(1)),
                        "size": size_label,
                    })
                i += 4
                continue
        i += 1
    return sales


def _parse_seller_table(text: str) -> List[Dict[str, Any]]:
    sales = []
    for date_s, time_s, size_label, price in _SELLER_ROW.findall(text):
        sold = datetime.strptime(f"{date_s} {time_s.replace(' ', '')}", "%b %d, %Y %I:%M%p")
        sales.append({"sold_at": sold.strftime("%Y-%m-%dT%H:%M"), "price": _money(price), "size": size_label.strip()})
    return sales


def parse_stockx_page(text: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Extracts SKU, product title, size, highest bid, lowest ask and sales from StockX page text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    sales = _parse_sales_panel(lines) or _parse_seller_table(text)

    sku, product_title = None, None
    if title:
        # Page title looks like "Jordan 1 Retro High OG Reverse Laney (Women's) - FD2596-700 - US"
        m = re.match(r"^(.*?) - ([A-Z0-9][A-Z0-9-]{3,}) - [A-Z]{2}$", title.strip())
        if m:
            product_title, sku = m.group(1), m.group(2)
    if not sku:
        m = re.search(r"Style\s*\n?\s*([A-Z0-9][A-Z0-9-]{3,})", text)
        sku = m.group(1) if m else None

    # Bid/ask belong to the size picked on the page ("Size: US Women's 11.5")
    m = re.search(r"Size:\s*\n?\s*([^\n]+)", text)
    page_size = m.group(1).strip() if m else (sales[0]["size"] if sales else None)

    return {
        "sku": sku,
        "title": product_title,
        "size": page_size,
        "highest_bid": _first(_BID_PATTERNS, text),
        "lowest_ask": _first(_ASK_PATTERNS, text),
        "sales": sales,
    }
