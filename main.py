from fastapi import FastAPI

import requests
import xml.etree.ElementTree as ET

ECB_URL = (
    "https://www.ecb.europa.eu/stats/"
    "eurofxref/eurofxref-daily.xml"
)

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


app = FastAPI(
    title="Currency Rates API",
    description="USD-based reference rates from the European Central Bank.",
    version="1.0.0",
)

@app.get("/api/rates")
def get_exchange_rates():
    return fetch_rates()

@app.get("/")
def home():
    return {
        "message": "Currency Rates API",
        "docs": "/docs",
    }
