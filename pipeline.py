from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from features.feature_builder import build_feature_frame
from ingestion.claritypay_scraper import scrape_claritypay
from ingestion.collate import collate_all_merchants
from ingestion.csv_ingestion import ingest_merchants_csv
from ingestion.data_quality import build_data_quality_report
from ingestion.pdf_ingestion import ingest_pdf_async
from ingestion.rest_countries_client import enrich_country
from ingestion.schemas import MerchantCsvRow, SimulatedApiResponse
from ingestion.simulated_api_client import get_internal_risk_data
from model.train import train_risk_model
from reporting.llm_report import write_report_artifacts


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def build_simulated_api_fallback(merchant: MerchantCsvRow) -> SimulatedApiResponse:
    avg_ticket_size = merchant.monthly_volume / merchant.transaction_count if merchant.transaction_count else 0.0
    return SimulatedApiResponse.model_validate(
        {
            "merchant_id": merchant.merchant_id,
            "internal_risk_flag": "medium",
            "transaction_summary": {
                "last_30d_volume": merchant.monthly_volume,
                "last_30d_txn_count": merchant.transaction_count,
                "avg_ticket_size": avg_ticket_size,
            },
            "last_review_date": None,
        }
    )


async def run_pipeline(simulated_api_base_url: str, skip_llm_report: bool = False) -> dict:
    setup_logging()
    load_dotenv()
    logger = logging.getLogger("pipeline")

    csv_path = Path("data/merchants.csv")
    pdf_path = Path("data/sample_merchant_summary.pdf")
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    merchants, invalid_rows = ingest_merchants_csv(csv_path)
    if invalid_rows:
        (artifacts_dir / "invalid_rows.json").write_text(json.dumps(invalid_rows, indent=2), encoding="utf-8")
        logger.warning("Detected %d invalid CSV rows; details written to artifacts/invalid_rows.json", len(invalid_rows))

    pdf_task = asyncio.create_task(ingest_pdf_async(pdf_path))

    unique_countries = sorted({m.country for m in merchants})
    country_by_name = {country: enrich_country(country) for country in unique_countries}

    site_data = scrape_claritypay()

    api_data_by_merchant = {}
    for merchant in merchants:
        try:
            api_data_by_merchant[merchant.merchant_id] = get_internal_risk_data(simulated_api_base_url, merchant.merchant_id)
        except Exception:
            logger.exception(
                "Simulated API call failed for merchant_id=%s; using fallback transaction summary",
                merchant.merchant_id,
            )
            api_data_by_merchant[merchant.merchant_id] = build_simulated_api_fallback(merchant)

    pdf_text = await pdf_task

    collated = collate_all_merchants(
        merchants=merchants,
        api_data_by_merchant=api_data_by_merchant,
        country_by_name=country_by_name,
        pdf_text=pdf_text,
        site_data=site_data,
    )
    collated_df = pd.DataFrame([record.model_dump(mode="json") for record in collated])
    collated_df.to_csv(artifacts_dir / "collated_merchants.csv", index=False)

    data_quality_report = build_data_quality_report(
        merchants=merchants,
        invalid_rows=invalid_rows,
        collated_records=collated,
    )
    (artifacts_dir / "data_quality_report.json").write_text(
        json.dumps(data_quality_report, indent=2, default=str),
        encoding="utf-8",
    )

    feature_df = build_feature_frame(collated)
    model_artifacts = train_risk_model(feature_df)

    model_artifacts.scored_df.to_csv(artifacts_dir / "scored_merchants.csv", index=False)
    model_artifacts.coefficients_df.to_csv(artifacts_dir / "model_coefficients.csv", index=False)
    (artifacts_dir / "model_evaluation.txt").write_text(
        json.dumps(model_artifacts.evaluation, indent=2, default=str), encoding="utf-8"
    )
    (artifacts_dir / "portfolio_summary.json").write_text(
        json.dumps(model_artifacts.portfolio_summary, indent=2), encoding="utf-8"
    )

    report_artifacts: dict[str, str] = {}
    if skip_llm_report:
        logger.info("Skipping LLM report generation by request")
    else:
        report_artifacts = write_report_artifacts(
            scored_df=model_artifacts.scored_df,
            evaluation=model_artifacts.evaluation,
            portfolio_summary=model_artifacts.portfolio_summary,
            output_dir=artifacts_dir,
        )

    result = {
        "collated_merchants_path": str(artifacts_dir / "collated_merchants.csv"),
        "data_quality_report_path": str(artifacts_dir / "data_quality_report.json"),
        "scored_merchants_path": str(artifacts_dir / "scored_merchants.csv"),
        "model_coefficients_path": str(artifacts_dir / "model_coefficients.csv"),
        "portfolio_summary_path": str(artifacts_dir / "portfolio_summary.json"),
        "model_evaluation_path": str(artifacts_dir / "model_evaluation.txt"),
        **report_artifacts,
    }
    logger.info("Pipeline completed successfully")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulated-api-base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--skip-llm-report", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        run_pipeline(simulated_api_base_url=args.simulated_api_base_url, skip_llm_report=args.skip_llm_report)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
