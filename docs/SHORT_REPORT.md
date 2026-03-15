# Short Written Report

## Assumptions

- `dispute_rate = dispute_count / transaction_count` is a reasonable first-order dispute risk signal.
- A threshold of `dispute_rate >= 0.001` is used to define a high-dispute training label for demonstration.
- Internal risk flag from the simulated API is predictive and encoded ordinally.
- Portfolio expected loss can be approximated with a simple proxy:
  - `predicted_high_risk_probability * 3.5% * monthly_volume`

## Trade-offs

- The model is intentionally simple (logistic regression) for interpretability and fast iteration, not peak predictive power.
- Site scraping relies on public HTML text patterns; changes in site structure can reduce extraction quality.
- REST Countries enrichment is robust for basic region/subregion but not legal-entity verification.
- PDF ingestion is asynchronous via `asyncio.to_thread`; production should use durable background workers and retries.

## What to harden for production

- Data contracts:
  - Add stricter schema versioning and contract tests for every source.
- Orchestration:
  - Use a scheduler/workflow tool (Dagster, Airflow, Prefect) with retries and alerting.
- Idempotency/state:
  - Add run-level metadata, source checkpoints, immutable storage partitions.
- Monitoring:
  - Track data freshness, validation failures, model drift, feature drift, and report latency.
- Modeling:
  - Use richer labels (true chargeback outcomes), cross-validation, calibration, and fairness checks.
- Reporting:
  - Add RAG/context constraints, hallucination checks, and a reviewer sign-off workflow.
