# Data Quality Intelligence (DQI)

**An impact-aware framework for assessing and prioritizing data quality issues in real-world analytics.**

## Highlights

- **Ten quality pillars:** completeness, uniqueness, validity, consistency, timeliness, accuracy, integrity, conformity, freshness and traceability, combined into one weighted Dataset Health Index.
- **Impact-aware ranking:** each issue is scored by severity, downstream sensitivity, business exposure and a capped frequency term, then compared with frequency ranking (Spearman and Kendall).
- **Safe remediation:** cleaning is applied to a copy, then checked with two-sample Kolmogorov–Smirnov tests and before-and-after health scores.
- **Governance:** PII pattern detection, data-contract validation and an audit log.
- **Live web app:** FastAPI backend with WebSocket pipeline progress, and a React dashboard with a drift timeline, row-level inspector, lineage view and shareable read-only reports.
- **Explainable by design:** a deterministic, rule-based engine, so every score traces back to a rule and a weight. No model training is needed.

## 1. Overview

Most data-quality tooling ranks issues by how *often* they occur. DQI ranks
them by how much they *matter*:

```
Data Quality Issue → Severity + Downstream Sensitivity + Business Exposure → Impact Score → Priority
```

The platform walks the full workflow — upload, profile, assess (10 pillars),
detect issues, score impact, rank, explain root cause, remediate, validate,
report, and govern — and its most important page is **Impact Analysis**,
where frequency-based and impact-aware prioritization are compared directly
on your own data, with Spearman/Kendall statistics computed live.

## 2. Research Motivation & Problem Statement

Frequency-first prioritization systematically under-ranks rare-but-severe
defects (e.g. a corrupted primary key affecting 0.5% of rows) in favor of
common-but-trivial ones (e.g. inconsistent capitalization affecting 30% of
rows). DQI's contribution is a transparent, configurable scoring model that
corrects for this, plus the statistical tooling to measure *how much* the two
approaches disagree on a given dataset.

## 3. Architecture

```
dqi_core/        UI-independent engine (pure Python/pandas/numpy/scipy)
  ingestion.py          robust CSV/Parquet/Excel loading
  profiling.py          dataset + column profiling engine
  quality/pillars.py     10-pillar quality model
  issues/detection.py    rule-based issue detectors
  impact/
    scoring.py            impact score engine (the core contribution)
    ranking.py            frequency vs. impact rankings
    stats.py              Spearman / Kendall validation
  health.py              Dataset Health Index
  business_impact.py     transparent $ exposure estimation
  rca.py                 rule-based root-cause analysis
  remediation/
    engine.py             governed remediation (audit-logged, non-destructive)
    validation.py         before/after + KS test
  governance/
    pii.py                heuristic PII detection + SHA-256 tokenization
    contracts.py          local YAML data-contract validation
    audit.py              append-only audit log
  integrations/
    streaming.py          Kafka (optional) + honest local Simulation Mode
    external_trackers.py  Jira / PagerDuty (optional, never fakes success)
  assistant.py           deterministic local Q&A over computed results
  reporting.py           JSON / CSV / PDF report export

backend/          FastAPI REST + WebSocket API — imports dqi_core, never the reverse
  main.py               app wiring + the /ws/{session_id} live socket
  session_store.py       in-memory per-browser-tab session state
  pipeline_runner.py      replays a computed pipeline as live staged events
  ws_manager.py           WebSocket connection registry (per session_id)
  serializers.py          dqi_core objects -> plain JSON dicts
  routers/                datasets, results, impact, remediation, governance,
                          reports, assistant

frontend/         React (Vite) single-page app — the primary UI
  src/context/            ThemeContext (light/dark), SocketContext (the one
                          live WebSocket), DataContext (datasets + active one)
  src/pages/               Dashboard, Profiling, Quality Pillars, Issue
                          Explorer, Impact Analysis, Remediation, Dataset
                          Comparison, Governance, Reports & Assistant
  src/components/          Layout, PipelineProgress (live stage-by-stage
                          upload progress), shared UI primitives

app/              Legacy Streamlit UI (multipage), kept as an alternate
                  thin client over the same dqi_core — not actively developed
  Home.py, pages/1..8    same page set as the React app, Streamlit-flavored

data/sample/      synthetic dataset generator + generated sample CSV
configs/          weights.yaml — every scoring assumption, in one editable file
contracts/        example YAML data contract
tests/            pytest suite covering every dqi_core module
docs/METHODOLOGY.md   the formulas behind every number the UI shows
```

**Primary UI is now FastAPI + React**, with one WebSocket per browser tab
(`/ws/{session_id}`) driving three kinds of live behavior: stage-by-stage
pipeline progress on upload (profiling → issue detection → quality pillars →
health index → impact scoring → ranking stats, each a real completed
computation, paced for legibility — see `backend/pipeline_runner.py`), a
continuously-ticking streaming-simulation feed on the Governance page, and
push-based dashboard refresh after a remediation commit (no polling). The
Streamlit app in `app/` still works against the same `dqi_core` engine and is
kept as a lighter-weight alternate UI, but the React app is where active
development happens.

`dqi_core` was built UI-independent from the start specifically so a real API
layer could be added later without touching the engine — that bet paid off
here: the FastAPI backend is a thin wrapper that reuses every `dqi_core`
function unchanged, including the Streamlit app's original formulas and tests.

## 4. Features

- Robust multi-format ingestion (CSV/Parquet/Excel) that never crashes the
  session on a single bad file.
- Dataset- and column-level profiling.
- 10-pillar quality model, each with a score, explanation, affected
  records/columns, and recommendations — pillars that can't be measured
  directly (Timeliness, Accuracy, Integrity, Traceability) are labeled as
  proxies, not asserted as ground truth.
- Rule-based issue detection (missing values, duplicates, invalid
  ranges/dates, outliers, categorical inconsistency, schema conformity).
- **Impact-aware scoring** with configurable severity/sensitivity/exposure
  weights, separate from raw frequency.
- Side-by-side frequency vs. impact rankings with live Spearman/Kendall
  statistical validation.
- Transparent, user-configured business exposure estimation (never invents a
  dollar figure).
- Rule-based root-cause analysis with explicit detected-evidence vs.
  inferred-explanation separation.
- Governed remediation (duplicate removal, missing-value strategies, invalid
  numeric handling, formatting/date normalization) with a full audit trail,
  a quarantine table, and a before/after KS-test validation report.
- Dataset Health Index with editable pillar weights.
- Multi-dataset workspace and comparison.
- Governance: heuristic PII detection + SHA-256 tokenization, local YAML data
  contract validation, append-only audit log.
- Optional integrations (Kafka streaming, Jira, PagerDuty) with honest
  "integration unavailable" fallbacks and a clearly labeled local Simulation
  Mode — never fake telemetry or fake success.
- Deterministic local assistant that answers only from already-computed
  results (LLM hook point provided, off by default).
- JSON / CSV / PDF report export.

## 5. Technology Stack

Python, pandas, PyArrow, NumPy, SciPy, Streamlit, Plotly, ReportLab, PyYAML, pytest.

## 6. Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## 7. Running locally

**React app (primary) — needs two terminals, backend then frontend:**

```bash
# Terminal 1 — API + WebSocket backend
python -m uvicorn backend.main:app --port 8000

# Terminal 2 — React dev server (proxies /api and /ws to :8000)
cd frontend
npm install   # first time only
npm run dev
```

Open `http://localhost:5173`. Click **"Load sample retail dataset"** (or drag
a file onto the dropzone) and watch the pipeline run live, stage by stage.

**Run both servers from VS Code (no terminal typing):**

1. Open this folder in VS Code.
2. Press `Ctrl+Shift+P` → **Tasks: Run Task** → **DQI: Start everything**
   (defined in `.vscode/tasks.json`).
3. Wait for `Application startup complete` (backend) and `Local: http://localhost:5173/` (frontend).
4. To stop: **Terminal → Terminate Task**.

If port 8000 or 5173 is already in use, close the older terminal that is still running the server first.

**Streamlit app (legacy/alternate, single process):**

```bash
python -m streamlit run app/Home.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## 8. Dataset usage

- `data/sample/retail_sample.csv` — a synthetic 5,000+ row retail-transactions
  dataset with documented, reproducible injected defects (see
  `data/sample/generator.py`, `seed=7`). Regenerate with:
  ```bash
  python data/sample/generator.py
  ```
- Bring your own CSV/Parquet/Excel file via the Home page uploader.
- Benchmark datasets such as UCI Online Retail or NYC TLC are not bundled
  (licensing) — download them yourself and upload via the same uploader.

## 9. Scoring methodology & 10. Statistical methodology

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for every formula, weight,
and statistical test used, with the exact file/function that implements it.

## 11. API documentation

`dqi_core` is a plain importable Python package — there is no HTTP API in
this build (see Architecture above for why). Every function/class is
documented inline; `scripts/smoke_test.py` demonstrates the full pipeline as
a script, independent of Streamlit.

## 12. Testing

```bash
python -m pytest tests/ -v
```

29 tests cover profiling, issue detection, pillar scoring, impact scoring and
ranking, rank correlation, remediation operations, KS validation, contract
validation, and PII detection/tokenization.

## 13. Screenshots

Run the app locally and visit each page — the Impact Analysis page in
particular is designed to be the visual centerpiece (frequency-rank vs.
impact-rank scatter plot against a "perfect agreement" line).

## 14. Research results

On the bundled sample dataset (`seed=7`), a representative run reports:

- Dataset Health Index: ~94/100 (Excellent)
- 11 detected issues
- Spearman's rs ≈ 0.43, Kendall's τ ≈ 0.35 between frequency rank and impact
  rank — a moderate-to-weak correlation, demonstrating real disagreement
  between frequency-first and impact-aware prioritization.

These numbers are **computed live by the app**, not hard-coded — re-run the
generator or upload a different dataset and they will change. The historical
DQI project reported rs≈0.5175, τ≈0.4242 on its own benchmark; this build
does not attempt to force a match to those figures.

## 15. Limitations

- Several quality pillars (Timeliness, Accuracy, Integrity, Traceability)
  are documented proxies, not direct measurements — a single flat file has
  no ground truth or related tables to check against.
- PII detection is heuristic regex matching, not a compliance determination.
- Business exposure is $0/unconfigured until the user supplies a revenue or
  cost assumption — the UI never fabricates a dollar figure.
- Kafka/Jira/PagerDuty integrations require real credentials/brokers to do
  anything beyond reporting "unavailable"; Streaming Mode without them is
  clearly labeled Simulation Mode.
- The optional assistant is deterministic by default; wiring in a live LLM
  (via `ANTHROPIC_API_KEY`) is a documented extension point, not implemented
  in this build.

## 16. Future work

- A FastAPI layer over `dqi_core` for programmatic/CI access (the module
  boundary is already in place for this).
- A React frontend, if/when richer interaction (drag-drop contract editing,
  collaborative workspaces) outgrows Streamlit.
- Real Kafka consumer wiring behind the existing `integrations/streaming.py`
  interface.
- Multi-table referential-integrity checks once a workspace supports more
  than one related dataset at a time.

## 17. Project Structure

```
DQI/  (this repo)
├── app/                 Streamlit UI
├── dqi_core/             engine (UI-independent)
├── data/sample/          synthetic data generator + sample CSV
├── configs/weights.yaml  every scoring assumption, centralized
├── contracts/            example data contract
├── reports/              exported JSON/CSV/PDF land here (gitignored)
├── tests/                pytest suite
├── docs/METHODOLOGY.md   formulas and methodology
├── scripts/smoke_test.py end-to-end pipeline script (no UI)
├── .env.example          optional integration credentials
├── requirements.txt
└── README.md
```
