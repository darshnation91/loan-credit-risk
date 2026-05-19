# Loan Portfolio Credit Risk Analytics System

**Python · SQL Server · PostgreSQL · Groq API · Streamlit · Power BI · MCP**

---

## Overview

End-to-end loan portfolio risk management and reporting platform built for a banking/NBFC client. Provides credit risk managers and senior leadership with real-time visibility into a ₹1,270 Cr loan book — replacing manual Excel-based weekly reporting with an automated enrichment pipeline, AI-powered query interface, and a 6-page executive Power BI dashboard.

**Business Problem:** The risk team spent significant analyst time weekly pulling loan data, calculating default rates, and preparing leadership reports manually — with no single source of truth and no way for non-technical users to query the live portfolio.

**Outcomes:** 35% reduction in manual reporting effort · 15–20% improvement in risk decision turnaround

**Live App:** https://darshnation9138-loan-risk-dashboard.hf.space

---

## Architecture

```
SQL Server — LoanRiskDB
(Client loan portfolio · source of truth)
         │
         │  Scheduled daily · 6 AM · Windows Task Scheduler
         │
         ├─ pipeline/transform.py    validate + enrich (10+ risk fields)
         ├─ pipeline/load.py         write enriched tables to SQL Server + export
         └─ pipeline/sync_to_cloud.py  incremental sync → Neon PostgreSQL
                    │
         ┌──────────┴──────────┐
         │                     │
   Power BI Desktop       Neon PostgreSQL
   (ODBC · SQL Server)    (cloud · AI app layer)
         │                     │
   6-Page Dashboard       Streamlit AI Chat
   Executive reporting    NL → SQL → Live answer
         │                     │
         └──────────┬──────────┘
                    │
             Power BI Page 6
          (AI app embedded via iframe)
                    │
              MCP Server
        (6 tools · developer AI queries)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Source DB | SQL Server Express · LoanRiskDB | Client loan portfolio — source of truth |
| Pipeline | Python · Pandas · SQLAlchemy · pyodbc | Validate, enrich, load |
| Scheduling | Windows Task Scheduler | Daily 6 AM pipeline trigger |
| Cloud Sync | Python · psycopg2 · Neon PostgreSQL | Incremental sync for AI app layer |
| BI Dashboard | Power BI Desktop | 6-page executive dashboard |
| AI Chat App | Groq API (LLaMA 3.3 70B) · Streamlit | NL → SQL → live answers |
| MCP Server | Python MCP SDK | AI-callable developer analytics tools |
| Deployment | Hugging Face Spaces | Cloud hosting for AI app |

---

## Project Structure

```
loan-credit-risk/
├── streamlit_app.py              ← AI chat app (root — required by Hugging Face)
├── requirements.txt
├── README.md
├── .gitignore
│
├── .streamlit/
│   └── secrets.toml              ← API keys — never committed
│
├── config/
│   └── settings.py               ← DB strings · file paths · risk constants
│
├── pipeline/
│   ├── transform.py              ← read SQL Server → validate → enrich
│   ├── load.py                   ← load enriched tables + export for Power BI
│   ├── sync_to_cloud.py          ← incremental SQL Server → Neon sync
│   └── run_pipeline.py           ← single entry point · orchestrates all steps
│
├── mcp_server/
│   ├── server.py
│   └── tools/
│       └── loan_queries.py       ← 6 AI-callable analytics tools
│
├── powerbi/
│   └── Loan Risk Analysis.pbix
│
└── data/
    └── exports/                  ← pipeline output · gitignored
        ├── loans_clean.csv
        └── powerbi_loans.xlsx
```

---

## Data Layer

### Source: SQL Server — LoanRiskDB · `loans` table · 33 columns

| Column | Type | Description |
|---|---|---|
| loan_id | TEXT | Unique account identifier |
| annual_income | INT | Annual income (INR) |
| loan_amount | INT | Sanctioned amount (INR) |
| loan_purpose | TEXT | Home · Vehicle · Education · Personal · Medical · Business |
| credit_score | INT | 300–900 |
| risk_score | INT | 0–100 |
| risk_category | TEXT | HIGH · MEDIUM · LOW |
| is_defaulted | INT | 1 = defaulted · 0 = active |
| debt_to_income_ratio | FLOAT | Monthly obligations / monthly income |
| monthly_emi | INT | EMI amount (INR) |
| employment_type | TEXT | Salaried · Self-Employed · Business Owner · Freelancer |
| state / city | TEXT | Location |
| application_date | DATE | Application date |

### Pipeline Enrichment — Fields Added

| Field | Calculation |
|---|---|
| `loan_to_income_ratio` | `loan_amount / annual_income` |
| `monthly_income` | `annual_income / 12` |
| `emi_burden_pct` | `(monthly_emi / monthly_income) × 100` |
| `credit_score_band` | Very Poor / Fair / Good / Very Good / Exceptional |
| `age_group` | 21–25 / 26–35 / 36–45 / 46–55 / 55+ |
| `income_band` | <3L / 3L–6L / 6L–12L / 12L–25L / 25L+ |
| `loan_size` | Small / Medium / Large / Very Large |
| `application_year/month/quarter` | Extracted from application_date |

The pipeline also creates a `risk_summary` aggregation table — pre-grouped by risk category, loan purpose, employment type, income band, and credit score band — used by Power BI summary visuals for faster query performance.

---

## Pipeline

### Run

```bash
python pipeline/run_pipeline.py       # full pipeline — all 3 steps
python pipeline/transform.py          # read + validate + enrich only
python pipeline/load.py               # load to SQL Server + export
python pipeline/sync_to_cloud.py      # sync to Neon only
```

### Scheduling — Windows Task Scheduler

New loan records enter SQL Server daily via the client's loan management system. The pipeline runs automatically every morning at 6 AM so dashboards and the AI app always reflect previous day's complete data.

```
Task Scheduler → Create Basic Task
  Name    : Loan Risk Pipeline
  Trigger : Daily · 06:00 AM
  Program : C:\path\to\venv\Scripts\python.exe
  Args    : D:\Development\loan-credit-risk\pipeline\run_pipeline.py
```

For environments with multiple pipelines or alerting requirements, the natural upgrade is **Apache Airflow** — which adds DAG-based dependency management, automatic retries, and a monitoring dashboard.

### Incremental Sync to Neon

`sync_to_cloud.py` checks the latest `application_date` already present in Neon and only syncs records newer than that timestamp — so daily sync transfers only new records regardless of total portfolio size.

```python
# Core incremental logic
last_synced  = get_max_date_from_neon()
new_records  = read_sql(f"SELECT * FROM loans WHERE application_date > '{last_synced}'")
insert_neon(new_records)
```

---

## Power BI Dashboard

6-page dark-theme dashboard. Connected to SQL Server via ODBC (Import mode).

### Data Model — Star Schema

`loans` fact table + custom `Date Table` built in DAX.

```dax
Date Table =
ADDCOLUMNS(
    CALENDAR(MIN(loans[application_date]), MAX(loans[application_date])),
    "Year",       YEAR([Date]),
    "Month",      MONTH([Date]),
    "Month Name", FORMAT([Date], "MMM"),
    "Quarter",    "Q" & QUARTER([Date]),
    "Week No",    WEEKNUM([Date]),
    "Day Name",   FORMAT([Date], "DDD"),
    "Year Month", FORMAT([Date], "YYYY-MMM")
)
```

Relationship: `Date Table[Date]` → `loans[application_date]` · One-to-many · Single direction

Power Query sort columns enforce correct ordering for `credit_score_band`, `age_group`, and `income_band`.

### Key DAX Measures

```dax
Default Rate % =
DIVIDE(COUNTROWS(FILTER(loans, loans[is_defaulted] = 1)), COUNTROWS(loans), 0) * 100

Portfolio at Risk % =
DIVIDE([Defaulted Amount Cr], [Total Loan Amount Cr], 0) * 100

Default Rate Color =
IF([Default Rate %] > 15, "#E24B4A", "#3B6D11")

Portfolio Subtitle Color =
VAR curr = CALCULATE(DIVIDE(SUM(loans[loan_amount]),10000000),
               'Date Table'[Year] = YEAR(MAX('Date Table'[Date])))
VAR prev = CALCULATE(DIVIDE(SUM(loans[loan_amount]),10000000),
               'Date Table'[Year] = YEAR(MAX('Date Table'[Date]))-1)
RETURN IF(curr - prev > 0, "#3B6D11", "#E24B4A")
```

### Pages

| Page | Visuals |
|---|---|
| Executive Summary | 5 KPI cards · Donut · Bar · Line with anomaly detection · Treemap |
| Risk Deep Dive | Default by purpose · Credit score distribution · Risk scatter |
| Geographic Risk | Top 10 states · Exposure bar · State → City drilldown matrix |
| Borrower Profile | Age · Income band · Employment type · Gender |
| AI Insights | Key Influencers · Decomposition Tree · Q&A Visual · Smart Narrative |
| AI Assistant | Streamlit AI app embedded via HTML Content iframe |

**Power BI AI features used (all free — no Premium required):**
Key Influencers · Decomposition Tree · Q&A Visual · Smart Narrative · Anomaly Detection

---

## AI Chat Application

Streamlit app embedded on Power BI Page 6. Risk analysts query the live portfolio in plain English.

### NL → SQL → Answer Pipeline

```
User question
    │
    ▼ Question enriched by Groq
    ▼ SQL generated (model outputs SQL only — no estimates)
    │
    ▼ SQL executed on live Neon PostgreSQL
    │  [failed query → self-healing retry auto-corrects SQL]
    │
    ▼ Result set → Groq → executive narrative
      (model narrates only values in the result — zero hallucination)
    │
    ▼ Data table + written summary returned to user
```

**Pre-built query engine:** High-frequency questions route to pre-written optimised SQL templates. AI SQL generation handles custom or complex queries. This hybrid gives consistency for common questions and flexibility for novel ones.

### Features

- 12 quick-insight sidebar buttons for one-click common queries
- Live KPI header: portfolio value · default rate · avg credit score · high risk count
- SQL transparency panel — users can expand and view the exact query
- Indian number formatting (₹ Cr · ₹ Lakh)
- Self-healing SQL — failed queries auto-corrected and retried

---

## MCP Server

6 analytics tools callable from developer AI environments (VS Code Copilot, Claude, Cursor) via Model Context Protocol.

| Tool | Returns |
|---|---|
| `get_portfolio_summary` | Total loans · default rate · exposure at risk |
| `get_high_risk_loans` | Top accounts by risk score in HIGH category |
| `get_default_rate_by_purpose` | Default breakdown by loan purpose |
| `search_loan_by_id` | Single account lookup by loan ID |
| `get_state_risk_report` | Default rate and exposure by state |
| `get_city_worst_portfolio` | Cities ranked by default rate |

```bash
python mcp_server/server.py
```

---

## Setup

### Prerequisites
Windows 10/11 · Python 3.12+ · SQL Server Express · ODBC Driver 17 for SQL Server · Power BI Desktop

### Install

```bash
git clone https://github.com/YOUR_USERNAME/loan-credit-risk.git
cd loan-credit-risk
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

Create `.streamlit/secrets.toml` — never commit:
```toml
GROQ_API_KEY = "your-groq-api-key"
NEON_URL     = "your-neon-connection-url"
```

Update `config/settings.py`:
```python
SQL_SERVER = r"YOUR_SERVER_NAME\SQLEXPRESS"   # match your SQL Server instance
```

### Run

```bash
python pipeline/run_pipeline.py    # full pipeline
streamlit run streamlit_app.py     # AI chat locally
python mcp_server/server.py        # MCP server
```

Open `powerbi/Loan Risk Analysis.pbix` → update data source name → Refresh.

---

## Key Design Decisions

**Python for transformation, not SQL stored procedures** — Enrichment logic changes when the client updates underwriting criteria. Python is easier to version-control, unit-test, and modify than stored procedures deployed to a production database.

**Two databases** — SQL Server serves Power BI via native ODBC (no Gateway needed). Neon PostgreSQL serves the cloud-deployed AI app. Same enriched data, two access patterns.

**Incremental sync** — Full reload works at current volume but becomes a bottleneck as the loan book grows. Incremental sync on `application_date` keeps daily sync fast regardless of total portfolio size.

**Hybrid query engine in AI app** — Pre-written SQL for high-frequency questions, AI-generated SQL for custom queries. Consistency where it matters, flexibility where needed.

---

## Future Enhancements

- **Apache Airflow** — DAG-based orchestration replacing Task Scheduler, with retries and failure alerting
- **dbt** — versioned SQL transformation models with built-in data quality tests and lineage documentation
- **Row-Level Security** — branch and region-level access control in Power BI
- **FastAPI** — REST API layer to expose portfolio analytics for external system consumption
- **ML model** — default probability prediction using existing risk features

---

*Python · SQL Server · Neon PostgreSQL · Groq API · Streamlit · Power BI · MCP · Windows Task Scheduler*
