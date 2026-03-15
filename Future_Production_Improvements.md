# Future Production Improvements

This report document expands on the current state of the underwriting pipeline and outlines what should happen next before a production deployment. It is intentionally more detailed than the short report so it can serve as a practical handoff note for engineering, risk, and model-governance stakeholders.

## Current Assumptions

- The current CSV snapshot is representative enough to demonstrate underwriting logic, even though it is small and static.
- `dispute_rate = dispute_count / transaction_count` is a reasonable first-order proxy for merchant dispute risk in a BNPL context.
- The current binary label, `high_dispute_risk = 1 if dispute_rate >= 0.001 else 0`, is acceptable for a demonstration model even though it is a proxy rather than a future-outcome label.
- The simulated API internal risk tier contains useful underwriting signal and is directionally aligned with merchant quality.
- The simulated API transaction summary is close enough to the CSV business metrics to support reconciliation and anomaly flagging, even though the two sources are not guaranteed to match exactly.
- REST Countries is sufficient for geography enrichment in this version, and no additional legal-entity verification is required for non-UK merchants.
- Companies House enrichment is not available in this submission because an API key could not be obtained in time, so the fallback is to preserve `registration_number` from the CSV and continue without company-profile enrichment.
- The ClarityPay website scrape is used as contextual information for reporting and business understanding, not as a strong merchant-level predictive signal.
- The sample PDF contains relevant contextual information for the report and collated view, even though it is not merchant-specific across the full dataset.
- The current expected-loss formula is intentionally simple:
  - `expected_loss_proxy = predicted_high_risk_probability * 0.035 * monthly_volume`
- A simple logistic regression is acceptable for the first version because interpretability matters more than squeezing out a small performance gain on this dataset.
- Human review is still assumed for adverse decisions, pricing overrides, exception handling, and policy interpretation.

## Current Trade-offs

- The dataset is extremely small, so model evaluation is directionally useful but not strong enough to justify aggressive automation.
- The label is based on current-period behavior rather than a true future-period outcome, which limits how production-like the modeling setup can be.
- The model is interpretable and easy to debug, but it does not capture nonlinear interactions or temporal behavior as well as stronger gradient-boosted or sequential approaches would.
- The scraper and public API enrichments are lightweight and quick to implement, but they are inherently more brittle than first-party or contracted data feeds.
- The PDF ingestion is asynchronous via application code, not through a durable queue or workflow engine, which is fine for a take-home but not sufficient for a fault-tolerant production system.
- The LLM report is valuable for synthesis and committee communication, but it adds cost, latency, vendor dependency, and hallucination risk.
- The new reconciliation flags are intentionally conservative; they are better for surfacing data issues than for serving as hard acceptance/rejection rules.
- The pipeline currently runs as a single-process job and writes artifacts locally, which is simple for iteration but weak for lineage, replayability, and operational robustness.

## What I will do Next for deploying in Production

## 1. Data Contracts and Source Governance

- Establish explicit source contracts for every upstream input, including schema version, required fields, allowable nullability, enum values, and freshness expectations.
- Promote the CSV validation from "row-level correctness" to "dataset contract correctness":
  - exact column set
  - duplicate policies
  - allowed country values
  - volume and count bounds
  - registration-number formatting rules by jurisdiction
- Add contract tests against the simulated API and any future real APIs so breaking payload changes are caught in CI before deployment.
- Replace implicit assumptions with versioned contract documentation stored in the repo and referenced in deployment runbooks.
- Add a formal fallback policy per source:
  - when a source can fail open
  - when it must fail closed
  - who gets alerted
  - how the downstream report should represent degraded data quality

## 2. Orchestration, Scheduling, and Idempotency

- Move orchestration into a workflow system such as Dagster, Prefect, or Airflow.
- Give each pipeline run a durable `run_id` and persist run metadata:
  - start time
  - finish time
  - code version
  - model version
  - source fingerprints
  - environment
- Persist raw, validated, collated, scored, and reporting outputs in immutable storage partitions keyed by `run_id`.
- Add retries with exponential backoff for all networked sources and configurable retry budgets per source type.
- Use checkpoints so re-running a partially failed workflow does not reprocess everything unnecessarily.
- Ensure the same inputs always produce the same outputs where possible, or at least produce auditable deltas when non-determinism exists.

## 3. Storage, Lineage, and Reproducibility

- Store raw source payloads in a "bronze" layer before any parsing or transformation.
- Store validated normalized records in a "silver" layer.
- Store model-ready feature sets and scored merchant outputs in a "gold" layer.
- Persist lineage columns through every stage:
  - `run_id`
  - source name
  - source record identifier
  - ingestion timestamp
  - validation status
  - fallback-used flag
- Track model artifacts as first-class objects:
  - coefficients
  - training metrics
  - feature list
  - label definition
  - training window
  - calibration version
- Keep report prompt versions and report hashes so the exact report can be reconstructed later.

## 4. Data Quality Monitoring

- Turn the current quality report into operational monitoring rather than a passive artifact.
- Add thresholded alerts for:
  - invalid-row spikes
  - missing enrichment spikes
  - sudden country-distribution changes
  - unexpected risk-tier distribution changes
  - extreme feature-value shifts
  - scrape failures or empty scrape outputs
- Add drift monitoring at both the raw-data and feature-engineering levels.
- Separate "warning" thresholds from "block the run" thresholds so the system does not become noisy or brittle.
- Review the reconciliation thresholds periodically because the right tolerance depends on source behavior and business policy.
- Add dashboards for risk and data-engineering teams so data problems are visible without opening raw artifact files.

## 5. Feature Engineering and Feature Governance

- Move from ad hoc engineered columns to a governed feature registry or feature-spec document.
- Separate explanatory features from decision-driving features so downstream users understand what is used for automated scoring versus narrative reporting.
- Add temporal discipline to feature generation:
  - no feature should use information from after the prediction timestamp
  - label windows and feature windows should be clearly defined
- Promote feature tests that assert:
  - no null explosions
  - no impossible ratios
  - stable categorical vocabularies
  - bounded ranges for engineered metrics
- Add merchant-history features once longitudinal data exists:
  - prior review outcomes
  - rolling dispute trends
  - growth velocity
  - repeat exception history
  - prior reserves or settlement holds
- Consider richer merchant-type classification using more reliable business descriptors than name-token heuristics once better source data is available.

## 6. Modeling, Retraining, and Validation

- Replace the current same-period proxy label with a true forward-looking target:
  - next-30-day dispute rate
  - next-90-day chargeback count
  - realized loss
  - bad-debt or fraud outcomes
- Evaluate models on time-based splits rather than only random splits once historical data is available.
- Compare the current logistic regression baseline against stronger but still explainable candidates such as gradient-boosted trees.
- Add calibration analysis because pricing decisions depend on probability quality, not only ranking quality.
- Track decision-threshold performance for multiple business use cases:
  - manual review routing
  - reserve triggers
  - settlement-delay rules
  - pricing adjustments
- Build a retraining cadence tied to data volume and drift, not an arbitrary calendar schedule.
- Add challenger models before replacing the production champion model.
- Version models formally and support rollback if a new model underperforms after deployment.

## 7. Portfolio Risk and Pricing Improvements

- Move from a simple expected-loss proxy to a better economic model:
  - expected loss
  - expected revenue
  - contribution margin
  - reserve requirement
  - concentration risk by sector / geography / merchant size
- Add portfolio limits and risk appetite policies:
  - sector concentration caps
  - stale-review exposure caps
  - jurisdiction-based limits
  - unregistered-merchant exposure limits
- Link model outputs to underwriting actions more explicitly:
  - approve
  - approve with pricing uplift
  - approve with reserve
  - manual review
  - decline
- Add policy simulation so risk can test the effect of threshold or pricing changes on portfolio-level P&L.

## 8. LLM Reporting Hardening

- Treat the LLM report as a controlled summarization layer, not a primary source of truth.
- Constrain the prompt to only the fields and metrics that are allowed to appear in the final report.
- Add report validation checks:
  - required sections present
  - no invented merchant IDs
  - no invented metrics
  - no mismatch between reported counts and computed counts
- Add a deterministic "fallback report mode" for cases where the LLM vendor is unavailable or times out.
- Persist prompt and report hashes, which has already started via the PDF `Traceback Metadata` page, and extend that to run-level governance records.
- Add reviewer sign-off fields if reports are used in any formal approval process.
- Evaluate migration from the current Gemini SDK to the newer supported SDK to reduce technical-debt risk.

## 9. Security, Compliance, and Access Control

- Move secrets into a secret manager rather than local `.env` files in deployed environments.
- Apply role-based access control to:
  - raw merchant data
  - scored outputs
  - LLM prompts and reports
  - audit metadata
- Encrypt data at rest and in transit.
- Add audit logging for:
  - who ran the pipeline
  - who accessed reports
  - who approved overrides
  - who changed thresholds or model versions
- Review whether any source fields should be treated as sensitive or regulated data, especially if expanded with additional merchant or consumer information later.

## 10. Reliability, Testing, and Release Process

- Expand automated tests beyond unit tests into:
  - contract tests
  - end-to-end pipeline smoke tests
  - failure-path tests
  - regression tests on stable fixtures
- Add synthetic canary runs on a fixed dataset so the team can detect behavioral regressions before every release.
- Introduce CI checks for:
  - schema stability
  - prompt-template stability
  - feature-column changes
  - artifact generation
- Add release notes whenever model logic, thresholds, or report prompt behavior changes.
- Add SLOs for the production system:
  - pipeline completion time
  - source freshness
  - report generation latency
  - model-score availability

## 11. Human-in-the-Loop Operating Model

- Define which decisions can be automated and which must remain human-approved.
- Require manual review for:
  - high-risk merchants above a configured threshold
  - large expected-loss outliers
  - severe data-quality issues
  - contradictory cross-source signals
- Provide reviewers with enough context to challenge the model:
  - source provenance
  - quality flags
  - top model drivers
  - prior decision history
- Create a feedback loop so analyst overrides are captured and later used for policy and model improvement.

## 12. Recommended Deployment Sequence

- Phase 1: Operationalize the current pipeline.
  - workflow orchestration
  - durable storage
  - secret management
  - run metadata
  - dashboarding
- Phase 2: Improve data quality and source depth.
  - Companies House integration
  - stronger legal-entity verification
  - better merchant descriptors
  - historical feature windows
- Phase 3: Upgrade modeling and decisioning.
  - forward-looking labels
  - calibration
  - challenger models
  - threshold simulations
- Phase 4: Harden governance.
  - model approval process
  - report review controls
  - audit trails
  - retraining and rollback standards

## Summary

The current pipeline is a strong prototype: it is structured, validated, test-backed, and now produces both human-readable and auditable reporting artifacts. For production, the biggest gaps are not cosmetic. They are operational and governance-related:

- stronger source contracts
- durable orchestration and storage
- true future-looking labels
- calibration and monitoring
- better human review workflows
- tighter controls around LLM usage and auditability

If those areas are addressed in order, the system can evolve from a good take-home implementation into a production-capable underwriting workflow.
