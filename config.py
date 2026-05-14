# ============================================================
# config.py — Sales & Revenue Analytics Pipeline
# ============================================================

import random

RANDOM_SEED = 42

# Simulation Settings
NUM_CUSTOMERS    = 1000
NUM_PRODUCTS     = 50
NUM_MONTHS       = 12
START_DATE       = "2025-01-01"

# Regions & performance multipliers
REGIONS = {
    "Northeast": 1.15,   # Strong performer
    "Southeast": 0.77,   # Underperforming (-23%)
    "Midwest":   1.05,   # Slight above average
    "West":      1.18,   # Top performer
}

# Product Categories
CATEGORIES = {
    "Electronics":   {"avg_price": 285, "margin": 0.22, "return_rate": 0.08},
    "Clothing":      {"avg_price":  65, "margin": 0.48, "return_rate": 0.12},
    "Home & Garden": {"avg_price":  95, "margin": 0.38, "return_rate": 0.06},
    "Sports":        {"avg_price": 120, "margin": 0.35, "return_rate": 0.07},
    "Beauty":        {"avg_price":  45, "margin": 0.55, "return_rate": 0.05},
}

# Customer Segments
SEGMENTS = ["Premium", "Regular", "Occasional"]
SEGMENT_WEIGHTS = [0.15, 0.55, 0.30]

# Seasonality multipliers by month
SEASONALITY = {
    1: 0.75, 2: 0.70, 3: 0.85,   # Q1 — post-holiday slowdown
    4: 0.90, 5: 0.95, 6: 1.00,   # Q2 — spring pickup
    7: 0.95, 8: 1.00, 9: 1.05,   # Q3 — back to school
    10: 1.10, 11: 1.45, 12: 1.65 # Q4 — holiday surge
}

# File Paths
RAW_DATA_PATH       = "data/raw"
PROCESSED_DATA_PATH = "data/processed"
OUTPUT_PATH         = "outputs"
DB_PATH             = "data/sales_pipeline.db"
