from __future__ import annotations

import csv
import logging
from pathlib import Path

from pydantic import ValidationError

from ingestion.schemas import MerchantCsvRow

LOGGER = logging.getLogger(__name__)
EXPECTED_COLUMNS = [
    "merchant_id",
    "name",
    "country",
    "registration_number",
    "monthly_volume",
    "dispute_count",
    "transaction_count",
]


def validate_csv_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("CSV file is missing a header row")

    normalized_header = [field.strip() for field in fieldnames]
    missing = [field for field in EXPECTED_COLUMNS if field not in normalized_header]
    unexpected = [field for field in normalized_header if field not in EXPECTED_COLUMNS]
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing columns: {missing}")
        if unexpected:
            details.append(f"unexpected columns: {unexpected}")
        raise ValueError("Invalid CSV schema: " + "; ".join(details))


def fetch_csv_rows(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        validate_csv_header(reader.fieldnames)
        reader.fieldnames = [field.strip() for field in reader.fieldnames or []]
        return list(reader)


def parse_csv_rows(raw_rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    parsed: list[dict[str, object]] = []
    parse_errors: list[dict[str, object]] = []
    for row in raw_rows:
        try:
            coerced = {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            coerced["registration_number"] = coerced.get("registration_number") or None
            coerced["monthly_volume"] = float(row["monthly_volume"])
            coerced["dispute_count"] = int(row["dispute_count"])
            coerced["transaction_count"] = int(row["transaction_count"])
            parsed.append(coerced)
        except (TypeError, ValueError) as exc:
            parse_errors.append({"row": row, "error": str(exc)})
            LOGGER.warning("CSV row parsing failed for merchant_id=%s", row.get("merchant_id"))
    return parsed, parse_errors


def validate_csv_rows(parsed_rows: list[dict[str, object]]) -> tuple[list[MerchantCsvRow], list[dict[str, object]]]:
    valid_rows: list[MerchantCsvRow] = []
    invalid_rows: list[dict[str, object]] = []

    for row in parsed_rows:
        try:
            valid_rows.append(MerchantCsvRow.model_validate(row))
        except ValidationError as exc:
            invalid_rows.append({"row": row, "error": str(exc)})
            LOGGER.warning("CSV row validation failed for merchant_id=%s", row.get("merchant_id"))

    return valid_rows, invalid_rows


def validate_csv_dataset(valid_rows: list[MerchantCsvRow]) -> tuple[list[MerchantCsvRow], list[dict[str, object]]]:
    deduplicated_rows: list[MerchantCsvRow] = []
    duplicate_errors: list[dict[str, object]] = []
    seen_merchant_ids: set[str] = set()

    for row in valid_rows:
        if row.merchant_id in seen_merchant_ids:
            duplicate_errors.append(
                {
                    "row": row.model_dump(),
                    "error": f"Duplicate merchant_id detected: {row.merchant_id}",
                }
            )
            LOGGER.warning("Duplicate merchant_id detected: %s", row.merchant_id)
            continue
        seen_merchant_ids.add(row.merchant_id)
        deduplicated_rows.append(row)

    return deduplicated_rows, duplicate_errors


def ingest_merchants_csv(csv_path: str | Path) -> tuple[list[MerchantCsvRow], list[dict[str, object]]]:
    LOGGER.info("CSV ingestion started: %s", csv_path)
    raw = fetch_csv_rows(csv_path)
    parsed, parse_errors = parse_csv_rows(raw)
    valid, invalid = validate_csv_rows(parsed)
    deduplicated, duplicate_errors = validate_csv_dataset(valid)
    invalid.extend(parse_errors)
    invalid.extend(duplicate_errors)
    LOGGER.info("CSV ingestion completed with %d valid and %d invalid rows", len(deduplicated), len(invalid))
    return deduplicated, invalid
