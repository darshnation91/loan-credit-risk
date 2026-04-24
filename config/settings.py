import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── File paths ───────────────────────────────────────────────
RAW_DATA_PATH  = os.path.join(BASE_DIR, 'data', 'raw',       'loan_applications.csv')
PROCESSED_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'loans_clean.csv')
EXPORT_PATH    = os.path.join(BASE_DIR, 'data', 'exports',   'powerbi_loans.xlsx')
LOG_PATH       = os.path.join(BASE_DIR, 'logs',              'etl.log')

# ── SQL Server Express (local) ───────────────────────────────
DB_PATH = None

DB_URL = (
    "mssql+pyodbc://localhost\\SQLEXPRESS/LoanRiskDB"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)

PYODBC_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=LoanRiskDB;"
    "Trusted_Connection=yes;"
)

# ── Risk thresholds ──────────────────────────────────────────
RISK_HIGH_THRESHOLD   = 60
RISK_MEDIUM_THRESHOLD = 30