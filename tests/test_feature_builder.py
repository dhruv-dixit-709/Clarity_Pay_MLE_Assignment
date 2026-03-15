from __future__ import annotations

from datetime import date

import pandas as pd

from features.feature_builder import build_feature_frame
from ingestion.schemas import CollatedMerchantRecord


def test_build_feature_frame_adds_richer_non_leaky_features() -> None:
    records = [
        CollatedMerchantRecord(
            merchant_id="M001",
            name="TravelWise Agency",
            country="United Kingdom",
            registration_number="SC123456",
            monthly_volume=100000.0,
            dispute_count=1,
            transaction_count=2000,
            dispute_rate=0.0005,
            internal_risk_flag="medium",
            last_30d_volume=120000.0,
            last_30d_txn_count=2200,
            avg_ticket_size=54.5,
            alpha2_code="GB",
            region="Europe",
            subregion="Northern Europe",
            last_review_date=date(2025, 1, 1),
            has_registration_number=True,
            pdf_context="sample pdf",
            claritypay_context={"value_propositions": [], "partners": [], "public_stats": [], "source_url": "x"},
        )
    ]

    feature_df = build_feature_frame(records, reference_date=pd.Timestamp("2025-04-01"))

    assert feature_df.loc[0, "merchant_sector"] == "travel_hospitality"
    assert feature_df.loc[0, "registration_type"] == "sc"
    assert "api_volume_to_monthly_volume_ratio" in feature_df.columns
    assert "review_age_days" in feature_df.columns
    assert "high_dispute_risk" in feature_df.columns
    assert feature_df.loc[0, "high_dispute_risk"] == 0
