import pytest
from starlette.testclient import TestClient
from snkrs.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SNKRS" in response.text
    assert "StockX" in response.text
    assert "Vinted" in response.text
    assert "GOAT" in response.text


def test_api_popular(client):
    response = client.get("/api/popular")
    assert response.status_code == 200
    data = response.json()
    assert "DD1391-100" in data
    assert "DZ5485-612" in data


def test_api_evaluate(client, monkeypatch):
    # Marketplaces return nothing (as when a site blocks the app); stub their network lookups
    from snkrs.platforms.ebay import EbayMarketplace
    from snkrs.platforms.goat import GoatMarketplace
    from snkrs.platforms.vinted import VintedMarketplace

    async def nothing(*args, **kwargs):
        return None

    async def no_listings(*args, **kwargs):
        return []

    monkeypatch.setattr(GoatMarketplace, "_attempt_live_goat_search", nothing)
    monkeypatch.setattr(EbayMarketplace, "_scrape_ebay_sold", no_listings)
    monkeypatch.setattr(EbayMarketplace, "_scrape_ebay_active", no_listings)
    monkeypatch.setattr(VintedMarketplace, "_attempt_vinted_scrape", no_listings)

    payload = {
        "sku": "DD1391-100",
        "size": "EU 44",
        "condition": "deadstock",
        "box_condition": "original_good"
    }
    response = client.post("/api/evaluate", data=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "DD1391-100"
    # No live data from GOAT, eBay or Vinted in tests: nothing is made up
    for pid in ("goat", "ebay", "vinted"):
        p = data["platforms"][pid]
        assert (p["lowest_ask"], p["highest_bid"], p["last_sale_price"], p["estimated_net_payout"]) == (None, None, None, None)
    assert "platforms" in data
    assert "stockx" in data["platforms"]
    assert "vinted" in data["platforms"]
    assert "goat" in data["platforms"]
    assert "ebay" in data["platforms"]


def test_api_history(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
