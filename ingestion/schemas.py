from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MerchantCsvRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_id: str
    name: str
    country: str
    registration_number: str | None = None
    monthly_volume: float = Field(ge=0)
    dispute_count: int = Field(ge=0)
    transaction_count: int = Field(ge=0)

    @field_validator("merchant_id", "name", "country", mode="before")
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("required string field cannot be blank")
        return stripped

    @field_validator("registration_number", mode="before")
    @classmethod
    def normalize_registration_number(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_semantics(self) -> "MerchantCsvRow":
        if self.dispute_count > self.transaction_count:
            raise ValueError("dispute_count cannot exceed transaction_count")
        if self.monthly_volume > 0 and self.transaction_count == 0:
            raise ValueError("transaction_count must be positive when monthly_volume is positive")
        return self


class TransactionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_30d_volume: float = Field(ge=0)
    last_30d_txn_count: int = Field(ge=0)
    avg_ticket_size: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_semantics(self) -> "TransactionSummary":
        if self.last_30d_volume > 0 and self.last_30d_txn_count == 0:
            raise ValueError("last_30d_txn_count must be positive when last_30d_volume is positive")
        return self


class SimulatedApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_id: str
    internal_risk_flag: Literal["low", "medium", "high"]
    transaction_summary: TransactionSummary
    last_review_date: date | None = None


class CountryEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str
    alpha2_code: str | None = None
    region: str | None = None
    subregion: str | None = None


class ScrapedSiteData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_propositions: list[str]
    partners: list[str]
    public_stats: list[str]
    source_url: str


class CollatedMerchantRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_id: str
    name: str
    country: str
    registration_number: str | None
    monthly_volume: float
    dispute_count: int
    transaction_count: int
    dispute_rate: float
    internal_risk_flag: str
    last_30d_volume: float
    last_30d_txn_count: int
    avg_ticket_size: float
    alpha2_code: str | None
    region: str | None
    subregion: str | None
    last_review_date: date | None = None
    has_registration_number: bool
    pdf_context: str
    claritypay_context: dict[str, Any]
