# ============================================================
# src/db_loader.py — Star schema DB for sales pipeline
# ============================================================

import sqlite3
import pandas as pd
import logging
import os
from datetime import datetime
from config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_tables():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id   TEXT PRIMARY KEY,
            customer_name TEXT,
            segment       TEXT,
            region        TEXT,
            city          TEXT,
            joined_date   TEXT
        );

        CREATE TABLE IF NOT EXISTS dim_product (
            product_id   TEXT PRIMARY KEY,
            product_name TEXT,
            category     TEXT,
            unit_price   REAL,
            cost_price   REAL,
            margin_pct   REAL
        );

        CREATE TABLE IF NOT EXISTS dim_date (
            date_id    TEXT PRIMARY KEY,
            month      INTEGER,
            month_name TEXT,
            quarter    TEXT,
            year       INTEGER,
            is_holiday INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS dim_region (
            region_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT UNIQUE,
            performance TEXT
        );

        CREATE TABLE IF NOT EXISTS fact_sales (
            order_id        TEXT PRIMARY KEY,
            customer_id     TEXT REFERENCES dim_customer(customer_id),
            product_id      TEXT REFERENCES dim_product(product_id),
            date_id         TEXT REFERENCES dim_date(date_id),
            region          TEXT,
            quantity        INTEGER,
            unit_price      REAL,
            discount_pct    REAL,
            discount_amt    REAL,
            gross_revenue   REAL,
            net_revenue     REAL,
            cost            REAL,
            profit          REAL,
            is_returned     INTEGER,
            payment_method  TEXT,
            ingested_at     TEXT
        );

        CREATE TABLE IF NOT EXISTS agg_monthly_kpis (
            kpi_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            year             INTEGER,
            month            INTEGER,
            month_name       TEXT,
            quarter          TEXT,
            total_revenue    REAL,
            total_profit     REAL,
            total_orders     INTEGER,
            avg_order_value  REAL,
            profit_margin_pct REAL,
            mom_growth_pct   REAL,
            ytd_revenue      REAL,
            created_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS agg_regional_kpis (
            region_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            region           TEXT,
            total_revenue    REAL,
            total_profit     REAL,
            total_orders     INTEGER,
            profit_margin    REAL,
            vs_avg_pct       REAL,
            performance      TEXT,
            created_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS pipeline_run_log (
            run_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp     TEXT,
            stage             TEXT,
            status            TEXT,
            records_processed INTEGER DEFAULT 0,
            error_message     TEXT,
            duration_sec      REAL
        );
    """)
    conn.commit()
    conn.close()
    logger.info("✅ Database schema created/verified")


def load_dimensions(transactions: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame):
    conn = get_connection()
    cursor = conn.cursor()

    # dim_customer
    for _, r in customers.iterrows():
        cursor.execute("INSERT OR IGNORE INTO dim_customer VALUES (?,?,?,?,?,?)",
            (r.customer_id, r.customer_name, r.segment, r.region, r.city, r.joined_date))

    # dim_product
    for _, r in products.iterrows():
        cursor.execute("INSERT OR IGNORE INTO dim_product VALUES (?,?,?,?,?,?)",
            (r.product_id, r.product_name, r.category, r.unit_price, r.cost_price, r.margin_pct))

    # dim_date
    for _, r in transactions[["order_date","month","month_name","quarter","year"]].drop_duplicates("order_date").iterrows():
        cursor.execute("INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?,?)",
            (str(r.order_date)[:10], int(r.month), r.month_name, r.quarter, int(r.year), 0))

    # dim_region
    for region in transactions["region"].unique():
        cursor.execute("INSERT OR IGNORE INTO dim_region (region_name) VALUES (?)", (region,))

    conn.commit()
    conn.close()
    logger.info("✅ Dimension tables loaded")


def load_fact_table(transactions: pd.DataFrame) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0

    for _, r in transactions.iterrows():
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO fact_sales (
                    order_id, customer_id, product_id, date_id, region,
                    quantity, unit_price, discount_pct, discount_amt,
                    gross_revenue, net_revenue, cost, profit,
                    is_returned, payment_method, ingested_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                r.order_id, r.customer_id, r.product_id,
                str(r.order_date)[:10], r.region,
                int(r.quantity), float(r.unit_price),
                float(r.discount_pct), float(r.discount_amt),
                float(r.gross_revenue), float(r.net_revenue),
                float(r.cost), float(r.profit),
                int(r.is_returned), r.payment_method, now
            ))
            inserted += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    logger.info(f"✅ Inserted {inserted:,} rows into fact_sales")
    return inserted


def load_kpi_aggregates(monthly: pd.DataFrame, regional: pd.DataFrame):
    conn = get_connection()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for _, r in monthly.iterrows():
        conn.execute("""
            INSERT INTO agg_monthly_kpis
            (year, month, month_name, quarter, total_revenue, total_profit,
             total_orders, avg_order_value, profit_margin_pct, mom_growth_pct, ytd_revenue, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (int(r.year), int(r.month), r.month_name, r.quarter,
              float(r.total_revenue), float(r.total_profit),
              int(r.total_orders), float(r.avg_order_value),
              float(r.profit_margin_pct), float(r.mom_growth_pct) if pd.notna(r.mom_growth_pct) else None,
              float(r.ytd_revenue), now))

    for _, r in regional.iterrows():
        conn.execute("""
            INSERT INTO agg_regional_kpis
            (region, total_revenue, total_profit, total_orders, profit_margin, vs_avg_pct, performance, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (r.region, float(r.total_revenue), float(r.total_profit),
              int(r.total_orders), float(r.profit_margin),
              float(r.vs_avg_pct), r.performance, now))

    conn.commit()
    conn.close()
    logger.info(f"✅ KPI aggregates loaded")


def log_run(stage, status, records=0, error=None, duration=None):
    conn = get_connection()
    conn.execute("INSERT INTO pipeline_run_log (run_timestamp,stage,status,records_processed,error_message,duration_sec) VALUES (?,?,?,?,?,?)",
        (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), stage, status, records, error, duration))
    conn.commit()
    conn.close()


def query_summary() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            f.region,
            COUNT(DISTINCT f.customer_id)     AS unique_customers,
            COUNT(f.order_id)                 AS total_orders,
            ROUND(SUM(f.net_revenue), 2)      AS total_revenue,
            ROUND(AVG(f.net_revenue), 2)      AS avg_order_value,
            ROUND(SUM(f.profit)/SUM(f.net_revenue)*100, 1) AS profit_margin_pct,
            SUM(f.is_returned)                AS total_returns
        FROM fact_sales f
        GROUP BY f.region
        ORDER BY total_revenue DESC
    """, conn)
    conn.close()
    return df


def run_db_load(dfs: dict):
    import time
    t = time.time()
    try:
        create_tables()
        load_dimensions(dfs["transactions"], dfs.get("customers_raw"), dfs.get("products_raw"))
        n = load_fact_table(dfs["transactions"])
        load_kpi_aggregates(dfs["monthly_kpis"], dfs["regional"])
        duration = round(time.time() - t, 2)
        log_run("db_load", "SUCCESS", n, duration=duration)
        logger.info(f"✅ DB load complete in {duration}s")
    except Exception as e:
        log_run("db_load", "FAILED", error=str(e))
        logger.error(f"❌ DB load failed: {e}")
        raise
