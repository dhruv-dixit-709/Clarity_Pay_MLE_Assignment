# Merchant Underwriting Pipeline (Master README)

This project implements a minimal but production-style BNPL underwriting pipeline.  
It ingests multi-source merchant data, validates and collates it, trains a risk model, computes portfolio risk, and generates an LLM-based underwriting report.

## 1) End-to-End Scope Implemented

### Required sources

1. CSV source: `data/merchants.csv`
2. Simulated API:
   - Server: `ingestion/simulated_api_server.py`
   - Client + schema validation: `ingestion/simulated_api_client.py`
   - Contract: `data/simulated_api_contract.json`
3. Real public API:
   - REST Countries integration: `ingestion/rest_countries_client.py`
   - Companies House was not integrated in this submission because an API key could not be obtained in time.
   - Fallback: keep `registration_number` from the CSV, continue the pipeline without Companies House enrichment, and treat UK company-profile data as unavailable rather than blocking underwriting.
4. PDF source:
   - Async text extraction from `data/sample_merchant_summary.pdf`: `ingestion/pdf_ingestion.py`
5. Scraping source:
   - `https://claritypay.com` scraper: `ingestion/claritypay_scraper.py`

### Pipeline outputs implemented

- Merchant-level collated dataset
- Data quality report with reconciliation flags
- Feature-engineered modeling frame
- Model training + evaluation metrics
- Model coefficient export for interpretability
- Portfolio-level risk aggregation
- LLM-generated underwriting report (when `GEMINI_API_KEY` is set, or skipped via `--skip-llm-report`)
- PDF export of the LLM underwriting report with a final `Traceback Metadata` page

## 2) Repository Structure

```text
data/                 Input data and API contract files
ingestion/            Fetch/parse/validate per source + collation
features/             Feature engineering
model/                Model training + portfolio aggregation
reporting/            LLM prompt + report generation
tests/                Unit tests
docs/                 Short written report
artifacts/            Runtime outputs (generated)
pipeline.py           Main orchestration entrypoint
AI_USAGE.md           AI transparency document
```

## 3) Methods Implemented

### 3.1 Ingestion pattern (governance-oriented)

Each source follows a clear pattern:

- `fetch`: retrieve raw payload/content
- `parse`: transform raw content into normalized Python structures
- `validate`: enforce schema/data constraints

Validation uses:

- `pydantic` models for row/object-level checks
- `jsonschema` validation for the simulated API contract
- CSV header validation, duplicate `merchant_id` rejection, and semantic checks
- Dataset-level reconciliation flags written to `artifacts/data_quality_report.json`

Logging is enabled throughout source ingestion and pipeline stages.

### 3.2 Collation

`ingestion/collate.py` builds one normalized record per merchant (typed by `CollatedMerchantRecord`), combining:

- CSV business fields
- Simulated API internal risk + transaction summary
- Country/region enrichment
- Country code + simulated API review date
- PDF extracted context
- ClarityPay scraped context

### 3.3 Feature Engineering

Implemented in `features/feature_builder.py`:

- `risk_flag_encoded`: ordinal mapping from internal risk tier
- `volume_band`: discretized monthly volume bucket
- `is_uk`: binary geography indicator
- `merchant_sector`: lightweight sector inference from merchant name tokens
- `registration_type`: UK registration prefix/category (`numeric`, `sc`, `ni`, `oc`, `lp`, etc.)
- Cross-source consistency features:
  - `csv_implied_avg_ticket`
  - `api_volume_to_monthly_volume_ratio`
  - `api_txn_to_csv_txn_ratio`
  - `avg_ticket_gap_ratio`
- Review recency and monitoring features:
  - `review_age_days`
  - `review_is_stale`
  - mismatch flags for volume / average-ticket divergence
- `high_dispute_risk`: current-period proxy label based on dispute rate threshold

The model no longer uses `dispute_rate` directly as an input feature, which avoids the earlier target-leakage issue.

### 3.4 Modeling

Implemented in `model/train.py`:

- Algorithm: `LogisticRegression(max_iter=1000, class_weight="balanced")`
- Preprocessing:
  - Numeric features: median imputation + `StandardScaler`
  - Categorical features: constant imputation + one-hot encoding
  - Boolean features: imputed and passed through
- Split strategy:
  - `train_test_split(test_size=0.3, random_state=42, stratify=y)`
- Evaluation:
  - ROC-AUC
  - Classification report
  - Top positive / negative coefficients for interpretability

### 3.5 Portfolio aggregation

From merchant-level predicted probabilities:

- Expected high-risk merchant count = sum of merchant high-risk probabilities
- Expected loss proxy total = sum of merchant expected loss proxy

### 3.6 LLM reporting

Implemented in `reporting/llm_report.py`:

- System prompt sets underwriting-committee style and required sections
- User prompt contains:
  - Collated merchant sample
  - Model evaluation summary
  - Portfolio summary
- Output:
  - `artifacts/underwriting_report.md`
  - `artifacts/underwriting_report.pdf`
  - `artifacts/llm_prompt.txt`

The generated PDF preserves the markdown report content and appends a final page titled `Traceback Metadata` that captures generation time, model feature columns, portfolio summary, data sources, and report/prompt hashes for auditability.

## 4) Key Mathematical / Statistical Formulas

### Merchant-level metrics

- **Dispute rate**
  - `dispute_rate = dispute_count / transaction_count`

### Labeling rule (binary target)

- **High dispute risk target**
  - `high_dispute_risk = 1 if dispute_rate >= 0.001 else 0`

### Portfolio risk metrics

- **Expected high-risk merchants**
  - `E[high_risk_count] = sum_i p_i`
  - where `p_i` is model-predicted probability merchant `i` is high risk

- **Expected loss proxy (merchant level)**
  - `expected_loss_proxy_i = p_i * loss_rate * monthly_volume_i`
  - configured `loss_rate = 0.035`

- **Portfolio expected loss proxy**
  - `expected_loss_proxy_total = sum_i expected_loss_proxy_i`

## 5) How to Run (after dependency install)

### Prerequisites

- Python environment with required packages
- Internet access (REST Countries + claritypay scrape)
- Gemini API key for final report generation, or use `--skip-llm-report` to skip that step

### Step A: Activate environment

```bash
micromamba activate general_env
```

### Step B: Install dependencies

```bash
pip install -r requirements.txt
```

### Step C: Configure environment variables

Create or update a `.env` file in the repo root with:

- `GEMINI_API_KEY=` (required for LLM report generation)
- `GEMINI_MODEL=gemini-1.5-flash` (optional override)

### Step D: Start simulated API (terminal 1)

```bash
micromamba activate general_env
uvicorn ingestion.simulated_api_server:app --host 127.0.0.1 --port 8001
```

### Step E: Run pipeline (terminal 2)

#### Full run (includes LLM report)

```bash
micromamba activate general_env
python pipeline.py --simulated-api-base-url http://127.0.0.1:8001
```

#### Dry run (skip LLM report generation)

```bash
micromamba activate general_env
python pipeline.py --simulated-api-base-url http://127.0.0.1:8001 --skip-llm-report
```

## 6) Generated Artifacts

Always produced:

- `artifacts/collated_merchants.csv`
- `artifacts/data_quality_report.json`
- `artifacts/scored_merchants.csv`
- `artifacts/model_coefficients.csv`
- `artifacts/portfolio_summary.json`
- `artifacts/model_evaluation.txt`
- `artifacts/invalid_rows.json` (only if invalid CSV rows exist)

Produced when LLM step is enabled:

- `artifacts/underwriting_report.md`
- `artifacts/underwriting_report.pdf`
- `artifacts/llm_prompt.txt`

## 7) Tests

Run:

```bash
micromamba activate general_env
pytest -q
```

Current tests cover:

- CSV validation behavior
- CSV header validation + duplicate merchant detection
- Simulated API contract shape validation
- Async PDF extraction non-empty output
- Feature engineering behavior for sector / registration / review-age features
- PDF report export including the final `Traceback Metadata` page

## 8) Operational and Governance Notes

### Idempotency strategy for production

- Derive deterministic `run_id` from input fingerprints (CSV hash, PDF hash, scrape batch key)
- Cache source results by `(source, entity_id, run_id)`
- Persist immutable outputs per run partition
- Upsert collated/scored tables on `(merchant_id, run_id)`
- Track source watermark/checkpoint state

### Reliability and monitoring (recommended next)

- Add retries with exponential backoff and circuit-breaking for external APIs
- Add data quality monitors (null spikes, drift in feature distributions)
- Add model monitoring (AUC drift, calibration drift, threshold performance)
- Add alerting for scrape/API failures and stale outputs
