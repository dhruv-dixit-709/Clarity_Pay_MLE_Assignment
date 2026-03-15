from __future__ import annotations

from ingestion.simulated_api_client import validate_simulated_api_payload


def test_validate_simulated_api_payload_accepts_contract_shape() -> None:
    payload = {
        "merchant_id": "M001",
        "internal_risk_flag": "low",
        "transaction_summary": {
            "last_30d_volume": 1000.0,
            "last_30d_txn_count": 100,
            "avg_ticket_size": 10.0,
        },
        "last_review_date": "2025-01-01",
    }
    validated = validate_simulated_api_payload(payload)
    assert validated.merchant_id == "M001"
