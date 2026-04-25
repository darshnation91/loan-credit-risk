import os
import sys
import re

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
import psycopg2
import streamlit as st
from groq import Groq

st.set_page_config(
    page_title="Loan Portfolio Intelligence",
    page_icon="🏦",
    layout="wide"
)

# ── Groq client ──────────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    try:
        key = st.secrets["GROQ_API_KEY"]
    except:
        key = os.environ.get("GROQ_API_KEY", "")
    return Groq(api_key=key)

MODEL = "llama-3.3-70b-versatile"


# ── DB connection ────────────────────────────────────────────
def get_conn():
    try:
        url = st.secrets["NEON_URL"]
    except:
        url = os.environ.get(
            "NEON_URL",
            "postgresql://username:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
        )
    return psycopg2.connect(url)

# ── Schema ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_schema() -> str:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name   = 'loans'
            AND   table_schema = 'public'
            ORDER BY ordinal_position
        """, conn)
        conn.close()
        if df.empty:
            return "ERROR: loans table not found"
        return (
            "Database: PostgreSQL\nTable: loans\n"
            "Use ONLY these exact column names:\n" +
            "\n".join(
                f"  - {r['column_name']} ({r['data_type']})"
                for _, r in df.iterrows()
            )
        )
    except Exception as e:
        return f"ERROR: {e}"


# ── Run SQL ──────────────────────────────────────────────────
def run_sql(sql: str) -> tuple:
    try:
        sql = sql.strip().rstrip(";")
        sql = sql.replace("```sql", "").replace("```", "").strip()

        # Convert TOP N → LIMIT N
        match = re.search(r'TOP\s+(\d+)', sql, re.IGNORECASE)
        if match:
            limit = match.group(1)
            sql   = re.sub(r'TOP\s+\d+\s*', '', sql, flags=re.IGNORECASE)
            sql   = sql + f" LIMIT {limit}"

        sql = sql.replace("GETDATE()", "NOW()")
        sql = sql.replace("NOLOCK", "").replace("WITH(NOLOCK)", "")

        conn = get_conn()
        df   = pd.read_sql(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)


# ── Groq call ────────────────────────────────────────────────
def call_groq(system: str, user: str,
              temp: float = 0, tokens: int = 500) -> str:
    client = get_groq_client()
    resp   = client.chat.completions.create(
        model      = MODEL,
        max_tokens = tokens,
        temperature= temp,
        messages   = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ]
    )
    return resp.choices[0].message.content.strip()

def enrich_question(question: str) -> str:
    """
    Rewrites simple questions into rich analyst questions
    so the SQL always returns multiple metrics
    """
    return call_groq(
        system="""You are a senior bank data analyst.
Your job is to rewrite a simple business question into a 
detailed analytical question that would require a rich SQL query.

Rules:
- Always ask for 5-6 metrics together
- Always include totals, rates, counts AND amounts
- Keep the original intent but make it richer
- Return only the rewritten question — nothing else

Examples:
Input:  "What is our default rate?"
Output: "Show total loans, total defaulted loans, default rate percentage, 
         total portfolio value in crores, defaulted amount in crores, 
         and average credit score of defaulters"

Input:  "Which city has worst defaults?"
Output: "Show each city with total loans, total defaults, default rate 
         percentage, total loan amount in crores, and average risk score, 
         ordered by default rate descending"

Input:  "Compare salaried vs self employed"
Output: "Show each employment type with total loans, total defaults, 
         default rate percentage, average loan amount, average credit 
         score and average risk score"
""",
        user=f"Rewrite this question to be richer: {question}"
    )


# ── Generate SQL ─────────────────────────────────────────────
def generate_sql(question: str, schema: str) -> str:
    sql = call_groq(
        system="""You are a PostgreSQL expert analyst.

STRICT RULES — follow every one:
1. Use ONLY column names listed in the schema
2. PostgreSQL syntax: LIMIT N not TOP N
3. ROUND() needs NUMERIC cast — always write:
   ROUND(CAST(value AS NUMERIC), 2)
4. For averages on integers:
   AVG(CAST(column AS NUMERIC))
5. For default rate:
   ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC)) * 100 AS NUMERIC), 2)
6. For loan amounts in Crores:
   ROUND(CAST(SUM(loan_amount) AS NUMERIC) / 10000000, 2)
7. Return raw SQL only — no markdown, no backticks, no explanation
8. One SELECT statement only
9. Add ORDER BY for ranking questions
10. Add LIMIT 20 unless question asks for all records""",
        user=f"{schema}\n\nWrite PostgreSQL SQL for: {question}"
    )
    return sql.replace("```sql", "").replace("```", "").strip()


# ── Fix SQL ──────────────────────────────────────────────────
def fix_sql(sql: str, error: str, schema: str) -> str:
    fixed = call_groq(
        system="""Fix this broken PostgreSQL query.
Key fixes needed:
- Use ROUND(CAST(value AS NUMERIC), 2) not ROUND(float, 2)
- Use LIMIT not TOP
- Use ONLY columns from the schema
Return fixed SQL only — no markdown.""",
        user=(
            f"Schema:\n{schema}\n\n"
            f"Broken SQL:\n{sql}\n\n"
            f"Error:\n{error}\n\n"
            f"Fixed SQL:"
        )
    )
    return fixed.replace("```sql", "").replace("```", "").strip()


# ── Data storytelling ────────────────────────────────────────
def tell_story(question: str, df: pd.DataFrame) -> str:
    data_text = df.to_string(index=False)
    cols      = list(df.columns)
    rows      = len(df)

    col_ref = "\n".join(
        f"  Column {i+1}: {c}"
        for i, c in enumerate(cols)
    )

    return call_groq(
        system="""You are a Chief Risk Officer writing a board report for an Indian bank.

NUMBER FORMAT — follow exactly:
- Columns ending _cr          → already Crores  → show as ₹X Cr
- Columns ending _lakhs       → already Lakhs   → show as ₹X Lakh
- Columns ending _pct or rate → already %       → show as X%
- Column avg_risk_score       → score out of 100 → show as X/100
- Column avg_credit_score     → score out of 900 → show as X/900
- Count columns               → add commas      → 5000 = 5,000
- NEVER multiply risk_score or credit_score by 100
- NEVER show raw decimals like 126969.23

SNAPSHOT RULE:
- Never open with default rate percentage
- Always open with RUPEE AMOUNT (₹ Cr)
- Good: "₹232 Cr of our ₹1,269 Cr portfolio is at risk"
- Bad:  "Our default rate is 15.32%" """,

        user=(
            f"Question: {question}\n\n"
            f"Available columns:\n{col_ref}\n\n"
            f"DATA TABLE:\n{data_text}\n\n"

            f"STEP 1 — Detect question type:\n"
            f"- Contains 'what is', 'how many', 'what %', 'rate' "
            f"→ TYPE = SIMPLE\n"
            f"- Contains 'vs', 'compare', 'difference', 'between' "
            f"→ TYPE = COMPARISON\n"
            f"- Contains 'summary', 'health', 'overview', 'complete' "
            f"→ TYPE = SUMMARY\n"
            f"- Contains 'top', 'list', 'show me', 'highest' "
            f"→ TYPE = LIST\n\n"

            f"STEP 2 — Based on type, use this template:\n\n"

            f"If SIMPLE → use:\n"
            f"**📊 Snapshot**\n"
            f"[One sentence with ₹ amount — NOT percentage]\n"
            f"**🔍 What This Means**\n"
            f"• **[Column 1 label]:** [value] — [10 words max]\n"
            f"• **[Column 2 label]:** [value] — [10 words max]\n"
            f"[STOP — no Watch Out, no Recommendation for simple questions]\n\n"

            f"If COMPARISON → use:\n"
            f"**📊 Snapshot**\n"
            f"[One sentence comparing the two groups with ₹ or % difference]\n"
            f"**🔍 What This Means**\n"
            f"• **[Group 1]:** [its value] — [10 words max]\n"
            f"• **[Group 2]:** [its value] — [10 words max]\n"
            f"• **[Key differentiator]:** [value] — [10 words max]\n"
            f"**⚠️ Watch Out**\n"
            f"[Name the riskier group + exact number that proves it]\n"
            f"**✅ Board Recommendation**\n"
            f"[Action verb + specific group + exact threshold number]\n\n"

            f"If SUMMARY → use:\n"
            f"**📊 Snapshot**\n"
            f"[₹ at risk out of ₹ total — most alarming framing]\n"
            f"**🔍 What This Means**\n"
            f"• **[Column 1]:** [value] — [10 words max]\n"
            f"• **[Column 2]:** [value] — [10 words max]\n"
            f"• **[Column 3]:** [value] — [10 words max]\n"
            f"**⚠️ Watch Out**\n"
            f"[Connect 2 specific numbers to show future risk — 20 words max]\n"
            f"**✅ Board Recommendation**\n"
            f"[Reject/Freeze/Review + exact number threshold from data]\n\n"

            f"If LIST → use:\n"
            f"**📊 Snapshot**\n"
            f"[One sentence — most alarming single fact from the list]\n"
            f"[STOP — no bullets, no Watch Out, no Recommendation — table tells the story]\n\n"

            f"RULES FOR ALL TYPES:\n"
            f"1. Every bullet must use a DIFFERENT column — no repeating\n"
            f"2. Watch Out MUST include at least one specific number\n"
            f"3. Recommendation MUST include an action verb and a number\n"
            f"4. Never say: monitor, rising, increasing — be specific\n"
            f"5. Bad recommendation: 'Monitor 766 defaults closely'\n"
            f"6. Good recommendation: "
            f"'Reject applicants with credit score below 650 immediately'\n"
        ),
        temp  = 0.0,
        tokens= 700
    )


# ── Pre-built rich queries for common questions ──────────────
# These ALWAYS return complete data — no AI guessing needed

PREBUILT_QUERIES = {
    "portfolio": """
        SELECT
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS total_defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_portfolio_cr,
            ROUND(CAST(SUM(CASE WHEN is_defaulted=1
                THEN loan_amount ELSE 0 END) AS NUMERIC)/10000000,2)          AS defaulted_amount_cr,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score,
            ROUND(CAST(AVG(CAST(risk_score AS NUMERIC)) AS NUMERIC),1)        AS avg_risk_score,
            SUM(CASE WHEN risk_category='HIGH' THEN 1 ELSE 0 END)             AS high_risk_count,
            ROUND(CAST(AVG(CAST(loan_amount AS NUMERIC)) AS NUMERIC)/100000,2) AS avg_loan_lakhs
        FROM loans
    """,

    "city": """
        SELECT
            city,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score,
            ROUND(CAST(AVG(CAST(risk_score AS NUMERIC)) AS NUMERIC),1)        AS avg_risk_score
        FROM loans
        GROUP BY city
        HAVING COUNT(*) > 5
        ORDER BY default_rate_pct DESC
        LIMIT 10
    """,

    "purpose": """
        SELECT
            loan_purpose,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr,
            ROUND(CAST(AVG(CAST(interest_rate AS NUMERIC)) AS NUMERIC),2)     AS avg_interest_rate,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score
        FROM loans
        GROUP BY loan_purpose
        ORDER BY default_rate_pct DESC
    """,

    "employment": """
        SELECT
            employment_type,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score,
            ROUND(CAST(AVG(CAST(annual_income AS NUMERIC)) AS NUMERIC)/100000,2) AS avg_income_lakhs,
            ROUND(CAST(AVG(CAST(risk_score AS NUMERIC)) AS NUMERIC),1)        AS avg_risk_score
        FROM loans
        GROUP BY employment_type
        ORDER BY default_rate_pct DESC
    """,

    "state": """
        SELECT
            state,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr,
            ROUND(CAST(AVG(CAST(risk_score AS NUMERIC)) AS NUMERIC),1)        AS avg_risk_score
        FROM loans
        GROUP BY state
        ORDER BY total_exposure_cr DESC
        LIMIT 15
    """,

    "monthly": """
        SELECT
            application_year                                                  AS year,
            application_month                                                 AS month,
            application_month_name                                            AS month_name,
            COUNT(*)                                                          AS total_applications,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_amount_cr
        FROM loans
        GROUP BY application_year, application_month, application_month_name
        ORDER BY application_year, application_month
    """,

    "risk": """
        SELECT
            risk_category,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score,
            ROUND(CAST(AVG(CAST(interest_rate AS NUMERIC)) AS NUMERIC),2)     AS avg_interest_rate
        FROM loans
        GROUP BY risk_category
        ORDER BY default_rate_pct DESC
    """,

    "credit": """
        SELECT
            credit_score_band,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score,
            ROUND(CAST(SUM(loan_amount) AS NUMERIC)/10000000,2)               AS total_exposure_cr
        FROM loans
        GROUP BY credit_score_band
        ORDER BY avg_credit_score
    """,

    "income": """
        SELECT
            income_band,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(AVG(CAST(loan_amount AS NUMERIC)) AS NUMERIC)/100000,2) AS avg_loan_lakhs,
            ROUND(CAST(AVG(CAST(debt_to_income_ratio AS NUMERIC)) AS NUMERIC),2) AS avg_dti
        FROM loans
        GROUP BY income_band
        ORDER BY default_rate_pct DESC
    """,

    "age": """
        SELECT
            age_group,
            COUNT(*)                                                          AS total_loans,
            SUM(CAST(is_defaulted AS INT))                                    AS defaults,
            ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC))*100 AS NUMERIC),2)  AS default_rate_pct,
            ROUND(CAST(AVG(CAST(loan_amount AS NUMERIC)) AS NUMERIC)/100000,2) AS avg_loan_lakhs,
            ROUND(CAST(AVG(CAST(credit_score AS NUMERIC)) AS NUMERIC),0)      AS avg_credit_score
        FROM loans
        GROUP BY age_group
        ORDER BY default_rate_pct DESC
    """,

    "top_risk": """
        SELECT
            loan_id,
            applicant_name,
            city,
            state,
            ROUND(CAST(loan_amount AS NUMERIC)/100000,2)                      AS loan_amount_lakhs,
            loan_purpose,
            credit_score,
            risk_score,
            risk_category,
            employment_type,
            loan_status,
            ROUND(CAST(debt_to_income_ratio AS NUMERIC),2)                    AS dti_ratio
        FROM loans
        WHERE risk_category = 'HIGH'
        ORDER BY risk_score DESC
        LIMIT 10
    """
}


def detect_query_type(question: str) -> str | None:
    """
    Detect if question matches a pre-built query type.
    Returns query key or None if AI should write custom SQL.
    """
    q = question.lower()

    # Portfolio / summary / overview / default rate
    if any(w in q for w in [
        "portfolio", "summary", "overview", "health",
        "total loans", "how many loans", "defaulted so far",
        "what percentage", "default rate", "overall"
    ]):
        return "portfolio"

    # City
    if any(w in q for w in ["city", "cities", "town"]):
        return "city"

    # Loan purpose
    if any(w in q for w in ["purpose", "home loan", "vehicle", "education",
                              "personal loan", "business loan", "dangerous",
                              "riskiest loan", "type of loan"]):
        return "purpose"

    # Employment type
    if any(w in q for w in ["employment", "salaried", "self employed",
                              "self-employed", "freelancer", "business owner",
                              "job type", "occupation"]):
        return "employment"

    # State / geography
    if any(w in q for w in ["state", "region", "geography",
                              "location", "exposure"]):
        return "state"

    # Monthly / trend
    if any(w in q for w in ["month", "monthly", "trend", "quarter",
                              "yearly", "year", "annual", "over time"]):
        return "monthly"

    # Risk category
    if any(w in q for w in ["risk category", "high risk", "medium risk",
                              "low risk", "risk level", "risk band"]):
        return "risk"

    # Credit score
    if any(w in q for w in ["credit score", "credit band",
                              "credit rating", "cibil"]):
        return "credit"

    # Income
    if any(w in q for w in ["income", "salary", "earning", "income band"]):
        return "income"

    # Age
    if any(w in q for w in ["age", "age group", "young", "old", "senior"]):
        return "age"

    # Top risk loans
    if any(w in q for w in ["top 10", "highest risk", "worst loans",
                              "riskiest loans", "most dangerous loans"]):
        return "top_risk"

    return None  # use AI-generated SQL


# ── Master answer ────────────────────────────────────────────
def get_answer(question: str) -> dict:
    schema = get_schema()

    if schema.startswith("ERROR"):
        return {
            "answer": "❌ Cannot connect to database.",
            "sql": None, "data": None, "error": schema
        }

    # ── DEBUG — show which path is taken ────────────────────
    query_type = detect_query_type(question)

    if query_type and query_type in PREBUILT_QUERIES:
        sql     = PREBUILT_QUERIES[query_type].strip()
        df, err = run_sql(sql)

        if err:
            query_type = None
        elif df is not None and not df.empty:
            return {
                "answer": tell_story(question, df),
                "sql"   : sql,
                "data"  : df,
                "error" : None
            }

    # AI path
    enriched = enrich_question(question)
    sql      = generate_sql(enriched, schema)
    df, err  = run_sql(sql)

    if err:
        sql     = fix_sql(sql, err, schema)
        df, err = run_sql(sql)

    if err or df is None:
        return {
            "answer": (
                "I wasn't able to find data for that question.\n\n"
                "Try asking:\n"
                "- *Which city has the highest default rate?*\n"
                "- *Show total loans by risk category*"
            ),
            "sql": sql, "data": None, "error": err
        }

    if df.empty:
        return {
            "answer": "No records matched your question.",
            "sql": sql, "data": df, "error": None
        }

    return {
        "answer": tell_story(question, df),
        "sql"   : sql,
        "data"  : df,
        "error" : None
    }


# ── KPI bar ──────────────────────────────────────────────────
def show_kpis():
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT
                COUNT(*)
                    AS total_loans,
                ROUND(CAST(SUM(loan_amount) AS NUMERIC) / 10000000, 2)
                    AS portfolio_cr,
                ROUND(CAST(AVG(CAST(is_defaulted AS NUMERIC)) * 100
                      AS NUMERIC), 1)
                    AS default_rate,
                ROUND(CAST(AVG(CAST(credit_score AS NUMERIC))
                      AS NUMERIC), 0)
                    AS avg_credit,
                SUM(CASE WHEN risk_category = 'HIGH'
                    THEN 1 ELSE 0 END)
                    AS high_risk,
                ROUND(CAST(SUM(
                    CASE WHEN loan_status = 'Defaulted'
                    THEN loan_amount ELSE 0 END
                ) AS NUMERIC) / 10000000, 2)
                    AS defaulted_cr
            FROM loans
        """, conn)
        conn.close()

        total    = int(df['total_loans'][0])
        port_cr  = float(df['portfolio_cr'][0])
        def_rate = float(df['default_rate'][0])
        credit   = int(df['avg_credit'][0])
        highrisk = int(df['high_risk'][0])
        at_risk  = float(df['defaulted_cr'][0])

        c1, c2, c3, c4, c5, c6 = st.columns(6)

        c1.metric(
            "Total Applications",
            f"{total:,}"
        )
        c2.metric(
            "Portfolio Size",
            f"₹{port_cr} Cr"
        )
        c3.metric(
            "Default Rate",
            f"{def_rate}%",
            delta      = f"{def_rate - 15:.1f}% vs 15% safe limit",
            delta_color= "inverse"
        )
        c4.metric(
            "Avg Credit Score",
            f"{credit} / 900"
        )
        c5.metric(
            "High Risk Loans",
            f"{highrisk:,}"
        )
        c6.metric(
            "Exposure at Risk",
            f"₹{at_risk} Cr"
        )
        st.divider()

    except Exception as e:
        st.warning(f"Dashboard metrics unavailable: {e}")


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 Loan Risk Assistant")
    st.divider()

    st.subheader("Quick Questions")
    st.caption("Click any question below to get instant insights")

    questions = [
        "Complete portfolio health summary",
        "Which city has worst default rate?",
        "Default rate by loan purpose",
        "Salaried vs self employed risk",
        "Credit score of defaulters vs non defaulters",
        "Top 10 highest risk loans",
        "State wise loan exposure",
        "Monthly application trend",
        "Income band vs default rate",
        "Age group with highest defaults",
        "Debt to income ratio by risk category",
        "Which loan size defaults the most?",
    ]

    for q in questions:
        if st.button(q, use_container_width=True):
            st.session_state["quick_q"] = q

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Main page ────────────────────────────────────────────────
st.title("🏦 Loan Portfolio Dashboard")
st.caption(
    "Ask any question about your loan portfolio "
    "and get instant answers based on real data."
)

# KPI bar
show_kpis()

# Init welcome message
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role"   : "assistant",
        "content": (
            "👋 **Welcome to the Loan Portfolio Dashboard!**\n\n"
            "I can answer any question about your loan data. "
            "Here are some things you can ask me:\n\n"
            "- *Which cities have the most loan defaults?*\n"
            "- *What is our overall default rate?*\n"
            "- *Which type of loan is the riskiest?*\n"
            "- *Show me the top 10 high risk borrowers*\n\n"
            "You can also click any question on the left to get started."
        ),
        "data": None,
        "sql" : None
    }]

# ── Handle sidebar quick question ─────────────────────────────
# Must be processed BEFORE rendering chat history
if "quick_q" in st.session_state:
    question = st.session_state.pop("quick_q")
    st.session_state.messages.append({
        "role": "user", "content": question,
        "data": None,   "sql":     None
    })
    with st.spinner("Finding your answer..."):
        result = get_answer(question)
    st.session_state.messages.append({
        "role"   : "assistant",
        "content": result["answer"],
        "data"   : result["data"],
        "sql"    : result["sql"]
    })
    st.rerun()

# ── Render chat history ───────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("data") is not None and not msg["data"].empty:
            st.dataframe(
                msg["data"],
                use_container_width=True,
                hide_index=True
            )
        if msg.get("sql"):
            with st.expander("View SQL Query"):
                st.code(msg["sql"], language="sql")

# ── Chat input ────────────────────────────────────────────────
prompt = st.chat_input("Type your question here...")

if prompt:
    st.session_state.messages.append({
        "role": "user", "content": prompt,
        "data": None,   "sql":     None
    })
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding your answer..."):
            result = get_answer(prompt)

        st.markdown(result["answer"])

        if result.get("data") is not None and not result["data"].empty:
            st.dataframe(
                result["data"],
                use_container_width=True,
                hide_index=True
            )
        if result.get("sql"):
            with st.expander("View SQL Query"):
                st.code(result["sql"], language="sql")

    st.session_state.messages.append({
        "role"   : "assistant",
        "content": result["answer"],
        "data"   : result["data"],
        "sql"    : result["sql"]
    })