from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pypdf import PdfReader

LOGGER = logging.getLogger(__name__)


def fetch_pdf_path(pdf_path: str | Path) -> Path:
    return Path(pdf_path)


def parse_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def validate_pdf_text(text: str) -> str:
    if not text:
        raise ValueError("Extracted PDF text is empty")
    return text


async def ingest_pdf_async(pdf_path: str | Path) -> str:
    LOGGER.info("PDF ingestion started asynchronously: %s", pdf_path)
    path = fetch_pdf_path(pdf_path)

    # In production this should be a durable queue worker; async keeps the interface non-blocking for now.
    parsed_text = await asyncio.to_thread(parse_pdf_text, path)
    validated_text = validate_pdf_text(parsed_text)
    LOGGER.info("PDF ingestion completed asynchronously: %s", pdf_path)
    return validated_text
