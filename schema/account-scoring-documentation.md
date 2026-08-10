# Workwize Account Scoring Model — Full Documentation

## 1. Overview

The account scoring model classifies ~323K Coresignal companies into ICP (Ideal Customer Profile) and Non-ICP using a combination of hard gates and a 6-signal composite score. Companies must pass all hard gates to be scored. The top 50% of scored companies are classified as ICP (~90K companies).

**Purpose**: TAM prioritization for outbound targeting. The score predicts which companies are most likely to enter the sales pipeline, progress to Stage 3, and close as won deals.

**Data source**: Coresignal company database (snapshot from November 2025), enriched with Workwize warehouse coverage data.

**Output table**: `analysis.coresignal_scoring__company_scoring`

---

## 2. Hard Gates

All four gates must pass for a company to be scored. Failing any gate = Non-ICP (untiered, excluded from scoring).

### Gate 1: FTE Minimum — `employees_count >= 150`

| Detail | Value |
|---|---|
| Threshold | 150 employees (LinkedIn/Coresignal count) |
| Evidence | The Coresignal dataset is pre-filtered to ≥150 FTE, so this gate is effectively baked in. Of the 33 won deals not in Coresignal, 20 (61%) were below 150 FTE — confirming the dataset boundary aligns with a natural ICP floor. |
| Won deals excluded | 0 (within Coresignal dataset) |

### Gate 2: FTE Maximum — `employees_count <= 10,000`

| Detail | Value |
|---|---|
| Threshold | 10,000 employees |
| Evidence | Pipeline data shows sharp conversion decline above 5K FTE. The 5K-10K bucket has 1.6% won rate (2 wins from 126 deals). The 10K-25K bucket has **0% won rate** (0 wins from 59 deals). The single 25K+ win was UST (38K FTE) — a $18K pilot deal on a $1.7B revenue IT services company, not a representative customer. |
| Won deals excluded | 1 (UST at 38K FTE — $18K pilot deal). The 2 wins in the 5K-10K range (including Cohesity at 7.5K FTE) pass this gate. |
| Rationale | Companies above 10K FTE have near-zero conversion rates and typically have internal IT procurement teams that handle equipment provisioning. The occasional pilot deal ($18K) doesn't justify scoring and targeting these companies. |

### Gate 3: Regions — `num_regions >= 2`

| Detail | Value |
|---|---|
| Threshold | Employees in at least 2 distinct shipping jurisdictions |
| Definition | Each country = 1 region, EXCEPT the EU (27 member states) which counts as 1 region |
| EU member states | Austria, Belgium, Bulgaria, Croatia, Cyprus, Czech Republic, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden |
| Non-EU European countries | UK, Switzerland, Norway, Iceland, Serbia, etc. — each counts as a separate region |
| Evidence | Single-region companies (e.g., US-only) had 4.9% won rate with only 3 wins total. These are edge cases — companies like Deer Oaks (US healthcare, 292 FTE) and WebTPA (US insurance, 520 FTE) that don't have cross-border shipping pain. |
| Won deals excluded | 2 (Deer Oaks, WebTPA — both US-only) |
| Rationale | Workwize's core value proposition is solving cross-border IT equipment shipping. Within the EU, shipping is easy (single market), so a company with employees in Germany + Netherlands is effectively single-region from a logistics perspective. A company needs employees in at least 2 distinct shipping jurisdictions to have the pain Workwize solves. |
| Alternatives considered | We tested ≥3 regions (macro-level) which would cut TAM to ~55K but excluded 18 won deals. The country-level ≥2 definition with EU grouping is the right balance — it captures the shipping jurisdiction logic without being overly restrictive. We also tested minimum employee thresholds per region (5 or 10 employees to "count" as a region) but this excluded 8-12 more won deals for only marginal TAM reduction. The score handles granularity better than hard gates. |

### Gate 4: Covered Employees — `covered_employees >= 100`

| Detail | Value |
|---|---|
| Threshold | At least 100 employees in countries where Workwize has active warehouse coverage |
| Calculation | `ROUND(employees_count × percent_employees_in_warehouse_regions / 100)` |
| Source | `warehouse_employee_coverage_scoring` transform, which maps employee countries to Workwize warehouse regions |
| Evidence | Clear cliff in pipeline data: companies with <100 covered employees have 9.4% S3 rate and 1.6% won rate, vs 26-30% S3 and 4-5% won for ≥100. Only 2 won deals had <100 covered employees (Codeway with 33 covered, XM Cyber with 94 covered — both headquartered in non-warehouse countries: Turkey and Israel). |
| Won deals excluded | 2 (Codeway, XM Cyber) |
| Rationale | If Workwize can't physically serve most of a company's employees through its warehouse network, the deal is unserviceable regardless of how good the firmographic fit is. This is a serviceability gate, not a fit gate. |

### Gate Summary

| Gate | Threshold | TAM Excluded | Won Deals Excluded | Reason |
|---|---|---|---|---|
| FTE min | ≥ 150 | Baked into dataset | 0 | Below minimum viable company size |
| FTE max | ≤ 10,000 | ~3.4K companies | 1 (UST, $18K pilot) | Zero conversion at 10K-25K; internal IT procurement |
| Regions | ≥ 2 (EU=1) | ~80K companies | 2 (Deer Oaks, WebTPA) | No cross-border shipping pain |
| Coverage | ≥ 100 covered | ~64K companies | 2 (Codeway, XM Cyber) | Unserviceable by Workwize warehouse network |
| **Total** | | **~144K excluded** | **5 of 96 matched won deals (5.2%)** | |

---

## 3. Scoring Signals

All 6 signals are **percentile-ranked** using `PERCENT_RANK()` across the gated population (~179K companies). NULLs are coalesced to 0 before ranking. This means:
- A company with no funding is ranked at the bottom of the funding distribution (genuinely unfunded, not missing data)
- A company at the 80th percentile on a signal scores higher than 80% of all gated companies on that signal

### Signal 1: Hiring Intensity — Weight 20%

| Detail | Value |
|---|---|
| Formula | `active_job_postings_count / employees_count` |
| Source | `staging.coresignal_scoring__hiring_activity` (from `raw.company_data.coresignal_company_data.active_job_postings_count`) |
| Coverage | 99.9% of companies (scalar field, always available) |
| Null treatment | NULL or 0 postings → 0 (ranks at bottom) |
| Correlation with Stage 0 entry | 0.011 (weak — not an entry predictor) |
| Correlation with Stage 3 conversion | **0.1127** (strongest of all signals) |
| Correlation with Won | **0.1017** (strongest of all signals) |
| Evidence | Monotonic conversion gradient: companies with 10%+ hiring intensity have 35.3% S3 rate and 9.0% won rate, vs 17.3% S3 and 2.3% won for companies with 0 postings. Companies actively hiring need to provision equipment for new employees — direct demand signal. |
| Why it's weighted 20% | Strongest conversion predictor. Directly measures the action (hiring) that creates the need for IT equipment provisioning. |

### Signal 2: Region Distribution — Weight 20%

| Detail | Value |
|---|---|
| Formula | HHI concentration index on employee distribution across geographic regions |
| Source | `companies_account_scoring.global_distribution_scoring` (pre-existing v1 sub-transform) |
| Scoring logic | Composite of breadth (40% weight), HHI inverse concentration (30%), and top-region share (30%). Higher score = more spread across regions. |
| Coverage | 100% (always available) |
| Correlation with Stage 0 entry | **0.042** (2nd strongest for entry) |
| Correlation with Stage 3 | 0.048 |
| Correlation with Won | -0.002 (near zero) |
| Evidence | Strong quintile gradient for pipeline entry: top quintile has 97.1 per 10K entry rate vs 4.4 for bottom quintile (22x). Measures core PMF — multi-country workforce = cross-border equipment shipping pain. |
| Why it's weighted 20% | Core product-market fit signal. Directly proxies the geographic distribution that creates the need for Workwize's cross-border provisioning. |

### Signal 3: Growth Expansion — Weight 20%

| Detail | Value |
|---|---|
| Formula | Composite of 12-month + 3-month employee growth rates (40%), geographic expansion into new regions (35%), and distributed growth outside primary region (25%) |
| Source | `companies_account_scoring.growth_expansion_scoring` (pre-existing v1 sub-transform) |
| Dependencies | `companies.employees_per_country_per_month`, `companies.employees_region_breakdown_per_month` |
| Coverage | 98.3% (1.7% NULL — no monthly data) |
| Null treatment | NULL → 0 (no growth data = no growth) |
| Correlation with Stage 0 entry | 0.024 |
| Correlation with Stage 3 | 0.046 |
| Correlation with Won | 0.038 |
| Evidence | Consistent positive correlation across all three stages — the only signal that predicts across the full funnel. Fast-growing companies (20%+ YoY) have 32.8% S3 and 6.4% won rate vs 20.3% S3 and 2.9% won for 0-5% growth. |
| Why it's weighted 20% | Best all-round predictor. Employee growth = continuous hiring = continuous provisioning need. Geographic expansion = new countries = new shipping complexity. |

### Signal 4: Funding — Weight 15%

| Detail | Value |
|---|---|
| Formula | Composite of recency (40%), stage (30%), amount (20%), round count (10%). Excludes debt financing. |
| Source | `companies_account_scoring.funding_round_scoring` (pre-existing v1 sub-transform) |
| Dependencies | `companies.funding_rounds` |
| Coverage | 4.1% have funding data (95.9% are genuinely unfunded) |
| Null treatment | NULL → 0 (no funding = unfunded, not missing data. Coresignal covers these companies — absence of funding records means they haven't raised VC rounds.) |
| Time dependency | Uses `CURRENT_DATE()` for recency decay. When running on historical snapshot, replace with snapshot date. |
| Correlation with Stage 0 entry | 0.027 |
| Correlation with Stage 3 | **0.097** (with percentile ranking — was 0.009 with min-max due to normalization destroying the signal) |
| Correlation with Won | 0.043 |
| Evidence | Companies with ANY funding data enter pipeline at 195.1 per 10K vs 21.5 for unfunded (9x). Within funded companies, top quintile converts at 289.8 per 10K. Funded companies typically precede hiring surges and have mandates to scale operations. |
| Why it's weighted 15% | Strong Stage 3 predictor. Indicates growth-stage companies that are scaling headcount and operations. Lower weight than hiring/region/growth because 96% of companies are unfunded — the signal is powerful but sparse. |

### Signal 5: Fast Turnover Ratio — Weight 15%

| Detail | Value |
|---|---|
| Formula | `(employees_count_sales + employees_count_customer_service) / employees_count` |
| Source | `staging.coresignal_scoring__department_breakdown` (from `raw.company_data.coresignal_company_data.employees_count_breakdown_by_department`) |
| Coverage | 98% (department data available for most companies) |
| Null treatment | NULL → 0 |
| Correlation with Stage 0 entry | 0.033 |
| Correlation with Stage 3 | **0.0997** |
| Correlation with Won | **0.0721** |
| Evidence | Monotonic gradient: companies with 15%+ sales+CS ratio have 31.1% S3 and 6.1% won rate, vs 19.1% S3 and 3.2% won for 0-3%. Sales and customer service roles have the highest turnover rates in any organization — more role churn = more equipment onboarding/offboarding cycles = higher Workwize value. |
| Why it's weighted 15% | Second strongest conversion predictor after hiring intensity. Directly measures the structural characteristic (high-turnover workforce) that creates recurring provisioning demand. |

### Signal 6: Acquisition Activity — Weight 10%

| Detail | Value |
|---|---|
| Formula | Composite of recency (60%) and volume in last 36 months (40%). Recency decays linearly from 6-36 months. Volume capped at 5 acquisitions. |
| Source | `companies_account_scoring.acquisition_scoring` (pre-existing v1 sub-transform) |
| Dependencies | `companies.acquisitions` |
| Coverage | 13.1% have acquisition data (86.9% haven't acquired) |
| Null treatment | NULL → 0 (no acquisitions = hasn't acquired, not missing data) |
| Time dependency | Uses `CURRENT_DATE()` for recency decay. |
| Correlation with Stage 0 entry | **0.063** (strongest entry predictor with percentile ranking) |
| Correlation with Stage 3 | 0.078 |
| Correlation with Won | 0.019 |
| Evidence | Companies with ANY acquisition data enter pipeline at 134.3 per 10K vs 12.7 for non-acquirers (10.5x). M&A creates immediate IT integration needs — absorbing another company's workforce means provisioning equipment for new employees across new geographies. |
| Why it's weighted 10% | Strong entry predictor and moderate Stage 3 predictor. Lower weight because the signal is sparse (87% have no data) and weakens significantly for Won prediction (0.019). |

### Signal Weight Summary

| Signal | Weight | Primary strength | Key metric |
|---|---|---|---|
| Hiring intensity | 20% | Conversion (S3 + Won) | r=0.113 S3, r=0.102 Won |
| Region distribution | 20% | Pipeline entry | 22x quintile lift for entry |
| Growth expansion | 20% | All-round predictor | Consistent across all stages |
| Funding | 15% | Stage 3 conversion | r=0.097 S3 (with percentile) |
| Fast turnover ratio | 15% | Conversion (S3 + Won) | r=0.100 S3, r=0.072 Won |
| Acquisition activity | 10% | Pipeline entry | 10.5x entry rate for acquirers |
| **Total** | **100%** | | |

---

## 4. Composite Score Formula

```sql
score = (
    PERCENT_RANK(region_distribution)  × 0.20 +
    PERCENT_RANK(growth_expansion)     × 0.20 +
    PERCENT_RANK(hiring_intensity)     × 0.20 +
    PERCENT_RANK(funding)              × 0.15 +
    PERCENT_RANK(fast_turnover_ratio)  × 0.15 +
    PERCENT_RANK(acquisition_activity) × 0.10
) × 100
```

Produces a score from 0 to 100. Percentile ranks are computed within the gated population only.

### ICP Classification

- **ICP**: Passes all 4 hard gates AND score in top 50% of gated population
- **Non-ICP**: Fails any gate OR score in bottom 50%

---

## 5. Normalization Method: Why Percentile Rank, Not Min-Max

The v1 model used min-max normalization: `1 + 99 × (value - min) / (max - min)`. This was replaced with percentile ranking in the new model.

### Problem with min-max

Min-max normalization is dominated by outliers. A single company with extreme values defines the entire 1-100 scale, compressing all other companies into a narrow range.

**Example — Growth 2y ago signal (v1)**:
- Raw data had 1,473 distinct values ranging from -7,050 to +6,337
- Average company growth: ~5 employees
- Min-max formula: `1 + 99 × (5 - (-7050)) / (6337 - (-7050))` = **41.37**
- Result: 99.7% of companies scored between 41.27 and 41.56 — effectively a constant
- The signal appeared to have zero discrimination, but the underlying data had meaningful variance

**Example — Offices signal (v1)**:
- One company (PCRK Group) had 164 offices, scoring 100
- 95.8% of companies scored under 10
- The entire meaningful range was compressed into the bottom 10% of the scale

### Why percentile ranking works better

Percentile ranking (`PERCENT_RANK()`) distributes companies evenly across the 0-1 scale by rank order, regardless of the underlying distribution shape. It is:
- **Outlier-resistant**: A company with 164 offices gets percentile ~1.0, but companies with 5-10 offices still spread across 0.5-0.9 instead of being compressed to 0.03
- **Scale-invariant**: Works equally well for signals with tight distributions (growth) and wide distributions (region)
- **Interpretable**: "This company is at the 80th percentile on hiring intensity" is immediately meaningful

### NULL handling

NULLs are coalesced to 0 before ranking. This is a deliberate design choice:
- **Funding NULL = genuinely unfunded** (not missing data). Coresignal covers these companies. If they had raised VC funding, it would be recorded.
- **Acquisition NULL = hasn't acquired**. Same reasoning.
- **Hiring NULL = 0 active postings**. The field is a scalar on every company record.

This was validated against pipeline data: companies with no funding convert at 21.5 per 10K vs 195.1 for funded companies. The "no funding" signal is real and should be penalized, not treated as neutral.

---

## 6. Signals Investigated and Rejected

### Removed from v1

| Signal | v1 Weight | Why removed | Evidence |
|---|---|---|---|
| **Number of offices** | 20% | Negatively correlated with Stage 3 (-0.006) and Won (-0.017). Acts as a proxy for company size, which above ~2,500 FTE is negatively correlated with conversion. | Quintile analysis showed non-monotonic pattern (Q2=0 anomaly). Offices correlate with FTE (r≈0.8), and FTE above the sweet spot hurts conversion. |
| **Growth 6m 2y ago** | 10% | 99.7% of companies had the same normalized score (41.3 ± 0.15) due to min-max outlier compression. Even with percentile ranking, correlation was 0.017 (Stage 3) and -0.015 (Won) — near zero. | The raw signal had 1,473 distinct values but was killed by normalization. Even with correct normalization, it adds no predictive value beyond what growth_expansion already captures. |

### Investigated but not added

| Signal | What it measures | Why rejected | Evidence |
|---|---|---|---|
| **Remote workers** | Employees in countries without an office (inferred) | Near-zero correlation: 0.009 (entry), 0.003 (S3), -0.04 (Won). Country-matching between employee data and office locations was noisy, and multi-country presence is already captured by region distribution. | Tested both absolute count and ratio. Neither discriminated. |
| **IT-to-FTE ratio** | Technical employees / total employees | Positive correlation (not inverted as hypothesized): higher IT ratio = better. But correlation was moderate (0.053 entry, 0.034 S3, 0.055 Won) and collinear with industry/company type. The growth expansion and region signals already capture the underlying pattern. | The hypothesis "understaffed IT = more pain" was wrong. Higher IT ratio means tech-heavy company = more laptops to manage. But this is already captured by other signals. |
| **FTE contraction** | YoY employee count decrease | Near-zero correlation as a standalone signal (0.007 Won). The bucket analysis showed mild shrinkage (0-5%) had a 5.2% won rate, but only 12 wins — too few to build a signal. Heavy shrinkage (20%+) converted poorly (2.3%). | Investigated after finding edge cases (DispatchHealth, Uptempo) that signed during downsizing. The pattern is real but too rare and narrow to be a useful scoring component. |

---

## 7. Validated Performance

### Methodology

Validation was performed against the 2025 New Sales Pipeline (deals created 2025-01-01 through 2026-08-03). 129 total won deals. Companies were matched to Coresignal data via `properties_coresignal_company_id` (17 matches) and domain name fallback (79 matches), for a total of **96 matched won deals** (74.4% match rate). The 33 unmatched were investigated individually.

The 33 unmatched won deals were investigated:
- 20 (61%) were below 150 FTE (below Coresignal dataset boundary)
- 4 (12%) had domain/name mismatches (company exists in Coresignal under different identity)
- 6 (18%) had no data available
- 2 (6%) were just below the 150 FTE cutoff
- 1 (3%) was an internal test deal

### Lift Analysis — Stage 0 Entry (Inbound)

Population: Full gated TAM (~180K companies). Outcome: Did company enter inbound pipeline?

| Decile | Lift | Deals |
|---|---|---|
| 10 (top) | **6.65x** | 600 |
| 9 | 1.25x | 113 |
| 8 | 0.88x | 79 |
| 1 (bottom) | 0.03x | 3 |

Top decile captures **67% of all inbound pipeline entries** with 6.65x lift. Near-perfect monotonic decrease.

### Lift Analysis — Stage 3 Conversion

Population: Companies that entered pipeline (~2.2K matched deals). Outcome: Did deal reach Stage 3?

| Metric | Value |
|---|---|
| Top decile lift | **1.54x** |
| Bottom decile lift | 0.59x |
| Correlation | **0.156** |

### Lift Analysis — Won

Population: Companies that entered pipeline. Outcome: Did deal close as won?

| Metric | Value |
|---|---|
| Top quintile lift | **1.92x** |
| Bottom quintile lift | 0.64x |
| Correlation | **0.085** |

### Cumulative Capture Analysis

Starting from the full gated TAM (~179K after 10K cap), how many won deals are captured at different score cutoff percentiles?

| Keep Top | TAM Size | Won Captured | Won Lost | Capture Rate |
|---|---|---|---|---|
| 100% | ~179K | 91 | 0 | 100% |
| 50% (= ICP) | ~90K | 88 | 3 | **96.7%** |
| 40% | ~72K | 86 | 5 | 94.5% |
| 30% | ~54K | 80 | 11 | 87.9% |
| 20% | ~36K | 77 | 14 | 84.6% |
| 10% | ~18K | 68 | 23 | 74.7% |
| 5% | ~9K | 57 | 34 | 62.6% |
| 1% | ~2K | 25 | 66 | 27.5% |

The top 10% of the TAM captures **~75% of all wins**. The top 50% (ICP cutoff) captures **~97%** while cutting the TAM in half.

*Note: Numbers adjusted from pre-10K-cap analysis (92 won deals in gated population) to post-10K-cap (91 — UST excluded). Capture rates are approximately the same.*

### Comparison to v1

| Metric | v1 (production) | New model |
|---|---|---|
| Signals | 6 (region, growth, offices, funding, growth_2y, acquisition) | 6 (region, growth, hiring, funding, turnover, acquisition) |
| Normalization | Min-max (outlier-sensitive) | Percentile rank |
| Hard gates | None (soft tiers + binary `is_servicable` flag) | 4 gates (FTE 150-10K, regions ≥ 2, coverage ≥ 100) |
| Stage 0 top decile lift | 5.80x | **6.65x** (+15%) |
| Stage 3 correlation | 0.086 | **0.156** (+81%) |
| Won top quintile lift | 1.23x | **1.92x** (+56%) |

---

## 8. Edge Cases — Won Deals Outside ICP

### Won deals failing hard gates (5 deals, $217K total revenue)

| Company | Gate Failed | Amount | FTE | Why they signed |
|---|---|---|---|---|
| Deer Oaks | Regions (US-only) | $63K | 292 | US behavioral health org with distributed field clinicians across US |
| WebTPA | Regions (US-only) | $95K | 520 | US insurance admin, single-country operations |
| Codeway | Coverage (33 covered) | $27K | 462 | Turkish venture builder, most employees in Turkey (not in warehouse network) |
| XM Cyber | Coverage (94 covered) | $14K | 434 | Israeli cybersecurity, most employees in Israel (not in warehouse network) |
| UST | FTE max (38K) | $18K | 38,497 | Indian IT services giant ($1.7B revenue), $18K pilot deal for one internal team |

### Won deals in bottom 50% of scored population (3 deals lost at ICP cutoff)

These 3 deals pass all gates but score below the 50th percentile. They represent $57K in total revenue. Investigation of the full set of 11 deals below the 30th percentile revealed three root causes:

**1. Stale Coresignal data (3 companies)**: DispatchHealth (actual 600 FTE vs 1,245 in data — downsized), Uptempo (actual 125 vs 266 — downsized), Sun River Health (actual 1,800 vs 643 — undercounted due to grant-funded/clinical staff).

**2. Invisible ownership structures (3 companies)**: Corporate Visions (PE-backed by Riverside Company), PTV Group (PE-backed by Bridgepoint), Uptempo (PE-backed by Rubicon). PE ownership drives vendor consolidation mandates that create Workwize demand, but Coresignal only tracks VC funding, not PE ownership.

**3. Structural pain invisible to firmographic data (3 companies)**: Genesys Works (nonprofit expanding from 7 to 14 cities), X-Team (2,400 remote contractors across 60+ countries), ACR (97% remote workforce with $500 stipend). These companies have strong provisioning needs from workforce structures (field clinicians, contractor communities, remote-first orgs) that don't register in traditional firmographic signals.

### Implication

The score correctly identifies these as lower-probability outbound targets. However, **the score should NOT be used to disqualify inbound leads**. When these companies come to Workwize proactively, they should be worked regardless of score. The score is for TAM prioritization, not lead qualification.

---

## 9. Technical Architecture

### Transform Pipeline

```
staging/coresignal_scoring/department_breakdown     → staging.coresignal_scoring__department_breakdown
staging/coresignal_scoring/hiring_activity          → staging.coresignal_scoring__hiring_activity
intermediate/coresignal_scoring/hard_gates          → intermediate.coresignal_scoring__hard_gates
intermediate/coresignal_scoring/signal_percentiles  → intermediate.coresignal_scoring__signal_percentiles
analysis/coresignal_scoring/company_scoring         → analysis.coresignal_scoring__company_scoring
```

### Dependencies on existing transforms

| Transform | Domain | Used for |
|---|---|---|
| `companies.companies` | companies/ | Base company table (ID, name, website, FTE, HQ) |
| `companies.employees_per_country` | companies/ | Region gate (country-level employee distribution) |
| `companies_account_scoring.global_distribution_scoring` | companies_account_scoring/ | Region distribution signal |
| `companies_account_scoring.growth_expansion_scoring` | companies_account_scoring/ | Growth expansion signal |
| `companies_account_scoring.funding_round_scoring` | companies_account_scoring/ | Funding signal |
| `companies_account_scoring.acquisition_scoring` | companies_account_scoring/ | Acquisition signal |
| `companies_account_scoring.warehouse_employee_coverage_scoring` | companies_account_scoring/ | Coverage gate |

### Raw data source

`raw.company_data.coresignal_company_data` — Coresignal company database. Last synced: 2025-12-17. Contains 166 columns including nested arrays for employee distribution, departments, job postings, funding rounds, acquisitions, and office locations.

### Time-dependent signals

Two sub-transforms use `CURRENT_DATE()` which causes score drift:
- `funding_round_scoring`: recency decay on months since latest funding round
- `acquisition_scoring`: recency decay + rolling 12m/36m acquisition windows

When the Coresignal data is refreshed, these transforms should be re-run. If validating against a historical snapshot, replace `CURRENT_DATE()` with the snapshot date.

### Materialization

All transforms use `materialization: "table"` per CLAUDE.md convention. Views have caused dataset creation failures and performance issues.

---

## 10. Output Schema

### `analysis.coresignal_scoring__company_scoring`

| Column | Type | Description |
|---|---|---|
| `company_id` | INT64 | Coresignal company ID |
| `company_name` | STRING | Company name |
| `website` | STRING | Company website |
| `industry` | STRING | Coresignal industry classification |
| `hq_country_iso2` | STRING | HQ country (ISO 3166-1 alpha-2) |
| `employees_count` | INT64 | Total employee count |
| `num_regions` | INT64 | Number of shipping jurisdictions (EU=1) |
| `covered_employees` | FLOAT64 | Employees in Workwize warehouse-covered countries |
| `gate_fte_min` | BOOL | FTE ≥ 150 |
| `gate_fte_max` | BOOL | FTE ≤ 10,000 |
| `gate_regions` | BOOL | Regions ≥ 2 |
| `gate_coverage` | BOOL | Covered employees ≥ 100 |
| `passes_all_gates` | BOOL | All 4 gates pass |
| `region_percentile` | FLOAT64 | Region distribution signal (0-1) |
| `growth_percentile` | FLOAT64 | Growth expansion signal (0-1) |
| `funding_percentile` | FLOAT64 | Funding signal (0-1) |
| `acquisition_percentile` | FLOAT64 | Acquisition signal (0-1) |
| `hiring_percentile` | FLOAT64 | Hiring intensity signal (0-1) |
| `turnover_percentile` | FLOAT64 | Fast turnover ratio signal (0-1) |
| `score` | FLOAT64 | Composite score (0-100) |
| `score_percentile_rank` | FLOAT64 | Percentile rank within gated population (0-100) |
| `is_icp` | BOOL | ICP classification (top 50% of gated) |

Rows: ~325K (all Coresignal companies). Non-gated companies have NULL for signal percentiles and score. `is_icp = FALSE` for non-gated companies.
