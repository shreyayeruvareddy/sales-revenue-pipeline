-- ============================================================
-- Query 7: Payment Method & Discount Analysis
-- Techniques: CTE, window functions, CASE WHEN
-- Business Question: Which payment methods and discount levels drive most revenue?
-- ============================================================

WITH payment_stats AS (
    -- Step 1: Aggregate by payment method
    SELECT
        payment_method,
        ROUND(SUM(net_revenue), 2)            AS total_revenue,
        ROUND(SUM(profit), 2)                 AS total_profit,
        ROUND(SUM(gross_revenue), 2)          AS gross_revenue,
        ROUND(SUM(discount_amt), 2)           AS total_discounts,
        COUNT(DISTINCT order_id)              AS total_orders,
        COUNT(DISTINCT customer_id)           AS unique_customers,
        SUM(quantity)                         AS total_units,
        ROUND(AVG(net_revenue), 2)            AS avg_order_value,
        ROUND(AVG(discount_pct), 2)           AS avg_discount_pct,
        SUM(is_returned)                      AS total_returns
    FROM fact_sales
    GROUP BY payment_method
),

discount_bands AS (
    -- Step 2: Analyze revenue by discount band
    SELECT
        CASE
            WHEN discount_pct = 0          THEN 'No Discount'
            WHEN discount_pct <= 5         THEN '1-5% Discount'
            WHEN discount_pct <= 10        THEN '6-10% Discount'
            ELSE '11%+ Discount'
        END                                   AS discount_band,
        ROUND(SUM(net_revenue), 2)            AS total_revenue,
        ROUND(SUM(profit), 2)                 AS total_profit,
        COUNT(DISTINCT order_id)              AS total_orders,
        ROUND(AVG(net_revenue), 2)            AS avg_order_value,
        SUM(is_returned)                      AS total_returns
    FROM fact_sales
    GROUP BY
        CASE
            WHEN discount_pct = 0          THEN 'No Discount'
            WHEN discount_pct <= 5         THEN '1-5% Discount'
            WHEN discount_pct <= 10        THEN '6-10% Discount'
            ELSE '11%+ Discount'
        END
),

company_total AS (
    SELECT SUM(total_revenue) AS grand_total FROM payment_stats
)

-- Step 3: Payment method analysis with window functions
SELECT
    'PAYMENT_METHOD'                                                AS analysis_type,
    ps.payment_method                                              AS dimension,
    ps.total_revenue,
    ps.total_profit,
    ps.total_orders,
    ps.unique_customers,
    ps.avg_order_value,
    ps.avg_discount_pct,
    ps.total_returns,
    ROUND(ps.total_profit  / ps.total_revenue * 100, 2)           AS profit_margin_pct,
    ROUND(ps.total_returns * 100.0 / ps.total_orders, 2)          AS return_rate_pct,
    ROUND(ps.total_revenue / ct.grand_total * 100, 2)             AS revenue_share_pct,
    RANK() OVER (ORDER BY ps.total_revenue DESC)                   AS revenue_rank
FROM payment_stats ps
CROSS JOIN company_total ct

UNION ALL

-- Step 4: Discount band analysis
SELECT
    'DISCOUNT_BAND'                                                AS analysis_type,
    db.discount_band                                               AS dimension,
    db.total_revenue,
    db.total_profit,
    db.total_orders,
    NULL                                                           AS unique_customers,
    db.avg_order_value,
    NULL                                                           AS avg_discount_pct,
    db.total_returns,
    ROUND(db.total_profit / db.total_revenue * 100, 2)            AS profit_margin_pct,
    ROUND(db.total_returns * 100.0 / db.total_orders, 2)          AS return_rate_pct,
    ROUND(db.total_revenue / ct.grand_total * 100, 2)             AS revenue_share_pct,
    RANK() OVER (ORDER BY db.total_revenue DESC)                   AS revenue_rank
FROM discount_bands db
CROSS JOIN company_total ct

ORDER BY analysis_type, revenue_rank;
