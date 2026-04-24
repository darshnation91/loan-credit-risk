import os
import sys

project_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)
sys.path.insert(0, project_root)

import pandas as pd
from sqlalchemy import create_engine, text
from config.settings import DB_URL


# ── Use SQLAlchemy engine (fixes pandas warning) ─────────────
def get_engine():
    """Return SQLAlchemy engine for SQL Server Express"""
    try:
        engine = create_engine(DB_URL, fast_executemany=True)
        # Test the connection immediately
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        raise ConnectionError(
            f"\n❌ Cannot connect to SQL Server.\n"
            f"   Check:\n"
            f"   1. SQL Server Express is running\n"
            f"      → Win+R → services.msc → 'SQL Server (SQLEXPRESS)' → Start\n"
            f"   2. ODBC Driver 17 is installed\n"
            f"      → Win+R → odbcad32.exe → Drivers tab\n"
            f"   3. LoanRiskDB database exists in SSMS\n"
            f"   Error detail: {e}"
        )


def check_table_exists(engine, table_name: str) -> bool:
    """Check if a table exists before querying it"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = :tname
        """), {"tname": table_name})
        return result.scalar() > 0


def get_portfolio_summary() -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run the ETL pipeline first:\n   python main.py"
    query = """
        SELECT
            COUNT(*)                                          AS total_applications,
            SUM(loan_amount)                                  AS total_portfolio_value,
            ROUND(AVG(CAST(loan_amount  AS FLOAT)), 0)        AS avg_loan_amount,
            ROUND(AVG(CAST(credit_score AS FLOAT)), 0)        AS avg_credit_score,
            ROUND(AVG(CAST(risk_score   AS FLOAT)), 1)        AS avg_risk_score,
            SUM(CASE WHEN risk_category='HIGH'   THEN 1 ELSE 0 END) AS high_risk_count,
            SUM(CASE WHEN risk_category='MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_count,
            SUM(CASE WHEN risk_category='LOW'    THEN 1 ELSE 0 END) AS low_risk_count,
            SUM(is_defaulted)                                 AS total_defaults,
            ROUND(AVG(CAST(is_defaulted AS FLOAT))*100, 2)   AS overall_default_rate_pct
        FROM loans
    """
    df = pd.read_sql(query, engine)
    return df.to_string(index=False)


def get_high_risk_loans(limit: int = 20) -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run: python main.py"
    query = f"""
        SELECT TOP {limit}
            loan_id, applicant_name, loan_amount, credit_score,
            risk_score, risk_category, loan_status, state
        FROM loans
        WHERE risk_category = 'HIGH'
        ORDER BY risk_score DESC
    """
    df = pd.read_sql(query, engine)
    return df.to_string(index=False)


def get_default_rate_by_purpose() -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run: python main.py"
    query = """
        SELECT
            loan_purpose,
            COUNT(*)                                          AS total_loans,
            SUM(is_defaulted)                                 AS defaults,
            ROUND(AVG(CAST(is_defaulted AS FLOAT))*100, 2)   AS default_rate_pct,
            ROUND(AVG(CAST(loan_amount  AS FLOAT)), 0)        AS avg_loan_amount
        FROM loans
        GROUP BY loan_purpose
        ORDER BY default_rate_pct DESC
    """
    df = pd.read_sql(query, engine)
    return df.to_string(index=False)


def search_loan_by_id(loan_id: str) -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run: python main.py"
    query = text("SELECT * FROM loans WHERE loan_id = :lid")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"lid": loan_id})
    if df.empty:
        return f"No loan found with ID: {loan_id}"
    return df.to_string(index=False)


def get_state_risk_report() -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run: python main.py"
    query = """
        SELECT TOP 15
            state,
            COUNT(*)                                          AS total_loans,
            ROUND(AVG(CAST(risk_score   AS FLOAT)), 1)        AS avg_risk_score,
            SUM(is_defaulted)                                 AS defaults,
            ROUND(AVG(CAST(is_defaulted AS FLOAT))*100, 2)   AS default_rate_pct,
            SUM(loan_amount)                                  AS total_exposure
        FROM loans
        GROUP BY state
        ORDER BY avg_risk_score DESC
    """
    df = pd.read_sql(query, engine)
    return df.to_string(index=False)


def get_city_worst_portfolio() -> str:
    engine = get_engine()
    if not check_table_exists(engine, 'loans'):
        return "⚠️ Table 'loans' not found. Please run: python main.py"
    query = """
        SELECT TOP 10
            city,
            COUNT(*)                                          AS total_loans,
            SUM(is_defaulted)                                 AS defaults,
            ROUND(AVG(CAST(is_defaulted AS FLOAT))*100, 2)   AS default_rate_pct,
            ROUND(AVG(CAST(risk_score   AS FLOAT)), 1)        AS avg_risk_score
        FROM loans
        GROUP BY city
        HAVING COUNT(*) > 5
        ORDER BY default_rate_pct DESC
    """
    df = pd.read_sql(query, engine)
    return df.to_string(index=False)


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing connection and queries...\n")
    try:
        engine = get_engine()
        print("✅ Connected to SQL Server\n")

        exists = check_table_exists(engine, 'loans')
        print(f"✅ loans table exists: {exists}\n")

        if exists:
            print("── Portfolio Summary ──")
            print(get_portfolio_summary())
            print("\n── Top 5 High Risk ──")
            print(get_high_risk_loans(5))
            print("\n── Worst Cities ──")
            print(get_city_worst_portfolio())
            print("\n✅ All queries working!")
        else:
            print("⚠️  Run ETL first: python main.py")
    except Exception as e:
        print(e)