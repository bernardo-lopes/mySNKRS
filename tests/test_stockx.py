from datetime import date

import pytest

from snkrs.platforms.stockx import StockXMarketplace
from snkrs.stockx_history import summarize_sales

TODAY = date(2026, 10, 31)
SALES = [
    {"date": "2026-10-25", "price": 36},
    {"date": "2026-10-23", "price": 36},
    {"date": "2026-10-21", "price": 89},
    {"date": "2026-10-14", "price": 89},
    {"date": "2026-10-02", "price": 90},
    {"date": "2026-09-07", "price": 94},
    {"date": "2025-01-10", "price": 140},
    {"date": "2023-01-01", "price": 300},  # older than 3 years
]


@pytest.mark.parametrize("price, expected", [(63, 50.44), (102, 84.76)])
def test_stockx_net_payout(price, expected):
    # 9% transaction + 3% processing + $5 shipping, as shown on StockX's payout breakdown
    assert StockXMarketplace().calculate_net_payout(price) == expected


def test_summarize_last_month():
    s = summarize_sales(SALES, "1m", TODAY)
    assert s["units_sold"] == 5
    assert s["avg_price"] == 68.0
    assert (s["low"], s["high"]) == (36, 90)
    assert [p["date"] for p in s["points"]][0] == "2026-10-02"


def test_summarize_ranges_exclude_older_sales():
    assert summarize_sales(SALES, "3m", TODAY)["units_sold"] == 6
    assert summarize_sales(SALES, "6m", TODAY)["units_sold"] == 6
    assert summarize_sales(SALES, "3y", TODAY)["units_sold"] == 7


def test_summarize_empty_period():
    s = summarize_sales([], "1m", TODAY)
    assert s["units_sold"] == 0 and s["avg_price"] is None


def test_summarize_rejects_unknown_range():
    with pytest.raises(ValueError):
        summarize_sales(SALES, "5y", TODAY)


# --- Parsing the real StockX Market Data > Sales panel (Reverse Laney, US W 11.5, captured Oct 31, 2026) ---

from pathlib import Path

from starlette.testclient import TestClient

from snkrs.stockx_sync import parse_stockx_page, size_key
from snkrs.web.app import app

FIXTURE = (Path(__file__).parent / "fixtures" / "stockx_reverse_laney_w11_5.txt").read_text()
TITLE = "Jordan 1 Retro High OG Reverse Laney (Women's) - FD2596-700 - US"


def test_parse_product_page():
    r = parse_stockx_page(FIXTURE, TITLE)
    assert r["sku"] == "FD2596-700"
    assert r["title"] == "Jordan 1 Retro High OG Reverse Laney (Women's)"
    assert (r["highest_bid"], r["lowest_ask"]) == (63, 102)
    assert r["retail_price"] == 180
    assert (r["model"], r["colorway"]) == ("Jordan 1 Retro High OG", "Reverse Laney (Women's)")
    assert size_key(r["size"]) == "W11.5"
    # 50 rows on the page, 2 with hidden prices ("--")
    assert len(r["sales"]) == 48
    assert r["sales"][0] == {"sold_at": "2026-10-25T03:51", "price": 36, "size": "US W 11.5"}
    assert r["sales"][-1] == {"sold_at": "2025-10-30T06:51", "price": 101, "size": "US W 11.5"}
    # Rows sharing one date header keep that date
    assert [s["sold_at"] for s in r["sales"] if s["sold_at"].startswith("2026-04-03")] == [
        "2026-04-03T23:29", "2026-04-03T17:45", "2026-04-03T09:41"]


@pytest.mark.parametrize("label, key", [
    ("US W 11.5", "W11.5"), ("US Women's 11.5", "W11.5"), ("11.5W", "W11.5"),
    ("US M 10", "M10"), ("10", "M10"), ("7Y", "Y7"), ("EU 44", None),
])
def test_size_key(label, key):
    assert size_key(label) == key


def test_sync_then_evaluate_and_history():
    client = TestClient(app)
    payload = {"text": FIXTURE, "title": TITLE, "url": "https://stockx.com/air-jordan-1-retro-high-og-reverse-laney-w"}
    first = client.post("/api/stockx/sync", json=payload).json()
    assert (first["sku"], first["sales_found"], first["highest_bid"]) == ("FD2596-700", 48, 63)
    # Syncing the same page again adds nothing
    assert client.post("/api/stockx/sync", json=payload).json()["sales_added"] == 0

    data = client.post("/api/evaluate", data={"sku": "FD2596-700", "size": "US W 11.5"}).json()
    sx = data["platforms"]["stockx"]
    assert sx["data_source"] == "browser_sync"
    assert (sx["highest_bid"], sx["lowest_ask"], sx["last_sale_price"]) == (63, 102, 36)
    assert sx["estimated_net_payout"] == 50.44
    assert sx["payout_breakdown"] == {"price": 63, "transaction_fee": 5.67, "processing_fee": 1.89, "shipping": 5.0, "payout": 50.44}
    assert sx["lowest_ask_net_payout"] == 84.76
    assert data["model_name"] == "Jordan 1 Retro High OG Reverse Laney (Women's)"
    assert data["retail_price"] == 180
    assert data["marketplace_links"]["stockx"]["url"] == "https://stockx.com/air-jordan-1-retro-high-og-reverse-laney-w?size=11.5W"

    h = client.get("/api/stockx/history", params={"sku": "FD2596-700", "size": "US W 11.5", "range": "3y"}).json()
    assert (h["units_sold"], h["sales_on_file"], h["oldest_sale"]) == (48, 48, "2025-10-30T06:51")
    assert client.get("/api/stockx/history", params={"sku": "FD2596-700", "size": "US W 11.5", "range": "5y"}).status_code == 422


def test_unsynced_size_has_no_made_up_prices():
    client = TestClient(app)
    sx = client.post("/api/evaluate", data={"sku": "DD1391-100", "size": "US 10"}).json()["platforms"]["stockx"]
    assert sx["data_source"] == "not_synced"
    assert sx["highest_bid"] is None and sx["lowest_ask"] is None and sx["estimated_net_payout"] is None


def test_sync_rejects_page_without_data():
    r = TestClient(app).post("/api/stockx/sync", json={"text": "hello", "title": TITLE})
    assert r.status_code == 400


def test_unisex_size_label_maps_to_mens_and_its_sales():
    from snkrs.stockx_sync import size_aliases, size_key
    assert size_key("US Men's 10 / Fits Women's 11") == "M10"
    assert size_aliases("US Men's 10 / Fits Women's 11") == ["M10", "W11"]
    assert size_key("US W 11") == "W11"
