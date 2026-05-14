# ============================================================
# src/data_generator.py — Simulate retail/e-commerce sales
# Generates 10,000+ transactions across 12 months
# ============================================================

import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime, timedelta
from config import (NUM_CUSTOMERS, NUM_PRODUCTS, NUM_MONTHS, START_DATE,
                    REGIONS, CATEGORIES, SEGMENTS, SEGMENT_WEIGHTS,
                    SEASONALITY, RAW_DATA_PATH, RANDOM_SEED)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
np.random.seed(RANDOM_SEED)


def generate_customers() -> pd.DataFrame:
    """Generate 1,000 customers with segments and regions."""
    regions = list(REGIONS.keys())
    customers = []
    for i in range(1, NUM_CUSTOMERS + 1):
        segment = np.random.choice(SEGMENTS, p=SEGMENT_WEIGHTS)
        region  = np.random.choice(regions)
        customers.append({
            "customer_id":   f"CUST_{i:04d}",
            "customer_name": f"Customer_{i:04d}",
            "segment":       segment,
            "region":        region,
            "city":          f"City_{np.random.randint(1, 50)}",
            "joined_date":   (datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 730))).strftime("%Y-%m-%d")
        })
    return pd.DataFrame(customers)


def generate_products() -> pd.DataFrame:
    """Generate 50 products across 5 categories."""
    products = []
    cat_names = list(CATEGORIES.keys())
    per_cat   = NUM_PRODUCTS // len(cat_names)

    for cat in cat_names:
        info = CATEGORIES[cat]
        for j in range(1, per_cat + 1):
            pid   = f"PROD_{cat[:3].upper()}_{j:02d}"
            price = round(info["avg_price"] * np.random.uniform(0.6, 1.6), 2)
            products.append({
                "product_id":   pid,
                "product_name": f"{cat} Item {j}",
                "category":     cat,
                "unit_price":   price,
                "cost_price":   round(price * (1 - info["margin"]), 2),
                "margin_pct":   round(info["margin"] * 100, 1),
                "return_rate":  info["return_rate"]
            })
    return pd.DataFrame(products)


def generate_transactions(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """
    Generate realistic sales transactions:
    - Premium customers buy more frequently and in higher quantities
    - Seasonality affects monthly volumes
    - Regional multipliers affect revenue
    - Returns simulated based on category return rates
    """
    transactions = []
    order_id = 1
    start    = datetime.strptime(START_DATE, "%Y-%m-%d")

    # Orders per segment per month
    orders_per_month = {"Premium": 4, "Regular": 1.5, "Occasional": 0.4}

    for month in range(NUM_MONTHS):
        current_month = (start.replace(day=1) + pd.DateOffset(months=month))
        month_num     = current_month.month
        season_mult   = SEASONALITY[month_num]

        for _, customer in customers.iterrows():
            seg       = customer["segment"]
            region    = customer["region"]
            reg_mult  = REGIONS[region]
            base_orders = orders_per_month[seg]

            # Number of orders this month (Poisson distributed)
            n_orders = np.random.poisson(base_orders * season_mult)

            for _ in range(n_orders):
                # Pick random product
                product = products.sample(1).iloc[0]
                qty     = np.random.choice([1, 1, 1, 2, 2, 3, 4, 5],
                                            p=[0.35, 0.20, 0.15, 0.12, 0.08, 0.05, 0.03, 0.02])

                # Apply regional pricing variation
                unit_price   = round(product["unit_price"] * reg_mult * np.random.uniform(0.95, 1.05), 2)
                gross_revenue = round(unit_price * qty, 2)

                # Discount (Premium gets more discounts for loyalty)
                discount_pct = 0
                if seg == "Premium":
                    discount_pct = np.random.choice([0, 5, 10, 15], p=[0.5, 0.25, 0.15, 0.10])
                elif seg == "Regular":
                    discount_pct = np.random.choice([0, 5, 10], p=[0.7, 0.2, 0.1])

                discount_amt  = round(gross_revenue * discount_pct / 100, 2)
                net_revenue   = round(gross_revenue - discount_amt, 2)
                profit        = round((unit_price - product["cost_price"]) * qty - discount_amt, 2)

                # Return flag
                is_returned = np.random.random() < product["return_rate"]

                # Random day in month
                days_in_month = (current_month + pd.DateOffset(months=1) - current_month).days
                order_day     = np.random.randint(1, days_in_month + 1)
                order_date    = current_month.replace(day=order_day)

                transactions.append({
                    "order_id":      f"ORD_{order_id:06d}",
                    "customer_id":   customer["customer_id"],
                    "product_id":    product["product_id"],
                    "order_date":    order_date.strftime("%Y-%m-%d"),
                    "month":         month_num,
                    "month_name":    order_date.strftime("%B"),
                    "quarter":       f"Q{(month_num - 1) // 3 + 1}",
                    "year":          order_date.year,
                    "region":        region,
                    "segment":       seg,
                    "category":      product["category"],
                    "product_name":  product["product_name"],
                    "quantity":      qty,
                    "unit_price":    unit_price,
                    "discount_pct":  discount_pct,
                    "discount_amt":  discount_amt,
                    "gross_revenue": gross_revenue,
                    "net_revenue":   net_revenue,
                    "cost":          round(product["cost_price"] * qty, 2),
                    "profit":        profit,
                    "is_returned":   int(is_returned),
                    "payment_method": np.random.choice(
                        ["Credit Card", "Debit Card", "PayPal", "Buy Now Pay Later"],
                        p=[0.45, 0.25, 0.20, 0.10]
                    )
                })
                order_id += 1

    df = pd.DataFrame(transactions)
    logger.info(f"✅ Generated {len(df):,} transactions | ${df['net_revenue'].sum():,.0f} total revenue")
    return df


def run_data_generation() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Main entry point."""
    logger.info("🛒 Generating retail sales data...")
    customers   = generate_customers()
    products    = generate_products()
    transactions = generate_transactions(customers, products)

    os.makedirs(RAW_DATA_PATH, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    t_path = os.path.join(RAW_DATA_PATH, f"transactions_{ts}.csv")
    c_path = os.path.join(RAW_DATA_PATH, f"customers_{ts}.csv")
    p_path = os.path.join(RAW_DATA_PATH, f"products_{ts}.csv")

    transactions.to_csv(t_path, index=False)
    customers.to_csv(c_path, index=False)
    products.to_csv(p_path, index=False)

    logger.info(f"💾 Saved {len(transactions):,} transactions, {len(customers)} customers, {len(products)} products")
    return transactions, customers, products, ts


if __name__ == "__main__":
    t, c, p, _ = run_data_generation()
    print(f"\nTransactions: {len(t):,}")
    print(f"Total Revenue: ${t['net_revenue'].sum():,.2f}")
    print(f"\nBy Region:\n{t.groupby('region')['net_revenue'].sum().sort_values(ascending=False)}")
