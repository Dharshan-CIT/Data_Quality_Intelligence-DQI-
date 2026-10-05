# DQI Methodology

Every number this platform shows is computed from the dataset in front of it,
using the formulas below. Weights live in [`configs/weights.yaml`](../configs/weights.yaml)
and are meant to be edited per organization — nothing here is a universal constant.

## 1. Profiling

Standard pandas/numpy descriptive statistics per column (nulls, uniqueness,
quantiles, IQR-based outliers) and per dataset (row/column counts, memory,
duplicate rows, missing-cell percentage). See [`dqi_core/profiling.py`](../dqi_core/profiling.py).

## 2. The 10-Pillar Quality Model

Each pillar returns a 0–100 score. Where a pillar cannot be measured directly
from a single flat file (no ground truth, no related tables), the result sets
a `limitation` field explaining the proxy used instead of silently presenting
a proxy as a direct measurement:

| Pillar | How it's measured |
|---|---|
| Completeness | `100 − missing_pct × 1.5` |
| Uniqueness | Severity-weighted deduction for duplicate rows / duplicate keys |
| Validity | Severity-weighted deduction for range/format/date violations |
| Consistency | Severity-weighted deduction for minority-variant categorical labels |
| Conformity | Severity-weighted deduction for type/schema-violating values |
| Timeliness | **Proxy**: share of date values that are not improbably in the future |
| Accuracy | **Proxy**: statistical outlier rate (1.5× IQR) — not a ground-truth check |
| Integrity | **Proxy**: uniqueness of identifier/key columns (no FK data in a single file) |
| Freshness | Share of "last touched" timestamps older than a 180-day threshold |
| Traceability | **Proxy**: presence of audit-friendly column name patterns (id, created_at, source) |

Every "severity-weighted deduction" uses:

```
deduction(issue) = min(40, (issue.severity / 5) × issue.frequency_pct)
pillar_score = 100 − Σ deduction(issue)   [floored at 0]
```

The per-issue cap of 40 points prevents one extreme issue from single-handedly
zeroing out a pillar.

## 3. Dataset Health Index

```
Health Index = Σ (pillar_score × pillar_weight) / Σ pillar_weight
```

Default weights are in `configs/weights.yaml → health_index.weights` and are
editable live in the **Quality Pillars** page. Bands: Excellent ≥90, Good ≥75,
Needs Attention ≥55, Poor ≥35, else Critical.

## 4. Impact Score — the central contribution

```
Impact Score = Severity × Downstream Sensitivity × Business Exposure × (1 + capped frequency modifier)
```

- **Severity** (1–5): intrinsic severity of the issue *type* (e.g. a duplicate
  primary key is a 5; a formatting inconsistency is a 2). See
  `configs/weights.yaml → impact.severity`.
- **Downstream Sensitivity** (0–1): 1.0 if the issue's column is in the
  user-configured "critical columns" list, else a default (0.4). Dataset-wide
  issues (no single column) get a small bump since they touch more consumers.
- **Business Exposure** (0–1):
  - If the user has configured a revenue/operational-cost-per-record
    assumption (Impact Analysis page), exposure is `affected_records × $value`,
    min-max normalized across this dataset's issues.
  - **If unconfigured** (the default — no dollar figure is invented), exposure
    falls back to a **log-scaled** share of affected records:
    `log1p(affected_records) / log1p(total_rows)`. This is deliberately
    sub-linear: a *linear* frequency proxy would let "touches everything,
    barely matters" issues dominate the ranking the way pure frequency-based
    prioritization does — defeating the point of an impact-aware score.
- **Frequency modifier**: `1 + min(0.15, cap) × (affected_records / total_rows)`.
  Frequency is real signal, but capped at a 15% multiplier so it can inform,
  not dominate, the final score — per the project's core design rule.

The raw score is scaled to 0–100 against the theoretical maximum
(`severity=5 × sensitivity=1 × exposure=1 × (1+cap)`).

## 5. Frequency vs. Impact Rankings

Two independent rankings are built from the same issue list:

- **Frequency rank**: `rank(affected_records, descending)`
- **Impact rank**: `rank(impact_score, descending)`
- **Rank change** = `frequency_rank − impact_rank` (positive = the issue is
  *more* urgent under impact-aware ranking than raw frequency suggested).

## 6. Statistical Validation

`scipy.stats.spearmanr` and `scipy.stats.kendalltau` are computed between the
frequency-rank and impact-rank arrays, **live, on whatever issues the current
dataset produced** — never hard-coded. The historical DQI project reported
`rs≈0.5175, τ≈0.4242` on its own benchmark run; this build will only
reproduce those numbers if run against that exact dataset and configuration,
and the UI says so explicitly.

## 7. Business Impact Estimation

```
Estimated Exposure = affected_records × (revenue_per_record + operational_cost_per_record) × severity_factor
```

`severity_factor` maps severity 1–5 to a 0.05–1.0 multiplier
(`configs/weights.yaml → business_impact.impact_factor_by_severity`). If no
revenue/cost assumption is entered, the UI labels the result **UNCONFIGURED**
rather than silently showing `$0` as if it were a measurement.

## 8. Root-Cause Analysis

Rule-based lookup from `issue_type` to a probable upstream cause and
contributing factors (`dqi_core/rca.py`). Every result is explicitly split
into **DETECTED EVIDENCE** (the issue's measured explanation) and **INFERRED
EXPLANATION** (a plausible-but-unverified cause) — the UI never merges the two.

## 9. Remediation Validation

After remediation, a two-sample **Kolmogorov–Smirnov test**
(`scipy.stats.ks_2samp`) compares each numeric column's before/after
distribution. `p > 0.05` is reported as "no significant distortion"; `p ≤ 0.05`
flags that the remediation step may have changed the underlying signal, not
just the defects. This is computed from the actual before/after data, not
asserted.

## 10. PII Detection

Regex pattern matching against column values (email, phone, SSN-like,
credit-card-like, IP address), with a name-based confidence bonus. Labeled
**"Heuristic Detection"** everywhere in the UI — this is not a GDPR/CCPA/HIPAA
compliance determination.

## 11. Reproducibility

- Random seeds are fixed in `data/sample/generator.py` (`seed=7`) — the sample
  dataset's injected defect rates are deterministic and documented in that file.
- All scoring weights live in `configs/weights.yaml`, version-controlled and
  human-readable.
- `dqi_core/` has zero Streamlit/UI imports — every number here can be
  reproduced from a plain Python script (see `scripts/smoke_test.py`).
