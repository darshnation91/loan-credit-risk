# EXTRACT - Pull raw data from source
# In real world: this connects to Oracle, SAP, APIs, etc.

import sys
import pandas as pd
from loguru import logger

sys.path.append('..')
from config.settings import RAW_DATA_PATH, LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")

def extract_loan_data() -> pd.DataFrame:
    """Extract raw loan data from CSV (simulates core banking system export)"""

    logger.info("📥 Starting data extraction...")

    try:
        df = pd.read_csv(RAW_DATA_PATH)
        logger.success(f"✅ Extracted {len(df)} records from {RAW_DATA_PATH}")
        logger.info(f"Columns found: {list(df.columns)}")
        return df

    except FileNotFoundError:
        logger.error(f"❌ File not found: {RAW_DATA_PATH}")
        raise
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        raise

if __name__ == "__main__":
    df = extract_loan_data()
    print(df.head())