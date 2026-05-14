-- ============================================================
-- Query 4: Category Revenue Share & Performance
-- Techniques: CTE, RANK() window function, revenue share %
-- Business Question: Which categories drive the most revenue and profit?
-- ============================================================

WITH category_metrics AS (
    -- Step 1: Aggregate all sales by category
    SELECT
        p.category,
        ROUND(SUM(f.net_revenue), 2)          AS total_revenue,
        ROUND(SUM(f.profit), 2)               AS total_profit,
        ROUND(SUM(f.gross_revenue), 2)        AS gross_revenue,
        ROUND(SUM(f.discount_amt), 2)         AS total_discounts,
        COUNT(DISTINCT f.order_id)            AS total_orders,
        COUNT(DISTINCT f.customer_id)         AS unique_customers,
        SUM(f.quantity)                       AS total_units,
        ROUND(AVG(f.net_revenue), 2)          AS avg_order_value,
        ROUND(AVG(f.unit_price), 2)           AS avg_unit_price,
        SUM(f.is_returned)                    AS total_returns
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.category
),

grand_totals AS (
    -- Step 2: Company-wide totals for share calculations
    SELECT
        SUM(total_revenue)  AS company_revenue,
        SUM(total_profit)   AS company_profit,
        SUM(total_orders)   AS company_orders
    FROM category_metrics
)

-- Step 3: Final output with revenue shares and rankings
SELECT
    cm.category,
    cm.total_revenue,
    cm.total_profit,
    cm.gross_revenue,
    cm.total_discounts,
    cm.total_orders,
    cm.unique_customers,
    cm.total_units,
    cm.avg_order_value,
    cm.avg_unit_price,
    cm.total_returns,

    -- Share metrics
    ROUND(cm.total_revenue / gt.company_revenue * 100, 2)       AS revenue_share_pct,
    ROUND(cm.total_profit  / gt.company_profit  * 100, 2)       AS profit_share_pct,
    ROUND(cm.total_orders  / gt.company_orders  * 100.0, 2)     AS order_share_pct,

    -- Margin metrics
    ROUND(cm.total_profit   / cm.total_revenue  * 100, 2)       AS profit_margin_pct,
    ROUND(cm.total_discounts/ cm.gross_revenue  * 100, 2)       AS discount_rate_pct,
    ROUND(cm.total_returns  * 100.0 / cm.total_orders, 2)       AS return_rate_pct,

    -- Rankings
    RANK() OVER (ORDER BY cm.total_revenue DESC)                 AS revenue_rank,
    RANK() OVER (ORDER BY cm.total_profit  DESC)                 AS profit_rank,
    RANK() OVER (ORDER BY
        cm.total_profit / cm.total_revenue DESC)                 AS margin_rank,

    -- Cumulative revenue share (running total)
    ROUND(SUM(cm.total_revenue) OVER (
        ORDER BY cm.total_revenue DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / gt.company_revenue * 100, 2)                             AS cumulative_revenue_share_pct

FROM category_metrics cm
CROSS JOIN grand_totals gt
ORDER BY revenue_rank;
