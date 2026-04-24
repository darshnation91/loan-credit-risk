# TRANSFORM - Clean, validate, and enrich the data
# This is where most of the real work happens!

import pandas as pd
import numpy as np
from loguru import logger
import sys
sys.path.append('..')
from config.settings import LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Check for data quality issues"""

    logger.info("🔍 Validating data quality...")

    initial_count = len(df)
    issues = []

    # Check for nulls
    null_counts = df.isnull().sum()
    if null_counts.any():
        issues.append(f"Nulls found: {null_counts[null_counts > 0].to_dict()}")

    # Remove duplicates
    df = df.drop_duplicates(subset=['loan_id'])
    dupes_removed = initial_count - len(df)
    if dupes_removed > 0:
        issues.append(f"Removed {dupes_removed} duplicate loan IDs")

    # Validate ranges
    invalid_credit = df[(df['credit_score'] < 300) | (df['credit_score'] > 900)]
    if len(invalid_credit) > 0:
        issues.append(f"Found {len(invalid_credit)} invalid credit scores")
        df = df[(df['credit_score'] >= 300) & (df['credit_score'] <= 900)]

    invalid_age = df[(df['age'] < 18) | (df['age'] > 80)]
    if len(invalid_age) > 0:
        df = df[(df['age'] >= 18) & (df['age'] <= 80)]
        issues.append(f"Removed {len(invalid_age)} records with invalid age")

    for issue in issues:
        logger.warning(f"⚠️  {issue}")

    logger.success(f"✅ Validation complete. {len(df)} clean records remain.")
    return df


def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
    """Add calculated columns that analysts need"""

    logger.info("⚙️  Enriching data with calculated fields...")

    # Loan-to-Income Ratio (LTI) - key banking metric
    df['loan_to_income_ratio'] = round(
        df['loan_amount'] / df['annual_income'], 2
    )

    # Monthly Income
    df['monthly_income'] = round(df['annual_income'] / 12, 2)

    # EMI Burden (% of monthly income going to EMI)
    df['emi_burden_pct'] = round(
        (df['monthly_emi'] / df['monthly_income']) * 100, 1
    )

    # Credit Score Band (human readable)
    df['credit_score_band'] = pd.cut(
        df['credit_score'],
        bins=[0, 579, 669, 739, 799, 900],
        labels=['Very Poor', 'Fair', 'Good', 'Very Good', 'Exceptional']
    ).astype(str)

    # Age Group
    df['age_group'] = pd.cut(
        df['age'],
        bins=[0, 25, 35, 45, 55, 100],
        labels=['21-25', '26-35', '36-45', '46-55', '55+']
    ).astype(str)

    # Income Band
    df['income_band'] = pd.cut(
        df['annual_income'],
        bins=[0, 300000, 600000, 1200000, 2500000, float('inf')],
        labels=['< 3L', '3L-6L', '6L-12L', '12L-25L', '25L+']
    ).astype(str)

    # Loan Size Category
    df['loan_size'] = pd.cut(
        df['loan_amount'],
        bins=[0, 200000, 500000, 2000000, float('inf')],
        labels=['Small', 'Medium', 'Large', 'Very Large']
    ).astype(str)

    # Application Year & Month (for time series in Power BI)
    df['application_date'] = pd.to_datetime(df['application_date'])
    df['application_year'] = df['application_date'].dt.year
    df['application_month'] = df['application_date'].dt.month
    df['application_month_name'] = df['application_date'].dt.strftime('%b')
    df['application_quarter'] = df['application_date'].dt.quarter.map(
        {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}
    )

    logger.success(f"✅ Added {10} enrichment columns")
    return df


def transform_loan_data(df: pd.DataFrame) -> pd.DataFrame:
    """Main transformation function — runs all steps"""

    logger.info("🔄 Starting transformation pipeline...")

    # Step 1: Validate
    df = validate_data(df)

    # Step 2: Fill any remaining nulls
    df['employment_years'] = df['employment_years'].fillna(0)
    df['missed_payments_history'] = df['missed_payments_history'].fillna(0)

    # Step 3: Standardize text columns
    df['gender'] = df['gender'].str.strip().str.title()
    df['loan_purpose'] = df['loan_purpose'].str.strip()
    df['employment_type'] = df['employment_type'].str.strip()
    df['loan_status'] = df['loan_status'].str.strip()
    df['risk_category'] = df['risk_category'].str.upper()

    # Step 4: Enrich with new columns
    df = enrich_data(df)

    # Step 5: Sort by application date
    df = df.sort_values('application_date', ascending=False)
    df = df.reset_index(drop=True)

    logger.success(f"✅ Transformation complete! Final shape: {df.shape}")
    return df


if __name__ == "__main__":
    from extract import extract_loan_data
    raw_df = extract_loan_data()
    clean_df = transform_loan_data(raw_df)
    print(clean_df.head(3))
    print(f"\nNew columns: {list(clean_df.columns)}")