SUMMARY_QUERY = """
SELECT
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.user_id) AS total_customers,
    COUNT(*) AS total_items,
    ROUND(SUM(p.unit_price), 2) AS estimated_revenue
FROM instacart_db.orders o
JOIN instacart_db.order_items oi
    ON o.order_id = oi.order_id
JOIN instacart_db.products p
    ON oi.product_id = p.product_id
"""
