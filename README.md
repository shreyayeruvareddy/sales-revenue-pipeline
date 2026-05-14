# Sales & Revenue Analytics Pipeline

> End-to-end retail/e-commerce ETL pipeline simulating 10,000+ transactions across 1,000 customers, 50 products, 4 regions, and 5 categories over 12 months — with star schema DB, KPI analytics, RFM segmentation, and Power BI/Tableau-ready exports.

---

## Project Overview

| Local | Production |
|---|---|
| `data/raw/` folder | AWS S3 Raw Zone |
| SQLite | PostgreSQL / AWS RDS |
| `run_pipeline.py` | Apache Airflow DAG |

---

## Architecture

```
Data Generation (1,000 customers, 50 products, 12 months)
        |
        v
[ Stage 1: Generate   ]  src/data_generator.py  → 10,000+ transactions
        |
        v
[ Stage 2: Transform  ]  src/transformation.py  → 6 KPI datasets
        |
        v
[ Stage 3: DB Load    ]  src/db_loader.py       → Star schema SQLite
        |
        v
[ Stage 4: Validate   ]  Query summary          → Power BI export
```

---

## Key KPIs Computed

- Monthly revenue with MoM growth %
- Regional performance vs average (identifies ~23% Southeast underperformance)
- Product ranking by revenue and profit margin
- Category revenue share %
- RFM customer segmentation (Champions → Lost)
- YTD cumulative revenue

---

## Database Schema (Star Schema)

```
fact_sales  ←→  dim_customer
                dim_product
                dim_date
                dim_region
                agg_monthly_kpis
                agg_regional_kpis
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Data Processing | Pandas 2.2, NumPy 1.26 |
| Database | SQLite → PostgreSQL upgrade path |
| Analytics | SQL CTEs, Window Functions, RFM |
| Visualization | CSV export → Power BI / Tableau |
| Version Control | Git / GitHub |

---

## Setup & Run

```bash
git clone https://github.com/shreyayeruvareddy/sales-revenue-pipeline.git
cd sales-revenue-pipeline
py -3.11 -m pip install -r requirements.txt
py -3.11 run_pipeline.py
```

---

## Key Business Insights

- Southeast region underperforms average by ~23% → targeted marketing opportunity
- Electronics drives highest absolute revenue; Beauty has highest profit margin (55%)
- Q4 (Oct–Dec) generates ~40% of annual revenue due to holiday seasonality
- Premium customers (15% of base) contribute ~35% of total revenue
- RFM Champions identified for retention and upsell campaigns

---

## Author

**Yeruva Bala Shreya Reddy**
M.S. Computer Science (Data Science) — UNC Charlotte
[GitHub](https://github.com/shreyayeruvareddy) | [Email](mailto:yeruvabalashreyareddy@gmail.com)
