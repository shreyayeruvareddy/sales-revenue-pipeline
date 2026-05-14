# ============================================================
# src/sql_runner.py — Reads and executes all .sql files
# This is the ONLY place SQL runs — all queries live in queries/
# ============================================================

import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime
from config import DB_PATH, OUTPUT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

QUERIES_DIR = "queries"

# Map query files to human-readable names and output filenames
QUERY_REGISTRY = [
    {
        "file":        "01_monthly_revenue_mom_growth.sql",
        "name":        "Monthly Revenue + MoM Growth",
        "output_name": "PowerBI_01_Monthly_Revenue",
        "description": "Monthly revenue trend with month-over-month growth % and YTD cumulative"
    },
    {
        "file":        "02_regional_performance.sql",
        "name":        "Regional Performance vs Average",
        "output_name": "PowerBI_02_Regional_KPIs",
        "description": "Revenue by region vs company average — identifies underperforming regions"
    },
    {
        "file":        "03_product_ranking.sql",
        "name":        "Product Revenue Ranking",
        "output_name": "PowerBI_03_Product_Ranking",
        "description": "Product revenue/profit ranking with RANK() and PARTITION BY category"
    },
    {
        "file":        "04_category_revenue_share.sql",
        "name":        "Category Revenue Share",
        "output_name": "PowerBI_04_Category_Analysis",
        "description": "Category-level performance with revenue share % and cumulative totals"
    },
    {
        "file":        "05_customer_ltv_rfm.sql",
        "name":        "Customer LTV + RFM Segmentation",
        "output_name": "PowerBI_05_Customer_LTV_RFM",
        "description": "Customer lifetime value with RFM scoring using NTILE() window function"
    },
    {
        "file":        "06_quarterly_growth.sql",
        "name":        "Quarter-over-Quarter Growth",
        "output_name": "PowerBI_06_Quarterly_Growth",
        "description": "Quarterly revenue with QoQ growth % using LAG() window function"
    },
    {
        "file":        "07_payment_discount_analysis.sql",
        "name":        "Payment & Discount Analysis",
        "output_name": "PowerBI_07_Payment_Discounts",
        "description": "Payment method revenue share and discount band impact analysis"
    },
    {
        "file":        "08_top_customers_per_region.sql",
        "name":        "Top 5 Customers Per Region",
        "output_name": "PowerBI_08_Top_Customers",
        "description": "Top customers per region using RANK() PARTITION BY with percentile scores"
    },
]


def get_connection() -> sqlite3.Connection:
    """Return SQLite connection (swap for PostgreSQL in production)."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run the full pipeline first: py -3.11 run_pipeline.py"
        )
    return sqlite3.connect(DB_PATH)


def load_sql_file(filename: str) -> str:
    """Read a .sql file from the queries/ directory."""
    filepath = os.path.join(QUERIES_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SQL file not found: {filepath}")
    with open(filepath, "r") as f:
        sql = f.read()
    return sql


def execute_query(name: str, sql: str) -> pd.DataFrame:
    """Execute a SQL query and return results as DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn)
        logger.info(f"  ✅ {name}: {len(df):,} rows returned")
        return df
    except Exception as e:
        logger.error(f"  ❌ {name} FAILED: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def export_to_csv(df: pd.DataFrame, output_name: str, ts: str) -> str:
    """Export query result to CSV for Power BI / Tableau import."""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    path = os.path.join(OUTPUT_PATH, f"{output_name}_{ts}.csv")
    df.to_csv(path, index=False)
    return path


def print_key_insights(results: dict):
    """Print the most important business insights from SQL results."""
    logger.info("\n" + "=" * 60)
    logger.info("📊 KEY BUSINESS INSIGHTS FROM SQL ANALYSIS")
    logger.info("=" * 60)

    # Monthly growth insight
    monthly = results.get("Monthly Revenue + MoM Growth")
    if monthly is not None and not monthly.empty:
        best = monthly.loc[monthly["total_revenue"].idxmax()]
        worst_growth = monthly.dropna(subset=["mom_growth_pct"])
        logger.info(f"\n📅 MONTHLY REVENUE:")
        logger.info(f"   Best month:    {best['month_name']} — ${best['total_revenue']:,.2f}")
        logger.info(f"   YTD (final):   ${monthly['ytd_revenue'].iloc[-1]:,.2f}")
        logger.info(f"   Nov→Dec growth: {monthly[monthly['month_name']=='December']['mom_growth_pct'].values[0] if 'December' in monthly['month_name'].values else 'N/A'}%")

    # Regional insight
    regional = results.get("Regional Performance vs Average")
    if regional is not None and not regional.empty:
        logger.info(f"\n🗺️  REGIONAL PERFORMANCE:")
        for _, row in regional.iterrows():
            flag = "🔴" if row["vs_avg_pct"] < -10 else ("🟡" if row["vs_avg_pct"] < 0 else "🟢")
            logger.info(f"   {flag} {row['region']}: ${row['total_revenue']:,.2f} ({row['vs_avg_pct']:+.1f}% vs avg) — {row['performance_tier']}")

    # Category insight
    category = results.get("Category Revenue Share")
    if category is not None and not category.empty:
        logger.info(f"\n🏷️  CATEGORY PERFORMANCE:")
        for _, row in category.iterrows():
            logger.info(f"   #{int(row['revenue_rank'])} {row['category']}: ${row['total_revenue']:,.2f} ({row['revenue_share_pct']}% share, {row['profit_margin_pct']}% margin)")

    # Quarterly insight
    quarterly = results.get("Quarter-over-Quarter Growth")
    if quarterly is not None and not quarterly.empty:
        logger.info(f"\n📆 QUARTERLY GROWTH:")
        for _, row in quarterly.iterrows():
            growth_str = f"{row['qoq_revenue_growth_pct']:+.1f}%" if pd.notna(row.get("qoq_revenue_growth_pct")) else "Baseline"
            logger.info(f"   {row['quarter']}: ${row['total_revenue']:,.2f} ({growth_str}) — {row.get('growth_classification','')}")

    # RFM insight
    rfm = results.get("Customer LTV + RFM Segmentation")
    if rfm is not None and not rfm.empty:
        segment_counts = rfm["rfm_segment"].value_counts()
        logger.info(f"\n👥 RFM CUSTOMER SEGMENTS:")
        for seg, count in segment_counts.items():
            avg_spend = rfm[rfm["rfm_segment"] == seg]["total_spend"].mean()
            logger.info(f"   {seg}: {count} customers (avg spend: ${avg_spend:,.2f})")

    logger.info("\n" + "=" * 60)


def run_sql_analytics() -> dict:
    """
    Main entry point:
    1. Load each .sql file from queries/
    2. Execute against the database
    3. Export results as Power BI-ready CSVs
    4. Print key insights
    """
    logger.info("🔍 Running SQL Analytics...")
    logger.info(f"   Queries directory: {os.path.abspath(QUERIES_DIR)}")
    logger.info(f"   Database:          {os.path.abspath(DB_PATH)}")
    logger.info(f"   Output directory:  {os.path.abspath(OUTPUT_PATH)}")
    logger.info(f"   Total queries:     {len(QUERY_REGISTRY)}\n")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}
    exported_files = []

    for query_info in QUERY_REGISTRY:
        logger.info(f"📄 Running: {query_info['file']}")
        logger.info(f"   → {query_info['description']}")

        # Load SQL from file
        sql = load_sql_file(query_info["file"])

        # Execute query
        df = execute_query(query_info["name"], sql)

        if not df.empty:
            # Export to CSV for Power BI
            path = export_to_csv(df, query_info["output_name"], ts)
            exported_files.append(path)
            logger.info(f"   📊 Exported → {path}\n")

        results[query_info["name"]] = df

    # Print business insights
    print_key_insights(results)

    logger.info(f"\n✅ SQL Analytics complete!")
    logger.info(f"   {len([r for r in results.values() if not r.empty])} queries succeeded")
    logger.info(f"   {len(exported_files)} Power BI CSV files exported to outputs/")

    return results


if __name__ == "__main__":
    results = run_sql_analytics()

    print("\n\n--- Monthly Revenue Sample ---")
    monthly = results.get("Monthly Revenue + MoM Growth")
    if monthly is not None and not monthly.empty:
        print(monthly[["month_name", "total_revenue", "mom_growth_pct", "ytd_revenue"]].to_string())

    print("\n--- Regional Performance ---")
    regional = results.get("Regional Performance vs Average")
    if regional is not None and not regional.empty:
        print(regional[["region", "total_revenue", "vs_avg_pct", "performance_tier", "recommendation"]].to_string())
