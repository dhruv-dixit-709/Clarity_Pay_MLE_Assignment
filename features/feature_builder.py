from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ingestion.schemas import CollatedMerchantRecord

RISK_FLAG_MAP = {"low": 0, "medium": 1, "high": 2}
SECTOR_KEYWORDS = {
    "travel_hospitality": ["travel", "hotel", "hotels", "wyndham", "margaritaville", "agency"],
    "beauty_wellness": ["spa", "beauty", "wellness", "removery"],
    "healthcare_care": ["health", "pharmacy", "care", "petcare"],
    "software_tech": ["software", "data", "analytics", "cloud", "tech", "electronics", "gadgets", "devices"],
    "home_services": ["home", "hvac", "repair", "repairs", "security", "construction", "landscaping", "garden"],
    "food_restaurants": ["kitchen", "restaurant", "restaurants", "grocers", "coffee", "catering", "eats", "bite"],
    "energy_auto": ["solar", "energy", "power", "motors", "auto"],
    "education_media": ["education", "book", "print"],
    "finance_professional": ["finance", "legal", "design", "creative"],
}
UK_REGISTRATION_PREFIXES = ("SC", "NI", "OC", "LP")


def _safe_ratio(numerator: pd.Series, denominator: pd.Series, default: float = 0.0) -> pd.Series:
    denominator = denominator.astype(float)
    valid_denominator = denominator.where(denominator != 0)
    ratio = numerator.astype(float) / valid_denominator
    return ratio.replace([np.inf, -np.inf], np.nan).fillna(default)


def infer_merchant_sector(name: str) -> str:
    normalized_name = re.sub(r"[^a-z0-9 ]+", " ", name.lower())
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword in normalized_name for keyword in keywords):
            return sector
    return "other"


def extract_registration_type(registration_number: str | None, country: str) -> str:
    if not registration_number:
        return "none"

    normalized = registration_number.strip().upper()
    if country != "United Kingdom":
        return "non_uk_registration"
    if normalized.isdigit():
        return "numeric"
    for prefix in UK_REGISTRATION_PREFIXES:
        if normalized.startswith(prefix):
            return prefix.lower()
    return "other_uk"


def build_feature_frame(
    collated_records: list[CollatedMerchantRecord],
    reference_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    rows = [record.model_dump(mode="json") for record in collated_records]
    df = pd.DataFrame(rows)

    if reference_date is None:
        reference_date = pd.Timestamp.utcnow().tz_localize(None).normalize()

    df["risk_flag_encoded"] = df["internal_risk_flag"].map(RISK_FLAG_MAP).fillna(0).astype(int)
    df["volume_band"] = pd.cut(
        df["monthly_volume"],
        bins=[-1, 50000, 100000, 200000, float("inf")],
        labels=["micro", "small", "mid", "large"],
    )
    df["is_uk"] = (df["country"] == "United Kingdom").astype(int)
    df["merchant_sector"] = df["name"].apply(infer_merchant_sector)
    df["registration_type"] = df.apply(
        lambda row: extract_registration_type(row["registration_number"], row["country"]),
        axis=1,
    )

    df["csv_implied_avg_ticket"] = _safe_ratio(df["monthly_volume"], df["transaction_count"])
    df["api_volume_to_monthly_volume_ratio"] = _safe_ratio(df["last_30d_volume"], df["monthly_volume"], default=1.0)
    df["api_txn_to_csv_txn_ratio"] = _safe_ratio(
        df["last_30d_txn_count"],
        df["transaction_count"],
        default=1.0,
    )
    df["avg_ticket_gap_ratio"] = _safe_ratio(df["avg_ticket_size"], df["csv_implied_avg_ticket"], default=1.0)

    df["log_monthly_volume"] = np.log1p(df["monthly_volume"])
    df["log_last_30d_volume"] = np.log1p(df["last_30d_volume"])
    df["log_last_30d_txn_count"] = np.log1p(df["last_30d_txn_count"])

    review_dates = pd.to_datetime(df["last_review_date"], errors="coerce")
    df["review_age_days"] = (reference_date - review_dates).dt.days.fillna(999).clip(lower=0)
    df["review_is_stale"] = (df["review_age_days"] > 90).astype(int)

    df["missing_country_enrichment"] = df["region"].isna().astype(int)
    df["volume_mismatch_flag"] = (
        (df["api_volume_to_monthly_volume_ratio"] < 0.8) | (df["api_volume_to_monthly_volume_ratio"] > 1.2)
    ).astype(int)
    df["avg_ticket_mismatch_flag"] = (
        (df["avg_ticket_gap_ratio"] < 0.8) | (df["avg_ticket_gap_ratio"] > 1.2)
    ).astype(int)
    df["risk_flag_x_review_stale"] = df["risk_flag_encoded"] * df["review_is_stale"]

    # The label is still a current-period proxy, but the model no longer uses dispute_rate itself as a feature.
    df["high_dispute_risk"] = (df["dispute_rate"] >= 0.001).astype(int)
    return df
