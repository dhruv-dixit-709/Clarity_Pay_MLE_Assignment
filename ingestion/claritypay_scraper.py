from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from ingestion.schemas import ScrapedSiteData

LOGGER = logging.getLogger(__name__)
CLARITYPAY_URL = "https://claritypay.com"
USER_AGENT = "claritypay-underwriting-pipeline/1.0 (+contact: engineering@example.com)"


def fetch_site_html(url: str = CLARITYPAY_URL, delay_seconds: float = 1.0) -> str:
    time.sleep(delay_seconds)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()
    return response.text


def parse_site_html(html: str, source_url: str = CLARITYPAY_URL) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    full_text = " ".join(soup.stripped_strings)

    value_prop_patterns = [
        r"Pay over time",
        r"Clear terms",
        r"fast approvals",
        r"frictionless checkout",
    ]
    value_props = sorted(
        {
            match
            for pattern in value_prop_patterns
            for match in re.findall(pattern, full_text, flags=re.IGNORECASE)
        }
    )

    stats = sorted(set(re.findall(r"\$?\d[\d.,]*\+?\s?(?:[MBKmbk]|Merchants|Transactions|Credit Issued)", full_text)))

    partner_keywords = ["Proud Partner", "Partner", "Partners"]
    partners: list[str] = []
    for keyword in partner_keywords:
        for node in soup.find_all(string=re.compile(keyword, flags=re.IGNORECASE)):
            candidate = " ".join(node.parent.get_text(" ", strip=True).split())
            if candidate and candidate not in partners:
                partners.append(candidate)

    if not value_props:
        value_props = ["Value propositions unavailable from current site structure"]

    return {
        "value_propositions": value_props,
        "partners": partners[:12],
        "public_stats": stats[:20],
        "source_url": source_url,
    }


def validate_site_data(parsed: dict) -> ScrapedSiteData:
    return ScrapedSiteData.model_validate(parsed)


def build_site_data_fallback() -> ScrapedSiteData:
    return validate_site_data(
        {
            "value_propositions": ["Unavailable due to scrape error"],
            "partners": [],
            "public_stats": [],
            "source_url": CLARITYPAY_URL,
        }
    )


def scrape_claritypay() -> ScrapedSiteData:
    LOGGER.info("Scrape started for %s", CLARITYPAY_URL)
    try:
        html = fetch_site_html()
        parsed = parse_site_html(html)
        validated = validate_site_data(parsed)
        LOGGER.info("Scrape completed for %s", CLARITYPAY_URL)
        return validated
    except requests.RequestException:
        LOGGER.exception("Scrape failed for %s; returning fallback payload", CLARITYPAY_URL)
        return build_site_data_fallback()
