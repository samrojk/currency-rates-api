from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def fake_rates():
    return {
        "source": "European Central Bank",
        "date": "2026-10-20",
        "base": "USD",
        "rates": {
            "USD": 1.0,
            "INR": 90.0,
            "EUR": 0.9,
        },
    }

def setup_function():
    main._cached_data = None
    main._cache_expires_at = 0.0


def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_rates(monkeypatch):
    monkeypatch.setattr(main, "fetch_rates", fake_rates)

    response = client.get("/api/rates")

    assert response.status_code == 200
    assert response.json()["base"] == "USD"
    assert response.json()["rates"]["USD"] == 1.0

def test_convert_usd_to_inr(monkeypatch):
    monkeypatch.setattr(main, "fetch_rates", fake_rates)

    response = client.get(
        "/api/convert",
        params={
            "from_currency": "USD",
            "to_currency": "INR",
            "amount": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["converted_amount"] == 900.0

def test_invalid_currency(monkeypatch):
    monkeypatch.setattr(main, "fetch_rates", fake_rates)

    response = client.get(
        "/api/convert",
        params={
            "from_currency": "XXX",
            "to_currency": "INR",
        },
    )

    assert response.status_code == 400

def test_invalid_amount():
    response = client.get(
        "/api/convert",
        params={
            "from_currency": "USD",
            "to_currency": "INR",
            "amount": 0,
        },
    )

    assert response.status_code == 422
