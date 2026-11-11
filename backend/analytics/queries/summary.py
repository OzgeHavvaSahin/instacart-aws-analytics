SUMMARY_QUERY = """
WITH order_stats AS (
    SELECT
        COUNT(*) AS total_orders,
        COUNT(DISTINCT user_id) AS total_customers
    FROM instacart_db.orders
),
item_stats AS (
    SELECT
        COUNT(*) AS total_items
    FROM instacart_db.order_items
),
revenue_stats AS (
    SELECT
        ROUND(
            COALESCE(SUM(p.unit_price), 0),
            2
        ) AS estimated_revenue
    FROM instacart_db.order_items oi
    JOIN instacart_db.products p
        ON oi.product_id = p.product_id
)
SELECT
    o.total_orders,
    o.total_customers,
    i.total_items,
    r.estimated_revenue
FROM order_stats o
CROSS JOIN item_stats i
CROSS JOIN revenue_stats r
"""
