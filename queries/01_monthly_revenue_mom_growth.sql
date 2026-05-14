-- ============================================================
-- Query 1: Monthly Revenue with Month-over-Month Growth
-- Techniques: CTE, LAG() window function, SUM() running total
-- Business Question: How is revenue trending month over month?
-- ============================================================

WITH monthly_revenue AS (
    -- Step 1: Aggregate raw sales into monthly buckets
    SELECT
        d.year,
        d.month,
        d.month_name,
        d.quarter,
        ROUND(SUM(f.net_revenue), 2)         AS total_revenue,
        ROUND(SUM(f.profit), 2)              AS total_profit,
        COUNT(DISTINCT f.order_id)           AS total_orders,
        COUNT(DISTINCT f.customer_id)        AS unique_customers,
        ROUND(AVG(f.net_revenue), 2)         AS avg_order_value,
        SUM(f.is_returned)                   AS total_returns
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month, d.month_name, d.quarter
),

with_lag AS (
    -- Step 2: Add previous month revenue using LAG() window function
    SELECT
        *,
        LAG(total_revenue) OVER (
            ORDER BY year, month
        ) AS prev_month_revenue,

        -- Running YTD total using cumulative SUM window
        SUM(total_revenue) OVER (
            ORDER BY year, month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS ytd_revenue
    FROM monthly_revenue
)

-- Step 3: Calculate MoM growth % and profit margin
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
    total_returns,
    ROUND(ytd_revenue, 2)                                              AS ytd_revenue,
    prev_month_revenue,
    ROUND(
        (total_revenue - prev_month_revenue) / prev_month_revenue * 100
    , 2)                                                               AS mom_growth_pct,
    ROUND(total_profit / total_revenue * 100, 2)                      AS profit_margin_pct,
    ROUND(total_returns * 100.0 / total_orders, 2)                    AS return_rate_pct
FROM with_lag
ORDER BY year, month;
