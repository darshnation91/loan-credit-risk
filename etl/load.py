# LOAD — Push clean data into SQL Server + export for Power BI
# SQL Server compatible: uses SELECT INTO instead of CREATE TABLE AS

import os
import sys

# ── Path fix: add project root to sys.path ───────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

from config.settings import DB_URL, PROCESSED_PATH, EXPORT_PATH, LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")


# ────────────────────────────────────────────────────────────
def load_to_database(df: pd.DataFrame):
    """Load clean loan data into SQL Server Express"""

    logger.info("💾 Connecting to SQL Server Express...")

    try:
        engine = create_engine(DB_URL, fast_executemany=True)

        # ── Drop and recreate loans table ────────────────────
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS risk_summary"))
            conn.execute(text("DROP TABLE IF EXISTS loans"))
            conn.commit()

        # ── Load main loans table ────────────────────────────
        df.to_sql(
            name='loans',
            con=engine,
            if_exists='replace',
            index=False,
            chunksize=500          # batch inserts for speed
        )
        logger.success(f"✅ Loaded {len(df)} records into [loans] table")

        # ── Create risk_summary aggregation table ────────────
        # SQL Server uses SELECT INTO instead of CREATE TABLE AS
        with engine.connect() as conn:
            conn.execute(text("""
                SELECT
                    risk_category,
                    loan_purpose,
                    employment_type,
                    income_band,
                    credit_score_band,
                    COUNT(*)                                    AS total_loans,
                    SUM(loan_amount)                            AS total_loan_amount,
                    AVG(CAST(credit_score  AS FLOAT))           AS avg_credit_score,
                    AVG(CAST(interest_rate AS FLOAT))           AS avg_interest_rate,
                    AVG(CAST(risk_score    AS FLOAT))           AS avg_risk_score,
                    SUM(is_defaulted)                           AS total_defaults,
                    ROUND(
                        SUM(is_defaulted) * 100.0 / COUNT(*), 2
                    )                                           AS default_rate_pct
                INTO risk_summary
                FROM loans
                GROUP BY
                    risk_category, loan_purpose, employment_type,
                    income_band, credit_score_band
            """))
            conn.commit()

        logger.success("✅ Created [risk_summary] aggregation table")

    except Exception as e:
        logger.error(f"❌ Database load failed: {e}")
        raise


# ────────────────────────────────────────────────────────────
def load_to_csv(df: pd.DataFrame):
    """Save processed CSV as backup"""
    try:
        df.to_csv(PROCESSED_PATH, index=False)
        logger.success(f"✅ Saved processed CSV → {PROCESSED_PATH}")
    except Exception as e:
        logger.error(f"❌ CSV save failed: {e}")
        raise


# ────────────────────────────────────────────────────────────
def export_for_powerbi(df: pd.DataFrame):
    """Export to Excel with multiple sheets for Power BI"""

    logger.info("📊 Exporting Power BI Excel file...")

    try:
        with pd.ExcelWriter(EXPORT_PATH, engine='openpyxl') as writer:

            # Sheet 1 — all loans
            df.to_excel(writer, sheet_name='All_Loans', index=False)

            # Sheet 2 — high risk only
            df[df['risk_category'] == 'HIGH'].to_excel(
                writer, sheet_name='High_Risk_Loans', index=False
            )

            # Sheet 3 — summary by state
            state_summary = df.groupby('state').agg(
                total_loans    = ('loan_id',      'count'),
                total_amount   = ('loan_amount',  'sum'),
                avg_risk_score = ('risk_score',   'mean'),
                defaults       = ('is_defaulted', 'sum')
            ).reset_index()
            state_summary.to_excel(writer, sheet_name='State_Summary', index=False)

            # Sheet 4 — monthly trend
            monthly = df.groupby(
                ['application_year', 'application_month']
            ).agg(
                applications = ('loan_id',      'count'),
                total_amount = ('loan_amount',  'sum'),
                defaults     = ('is_defaulted', 'sum')
            ).reset_index()
            monthly.to_excel(writer, sheet_name='Monthly_Trend', index=False)

        logger.success(f"✅ Power BI file exported → {EXPORT_PATH}")

    except Exception as e:
        logger.error(f"❌ Power BI export failed: {e}")
        raise


# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from etl.extract import extract_loan_data
    from etl.transform import transform_loan_data

    df = extract_loan_data()
    df = transform_loan_data(df)
    load_to_database(df)
    load_to_csv(df)
    export_for_powerbi(df)
    print("🎉 All loading complete!")