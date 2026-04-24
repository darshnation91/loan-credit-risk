# 🏦 Loan Credit Risk Analysis System
### End-to-End Data Analytics Project | Python · SQL Server · Neon · Power BI · AI

---

## 📌 Project Overview

A production-grade loan portfolio risk management system built to simulate real banking analytics workflows. The system ingests raw loan application data, runs an automated ETL pipeline, stores data in both local and cloud databases, and exposes an AI-powered chat interface where business users can ask questions about the portfolio in plain English — and receive board-level insights backed by live data.

**Business Problem:**
> A bank has 5,000+ loan applications. Risk managers need to identify which borrowers are likely to default, which regions carry the highest exposure, and what actions the board should take — without writing a single line of SQL.

**Solution:**
> An end-to-end system combining ETL automation, SQL analytics, MCP server for developer queries, and an AI chatbot that converts natural language questions into SQL, runs them on live data, and returns executive-ready storytelling — embedded directly inside Power BI.

---

## 🏗️ Architecture

```
Raw Data (CSV)
      ↓
ETL Pipeline (Python)
  ├── Extract  → load raw CSV
  ├── Transform → clean, validate, enrich (33 columns)
  └── Load     → SQL Server (local) + Neon (cloud)
      ↓
┌─────────────────────────────────────┐
│         Data Layer                  │
│  SQL Server Express (local dev)     │
│  Neon PostgreSQL (cloud/prod)   │
└─────────────────────────────────────┘
      ↓                    ↓
MCP Server            Streamlit App
(developer queries)   (end user AI chat)
      ↓                    ↓
VS Code Chat          Power BI Embed
                      (iframe visual)
      ↓
Power BI Dashboard
(5 built-in AI features)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Generation | Python, Faker | Generate 5,000 realistic loan records |
| ETL | Python, pandas, SQLAlchemy | Extract, transform, load pipeline |
| Local Database | SQL Server Express, SSMS | Local development database |
| Cloud Database | Neon (PostgreSQL) | Production cloud database |
| AI Chat | Groq API (LLaMA 3.3 70B) | Free AI for natural language queries |
| MCP Server | Python MCP SDK | Developer AI tool interface |
| Web App | Streamlit | End user chat interface |
| BI Dashboard | Power BI Desktop | Executive dashboards |
| Version Control | Git, GitHub | Code management |
| Deployment | Streamlit Cloud | Free permanent hosting |

---

## 📁 Project Structure

```
├── loan-credit-risk/
│   ├── .gitignore
│   ├── main.py
│   ├── project_folder_structure
│   ├── README.md
│   ├── requirements.txt
│   ├── structure.txt
│   ├── .streamlit/
│   │   ├── secrets.toml
│   ├── analysis/
│   │   ├── chatbot.py
│   │   ├── loan_chat_app.py
│   ├── config/
│   │   ├── settings.py
│   ├── data/
│   │   ├── exports/
│   │   │   ├── powerbi_loans.xlsx
│   │   ├── processed/
│   │   │   ├── loans_clean.csv
│   │   ├── raw/
│   │   │   ├── generate_data.py
│   │   │   ├── loan_applications.csv
│   ├── database/
│   │   ├── loan_risk.db
│   ├── etl/
│   │   ├── extract.py
│   │   ├── load.py
│   │   ├── transform.py
│   ├── logs/
│   │   ├── etl.log
│   ├── mcp_server/
│   │   ├── server.py
│   │   ├── tools/
│   │   │   ├── loan_queries.py
│   ├── powerbi/
│   │   ├── loan_dashboard.pbix
│   ├── scripts/
│   │   ├── auto_folder_structure.py
│   │   ├── export_to_neon_cloud.py
```

---

## ✨ Key Features

### 1. Automated ETL Pipeline
- Generates 5,000 realistic Indian loan records using Faker
- Validates data quality — removes duplicates, invalid ranges
- Enriches data with 10+ calculated columns:
  - Loan-to-income ratio
  - EMI burden percentage
  - Credit score band (Very Poor → Exceptional)
  - Age group, income band, loan size category
  - Application year, month, quarter
- Loads to SQL Server Express locally
- Exports Excel with 4 sheets for Power BI

### 2. Dual Database Setup
- **SQL Server Express** for local development and Power BI
- **Neon PostgreSQL** for cloud deployment and Streamlit app
- Migration script to sync data between both

### 3. MCP Server (Developer Tool)
- 6 pre-built tools callable by AI in VS Code:
  - `get_portfolio_summary` — overall health metrics
  - `get_high_risk_loans` — top risky applications
  - `get_default_rate_by_purpose` — risk by loan type
  - `search_loan_by_id` — specific loan lookup
  - `get_state_risk_report` — geographic risk
  - `get_city_worst_portfolio` — city-level default rates

### 4. AI Chat App (End User Tool)
- Natural language → SQL → plain English storytelling
- Zero hallucination policy — only real data, no estimates
- Self-healing SQL — auto-retries with fix on failure
- Board-level data storytelling with Indian number formatting
- Live KPI dashboard: portfolio value, default rate, credit score
- 12 quick insight buttons for common questions
- SQL transparency — users can view generated query

### 5. Power BI Dashboard
- 5 built-in AI features (free, no premium needed):
  - **Q&A Visual** — ask questions, get charts
  - **Smart Narratives** — auto text summaries
  - **Key Influencers** — what drives defaults
  - **Anomaly Detection** — unusual spikes flagged
  - **Decomposition Tree** — root cause drill-down
- Streamlit app embedded via iframe (HTML Content visual)
- Connected to SQL Server for live data refresh

---

## 🚀 Setup Guide

### Prerequisites
- Windows 10/11
- Python 3.12+
- SQL Server Express (free)
- ODBC Driver 17 for SQL Server
- Power BI Desktop (free)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOURNAME/loan-credit-risk.git
cd loan-credit-risk

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.streamlit/secrets.toml` (never commit this file):

```toml
GROQ_API_KEY   = "your-groq-api-key"
NEON_URL = "Your Neon URL"
```

Get your free keys:
- **Groq API** → console.groq.com (free, no credit card)
- **Neon URL** → neon.com (free PostgreSQL cloud)

### Run the project

```bash
# Step 1: Generate raw data
python data/raw/generate_data.py

# Step 2: Run full ETL pipeline
python main.py

# Step 3: Upload to neon cloud
python scripts/export_to_neon_cloud.py

# Step 4: Start AI chat app
streamlit run analysis/loan_chat_app.py

# Step 5: Start MCP server (developer tool)
python mcp_server/server.py
```

---

## 💬 Example AI Chat Questions

```
"Give me a complete portfolio health summary"
"Which city has the worst default rate?"
"Compare salaried vs self-employed borrower risk"
"What loan purpose defaults the most?"
"Show top 10 highest risk loans"
"What is the credit score distribution of defaulters?"
"Which state has the highest loan exposure?"
"How does income level affect default probability?"
```

---

## 📊 Sample Insights Generated

**Portfolio Snapshot**
> Your loan book stands at 5,000 loans with a total exposure of ₹126.9 Cr — and 766 of those loans (15.3%) have already defaulted, representing ₹19.4 Cr in at-risk capital.

**Risk Signal**
> Personal loans account for 41% of all defaults despite being only 28% of total loan volume — a concentration risk that demands immediate policy intervention.

**Board Recommendation**
> Implement a hard cap: reject personal loan applicants with debt-to-income ratio above 0.45 and credit score below 650. This single rule would have prevented an estimated 60% of current defaults.

---

## 🗂️ Database Schema

**Table: loans** — 33 columns

| Column | Type | Description |
|---|---|---|
| loan_id | TEXT | Unique loan identifier (LN000001) |
| applicant_name | TEXT | Borrower name |
| age | INT | Applicant age |
| annual_income | INT | Annual income in INR |
| loan_amount | INT | Loan amount in INR |
| loan_purpose | TEXT | Home, Vehicle, Education, etc. |
| credit_score | INT | 300–900 score |
| risk_score | INT | 0–100 calculated risk score |
| risk_category | TEXT | HIGH / MEDIUM / LOW |
| is_defaulted | INT | 1 = defaulted, 0 = not |
| loan_status | TEXT | Active / Defaulted / Closed |
| debt_to_income_ratio | FLOAT | Monthly debt / monthly income |
| emi_burden_pct | FLOAT | EMI as % of monthly income |
| credit_score_band | TEXT | Very Poor / Fair / Good / Very Good / Exceptional |
| application_year | INT | Year of application |
| application_quarter | TEXT | Q1 / Q2 / Q3 / Q4 |

*Full schema: 33 columns — run `get_schema()` in the app to see all*

---

## 🎯 Resume / Interview Highlights

```
- Built end-to-end ETL pipeline processing 5,000 loan records
  with automated data quality validation and enrichment

- Developed MCP (Model Context Protocol) server with 6 AI-callable
  tools enabling natural language queries on live SQL database

- Created AI chat application using Groq (LLaMA 3.3 70B) that
  converts plain English questions into SQL with zero hallucination
  policy — only real database values used in responses

- Built Power BI dashboard with 5 built-in AI features integrated
  with AI chat app embedded via HTML Content visual

- Deployed full stack on free tier: Neon (PostgreSQL) +
  Streamlit Cloud — permanent URL, no maintenance cost

- Implemented dual database architecture:
  SQL Server Express (local) + Neon PostgreSQL (cloud)
```

---

## 📝 What I Learned

- Industry-standard ETL pipeline design and execution
- SQL Server Express setup and T-SQL querying
- MCP (Model Context Protocol) — emerging AI integration standard
- PostgreSQL via Neon cloud deployment
- AI prompt engineering for data storytelling without hallucination
- Power BI AI features and custom visual embedding
- Full-stack deployment: GitHub → Streamlit Cloud
- Data storytelling for executive and board-level audiences

---

## 🔮 Future Enhancements

- [ ] Machine Learning model — predict loan default probability
- [ ] REST API (Flask) — expose data to external systems
- [ ] Automated daily PDF reports via email
- [ ] Power BI Premium — Copilot integration
- [ ] Real-time data streaming with Apache Kafka
- [ ] Advanced Power BI — DAX measures, row-level security

---

## 👤 Author

Built as a portfolio project demonstrating 2.5-year data analyst skills.
Covers: ETL · SQL · Cloud Databases · AI Integration · BI Dashboards · Deployment

---

*Built with Python · SQL Server · Neon · Groq · Streamlit · Power BI*