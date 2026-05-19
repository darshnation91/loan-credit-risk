"""
pipeline/run_pipeline.py
────────────────────────
Single entry point to run the full data pipeline.

What it does:
  Step 1 — Read from SQL Server + validate + enrich (transform.py)
  Step 2 — Load enriched data back to SQL Server + export files (load.py)
  Step 3 — Sync enriched data to Neon PostgreSQL (sync_to_cloud.py)

Run: python pipeline/run_pipeline.py
"""

import os
import sys
import time
from rich.console import Console
from rich.panel import Panel

# ── Path fix ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

console = Console()


def run():
    console.print(Panel.fit(
        "🏦  LOAN CREDIT RISK — DATA PIPELINE\n"
        "   SQL Server → Enrich → Load → Sync to Cloud",
        style="bold blue"
    ))

    start = time.time()

    # ── STEP 1: TRANSFORM ─────────────────────────────────────
    console.print("\n[bold yellow]Step 1/3 — Reading from SQL Server + enriching data...[/bold yellow]")
    try:
        from pipeline.transform import transform_loan_data
        df = transform_loan_data()
        console.print(f"  ✅ {len(df):,} records · {df.shape[1]} columns")
    except Exception as e:
        console.print(f"  [red]❌ Transform failed: {e}[/red]")
        raise

    # ── STEP 2: LOAD ──────────────────────────────────────────
    console.print("\n[bold yellow]Step 2/3 — Loading to SQL Server + exporting files...[/bold yellow]")
    try:
        from pipeline.load import load_to_database, load_to_csv, export_for_powerbi
        load_to_database(df)
        load_to_csv(df)
        export_for_powerbi(df)
        console.print("  ✅ SQL Server updated · CSV saved · Excel exported")
    except Exception as e:
        console.print(f"  [red]❌ Load failed: {e}[/red]")
        raise

    # ── STEP 3: SYNC TO CLOUD ─────────────────────────────────
    console.print("\n[bold yellow]Step 3/3 — Syncing to Neon PostgreSQL (cloud)...[/bold yellow]")
    try:
        from pipeline.sync_to_cloud import run_sync
        run_sync()
        console.print("  ✅ Neon PostgreSQL synced")
    except Exception as e:
        console.print(f"  [red]❌ Cloud sync failed: {e}[/red]")
        raise

    elapsed = round(time.time() - start, 1)

    console.print(Panel.fit(
        f"🎉  PIPELINE COMPLETE  ({elapsed}s)\n\n"
        "  📊  Power BI file  →  data/exports/powerbi_loans.xlsx\n"
        "  📁  CSV export     →  data/exports/loans_clean.csv\n"
        "  🗄️   SQL Server     →  LoanRiskDB · [loans] + [risk_summary]\n"
        "  ☁️   Neon cloud     →  PostgreSQL synced\n"
        "  📋  Logs           →  logs/pipeline.log",
        style="bold green"
    ))


if __name__ == "__main__":
    run()