from __future__ import annotations

import asyncio
from pathlib import Path

from ingestion.pdf_ingestion import ingest_pdf_async


def test_ingest_pdf_async_extracts_non_empty_text() -> None:
    pdf_path = Path("data/sample_merchant_summary.pdf")
    text = asyncio.run(ingest_pdf_async(pdf_path))
    assert isinstance(text, str)
    assert len(text.strip()) > 0
