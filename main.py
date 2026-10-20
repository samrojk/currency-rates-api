from fastapi import FastAPI, HTTPException, Query

import time
import requests
import xml.etree.ElementTree as ET

ECB_URL = (
    "https://www.ecb.europa.eu/stats/"
    "eurofxref/eurofxref-daily.xml"
)

CACHE_SECONDS = 8 * 60 * 60  # 8 hours

_cached_data = None
_cache_expires_at = 0.0

def fetch_rates():
    """Fetch the latest available reference rates from the ECB."""
    response = requests.get(ECB_URL, timeout=10)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    rates = {"EUR": 1.0}
    rate_date = None

    for element in root.iter():
        if not element.tag.endswith("Cube"):
            continue

        if "time" in element.attrib:
            rate_date = element.attrib["time"]

        currency = element.attrib.get("currency")
        rate = element.attrib.get("rate")

        if currency and rate:
            rates[currency] = float(rate)

    if not rate_date or "USD" not in rates:
        raise ValueError("Invalid or incomplete ECB response")

    # Convert EUR-based rates to USD-based rates.
    eur_to_usd = rates["USD"]

    usd_rates = {
        currency: round(rate / eur_to_usd, 6)
        for currency, rate in rates.items()
    }

    return {
        "source": "European Central Bank",
        "date": rate_date,
        "base": "USD",
        "rates": usd_rates,
    }


def get_rates():
    """Return cached rates or fetch fresh data when the cache expires."""
    global _cached_data, _cache_expires_at

    now = time.monotonic()

    if _cached_data is not None and now < _cache_expires_at:
        return _cached_data

    try:
        data = fetch_rates()
    except (
        requests.RequestException,
        ET.ParseError,
        ValueError,
    ) as exc:
        # If fetching fails, serve the last successful data if available.
        if _cached_data is not None:
            return _cached_data

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve exchange rates from the ECB.",
        ) from exc

    _cached_data = data
    _cache_expires_at = now + CACHE_SECONDS
    return _cached_data

app = FastAPI(
    title="Currency Rates API",
    description="USD-based reference rates from the European Central Bank.",
    version="1.0.0",
)


@app.get("/api/rates")
def get_exchange_rates():
    return get_rates()


@app.get("/api/convert")
def convert_currency(
    from_currency: str = Query(default="USD", min_length=3, max_length=3),
    to_currency: str = Query(default="INR", min_length=3, max_length=3),
    amount: float = Query(default=1.0, gt=0),
):
    data = get_rates()
    rates = data["rates"]

    source = from_currency.upper()
    target = to_currency.upper()

    if source not in rates:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source currency: {source}",
        )

    if target not in rates:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target currency: {target}",
        )

    rate = rates[target] / rates[source]

    return {
        "from": source,
        "to": target,
        "amount": amount,
        "rate": round(rate, 6),
        "converted_amount": round(amount * rate, 2),
        "date": data["date"],
        "source": data["source"],
    }

# get request for home page
@app.get("/")
def home():
    return {
        "message": "Currency Rates API",
        "docs": "/docs",
    }
