-- ============================================================
-- Query 6: Quarter-over-Quarter Revenue Growth
-- Techniques: CTE, LAG() window function, CASE WHEN
-- Business Question: How does each quarter compare to the previous?
-- ============================================================

WITH quarterly_revenue AS (
    -- Step 1: Aggregate sales by quarter
    SELECT
        d.year,
        d.quarter,
        ROUND(SUM(f.net_revenue), 2)          AS total_revenue,
        ROUND(SUM(f.profit), 2)               AS total_profit,
        ROUND(SUM(f.gross_revenue), 2)        AS gross_revenue,
        ROUND(SUM(f.discount_amt), 2)         AS total_discounts,
        COUNT(DISTINCT f.order_id)            AS total_orders,
        COUNT(DISTINCT f.customer_id)         AS unique_customers,
        SUM(f.quantity)                       AS total_units,
        SUM(f.is_returned)                    AS total_returns,
        ROUND(AVG(f.net_revenue), 2)          AS avg_order_value
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.quarter
),

with_qoq AS (
    -- Step 2: Add previous quarter using LAG() window function
    SELECT
        *,
        LAG(total_revenue) OVER (
            ORDER BY year, quarter
        )                                     AS prev_quarter_revenue,

        LAG(total_orders) OVER (
            ORDER BY year, quarter
        )                                     AS prev_quarter_orders,

        -- Cumulative revenue
        SUM(total_revenue) OVER (
            ORDER BY year, quarter
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                     AS cumulative_revenue
    FROM quarterly_revenue
)

-- Step 3: Calculate QoQ growth and classification
SELECT
    year,
    quarter,
    total_revenue,
    total_profit,
    gross_revenue,
    total_discounts,
    total_orders,
    unique_customers,
    total_units,
    total_returns,
    avg_order_value,
    ROUND(cumulative_revenue, 2)                                    AS cumulative_revenue,
    prev_quarter_revenue,

    -- QoQ Revenue Growth
    ROUND(
        (total_revenue - prev_quarter_revenue) / prev_quarter_revenue * 100
    , 2)                                                            AS qoq_revenue_growth_pct,

    -- QoQ Orders Growth
    ROUND(
        (total_orders - prev_quarter_orders) * 100.0 / prev_quarter_orders
    , 2)                                                            AS qoq_orders_growth_pct,

    -- Profit margin
    ROUND(total_profit / total_revenue * 100, 2)                   AS profit_margin_pct,

    -- Discount rate
    ROUND(total_discounts / gross_revenue * 100, 2)                AS discount_rate_pct,

    -- Growth classification
    CASE
        WHEN (total_revenue - prev_quarter_revenue) / prev_quarter_revenue * 100 >= 20
            THEN 'Strong Growth'
        WHEN (total_revenue - prev_quarter_revenue) / prev_quarter_revenue * 100 >= 5
            THEN 'Moderate Growth'
        WHEN (total_revenue - prev_quarter_revenue) / prev_quarter_revenue * 100 >= -5
            THEN 'Stable'
        WHEN (total_revenue - prev_quarter_revenue) / prev_quarter_revenue * 100 >= -20
            THEN 'Declining'
        WHEN prev_quarter_revenue IS NULL
            THEN 'Baseline Quarter'
        ELSE 'Significant Decline'
    END                                                             AS growth_classification

FROM with_qoq
ORDER BY year, quarter;
