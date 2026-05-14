-- ============================================================
-- Query 8: Top 5 Customers Per Region (Advanced Window Function)
-- Techniques: CTE, RANK() with PARTITION BY, DENSE_RANK()
-- Business Question: Who are the top customers in each region?
-- ============================================================

WITH customer_revenue AS (
    -- Step 1: Customer-level revenue summary
    SELECT
        f.customer_id,
        c.segment,
        f.region,
        ROUND(SUM(f.net_revenue), 2)          AS total_revenue,
        ROUND(SUM(f.profit), 2)               AS total_profit,
        COUNT(DISTINCT f.order_id)            AS total_orders,
        ROUND(AVG(f.net_revenue), 2)          AS avg_order_value,
        SUM(f.is_returned)                    AS total_returns,
        MAX(f.date_id)                        AS last_purchase_date
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_id = c.customer_id
    GROUP BY f.customer_id, c.segment, f.region
),

ranked_customers AS (
    -- Step 2: Rank customers within each region using PARTITION BY
    SELECT
        *,
        RANK() OVER (
            PARTITION BY region
            ORDER BY total_revenue DESC
        )                                     AS region_rank,

        DENSE_RANK() OVER (
            PARTITION BY region
            ORDER BY total_orders DESC
        )                                     AS order_frequency_rank,

        -- Percentile within region
        ROUND(
            PERCENT_RANK() OVER (
                PARTITION BY region
                ORDER BY total_revenue
            ) * 100
        , 1)                                  AS revenue_percentile_in_region,

        -- Running total within region
        ROUND(SUM(total_revenue) OVER (
            PARTITION BY region
            ORDER BY total_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2)                                 AS region_cumulative_revenue,

        -- Region total for share calculation
        SUM(total_revenue) OVER (
            PARTITION BY region
        )                                     AS region_total_revenue

    FROM customer_revenue
)

-- Step 3: Filter to top 5 per region
SELECT
    region,
    region_rank,
    customer_id,
    segment,
    total_revenue,
    total_profit,
    total_orders,
    avg_order_value,
    total_returns,
    last_purchase_date,
    order_frequency_rank,
    revenue_percentile_in_region,
    region_cumulative_revenue,
    ROUND(total_revenue / region_total_revenue * 100, 2)     AS region_revenue_share_pct,
    ROUND(total_profit / total_revenue * 100, 2)             AS profit_margin_pct
FROM ranked_customers
WHERE region_rank <= 5
ORDER BY region, region_rank;
