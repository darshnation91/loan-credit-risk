"""
pipeline/transform.py
─────────────────────
Reads raw loan data from SQL Server (LoanRiskDB),
validates it, and enriches it with calculated risk fields.

Returns a clean, analysis-ready DataFrame.
Run standalone: python pipeline/transform.py
"""

import os
import sys
import pandas as pd
import numpy as np
import pyodbc
from loguru import logger

# ── Path fix: allow running from project root or pipeline/ ────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PYODBC_CONN_STR, LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")


# ─────────────────────────────────────────────────────────────
# STEP 1 — READ FROM SQL SERVER
# ─────────────────────────────────────────────────────────────

def read_from_sql() -> pd.DataFrame:
    """Read raw loan records from SQL Server — LoanRiskDB"""

    logger.info("📥 Reading loan data from SQL Server (LoanRiskDB)...")

    try:
        conn = pyodbc.connect(PYODBC_CONN_STR)
        df   = pd.read_sql("SELECT * FROM loans", conn)
        conn.close()
        logger.success(f"✅ Read {len(df):,} records · {len(df.columns)} columns")
        return df

    except pyodbc.Error as e:
        logger.error(f"❌ SQL Server connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Read failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────
# STEP 2 — VALIDATE
# ─────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate data quality — remove bad records, log issues"""

    logger.info("🔍 Validating data quality...")
    initial = len(df)

    # Remove duplicate loan IDs
    df = df.drop_duplicates(subset=["loan_id"])
    dupes = initial - len(df)
    if dupes:
        logger.warning(f"⚠️  Removed {dupes} duplicate loan IDs")

    # Credit score must be 300–900
    invalid_credit = df[(df["credit_score"] < 300) | (df["credit_score"] > 900)]
    if len(invalid_credit):
        logger.warning(f"⚠️  Removed {len(invalid_credit)} records with invalid credit score")
        df = df[(df["credit_score"] >= 300) & (df["credit_score"] <= 900)]

    # Age must be 18–80
    invalid_age = df[(df["age"] < 18) | (df["age"] > 80)]
    if len(invalid_age):
        logger.warning(f"⚠️  Removed {len(invalid_age)} records with invalid age")
        df = df[(df["age"] >= 18) & (df["age"] <= 80)]

    # Null handling
    df["employment_years"]        = df["employment_years"].fillna(0)
    df["missed_payments_history"] = df["missed_payments_history"].fillna(0)

    # Standardise text
    df["gender"]          = df["gender"].str.strip().str.title()
    df["loan_purpose"]    = df["loan_purpose"].str.strip()
    df["employment_type"] = df["employment_type"].str.strip()
    df["loan_status"]     = df["loan_status"].str.strip()
    df["risk_category"]   = df["risk_category"].str.upper()

    logger.success(f"✅ Validation complete — {len(df):,} clean records")
    return df


# ─────────────────────────────────────────────────────────────
# STEP 3 — ENRICH
# ─────────────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add 10+ calculated risk fields used by Power BI and the AI app"""

    logger.info("⚙️  Enriching data with calculated risk fields...")

    # Loan-to-Income Ratio — key banking metric
    df["loan_to_income_ratio"] = (
        df["loan_amount"] / df["annual_income"]
    ).round(2)

    # Monthly income
    df["monthly_income"] = (df["annual_income"] / 12).round(2)

    # EMI Burden — % of monthly income consumed by EMI
    df["emi_burden_pct"] = (
        (df["monthly_emi"] / df["monthly_income"]) * 100
    ).round(1)

    # Credit Score Band
    df["credit_score_band"] = pd.cut(
        df["credit_score"],
        bins  = [0, 579, 669, 739, 799, 900],
        labels= ["Very Poor", "Fair", "Good", "Very Good", "Exceptional"]
    ).astype(str)

    # Age Group
    df["age_group"] = pd.cut(
        df["age"],
        bins  = [0, 25, 35, 45, 55, 100],
        labels= ["21-25", "26-35", "36-45", "46-55", "55+"]
    ).astype(str)

    # Income Band
    df["income_band"] = pd.cut(
        df["annual_income"],
        bins  = [0, 300000, 600000, 1200000, 2500000, float("inf")],
        labels= ["< 3L", "3L-6L", "6L-12L", "12L-25L", "25L+"]
    ).astype(str)

    # Loan Size Category
    df["loan_size"] = pd.cut(
        df["loan_amount"],
        bins  = [0, 200000, 500000, 2000000, float("inf")],
        labels= ["Small", "Medium", "Large", "Very Large"]
    ).astype(str)

    # Date fields for Power BI time intelligence
    df["application_date"]       = pd.to_datetime(df["application_date"])
    df["application_year"]       = df["application_date"].dt.year
    df["application_month"]      = df["application_date"].dt.month
    df["application_month_name"] = df["application_date"].dt.strftime("%b")
    df["application_quarter"]    = df["application_date"].dt.quarter.map(
        {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
    )

    logger.success(f"✅ Enrichment complete — {df.shape[1]} total columns")
    return df


# ─────────────────────────────────────────────────────────────
# MAIN — orchestrate all steps
# ─────────────────────────────────────────────────────────────

def transform_loan_data() -> pd.DataFrame:
    """
    Full transform pipeline:
      1. Read from SQL Server
      2. Validate
      3. Enrich
      4. Return clean DataFrame
    """
    logger.info("🔄 Starting transform pipeline...")

    df = read_from_sql()
    df = validate(df)
    df = enrich(df)

    df = df.sort_values("application_date", ascending=False).reset_index(drop=True)

    logger.success(f"✅ Transform complete — final shape: {df.shape}")
    return df


if __name__ == "__main__":
    df = transform_loan_data()
    print(f"\nShape     : {df.shape}")
    print(f"Columns   : {list(df.columns)}")
    print(f"\nSample:\n{df.head(3)}")