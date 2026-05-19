"""
pipeline/sync_to_cloud.py
──────────────────────────
Reads the enriched loans table from SQL Server (LoanRiskDB)
and syncs it to Neon PostgreSQL (cloud layer for the AI chat app).

Run standalone : python pipeline/sync_to_cloud.py
Called by      : pipeline/run_pipeline.py  →  run_sync()
"""

import os
import sys
import pandas as pd
import pyodbc
import psycopg2
from loguru import logger

# ── Path fix ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PYODBC_CONN_STR, LOG_PATH

logger.add(LOG_PATH, rotation="1 MB")

# ── Neon connection string from environment ────────────────────
from dotenv import load_dotenv
load_dotenv()
NEON_URL = os.getenv("NEON_URL")


# ─────────────────────────────────────────────────────────────
def _read_from_sqlserver() -> pd.DataFrame:
    """Read enriched loans table from SQL Server"""
    logger.info("📥 Reading enriched loans from SQL Server...")
    try:
        conn = pyodbc.connect(PYODBC_CONN_STR)
        df   = pd.read_sql("SELECT * FROM loans", conn)
        conn.close()
        logger.success(f"✅ Read {len(df):,} rows · {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"❌ SQL Server read failed: {e}")
        raise


def _get_neon_conn():
    """Return a psycopg2 connection to Neon PostgreSQL"""
    if not NEON_URL:
        raise ValueError("NEON_URL not set. Add it to .streamlit/secrets.toml or .env")
    return psycopg2.connect(NEON_URL)


def _create_table(conn, df: pd.DataFrame):
    """Drop and recreate loans table in Neon based on DataFrame dtypes"""
    type_map = {
        "int64":   "BIGINT",
        "float64": "FLOAT",
        "object":  "TEXT",
        "bool":    "BOOLEAN",
    }
    cols_def = [
        f'"{col}" {type_map.get(str(dtype), "TEXT")}'
        for col, dtype in df.dtypes.items()
    ]
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS loans")
    cur.execute(f'CREATE TABLE loans ({", ".join(cols_def)})')
    conn.commit()
    cur.close()
    logger.success("✅ loans table created in Neon")


def _upload_batches(conn, df: pd.DataFrame, batch_size: int = 200):
    """Insert rows in batches for memory efficiency"""
    cols         = [f'"{c}"' for c in df.columns]
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql          = f'INSERT INTO loans ({", ".join(cols)}) VALUES ({placeholders})'

    cur      = conn.cursor()
    total    = len(df)
    uploaded = 0

    for i in range(0, total, batch_size):
        batch = df.iloc[i : i + batch_size]
        rows  = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in batch.itertuples(index=False)
        ]
        cur.executemany(sql, rows)
        conn.commit()
        uploaded += len(batch)
        logger.info(f"   Uploaded {uploaded:,}/{total:,} rows...")

    cur.close()
    logger.success(f"✅ All {total:,} rows uploaded to Neon")


def _verify(conn):
    """Quick row count + sample columns check"""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM loans")
    count = cur.fetchone()[0]
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'loans'
        ORDER BY ordinal_position LIMIT 5
    """)
    sample_cols = [r[0] for r in cur.fetchall()]
    cur.close()
    logger.success(f"✅ Neon verified — {count:,} rows · sample cols: {sample_cols}")


# ─────────────────────────────────────────────────────────────
def run_sync():
    """
    Full sync: SQL Server enriched loans → Neon PostgreSQL.
    Called by run_pipeline.py and can be run standalone.
    """
    logger.info("☁️  Starting SQL Server → Neon sync...")

    df   = _read_from_sqlserver()
    conn = _get_neon_conn()
    logger.success("✅ Connected to Neon PostgreSQL")

    _create_table(conn, df)
    _upload_batches(conn, df)
    _verify(conn)

    conn.close()
    logger.success("🎉 Sync to Neon complete!")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  SQL Server → Neon PostgreSQL Sync")
    print("=" * 50)
    try:
        run_sync()
    except Exception as e:
        print(f"\n❌ Sync failed: {type(e).__name__}: {e}")