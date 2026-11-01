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


def test_api_evaluate(client):
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
    assert data["fair_market_price"] > 0
    assert "platforms" in data
    assert "stockx" in data["platforms"]
    assert "vinted" in data["platforms"]
    assert "goat" in data["platforms"]
    assert "ebay" in data["platforms"]


def test_api_history(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
