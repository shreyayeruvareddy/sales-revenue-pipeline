# ============================================================
# src/transformation.py — ETL + KPI Analytics
# Computes revenue KPIs, regional analysis, RFM segmentation
# ============================================================

import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
from config import PROCESSED_DATA_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply data quality rules."""
    initial = len(df)
    df = df.dropna(subset=["order_id", "customer_id", "product_id", "order_date", "net_revenue"])
    df = df[df["net_revenue"] > 0]
    df = df[df["quantity"] > 0]
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["profit"]     = df["profit"].fillna(0)
    dropped = initial - len(df)
    if dropped:
        logger.warning(f"⚠️  Dropped {dropped} invalid records")
    logger.info(f"✅ Clean transactions: {len(df):,} records")
    return df


def compute_monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly revenue KPIs with MoM growth using window functions logic.
    Includes: revenue, orders, avg order value, profit margin, growth %.
    """
    monthly = df.groupby(["year", "month", "month_name", "quarter"]).agg(
        total_revenue  = ("net_revenue",   "sum"),
        total_profit   = ("profit",        "sum"),
        total_orders   = ("order_id",      "nunique"),
        total_units    = ("quantity",      "sum"),
        total_returns  = ("is_returned",   "sum"),
        unique_customers = ("customer_id", "nunique")
    ).reset_index().sort_values(["year", "month"])

    monthly["avg_order_value"]  = (monthly["total_revenue"] / monthly["total_orders"]).round(2)
    monthly["profit_margin_pct"] = (monthly["total_profit"]  / monthly["total_revenue"] * 100).round(2)
    monthly["return_rate_pct"]  = (monthly["total_returns"]  / monthly["total_orders"]  * 100).round(2)

    # Month-over-month revenue growth (window function equivalent)
    monthly["prev_month_revenue"] = monthly["total_revenue"].shift(1)
    monthly["mom_growth_pct"] = (
        (monthly["total_revenue"] - monthly["prev_month_revenue"])
        / monthly["prev_month_revenue"] * 100
    ).round(2)

    # Cumulative revenue (YTD)
    monthly["ytd_revenue"] = monthly["total_revenue"].cumsum().round(2)

    monthly["total_revenue"]  = monthly["total_revenue"].round(2)
    monthly["total_profit"]   = monthly["total_profit"].round(2)
    logger.info(f"📅 Monthly KPIs computed: {len(monthly)} months")
    return monthly


def compute_regional_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Regional performance analysis.
    Identifies underperforming regions vs average.
    Key insight: Southeast underperforms by ~23%.
    """
    regional = df.groupby("region").agg(
        total_revenue    = ("net_revenue",  "sum"),
        total_profit     = ("profit",       "sum"),
        total_orders     = ("order_id",     "nunique"),
        unique_customers = ("customer_id",  "nunique"),
        avg_order_value  = ("net_revenue",  "mean"),
        total_returns    = ("is_returned",  "sum")
    ).reset_index()

    avg_revenue = regional["total_revenue"].mean()
    regional["vs_avg_pct"]      = ((regional["total_revenue"] - avg_revenue) / avg_revenue * 100).round(2)
    regional["profit_margin"]   = (regional["total_profit"] / regional["total_revenue"] * 100).round(2)
    regional["avg_order_value"] = regional["avg_order_value"].round(2)
    regional["performance"]     = regional["vs_avg_pct"].apply(
        lambda x: "Above Average" if x >= 5 else ("Below Average" if x <= -5 else "Average")
    )
    regional = regional.sort_values("total_revenue", ascending=False)
    regional[["total_revenue", "total_profit"]] = regional[["total_revenue", "total_profit"]].round(2)

    # Log the underperforming region insight
    underperforming = regional[regional["vs_avg_pct"] < -5]
    for _, row in underperforming.iterrows():
        logger.warning(f"⚠️  Underperforming region: {row['region']} ({row['vs_avg_pct']}% vs avg)")

    logger.info(f"🗺️  Regional analysis: {len(regional)} regions")
    return regional


def compute_product_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Product-level KPIs — revenue, units, profit margin, return rate."""
    products = df.groupby(["product_id", "product_name", "category"]).agg(
        total_revenue  = ("net_revenue", "sum"),
        total_profit   = ("profit",      "sum"),
        total_units    = ("quantity",    "sum"),
        total_orders   = ("order_id",    "nunique"),
        return_count   = ("is_returned", "sum"),
        avg_unit_price = ("unit_price",  "mean")
    ).reset_index()

    products["profit_margin_pct"] = (products["total_profit"] / products["total_revenue"] * 100).round(2)
    products["return_rate_pct"]   = (products["return_count"] / products["total_orders"]  * 100).round(2)
    products["avg_unit_price"]    = products["avg_unit_price"].round(2)
    products["revenue_rank"]      = products["total_revenue"].rank(ascending=False).astype(int)
    products = products.sort_values("total_revenue", ascending=False)
    products[["total_revenue", "total_profit"]] = products[["total_revenue", "total_profit"]].round(2)

    logger.info(f"📦 Product analysis: {len(products)} products")
    return products


def compute_category_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Category-level summary."""
    cats = df.groupby("category").agg(
        total_revenue    = ("net_revenue", "sum"),
        total_profit     = ("profit",      "sum"),
        total_orders     = ("order_id",    "nunique"),
        total_units      = ("quantity",    "sum"),
        unique_customers = ("customer_id", "nunique"),
        avg_order_value  = ("net_revenue", "mean")
    ).reset_index().sort_values("total_revenue", ascending=False)

    cats["profit_margin_pct"] = (cats["total_profit"] / cats["total_revenue"] * 100).round(2)
    cats["revenue_share_pct"] = (cats["total_revenue"] / cats["total_revenue"].sum() * 100).round(2)
    cats["avg_order_value"]   = cats["avg_order_value"].round(2)
    cats[["total_revenue", "total_profit"]] = cats[["total_revenue", "total_profit"]].round(2)
    logger.info(f"🏷️  Category analysis: {len(cats)} categories")
    return cats


def compute_rfm_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """
    RFM (Recency, Frequency, Monetary) customer segmentation.
    Segments customers into Champions, Loyal, At Risk, etc.
    """
    snapshot_date = df["order_date"].max()

    rfm = df.groupby("customer_id").agg(
        recency   = ("order_date",  lambda x: (snapshot_date - x.max()).days),
        frequency = ("order_id",    "nunique"),
        monetary  = ("net_revenue", "sum")
    ).reset_index()

    # Score 1-5 for each dimension
    rfm["r_score"] = pd.qcut(rfm["recency"],   5, labels=[5,4,3,2,1], duplicates="drop").astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"], 5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"],  5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def rfm_segment(score):
        if score >= 13: return "Champions"
        if score >= 10: return "Loyal Customers"
        if score >= 7:  return "Potential Loyalists"
        if score >= 5:  return "At Risk"
        return "Lost"

    rfm["rfm_segment"] = rfm["rfm_score"].apply(rfm_segment)
    rfm["monetary"]    = rfm["monetary"].round(2)
    logger.info(f"👥 RFM segmentation: {len(rfm)} customers")
    logger.info(f"\n{rfm['rfm_segment'].value_counts().to_string()}")
    return rfm


def compute_customer_analysis(df: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    """Customer-level KPIs merged with RFM segments."""
    cust = df.groupby(["customer_id", "segment", "region"]).agg(
        total_revenue  = ("net_revenue", "sum"),
        total_orders   = ("order_id",    "nunique"),
        total_units    = ("quantity",    "sum"),
        avg_order_value = ("net_revenue", "mean"),
        first_order    = ("order_date",  "min"),
        last_order     = ("order_date",  "max")
    ).reset_index()

    cust = cust.merge(rfm[["customer_id", "rfm_segment", "rfm_score"]], on="customer_id", how="left")
    cust["avg_order_value"] = cust["avg_order_value"].round(2)
    cust["total_revenue"]   = cust["total_revenue"].round(2)
    cust = cust.sort_values("total_revenue", ascending=False)
    logger.info(f"👤 Customer analysis: {len(cust)} customers")
    return cust


def save_all(dfs: dict, ts: str) -> dict:
    """Save all computed datasets."""
    os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)
    paths = {}
    for name, df in dfs.items():
        path = os.path.join(PROCESSED_DATA_PATH, f"{name}_{ts}.csv")
        df.to_csv(path, index=False)
        paths[name] = path
        logger.info(f"💾 {name} → {path}")
    return paths


def run_transformation(transactions: pd.DataFrame, ts: str) -> dict:
    """Main transformation entry point."""
    df = clean_transactions(transactions)

    monthly    = compute_monthly_revenue(df)
    regional   = compute_regional_analysis(df)
    products   = compute_product_performance(df)
    categories = compute_category_analysis(df)
    rfm        = compute_rfm_segmentation(df)
    customers  = compute_customer_analysis(df, rfm)

    dfs = {
        "monthly_kpis": monthly,
        "regional":     regional,
        "products":     products,
        "categories":   categories,
        "rfm":          rfm,
        "customers":    customers,
        "transactions": df
    }
    save_all(dfs, ts)
    return dfs


if __name__ == "__main__":
    import glob
    from config import RAW_DATA_PATH
    files = sorted(glob.glob(os.path.join(RAW_DATA_PATH, "transactions_*.csv")))
    if files:
        df = pd.read_csv(files[-1], parse_dates=["order_date"])
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = run_transformation(df, ts)
        print(f"\nRegional Performance:\n{results['regional'][['region','total_revenue','vs_avg_pct','performance']].to_string()}")
        print(f"\nTop 5 Products:\n{results['products'].head(5)[['product_name','category','total_revenue','profit_margin_pct']].to_string()}")
