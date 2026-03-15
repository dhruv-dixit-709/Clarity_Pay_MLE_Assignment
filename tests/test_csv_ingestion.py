from __future__ import annotations

import pytest

from ingestion.csv_ingestion import validate_csv_dataset, validate_csv_header, validate_csv_rows


def test_validate_csv_rows_separates_invalid_rows() -> None:
    parsed_rows = [
        {
            "merchant_id": "M001",
            "name": "Example",
            "country": "United Kingdom",
            "registration_number": "123456",
            "monthly_volume": 1000.0,
            "dispute_count": 1,
            "transaction_count": 100,
        },
        {
            "merchant_id": "M002",
            "name": "Bad Merchant",
            "country": "United Kingdom",
            "registration_number": None,
            "monthly_volume": -1.0,
            "dispute_count": 1,
            "transaction_count": 100,
        },
    ]
    valid, invalid = validate_csv_rows(parsed_rows)
    assert len(valid) == 1
    assert len(invalid) == 1


def test_validate_csv_header_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_csv_header(
            [
                "merchant_id",
                "name",
                "country",
                "monthly_volume",
                "dispute_count",
            ]
        )


def test_validate_csv_dataset_rejects_duplicate_merchant_ids() -> None:
    parsed_rows = [
        {
            "merchant_id": "M001",
            "name": "Example",
            "country": "United Kingdom",
            "registration_number": "123456",
            "monthly_volume": 1000.0,
            "dispute_count": 1,
            "transaction_count": 100,
        },
        {
            "merchant_id": "M001",
            "name": "Example Duplicate",
            "country": "United Kingdom",
            "registration_number": "654321",
            "monthly_volume": 900.0,
            "dispute_count": 0,
            "transaction_count": 90,
        },
    ]
    valid_rows, invalid_rows = validate_csv_rows(parsed_rows)
    deduplicated, duplicate_errors = validate_csv_dataset(valid_rows)

    assert len(invalid_rows) == 0
    assert len(deduplicated) == 1
    assert len(duplicate_errors) == 1
