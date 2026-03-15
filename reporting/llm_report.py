from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from reporting.pdf_export import write_underwriting_report_pdf


SYSTEM_PROMPT = """You are a risk analyst writing for a BNPL underwriting committee.
Use concise, factual language and explicitly connect risk to expected loss/pricing.
Output markdown with sections: Executive Summary, Merchant Highlights, Model Output, Red Flags, Portfolio View, Recommendations."""
DATA_SOURCES = [
    "data/merchants.csv",
    "data/sample_merchant_summary.pdf",
    "data/simulated_api_contract.json",
    "Local simulated API: /internal-risk/{merchant_id}",
    "REST Countries API: https://restcountries.com/v3.1/name/{country}",
    "https://claritypay.com",
]


def build_report_prompt(collated_rows: list[dict], evaluation: dict, portfolio_summary: dict) -> str:
    trimmed_collated = collated_rows[:20]
    payload = {
        "collated_merchants_sample": trimmed_collated,
        "evaluation": evaluation,
        "portfolio_summary": portfolio_summary,
    }
    return (
        "Generate a 1-2 page underwriting report for the risk team from this pipeline output. "
        "Use explicit risk bands and rationale.\n\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )


def generate_underwriting_report_with_gemini(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to generate the LLM report.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        [
            SYSTEM_PROMPT,
            prompt,
        ]
    )
    if not response.candidates:
        raise RuntimeError("Gemini response had no candidates.")
    return response.text


def build_traceback_metadata(
    scored_df: pd.DataFrame,
    evaluation: dict,
    portfolio_summary: dict,
    model_name: str,
    report_path: Path,
    prompt_path: Path,
) -> dict[str, object]:
    report_text = report_path.read_text(encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    return {
        "generated_at_utc": generated_at,
        "report_markdown_path": str(report_path),
        "prompt_path": str(prompt_path),
        "pdf_version": "1.0",
        "llm_model": model_name,
        "merchant_count": int(len(scored_df)),
        "countries_in_run": sorted(scored_df["country"].dropna().astype(str).unique().tolist()),
        "data_sources": DATA_SOURCES,
        "prediction_label": str(evaluation.get("label_column", "high_dispute_risk")),
        "model_feature_columns": evaluation.get("model_feature_columns", []),
        "training_row_count": int(evaluation.get("training_row_count", 0)),
        "test_row_count": int(evaluation.get("test_row_count", 0)),
        "roc_auc": round(float(evaluation.get("roc_auc", 0.0)), 4),
        "expected_high_risk_merchants": round(float(portfolio_summary.get("expected_high_risk_merchants", 0.0)), 4),
        "expected_loss_proxy_total": round(float(portfolio_summary.get("expected_loss_proxy_total", 0.0)), 2),
        "report_sha256": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
    }


def write_report_artifacts(
    scored_df: pd.DataFrame,
    evaluation: dict,
    portfolio_summary: dict,
    output_dir: str | Path = "artifacts",
) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    collated_rows = scored_df.to_dict(orient="records")
    prompt = build_report_prompt(collated_rows=collated_rows, evaluation=evaluation, portfolio_summary=portfolio_summary)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    report_text = generate_underwriting_report_with_gemini(prompt=prompt, model_name=model_name)

    report_path = path / "underwriting_report.md"
    prompt_path = path / "llm_prompt.txt"
    pdf_path = path / "underwriting_report.pdf"
    report_path.write_text(report_text, encoding="utf-8")
    prompt_path.write_text(prompt, encoding="utf-8")
    traceback_metadata = build_traceback_metadata(
        scored_df=scored_df,
        evaluation=evaluation,
        portfolio_summary=portfolio_summary,
        model_name=model_name,
        report_path=report_path,
        prompt_path=prompt_path,
    )
    write_underwriting_report_pdf(
        markdown_text=report_text,
        output_path=pdf_path,
        traceback_metadata=traceback_metadata,
    )

    return {
        "report_path": str(report_path),
        "prompt_path": str(prompt_path),
        "report_pdf_path": str(pdf_path),
    }
