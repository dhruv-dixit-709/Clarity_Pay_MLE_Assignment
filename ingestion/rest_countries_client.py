from __future__ import annotations

import logging
import time

import requests

from ingestion.schemas import CountryEnrichment

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://restcountries.com/v3.1/name/{country}"


def fetch_country_payload(country: str, timeout_seconds: int = 10) -> list[dict]:
    response = requests.get(
        BASE_URL.format(country=country),
        params={"fields": "name,cca2,region,subregion"},
        headers={"User-Agent": "claritypay-underwriting-pipeline/1.0"},
        timeout=timeout_seconds,
    )
    if response.status_code == 429:
        LOGGER.warning("Rate limited by REST Countries for country=%s", country)
        time.sleep(1.5)
        response = requests.get(
            BASE_URL.format(country=country),
            params={"fields": "name,cca2,region,subregion"},
            headers={"User-Agent": "claritypay-underwriting-pipeline/1.0"},
            timeout=timeout_seconds,
        )
    response.raise_for_status()
    return response.json()


def parse_country_payload(payload: list[dict], requested_country: str) -> dict:
    if not payload:
        return {"country": requested_country}
    first = payload[0]
    return {
        "country": first.get("name", {}).get("common", requested_country),
        "alpha2_code": first.get("cca2"),
        "region": first.get("region"),
        "subregion": first.get("subregion"),
    }


def validate_country_payload(parsed: dict) -> CountryEnrichment:
    return CountryEnrichment.model_validate(parsed)


def enrich_country(country: str) -> CountryEnrichment:
    LOGGER.info("Country enrichment started for country=%s", country)
    try:
        payload = fetch_country_payload(country)
        parsed = parse_country_payload(payload, requested_country=country)
        validated = validate_country_payload(parsed)
        LOGGER.info("Country enrichment completed for country=%s", country)
        return validated
    except requests.RequestException as exc:
        LOGGER.exception("Country enrichment failed for country=%s", country)
        fallback = {"country": country, "alpha2_code": None, "region": None, "subregion": None}
        return validate_country_payload(fallback)
