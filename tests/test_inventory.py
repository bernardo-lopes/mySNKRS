from pathlib import Path

from starlette.testclient import TestClient

from snkrs.web.app import app, storage

FIXTURE = (Path(__file__).parent / "fixtures" / "stockx_reverse_laney_w11_5.txt").read_text()
TITLE = "Jordan 1 Retro High OG Reverse Laney (Women's) - FD2596-700 - US"


def _client_with_laney_synced():
    client = TestClient(app)
    client.post("/api/stockx/sync", json={"text": FIXTURE, "title": TITLE})
    for item in storage.get_inventory():
        storage.delete_inventory_item(item["id"])
    return client


def _item(client, **match):
    items = client.get("/api/inventory").json()["items"]
    return next(i for i in items if all(i[k] == v for k, v in match.items()))


def test_ds_pair_is_priced_from_synced_stockx_data():
    client = _client_with_laney_synced()
    item_id = client.post("/api/inventory", json={"sku": "fd2596-700", "size": "US W 11.5", "purchase_price": 40}).json()["id"]

    i = _item(client, id=item_id)
    assert i["sku"] == "FD2596-700"
    assert i["title"] == "Jordan 1 Retro High OG Reverse Laney (Women's)"
    assert (i["synced"], i["stockx_eligible"]) == (True, True)
    assert (i["highest_bid"], i["lowest_ask"], i["last_sale"]) == (63, 102, 36)
    assert i["net_payout_now"] == 50.44
    assert i["profit_now"] == 10.44

    totals = client.get("/api/inventory").json()["totals"]
    assert (totals["pairs"], totals["priced"], totals["net_payout_now"], totals["profit_now"]) == (1, 1, 50.44, 10.44)


def test_used_or_reboxed_pairs_get_no_stockx_payout():
    client = _client_with_laney_synced()
    used = client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5", "condition": "used_good"}).json()["id"]
    reboxed = client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5", "box_condition": "replacement"}).json()["id"]
    for item_id in (used, reboxed):
        i = _item(client, id=item_id)
        assert i["stockx_eligible"] is False
        assert i["highest_bid"] == 63  # market reference is still shown
        assert i["net_payout_now"] is None


def test_unsynced_pair_has_no_prices():
    client = _client_with_laney_synced()
    item_id = client.post("/api/inventory", json={"sku": "EG7596", "size": "US 10", "model_name": "Yeezy Boost 700 Analog"}).json()["id"]
    i = _item(client, id=item_id)
    assert i["synced"] is False
    assert i["highest_bid"] is None and i["net_payout_now"] is None
    assert i["stockx_url"] == "https://stockx.com/search?s=EG7596"


def test_edit_sell_and_remove():
    client = _client_with_laney_synced()
    item_id = client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5"}).json()["id"]

    assert client.patch(f"/api/inventory/{item_id}", json={"purchase_price": 55.5}).status_code == 200
    assert _item(client, id=item_id)["purchase_price"] == 55.5

    assert client.patch(f"/api/inventory/{item_id}", json={"status": "sold", "sold_price": 90, "sold_platform": "StockX"}).status_code == 200
    assert client.get("/api/inventory").json()["items"] == []
    sold = client.get("/api/inventory", params={"status": "sold"}).json()["items"]
    assert (sold[0]["sold_price"], sold[0]["sold_platform"]) == (90, "StockX")

    assert client.patch(f"/api/inventory/{item_id}", json={"status": "gone"}).status_code == 422
    assert client.delete(f"/api/inventory/{item_id}").status_code == 200
    assert client.delete(f"/api/inventory/{item_id}").status_code == 404


def test_key_numbers_and_favorites():
    client = _client_with_laney_synced()
    fav = client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5"}).json()["id"]
    client.post("/api/inventory", json={"sku": "EG7596", "size": "US 10", "model_name": "Yeezy Boost 700 Analog"})

    i = _item(client, id=fav)
    assert i["favorite"] is False
    assert i["lowest_ask_net_payout"] == 84.76
    assert "avg_sale_6m" in i and "units_sold_6m" in i

    assert client.patch(f"/api/inventory/{fav}", json={"favorite": True}).status_code == 200
    favorites = client.get("/api/inventory", params={"favorites": "true"}).json()
    assert [i["id"] for i in favorites["items"]] == [fav] and favorites["items"][0]["favorite"] is True
    assert favorites["totals"]["pairs"] == 1
    assert len(client.get("/api/inventory").json()["items"]) == 2


def test_one_line_notes():
    from io import BytesIO
    from openpyxl import load_workbook

    client = _client_with_laney_synced()
    item_id = client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5", "notes": "Bought at\nFootpatrol "}).json()["id"]
    assert _item(client, id=item_id)["notes"] == "Bought at Footpatrol"

    assert client.patch(f"/api/inventory/{item_id}", json={"notes": "Small scuff on left toe"}).status_code == 200
    assert _item(client, id=item_id)["notes"] == "Small scuff on left toe"
    assert client.patch(f"/api/inventory/{item_id}", json={"notes": "x" * 141}).status_code == 422

    ws = load_workbook(BytesIO(client.get("/api/inventory/export.xlsx").content)).active
    headers = [c.value for c in ws[7]]
    assert ws.cell(row=8, column=headers.index("My note") + 1).value == "Small scuff on left toe"


def test_inventory_page_renders():
    r = TestClient(app).get("/inventory")
    assert r.status_code == 200 and "Inventory" in r.text


def test_export_excel_and_pdf():
    from io import BytesIO
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    client = _client_with_laney_synced()
    client.post("/api/inventory", json={"sku": "FD2596-700", "size": "US W 11.5", "purchase_price": 40})
    client.post("/api/inventory", json={"sku": "EG7596", "size": "US 10", "model_name": "Yeezy Boost 700 Analog"})

    r = client.get("/api/inventory/export.xlsx")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    ws = load_workbook(BytesIO(r.content)).active
    assert ws["A1"].value == "mySNKRS Inventory"
    headers = [ws.cell(row=7, column=c).value for c in range(1, ws.max_column + 1)]
    col = {h: get_column_letter(n) for n, h in enumerate(headers, start=1)}
    assert ws[f"{col['Sneaker']}8"].value == "Jordan 1 Retro High OG Reverse Laney (Women's)"
    assert (ws[f"{col['Net if sold now']}8"].value, ws[f"{col['Paid']}8"].value, ws[f"{col['Lowest ask']}8"].value) == (50.44, 40, 102)
    assert ws[f"{col['Net if sold now']}10"].value == f"=SUM({col['Net if sold now']}8:{col['Net if sold now']}9)"

    r = client.get("/api/inventory/export.pdf", params={"status": "sold"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert client.get("/api/inventory/export.csv").status_code == 422
