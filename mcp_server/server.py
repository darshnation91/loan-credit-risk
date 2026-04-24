# MCP SERVER — exposes loan database tools to AI clients
# Run from PROJECT ROOT: python mcp_server/server.py

import os
import sys
import asyncio

# ── Path fix: go up 1 level (mcp_server → project root) ─────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_server.tools.loan_queries import (
    get_portfolio_summary,
    get_high_risk_loans,
    get_default_rate_by_purpose,
    search_loan_by_id,
    get_state_risk_report,
    get_city_worst_portfolio,
)

# ── Create MCP server instance ───────────────────────────────
app = Server("loan-risk-mcp-server")


# ── Register available tools ─────────────────────────────────
@app.list_tools()
async def list_tools() -> list[Tool]:
    """Tell the AI which tools exist and what they do"""
    return [
        Tool(
            name="get_portfolio_summary",
            description=(
                "Get overall loan portfolio health — "
                "total loans, portfolio value, defaults, risk split by category."
            ),
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_high_risk_loans",
            description="Get list of high-risk loan applications sorted by risk score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return (default 20, max 100)",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_default_rate_by_purpose",
            description="See which loan purposes (home, vehicle, education etc.) have the highest default rates.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="search_loan_by_id",
            description="Look up every detail of a specific loan by its ID (e.g. LN000123).",
            inputSchema={
                "type": "object",
                "properties": {
                    "loan_id": {
                        "type": "string",
                        "description": "The loan ID to search — format LN followed by 6 digits"
                    }
                },
                "required": ["loan_id"]
            }
        ),
        Tool(
            name="get_state_risk_report",
            description="Rank states/regions by average risk score and default rate.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_city_worst_portfolio",
            description="Find the top 10 cities with the worst loan portfolios by default rate.",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


# ── Execute tool when AI calls it ────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route the AI's tool call to the correct function"""

    try:
        if name == "get_portfolio_summary":
            result = get_portfolio_summary()

        elif name == "get_high_risk_loans":
            limit = int(arguments.get("limit", 20))
            limit = min(limit, 100)   # cap at 100 rows
            result = get_high_risk_loans(limit)

        elif name == "get_default_rate_by_purpose":
            result = get_default_rate_by_purpose()

        elif name == "search_loan_by_id":
            loan_id = arguments.get("loan_id", "").strip().upper()
            if not loan_id:
                result = "Error: loan_id is required. Example: LN000123"
            else:
                result = search_loan_by_id(loan_id)

        elif name == "get_state_risk_report":
            result = get_state_risk_report()

        elif name == "get_city_worst_portfolio":
            result = get_city_worst_portfolio()

        else:
            result = f"Unknown tool: '{name}'. Check list_tools() for available tools."

    except ConnectionError as e:
        result = f"Database connection error:\n{e}"
    except Exception as e:
        result = f"Tool execution error in '{name}':\n{type(e).__name__}: {e}"

    return [TextContent(type="text", text=result)]


# ── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Loan Risk MCP Server starting...")
    print(f"   Project root: {project_root}")
    print("   Tools available: 6")
    print("   Database: SQL Server Express / LoanRiskDB")
    print("   Waiting for AI client connections...\n")
    asyncio.run(stdio_server(app))