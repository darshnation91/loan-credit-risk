"""
pipeline/load.py
────────────────
Takes the enriched DataFrame from transform.py and:
  1. Loads it into SQL Server (loans table + risk_summary aggregation)
  2. Saves a processed CSV export
  3. Exports a 4-sheet Excel file for Power BI

Run standalone: python pipeline/load.py
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

# ── Path fix: allow running from project root or pipeline/ ────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DB_URL, PROCESSED_PATH, EXPORT_PATH, LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")


# ─────────────────────────────────────────────────────────────
# 1 — LOAD TO SQL SERVER
# ─────────────────────────────────────────────────────────────

def load_to_database(df: pd.DataFrame):
    """Load enriched loan data into SQL Server — replaces loans table"""

    logger.info("💾 Loading enriched data to SQL Server...")

    try:
        engine = create_engine(DB_URL, fast_executemany=True)

        # Drop dependent objects first
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS risk_summary"))
            conn.execute(text("DROP TABLE IF EXISTS loans"))
            conn.commit()

        # Load enriched loans table
        df.to_sql(
            name      = "loans",
            con       = engine,
            if_exists = "replace",
            index     = False,
            chunksize = 500
        )
        logger.success(f"✅ Loaded {len(df):,} records → [loans] table")

        # Create risk_summary aggregation table
        # SQL Server uses SELECT INTO instead of CREATE TABLE AS SELECT
        with engine.connect() as conn:
            conn.execute(text("""
                SELECT
                    risk_category,
                    loan_purpose,
                    employment_type,
                    income_band,
                    credit_score_band,
                    COUNT(*)                                        AS total_loans,
                    SUM(loan_amount)                                AS total_loan_amount,
                    AVG(CAST(credit_score  AS FLOAT))               AS avg_credit_score,
                    AVG(CAST(interest_rate AS FLOAT))               AS avg_interest_rate,
                    AVG(CAST(risk_score    AS FLOAT))               AS avg_risk_score,
                    SUM(is_defaulted)                               AS total_defaults,
                    ROUND(SUM(is_defaulted) * 100.0 / COUNT(*), 2) AS default_rate_pct
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


# ─────────────────────────────────────────────────────────────
# 2 — SAVE PROCESSED CSV
# ─────────────────────────────────────────────────────────────

def load_to_csv(df: pd.DataFrame):
    """Save enriched DataFrame as CSV export"""

    try:
        os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
        df.to_csv(PROCESSED_PATH, index=False)
        logger.success(f"✅ Saved CSV export → {PROCESSED_PATH}")
    except Exception as e:
        logger.error(f"❌ CSV save failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────
# 3 — EXPORT FOR POWER BI
# ─────────────────────────────────────────────────────────────

def export_for_powerbi(df: pd.DataFrame):
    """Export 4-sheet Excel file for Power BI"""

    logger.info("📊 Exporting Power BI Excel file...")

    try:
        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)

        with pd.ExcelWriter(EXPORT_PATH, engine="openpyxl") as writer:

            # Sheet 1 — full enriched dataset
            df.to_excel(writer, sheet_name="All_Loans", index=False)

            # Sheet 2 — high risk accounts only
            df[df["risk_category"] == "HIGH"].to_excel(
                writer, sheet_name="High_Risk_Loans", index=False
            )

            # Sheet 3 — state-level summary
            state_summary = df.groupby("state").agg(
                total_loans    = ("loan_id",      "count"),
                total_amount   = ("loan_amount",  "sum"),
                avg_risk_score = ("risk_score",   "mean"),
                defaults       = ("is_defaulted", "sum")
            ).reset_index()
            state_summary.to_excel(writer, sheet_name="State_Summary", index=False)

            # Sheet 4 — monthly application trend
            monthly = df.groupby(
                ["application_year", "application_month"]
            ).agg(
                applications = ("loan_id",      "count"),
                total_amount = ("loan_amount",  "sum"),
                defaults     = ("is_defaulted", "sum")
            ).reset_index()
            monthly.to_excel(writer, sheet_name="Monthly_Trend", index=False)

        logger.success(f"✅ Power BI file exported → {EXPORT_PATH}")

    except Exception as e:
        logger.error(f"❌ Power BI export failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────
# STANDALONE — run all three steps
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pipeline.transform import transform_loan_data

    df = transform_loan_data()
    load_to_database(df)
    load_to_csv(df)
    export_for_powerbi(df)

    print("\n🎉 All loading steps complete!")