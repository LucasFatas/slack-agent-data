# v3 Account Scoring Model

## Overview

Score 332K Coresignal companies into ICP (top ~90K) and Non-ICP using hard gates + a 6-signal composite score. Companies passing all gates are scored 0-100 and the top 50% by score are classified as ICP.

## Hard Gates

All three must pass for a company to be scored. Failing any → Non-ICP.

| Gate | Threshold | Logic |
|---|---|---|
| **FTE min** | ≥ 150 | `employees_count >= 150` (baked into dataset) |
| **FTE max** | ≤ 10,000 | `employees_count <= 10000` — 0% won rate at 10K-25K bucket (59 deals, 0 wins) |
| **Regions** | ≥ 2 | Country-level, EU (27 member states) counts as one region. A company needs employees in at least 2 distinct shipping jurisdictions. |
| **Covered employees** | ≥ 100 | `ROUND(employees_count × percent_employees_in_warehouse_regions / 100) >= 100` |

### Region Definition

Each country = 1 region, EXCEPT EU member states which all count as 1 region (because cross-border shipping within the EU single market is easy).

EU member states (27): Austria, Belgium, Bulgaria, Croatia, Cyprus, Czech Republic, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden.

Non-EU European countries are separate regions: UK, Switzerland, Norway, Iceland, Serbia, etc.

## Scoring Signals (6)

All signals are **percentile-ranked** (`PERCENT_RANK()`) across the full gated population. NULLs are coalesced to 0 before ranking — no funding genuinely means unfunded, not missing data.

| Signal | Weight | Source | Description |
|---|---|---|---|
| **Hiring intensity** | 20% | `active_job_postings_count / employees_count` from raw Coresignal | Active hiring relative to company size. Strongest conversion predictor. |
| **Region distribution** | 20% | `global_distribution_scoring.region_global_distribution_score` | HHI concentration index on employee distribution across regions. |
| **Growth expansion** | 20% | `growth_expansion_scoring.growth_expansion_score` | Composite of 12m + 3m employee growth, geographic expansion, distributed growth. |
| **Funding** | 15% | `funding_round_scoring.funding_score` | Recency (40%), stage (30%), amount (20%), round count (10%). Excludes debt. |
| **Fast turnover ratio** | 15% | `(employees_count_sales + employees_count_customer_service) / employees_count` from department breakdown | High-turnover roles as % of headcount = more equipment cycling. |
| **Acquisition** | 10% | `acquisition_scoring.acquisition_score` | Recency (60%) and volume (40%) of acquisitions in last 36 months. |

## Composite Formula

```sql
v3_score = (
    PERCENT_RANK(OVER ORDER BY region_raw)              × 0.20 +
    PERCENT_RANK(OVER ORDER BY growth_raw)               × 0.20 +
    PERCENT_RANK(OVER ORDER BY COALESCE(funding_raw, 0)) × 0.15 +
    PERCENT_RANK(OVER ORDER BY COALESCE(acq_raw, 0))     × 0.10 +
    PERCENT_RANK(OVER ORDER BY COALESCE(hiring_intensity, 0)) × 0.20 +
    PERCENT_RANK(OVER ORDER BY COALESCE(turnover_ratio, 0))   × 0.15
) × 100
```

## ICP Classification

- **ICP**: Passes all 3 hard gates AND v3_score in top 50% of gated population (~90K companies)
- **Non-ICP**: Fails any gate OR v3_score in bottom 50%

## Validated Performance

| Metric | v1 (production) | v3 |
|---|---|---|
| Stage 0 top decile lift | 5.80x | **6.65x** |
| Stage 3 correlation | 0.086 | **0.156** |
| Won top quintile lift | 1.23x | **1.92x** |
| Won deals in top 50% | — | 89/92 (**96.7%**) |
| Won deals excluded by gates | — | 4/97 (4.1%) |

## Time-Dependent Signals

Three sub-transforms use `CURRENT_DATE()` and will drift over time:
- `funding_round_scoring`: recency decay on months since latest round
- `acquisition_scoring`: recency decay + rolling 12m/36m windows
- `company_scoring` (v1): growth_2y_ago lookup (not used in v3)

When running on a historical snapshot (e.g., November 2025 data), replace `CURRENT_DATE()` with the snapshot date in funding and acquisition sub-transforms.

## Data Sources

- All signals derive from `raw.company_data.coresignal_company_data`
- Sub-transforms in `companies_account_scoring.*` and `companies.*` datasets in Weld
- Pipeline validation against `analysis.commercial.deal_clean` (2025 New Sales Pipeline, deals created 2025-01-01+)
- Company matching: Coresignal ID via `hubspot.company.properties_coresignal_company_id`, fallback to domain matching
