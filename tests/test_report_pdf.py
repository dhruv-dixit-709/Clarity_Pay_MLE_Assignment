from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from reporting.pdf_export import write_underwriting_report_pdf


def test_write_underwriting_report_pdf_includes_traceback_metadata(tmp_path: Path) -> None:
    output_path = tmp_path / "underwriting_report.pdf"
    markdown_text = "# Executive Summary\n\n- Merchant looks acceptable.\n- Price risk carefully."
    traceback_metadata = {
        "generated_at_utc": "2026-03-14T18:30:00+00:00",
        "data_sources": ["data/merchants.csv", "https://claritypay.com"],
        "merchant_count": 50,
    }

    write_underwriting_report_pdf(
        markdown_text=markdown_text,
        output_path=output_path,
        traceback_metadata=traceback_metadata,
    )

    reader = PdfReader(str(output_path))
    first_page_text = reader.pages[0].extract_text() or ""
    last_page_text = reader.pages[-1].extract_text() or ""

    assert "Executive Summary" in first_page_text
    assert "Traceback Metadata" in last_page_text
    assert "generated_at_utc" in last_page_text
    assert "data/merchants.csv" in last_page_text
