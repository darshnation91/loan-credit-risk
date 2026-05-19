"""
config/settings.py
───────────────────
Central configuration — DB connections, file paths, constants.
All sensitive values (NEON_URL, API keys) come from environment
variables or .streamlit/secrets.toml — never hardcoded here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Project root (one level up from config/) ──────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────
# SQL SERVER — LoanRiskDB (source of truth + Power BI layer)
# ─────────────────────────────────────────────────────────────

# Update SERVER to match your SQL Server instance name
# Find it in SSMS: right-click server → Properties → General → Name
SQL_SERVER   = r"DESKTOP-7PR79EA\SQLEXPRESS"   # ← update if different
SQL_DATABASE = "LoanRiskDB"

PYODBC_CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"Trusted_Connection=yes;"
)

# SQLAlchemy URL (used by load.py for df.to_sql)
DB_URL = (
    f"mssql+pyodbc://{SQL_SERVER}/{SQL_DATABASE}"
    f"?driver=ODBC+Driver+17+for+SQL+Server"
    f"&trusted_connection=yes"
)

# ─────────────────────────────────────────────────────────────
# NEON POSTGRESQL — cloud layer for AI chat app
# Set NEON_URL in .streamlit/secrets.toml or .env
# ─────────────────────────────────────────────────────────────

NEON_URL = os.getenv("NEON_URL", "")

# ─────────────────────────────────────────────────────────────
# GROQ API — AI chat app
# Set GROQ_API_KEY in .streamlit/secrets.toml or .env
# ─────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────────────────────

# Pipeline exports
PROCESSED_PATH = os.path.join(ROOT, "data", "exports", "loans_clean.csv")
EXPORT_PATH    = os.path.join(ROOT, "data", "exports", "powerbi_loans.xlsx")

# Logs
LOG_PATH = os.path.join(ROOT, "logs", "pipeline.log")

# ─────────────────────────────────────────────────────────────
# PIPELINE CONSTANTS
# ─────────────────────────────────────────────────────────────

BATCH_SIZE     = 200      # rows per batch for Neon upload
CHUNK_SIZE     = 500      # rows per chunk for SQLAlchemy to_sql

# Risk thresholds (used in DAX and AI chat context)
HIGH_RISK_SCORE_THRESHOLD = 63
HIGH_DTI_THRESHOLD        = 0.50
HIGH_EMI_BURDEN_THRESHOLD = 60.0
LOW_CREDIT_SCORE_CUTOFF   = 666