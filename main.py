# Run the ENTIRE pipeline from one place
# This is what you run every morning as a data analyst!

from rich.console import Console
from rich.panel import Panel
from rich.progress import track
import time

console = Console()

def run_pipeline():
    console.print(Panel.fit(
        "🏦 LOAN CREDIT RISK — ETL PIPELINE",
        style="bold blue"
    ))

    # Step 1: Extract
    console.print("\n[bold yellow]Step 1/3: EXTRACTING data...[/bold yellow]")
    from etl.extract import extract_loan_data
    df = extract_loan_data()
    console.print(f"  ✅ Extracted [green]{len(df)}[/green] records")

    # Step 2: Transform
    console.print("\n[bold yellow]Step 2/3: TRANSFORMING data...[/bold yellow]")
    from etl.transform import transform_loan_data
    df = transform_loan_data(df)
    console.print(f"  ✅ Transformed — [green]{df.shape[1]}[/green] columns now")

    # Step 3: Load
    console.print("\n[bold yellow]Step 3/3: LOADING data...[/bold yellow]")
    from etl.load import load_to_database, load_to_csv, export_for_powerbi
    load_to_database(df)
    load_to_csv(df)
    export_for_powerbi(df)

    console.print(Panel.fit(
        "🎉 PIPELINE COMPLETE!\n"
        "📁 Database: database/loan_risk.db\n"
        "📊 Power BI: data/exports/powerbi_loans.xlsx\n"
        "📝 Logs: logs/etl.log",
        style="bold green"
    ))

if __name__ == "__main__":
    run_pipeline()