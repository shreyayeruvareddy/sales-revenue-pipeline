-- ============================================================
-- Query 5: Customer Lifetime Value & Segment Analysis
-- Techniques: CTE, window functions, NTILE() for scoring
-- Business Question: Who are our most valuable customers?
-- ============================================================

WITH customer_transactions AS (
    -- Step 1: Build customer-level transaction summary
    SELECT
        f.customer_id,
        c.segment,
        c.region,
        ROUND(SUM(f.net_revenue), 2)          AS total_spend,
        ROUND(SUM(f.profit), 2)               AS total_profit_generated,
        COUNT(DISTINCT f.order_id)            AS total_orders,
        SUM(f.quantity)                       AS total_units,
        ROUND(AVG(f.net_revenue), 2)          AS avg_order_value,
        MIN(f.date_id)                        AS first_order_date,
        MAX(f.date_id)                        AS last_order_date,
        SUM(f.is_returned)                    AS total_returns,
        MAX(f.date_id)                        AS last_active_date
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_id = c.customer_id
    GROUP BY f.customer_id, c.segment, c.region
),

rfm_scores AS (
    -- Step 2: Compute RFM scores using NTILE() window function
    SELECT
        customer_id,
        segment,
        region,
        total_spend,
        total_profit_generated,
        total_orders,
        total_units,
        avg_order_value,
        first_order_date,
        last_order_date,
        total_returns,

        -- Recency: higher score = more recent (NTILE reverses for recency)
        NTILE(5) OVER (ORDER BY last_order_date DESC)   AS recency_score,

        -- Frequency: higher score = more orders
        NTILE(5) OVER (ORDER BY total_orders ASC)       AS frequency_score,

        -- Monetary: higher score = higher spend
        NTILE(5) OVER (ORDER BY total_spend ASC)        AS monetary_score

    FROM customer_transactions
),

rfm_classified AS (
    -- Step 3: Classify customers into RFM segments
    SELECT
        *,
        recency_score + frequency_score + monetary_score AS rfm_total_score,
        CASE
            WHEN recency_score + frequency_score + monetary_score >= 13
                THEN 'Champions'
            WHEN recency_score + frequency_score + monetary_score >= 10
                THEN 'Loyal Customers'
            WHEN recency_score + frequency_score + monetary_score >= 7
                THEN 'Potential Loyalists'
            WHEN recency_score + frequency_score + monetary_score >= 5
                THEN 'At Risk'
            ELSE 'Lost'
        END AS rfm_segment
    FROM rfm_scores
)

-- Step 4: Final output with rankings
SELECT
    customer_id,
    segment,
    region,
    total_spend,
    total_profit_generated,
    total_orders,
    total_units,
    avg_order_value,
    first_order_date,
    last_order_date,
    total_returns,
    recency_score,
    frequency_score,
    monetary_score,
    rfm_total_score,
    rfm_segment,

    -- Global spend rank
    RANK() OVER (ORDER BY total_spend DESC)              AS spend_rank,

    -- Rank within segment
    RANK() OVER (
        PARTITION BY segment
        ORDER BY total_spend DESC
    )                                                    AS segment_spend_rank,

    -- Rank within region
    RANK() OVER (
        PARTITION BY region
        ORDER BY total_spend DESC
    )                                                    AS region_spend_rank

FROM rfm_classified
ORDER BY total_spend DESC;
