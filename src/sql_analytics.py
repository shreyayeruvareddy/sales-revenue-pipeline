# ============================================================
# src/sql_analytics.py — Real SQL CTEs + Window Functions
# Runs directly against SQLite database
# Swap connection string for PostgreSQL in production
# ============================================================

import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime
from config import DB_PATH, OUTPUT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_connection():
    return sqlite3.connect(DB_PATH)


# ── QUERY 1: Monthly Revenue with MoM Growth (Window Function) ──
QUERY_MONTHLY_GROWTH = """
WITH monthly_revenue AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
        d.quarter,
        ROUND(SUM(f.net_revenue), 2)         AS total_revenue,
        ROUND(SUM(f.profit), 2)              AS total_profit,
        COUNT(DISTINCT f.order_id)           AS total_orders,
        COUNT(DISTINCT f.customer_id)        AS unique_customers,
        ROUND(AVG(f.net_revenue), 2)         AS avg_order_value
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month, d.month_name, d.quarter
),
with_growth AS (
    SELECT
        *,
        LAG(total_revenue) OVER (ORDER BY year, month) AS prev_month_revenue,
        SUM(total_revenue) OVER (ORDER BY year, month ROWS UNBOUNDED PRECEDING) AS ytd_revenue
    FROM monthly_revenue
)
SELECT
    year,
    month,
    month_name,
    quarter,
    total_revenue,
    total_profit,
    total_orders,
    unique_customers,
    avg_order_value,
    ytd_revenue,
    ROUND((total_revenue - prev_month_revenue) / prev_month_revenue * 100, 2) AS mom_growth_pct,
    ROUND(total_profit / total_revenue * 100, 2) AS profit_margin_pct
FROM with_growth
ORDER BY year, month;
"""

# ── QUERY 2: Regional Performance vs Average (CTE) ──
QUERY_REGIONAL = """
WITH regional_totals AS (
    SELECT
        f.region,
        ROUND(SUM(f.net_revenue), 2)    AS total_revenue,
        ROUND(SUM(f.profit), 2)         AS total_profit,
        COUNT(DISTINCT f.order_id)      AS total_orders,
        COUNT(DISTINCT f.customer_id)   AS unique_customers,
        ROUND(AVG(f.net_revenue), 2)    AS avg_order_value,
        SUM(f.is_returned)              AS total_returns
    FROM fact_sales f
    GROUP BY f.region
),
avg_revenue AS (
    SELECT AVG(total_revenue) AS avg_rev FROM regional_totals
)
SELECT
    r.region,
    r.total_revenue,
    r.total_profit,
    r.total_orders,
    r.unique_customers,
    r.avg_order_value,
    r.total_returns,
    ROUND(r.total_profit / r.total_revenue * 100, 2)           AS profit_margin_pct,
    ROUND((r.total_revenue - a.avg_rev) / a.avg_rev * 100, 2)  AS vs_avg_pct,
    CASE
        WHEN (r.total_revenue - a.avg_rev) / a.avg_rev * 100 >= 5  THEN 'Above Average'
        WHEN (r.total_revenue - a.avg_rev) / a.avg_rev * 100 <= -5 THEN 'Below Average'
        ELSE 'Average'
    END AS performance_tier
FROM regional_totals r, avg_revenue a
ORDER BY total_revenue DESC;
"""

# ── QUERY 3: Product Revenue Ranking (Window Function) ──
QUERY_PRODUCT_RANKING = """
WITH product_stats AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND(SUM(f.net_revenue), 2)     AS total_revenue,
        ROUND(SUM(f.profit), 2)          AS total_profit,
        SUM(f.quantity)                  AS total_units,
        COUNT(DISTINCT f.order_id)       AS total_orders,
        ROUND(AVG(f.unit_price), 2)      AS avg_unit_price,
        SUM(f.is_returned)               AS return_count
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category
)
SELECT
    product_id,
    product_name,
    category,
    total_revenue,
    total_profit,
    total_units,
    total_orders,
    avg_unit_price,
    ROUND(total_profit / total_revenue * 100, 2)     AS profit_margin_pct,
    ROUND(return_count * 100.0 / total_orders, 2)    AS return_rate_pct,
    RANK() OVER (ORDER BY total_revenue DESC)         AS revenue_rank,
    RANK() OVER (ORDER BY total_profit DESC)          AS profit_rank,
    RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS category_rank
FROM product_stats
ORDER BY revenue_rank;
"""

# ── QUERY 4: Category Performance + Revenue Share ──
QUERY_CATEGORY = """
WITH category_totals AS (
    SELECT
        p.category,
        ROUND(SUM(f.net_revenue), 2)    AS total_revenue,
        ROUND(SUM(f.profit), 2)         AS total_profit,
        COUNT(DISTINCT f.order_id)      AS total_orders,
        SUM(f.quantity)                 AS total_units,
        COUNT(DISTINCT f.customer_id)   AS unique_customers
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.category
),
grand_total AS (
    SELECT SUM(total_revenue) AS grand_rev FROM category_totals
)
SELECT
    c.category,
    c.total_revenue,
    c.total_profit,
    c.total_orders,
    c.total_units,
    c.unique_customers,
    ROUND(c.total_revenue / g.grand_rev * 100, 2)    AS revenue_share_pct,
    ROUND(c.total_profit  / c.total_revenue * 100, 2) AS profit_margin_pct,
    RANK() OVER (ORDER BY c.total_revenue DESC)       AS revenue_rank
FROM category_totals c, grand_total g
ORDER BY revenue_rank;
"""

# ── QUERY 5: Customer Lifetime Value + Segment Analysis ──
QUERY_CUSTOMER_LTV = """
WITH customer_stats AS (
    SELECT
        f.customer_id,
        c.segment,
        c.region,
        ROUND(SUM(f.net_revenue), 2)     AS total_spend,
        ROUND(SUM(f.profit), 2)          AS total_profit,
        COUNT(DISTINCT f.order_id)       AS total_orders,
        ROUND(AVG(f.net_revenue), 2)     AS avg_order_value,
        MIN(f.date_id)                   AS first_order_date,
        MAX(f.date_id)                   AS last_order_date
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_id = c.customer_id
    GROUP BY f.customer_id, c.segment, c.region
)
SELECT
    segment,
    COUNT(customer_id)                   AS customer_count,
    ROUND(AVG(total_spend), 2)           AS avg_ltv,
    ROUND(SUM(total_spend), 2)           AS segment_revenue,
    ROUND(AVG(total_orders), 2)          AS avg_orders_per_customer,
    ROUND(AVG(avg_order_value), 2)       AS avg_order_value,
    ROUND(SUM(total_spend) * 100.0 /
        (SELECT SUM(net_revenue) FROM fact_sales), 2) AS revenue_share_pct
FROM customer_stats
GROUP BY segment
ORDER BY avg_ltv DESC;
"""

# ── QUERY 6: Quarter-over-Quarter Revenue (CTE + Window) ──
QUERY_QOQ = """
WITH quarterly AS (
    SELECT
        d.quarter,
        d.year,
        ROUND(SUM(f.net_revenue), 2)   AS total_revenue,
        ROUND(SUM(f.profit), 2)        AS total_profit,
        COUNT(DISTINCT f.order_id)     AS total_orders
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.quarter
)
SELECT
    quarter,
    year,
    total_revenue,
    total_profit,
    total_orders,
    ROUND(total_profit / total_revenue * 100, 2) AS profit_margin_pct,
    LAG(total_revenue) OVER (ORDER BY year, quarter)  AS prev_quarter_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY year, quarter))
        / LAG(total_revenue) OVER (ORDER BY year, quarter) * 100, 2
    ) AS qoq_growth_pct
FROM quarterly
ORDER BY year, quarter;
"""

# ── QUERY 7: Payment Method Analysis ──
QUERY_PAYMENT = """
SELECT
    payment_method,
    COUNT(DISTINCT order_id)             AS total_orders,
    ROUND(SUM(net_revenue), 2)           AS total_revenue,
    ROUND(AVG(net_revenue), 2)           AS avg_order_value,
    SUM(is_returned)                     AS total_returns,
    ROUND(SUM(is_returned) * 100.0 /
          COUNT(order_id), 2)            AS return_rate_pct,
    ROUND(COUNT(order_id) * 100.0 /
          (SELECT COUNT(*) FROM fact_sales), 2) AS order_share_pct
FROM fact_sales
GROUP BY payment_method
ORDER BY total_revenue DESC;
"""


def run_query(name: str, query: str) -> pd.DataFrame:
    """Execute a SQL query and return results as DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        logger.info(f"✅ [{name}]: {len(df)} rows returned")
        return df
    except Exception as e:
        logger.error(f"❌ [{name}] failed: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def export_for_powerbi(results: dict, ts: str):
    """
    Export all query results as CSVs for Power BI / Tableau.
    Each file is named clearly for easy import into BI tools.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    export_map = {
        "PowerBI_Monthly_Revenue":   results.get("monthly_growth"),
        "PowerBI_Regional_KPIs":     results.get("regional"),
        "PowerBI_Product_Ranking":   results.get("product_ranking"),
        "PowerBI_Category_Analysis": results.get("category"),
        "PowerBI_Customer_LTV":      results.get("customer_ltv"),
        "PowerBI_Quarterly_KPIs":    results.get("qoq"),
        "PowerBI_Payment_Methods":   results.get("payment"),
    }

    for filename, df in export_map.items():
        if df is not None and not df.empty:
            path = os.path.join(OUTPUT_PATH, f"{filename}_{ts}.csv")
            df.to_csv(path, index=False)
            logger.info(f"📊 Power BI export → {path}")


def run_sql_analytics() -> dict:
    """Run all SQL queries and export results."""
    logger.info("🔍 Running SQL analytics (CTEs + Window Functions)...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        "monthly_growth":  run_query("Monthly Revenue + MoM Growth",     QUERY_MONTHLY_GROWTH),
        "regional":        run_query("Regional Performance vs Avg",       QUERY_REGIONAL),
        "product_ranking": run_query("Product Revenue Ranking",           QUERY_PRODUCT_RANKING),
        "category":        run_query("Category Revenue Share",            QUERY_CATEGORY),
        "customer_ltv":    run_query("Customer LTV by Segment",           QUERY_CUSTOMER_LTV),
        "qoq":             run_query("Quarter-over-Quarter Growth",       QUERY_QOQ),
        "payment":         run_query("Payment Method Analysis",           QUERY_PAYMENT),
    }

    export_for_powerbi(results, ts)

    # Print key insights
    logger.info("\n📊 SQL ANALYTICS RESULTS:")

    if not results["regional"].empty:
        underperf = results["regional"][results["regional"]["vs_avg_pct"] < -5]
        for _, row in underperf.iterrows():
            logger.info(f"   ⚠️  {row['region']}: {row['vs_avg_pct']}% vs average → Below Average")

    if not results["monthly_growth"].empty:
        best_month = results["monthly_growth"].loc[results["monthly_growth"]["total_revenue"].idxmax()]
        logger.info(f"   📈 Best month: {best_month['month_name']} (${best_month['total_revenue']:,.2f})")

    if not results["category"].empty:
        top_cat = results["category"].iloc[0]
        logger.info(f"   🏆 Top category: {top_cat['category']} ({top_cat['revenue_share_pct']}% revenue share)")

    if not results["customer_ltv"].empty:
        logger.info(f"\n   Customer LTV by Segment:\n{results['customer_ltv'][['segment','customer_count','avg_ltv','revenue_share_pct']].to_string()}")

    return results


if __name__ == "__main__":
    results = run_sql_analytics()
    print("\n--- Monthly Revenue (with MoM Growth) ---")
    print(results["monthly_growth"][["month_name","total_revenue","mom_growth_pct","ytd_revenue"]].to_string())
    print("\n--- Regional Performance ---")
    print(results["regional"][["region","total_revenue","vs_avg_pct","performance_tier"]].to_string())
    print("\n--- Top 10 Products ---")
    print(results["product_ranking"].head(10)[["product_name","category","total_revenue","profit_margin_pct","revenue_rank"]].to_string())
