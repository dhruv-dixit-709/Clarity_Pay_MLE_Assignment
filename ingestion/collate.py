from __future__ import annotations

import logging

from ingestion.schemas import (
    CollatedMerchantRecord,
    CountryEnrichment,
    MerchantCsvRow,
    ScrapedSiteData,
    SimulatedApiResponse,
)

LOGGER = logging.getLogger(__name__)


def collate_merchant_record(
    merchant: MerchantCsvRow,
    api_data: SimulatedApiResponse,
    country: CountryEnrichment,
    pdf_text: str,
    site_data: ScrapedSiteData,
) -> CollatedMerchantRecord:
    dispute_rate = merchant.dispute_count / merchant.transaction_count if merchant.transaction_count else 0.0
    record = CollatedMerchantRecord(
        merchant_id=merchant.merchant_id,
        name=merchant.name,
        country=merchant.country,
        registration_number=merchant.registration_number,
        monthly_volume=merchant.monthly_volume,
        dispute_count=merchant.dispute_count,
        transaction_count=merchant.transaction_count,
        dispute_rate=dispute_rate,
        internal_risk_flag=api_data.internal_risk_flag,
        last_30d_volume=api_data.transaction_summary.last_30d_volume,
        last_30d_txn_count=api_data.transaction_summary.last_30d_txn_count,
        avg_ticket_size=api_data.transaction_summary.avg_ticket_size,
        alpha2_code=country.alpha2_code,
        region=country.region,
        subregion=country.subregion,
        last_review_date=api_data.last_review_date,
        has_registration_number=bool(merchant.registration_number),
        pdf_context=pdf_text,
        claritypay_context=site_data.model_dump(),
    )
    return record


def collate_all_merchants(
    merchants: list[MerchantCsvRow],
    api_data_by_merchant: dict[str, SimulatedApiResponse],
    country_by_name: dict[str, CountryEnrichment],
    pdf_text: str,
    site_data: ScrapedSiteData,
) -> list[CollatedMerchantRecord]:
    LOGGER.info("Collation started for %d merchants", len(merchants))
    collated: list[CollatedMerchantRecord] = []
    for merchant in merchants:
        api_data = api_data_by_merchant[merchant.merchant_id]
        country = country_by_name[merchant.country]
        collated.append(collate_merchant_record(merchant, api_data, country, pdf_text, site_data))
    LOGGER.info("Collation completed for %d merchants", len(collated))
    return collated
