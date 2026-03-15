from __future__ import annotations

import json
import logging
from pathlib import Path

import requests
from jsonschema import validate

from ingestion.schemas import SimulatedApiResponse

LOGGER = logging.getLogger(__name__)
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "data" / "simulated_api_contract.json"


def fetch_simulated_api_payload(base_url: str, merchant_id: str, timeout_seconds: int = 10) -> dict:
    response = requests.get(
        f"{base_url.rstrip('/')}/internal-risk/{merchant_id}",
        headers={"User-Agent": "claritypay-underwriting-pipeline/1.0"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def parse_simulated_api_payload(payload: dict) -> dict:
    return payload


def validate_simulated_api_payload(parsed_payload: dict) -> SimulatedApiResponse:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    validate(instance=parsed_payload, schema=schema)
    return SimulatedApiResponse.model_validate(parsed_payload)


def get_internal_risk_data(base_url: str, merchant_id: str) -> SimulatedApiResponse:
    LOGGER.info("Simulated API call started for merchant_id=%s", merchant_id)
    payload = fetch_simulated_api_payload(base_url=base_url, merchant_id=merchant_id)
    parsed = parse_simulated_api_payload(payload)
    validated = validate_simulated_api_payload(parsed)
    LOGGER.info("Simulated API call completed for merchant_id=%s", merchant_id)
    return validated
