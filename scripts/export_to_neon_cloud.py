import sys, os
sys.path.insert(0, r'D:\Development\loan-credit-risk')

import pandas as pd
import pyodbc
import psycopg2
from config.settings import PYODBC_CONN_STR
import streamlit as st

# ── Neon connection ──────────────────────────────────────────
NEON_URL = f"postgresql://neondb_owner:{st.secrets['NEON_URL']}@ep-mute-hall-aog3a4ao.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"  # paste your full Neon URL

def get_cloud_conn():
    return psycopg2.connect(NEON_URL)


def export_from_sqlserver() -> pd.DataFrame:
    print("📥 Reading from SQL Server...")
    conn = pyodbc.connect(PYODBC_CONN_STR)
    df   = pd.read_sql("SELECT * FROM loans", conn)
    conn.close()
    print(f"   ✅ {len(df)} rows, {len(df.columns)} columns")
    return df


def create_table(conn, df: pd.DataFrame):
    type_map = {
        "int64":   "BIGINT",
        "float64": "FLOAT",
        "object":  "TEXT",
        "bool":    "BOOLEAN"
    }
    cols_def = []
    for col, dtype in df.dtypes.items():
        pg_type = type_map.get(str(dtype), "TEXT")
        cols_def.append(f'"{col}" {pg_type}')

    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS loans')
    cur.execute(f'CREATE TABLE loans ({", ".join(cols_def)})')
    conn.commit()
    cur.close()
    print("   ✅ Table created in Neon")


def upload_batch(conn, df: pd.DataFrame):
    cur          = conn.cursor()
    cols         = [f'"{c}"' for c in df.columns]
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_sql   = f'INSERT INTO loans ({", ".join(cols)}) VALUES ({placeholders})'

    batch_size = 200
    total      = len(df)
    uploaded   = 0

    for i in range(0, total, batch_size):
        batch  = df.iloc[i:i + batch_size]
        values = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in batch.itertuples(index=False)
        ]
        cur.executemany(insert_sql, values)
        conn.commit()
        uploaded += len(batch)
        print(f"   📤 Uploaded {uploaded}/{total} rows...", end="\r")

    cur.close()
    print(f"\n   ✅ All {total} rows uploaded!")


def verify(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM loans")
    count = cur.fetchone()[0]
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'loans'
        ORDER BY ordinal_position
        LIMIT 5
    """)
    cols = [r[0] for r in cur.fetchall()]
    cur.close()
    print(f"   ✅ Rows in Neon  : {count}")
    print(f"   ✅ Sample columns: {cols}...")


if __name__ == "__main__":
    print("=" * 50)
    print("  SQL Server → Neon Migration")
    print("=" * 50)
    try:
        df   = export_from_sqlserver()

        print("\n🔌 Connecting to Neon...")
        conn = get_cloud_conn()
        print("   ✅ Connected!")

        create_table(conn, df)

        print(f"\n📤 Uploading {len(df)} rows...")
        upload_batch(conn, df)

        print("\n🔍 Verifying...")
        verify(conn)

        conn.close()
        print("\n🎉 Migration to Neon complete!")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")