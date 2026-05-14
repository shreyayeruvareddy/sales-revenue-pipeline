-- ============================================================
-- Query 3: Product Revenue Ranking
-- Techniques: CTE, RANK() window function, PARTITION BY category
-- Business Question: Which products and categories drive the most revenue?
-- ============================================================

WITH product_stats AS (
    -- Step 1: Aggregate sales per product
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.unit_price                              AS list_price,
        ROUND(SUM(f.net_revenue), 2)              AS total_revenue,
        ROUND(SUM(f.profit), 2)                   AS total_profit,
        ROUND(SUM(f.gross_revenue), 2)            AS gross_revenue,
        ROUND(SUM(f.discount_amt), 2)             AS total_discounts,
        SUM(f.quantity)                           AS total_units_sold,
        COUNT(DISTINCT f.order_id)                AS total_orders,
        COUNT(DISTINCT f.customer_id)             AS unique_buyers,
        ROUND(AVG(f.unit_price), 2)               AS avg_selling_price,
        ROUND(AVG(f.discount_pct), 2)             AS avg_discount_pct,
        SUM(f.is_returned)                        AS return_count
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category, p.unit_price
),

category_totals AS (
    -- Step 2: Category-level totals for revenue share calculation
    SELECT
        category,
        SUM(total_revenue) AS cat_revenue
    FROM product_stats
    GROUP BY category
),

company_total AS (
    SELECT SUM(total_revenue) AS grand_total FROM product_stats
)

-- Step 3: Apply window functions for rankings
SELECT
    ps.product_id,
    ps.product_name,
    ps.category,
    ps.list_price,
    ps.avg_selling_price,
    ps.total_revenue,
    ps.total_profit,
    ps.gross_revenue,
    ps.total_discounts,
    ps.total_units_sold,
    ps.total_orders,
    ps.unique_buyers,
    ps.avg_discount_pct,
    ps.return_count,

    -- Derived metrics
    ROUND(ps.total_profit / ps.total_revenue * 100, 2)              AS profit_margin_pct,
    ROUND(ps.return_count * 100.0 / ps.total_orders, 2)             AS return_rate_pct,
    ROUND(ps.total_revenue / ct.company_total * 100, 2)             AS company_revenue_share_pct,
    ROUND(ps.total_revenue / cc.cat_revenue * 100, 2)               AS category_revenue_share_pct,

    -- Global rankings using RANK() window function
    RANK() OVER (ORDER BY ps.total_revenue DESC)                     AS revenue_rank,
    RANK() OVER (ORDER BY ps.total_profit DESC)                      AS profit_rank,
    RANK() OVER (ORDER BY ps.total_units_sold DESC)                  AS volume_rank,

    -- Within-category ranking using PARTITION BY
    RANK() OVER (
        PARTITION BY ps.category
        ORDER BY ps.total_revenue DESC
    )                                                                AS category_rank,

    -- Running total within category
    ROUND(SUM(ps.total_revenue) OVER (
        PARTITION BY ps.category
        ORDER BY ps.total_revenue DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                                                            AS category_cumulative_revenue

FROM product_stats ps
JOIN category_totals cc ON ps.category = cc.category
CROSS JOIN company_total ct
ORDER BY revenue_rank;
