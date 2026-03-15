# BNPL Underwriting Committee Report

## Executive Summary
This report evaluates a portfolio of 50 BNPL merchants based on recent pipeline extraction and risk modeling. The portfolio exhibits a **Mean Predicted Risk Probability of 42.1%**, projecting ~21 merchants into the high-dispute-risk category. The total Expected Loss (EL) proxy for the portfolio is calculated at **$50,877**. 

A critical portfolio vulnerability is **stale underwriting**; the vast majority of reviewed accounts have not been evaluated in over 400 days. Furthermore, specific sub-sectors (Beauty/Wellness, Food/Restaurants) are driving outsized expected losses. To maintain target ROA, the committee must strictly align Merchant Discount Rates (MDR) and settlement terms (e.g., reserves, T+X delays) with these modeled expected losses.

## Merchant Highlights
Based on predicted high-risk probabilities, merchants have been segmented into explicit risk bands. MDR and settlement pricing must be adjusted to absorb the associated EL.

**🔴 Extreme Risk (Probability > 80%) - *Action: Implement Reserves / Re-price***
*   **MedSpa Wellness Co (M002):** 95.5% Risk Prob | EL: $2,976. 
    *   *Rationale:* Beauty/Wellness sector, unregistered US entity, high dispute rate (23.8 bps). 
    *   *Pricing Impact:* EL warrants an immediate +150 bps MDR increase and a 10% rolling reserve to cover potential chargeback liability.
*   **CleanEats Kitchen (M012):** 85.6% Risk Prob | EL: $839.
    *   *Rationale:* Food/Restaurant sector with an API-to-CSV volume mismatch of 1.78x. Rapid, un-underwritten growth increases bust-out risk.
    *   *Pricing Impact:* Move from T+2 to T+5 settlement until volume stabilization is verified.
*   **StyleHub Fashion (M011):** 80.8% Risk Prob | EL: $2,773.
    *   *Rationale:* High absolute dispute count (6) and unregistered Spanish entity.
    *   *Pricing Impact:* High EL requires +100 bps MDR adjustment. 

**🟡 Medium Risk (Probability 40% - 80%) - *Action: Enhanced Due Diligence***
*   **LaseyAway Beauty (M005):** 78.1% Risk Prob | EL: $1,231. Unregistered entity; high ticket gap ratio.
*   **BookNook Education (M014):** 41.7% Risk Prob | EL: $599. Volume API/CSV mismatch (1.34x) offsets the typically safe education sector classification. 
    *   *Pricing Impact:* Maintain current pricing but trigger manual review.

**🟢 Low Risk (Probability < 40%) - *Action: Standard/Preferred Pricing***
*   **GreenLeaf Retail (M001):** 4.6% Risk Prob | EL: $205. 
*   **TechGear Electronics (M003):** 14.1% Risk Prob | EL: $1,037. 
    *   *Rationale:* Large volume, tech sector, registered entities.
    *   *Pricing Impact:* Eligible for volume-based MDR discounting to retain share of wallet.

## Model Output
The dispute risk model exhibits strong predictive power with an **ROC AUC of 0.80** and an overall accuracy of 67%. 

**Key Drivers of Expected Loss (Positive Coefficients):**
1.  **Sectors:** `Beauty/Wellness` (+0.71) and `Food/Restaurants` (+0.66). These sectors structurally experience higher service-related disputes, increasing total BNPL liability.
2.  **Review Age:** `review_age_days` (+0.47). Stale reviews are the strongest behavioral predictor of elevated dispute risk. 
3.  **Volume Band:** `small` (+0.44). Micro/small merchants show higher volatility in fulfillment capabilities.

**Mitigators of Risk (Negative Coefficients):**
1.  **Scale:** `log_monthly_volume` (-0.76). Higher total volume strongly correlates with institutionalized dispute management and lower risk.
2.  **Sectors:** `Software/Tech` (-0.70) and `Education/Media` (-0.52). 

*Note:* The model identifies `volume_mismatch_flag` as a negative risk feature (-0.98). While minor mismatches in training data correlated with lower rates, extreme outliers (detailed below) represent unquantified tail risk outside standard model bounds.

## Red Flags
1.  **Systemic Stale Reviews:** 100% of the sample merchants have a `review_is_stale = 1` flag (average review age >430 days). The model explicitly penalizes this. Current policy dictates reviews every 365 days; the portfolio is out of compliance.
2.  **Unregistered Entities:** Merchants M002, M003, M005, M007, M009, M011, M013, M016, M018, and M020 lack formal registration numbers. In the event of merchant insolvency or severe chargeback spikes, BNPL recovery/recourse is severely compromised, directly increasing Loss Given Default (LGD).
3.  **Extreme Volume Discrepancies:**
    *   *Artisan Crafts Co (M020):* API volume is **3.18x** stated monthly volume.
    *   *CleanEats Kitchen (M012):* API volume is **1.78x** stated monthly volume.
    *   Such drastic deviations from underwritten baselines often precede fulfillment failures or bust-out fraud.

## Portfolio View
*   **Total Merchants Analyzed:** 50
*   **Expected High-Risk Merchants:** 21.06 (42.1% of portfolio)
*   **Expected Loss Proxy Total:** $50,877.58
*   **Summary:** The portfolio skews risky due to a high concentration of small/micro merchants in volatile sectors, compounded by outdated underwriting data. The EL proxy of ~$50k must be benchmarked against total portfolio revenue to ensure the BNPL program remains profitable. 

## Recommendations
To protect portfolio yield and align risk with pricing, the committee should execute the following:

1.  **Immediate Remediation of Stale Accounts:** Initiate a bulk re-underwriting sprint for all merchants with a `review_age_days` > 365. Halt limit increases for these accounts until completed.
2.  **Repricing by Sector:** Implement a baseline MDR premium (+50 to +100 bps) for all new and renewing merchants in the `Beauty/Wellness` and `Food/Restaurants` sectors to pre-fund expected dispute losses.
3.  **Implement Dynamic Holdbacks:** For merchants exhibiting >1.5x API-to-CSV volume mismatches (e.g., M020, M012), automatically transition settlement terms from T+2 to T+5 or apply a 10% rolling reserve until the volume spike is manually validated.
4.  **Registration Requirement:** Update the onboarding funnel to strictly require corporate registration numbers for EU/US merchants. Offboard unregistered merchants that cross the $100k/month volume threshold due to unacceptable LGD profiles.