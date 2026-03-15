from __future__ import annotations

from collections import Counter

from ingestion.schemas import CollatedMerchantRecord, MerchantCsvRow


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def build_quality_flags(record: CollatedMerchantRecord) -> list[str]:
    flags: list[str] = []

    if record.country == "United Kingdom" and not record.has_registration_number:
        flags.append("uk_missing_registration_number")
    if record.alpha2_code is None:
        flags.append("missing_country_code")
    if record.region is None:
        flags.append("missing_region_enrichment")
    if record.last_review_date is None:
        flags.append("missing_last_review_date")

    volume_ratio = _safe_ratio(record.last_30d_volume, record.monthly_volume)
    if volume_ratio is not None and (volume_ratio < 0.5 or volume_ratio > 1.5):
        flags.append("api_volume_mismatch")

    txn_ratio = _safe_ratio(float(record.last_30d_txn_count), float(record.transaction_count))
    if txn_ratio is not None and (txn_ratio < 0.5 or txn_ratio > 1.5):
        flags.append("api_txn_mismatch")

    csv_implied_avg_ticket = _safe_ratio(record.monthly_volume, float(record.transaction_count))
    avg_ticket_gap_ratio = _safe_ratio(record.avg_ticket_size, csv_implied_avg_ticket or 0.0)
    if avg_ticket_gap_ratio is not None and (avg_ticket_gap_ratio < 0.75 or avg_ticket_gap_ratio > 1.25):
        flags.append("avg_ticket_mismatch")

    return flags


def build_data_quality_report(
    merchants: list[MerchantCsvRow],
    invalid_rows: list[dict[str, object]],
    collated_records: list[CollatedMerchantRecord],
) -> dict[str, object]:
    merchant_flags = [
        {"merchant_id": record.merchant_id, "flags": flags}
        for record in collated_records
        if (flags := build_quality_flags(record))
    ]
    flag_counter = Counter(flag for item in merchant_flags for flag in item["flags"])
    risk_distribution = Counter(record.internal_risk_flag for record in collated_records)

    return {
        "csv_summary": {
            "valid_merchant_count": len(merchants),
            "invalid_row_count": len(invalid_rows),
            "countries_present": sorted({merchant.country for merchant in merchants}),
            "duplicate_merchant_ids_rejected": sum(
                1 for item in invalid_rows if "Duplicate merchant_id" in str(item.get("error", ""))
            ),
        },
        "collated_summary": {
            "merchant_count": len(collated_records),
            "uk_merchant_count": sum(record.country == "United Kingdom" for record in collated_records),
            "merchant_with_registration_count": sum(record.has_registration_number for record in collated_records),
            "missing_region_count": sum(record.region is None for record in collated_records),
            "missing_subregion_count": sum(record.subregion is None for record in collated_records),
            "missing_review_date_count": sum(record.last_review_date is None for record in collated_records),
            "observed_high_dispute_count": sum(record.dispute_rate >= 0.001 for record in collated_records),
        },
        "internal_risk_distribution": dict(sorted(risk_distribution.items())),
        "quality_flag_counts": dict(sorted(flag_counter.items())),
        "merchant_quality_flags": merchant_flags,
    }
