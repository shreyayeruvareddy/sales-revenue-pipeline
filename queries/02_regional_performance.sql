-- ============================================================
-- Query 2: Regional Performance vs Company Average
-- Techniques: CTE, CASE WHEN, cross-join for avg comparison
-- Business Question: Which regions are underperforming and by how much?
-- Key Insight: Southeast underperforms by ~21.88%, Midwest by ~10.83%
-- ============================================================

WITH regional_totals AS (
    -- Step 1: Aggregate sales metrics by region
    SELECT
        f.region,
        ROUND(SUM(f.net_revenue), 2)         AS total_revenue,
        ROUND(SUM(f.profit), 2)              AS total_profit,
        ROUND(SUM(f.gross_revenue), 2)       AS gross_revenue,
        ROUND(SUM(f.discount_amt), 2)        AS total_discounts,
        COUNT(DISTINCT f.order_id)           AS total_orders,
        COUNT(DISTINCT f.customer_id)        AS unique_customers,
        ROUND(AVG(f.net_revenue), 2)         AS avg_order_value,
        SUM(f.quantity)                      AS total_units,
        SUM(f.is_returned)                   AS total_returns
    FROM fact_sales f
    GROUP BY f.region
),

company_average AS (
    -- Step 2: Compute company-wide average revenue (used for comparison)
    SELECT
        AVG(total_revenue)  AS avg_revenue,
        SUM(total_revenue)  AS company_total
    FROM regional_totals
)

-- Step 3: Compare each region to the company average
SELECT
    r.region,
    r.total_revenue,
    r.total_profit,
    r.gross_revenue,
    r.total_discounts,
    r.total_orders,
    r.unique_customers,
    r.avg_order_value,
    r.total_units,
    r.total_returns,

    -- Profit margin
    ROUND(r.total_profit / r.total_revenue * 100, 2)               AS profit_margin_pct,

    -- Return rate
    ROUND(r.total_returns * 100.0 / r.total_orders, 2)             AS return_rate_pct,

    -- Revenue share of company total
    ROUND(r.total_revenue / c.company_total * 100, 2)              AS revenue_share_pct,

    -- Performance vs average
    ROUND(c.avg_revenue, 2)                                         AS company_avg_revenue,
    ROUND(r.total_revenue - c.avg_revenue, 2)                       AS variance_from_avg,
    ROUND(
        (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100
    , 2)                                                             AS vs_avg_pct,

    -- Performance tier classification
    CASE
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 >= 10
            THEN 'Strong Performer'
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 >= 5
            THEN 'Above Average'
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 >= -5
            THEN 'Average'
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 >= -15
            THEN 'Below Average'
        ELSE 'Underperforming'
    END                                                              AS performance_tier,

    -- Recommendation
    CASE
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 < -10
            THEN 'Immediate action required — review pricing and marketing strategy'
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 < -5
            THEN 'Monitor closely — targeted campaigns recommended'
        WHEN (r.total_revenue - c.avg_revenue) / c.avg_revenue * 100 >= 10
            THEN 'Replicate strategy in other regions'
        ELSE 'Maintain current strategy'
    END                                                              AS recommendation

FROM regional_totals r
CROSS JOIN company_average c
ORDER BY r.total_revenue DESC;
