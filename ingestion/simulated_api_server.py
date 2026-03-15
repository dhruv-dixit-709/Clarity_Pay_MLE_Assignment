from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "simulated_api_example_response.json"

app = FastAPI(title="Simulated Merchant Risk API")


def _load_seed_data() -> list[dict]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


SEED_DATA = _load_seed_data()


@app.get("/internal-risk/{merchant_id}")
def get_internal_risk(merchant_id: str) -> dict:
    for item in SEED_DATA:
        if item["merchant_id"] == merchant_id:
            return item

    # Deterministic fallback for merchants that are not in the example seed.
    numeric_id = int(merchant_id.replace("M", "")) if merchant_id.startswith("M") else 0
    flag = "high" if numeric_id % 7 == 0 else "medium" if numeric_id % 3 == 0 else "low"
    volume = 20000 + (numeric_id * 2500)
    txn_count = 700 + (numeric_id * 40)

    if txn_count <= 0:
        raise HTTPException(status_code=400, detail="Invalid transaction count generated")

    return {
        "merchant_id": merchant_id,
        "internal_risk_flag": flag,
        "transaction_summary": {
            "last_30d_volume": float(volume),
            "last_30d_txn_count": int(txn_count),
            "avg_ticket_size": float(volume / txn_count),
        },
        "last_review_date": "2025-01-01",
    }
