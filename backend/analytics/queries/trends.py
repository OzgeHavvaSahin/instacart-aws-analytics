ORDERS_TREND_QUERY = """
SELECT
    CAST(
        synthetic_order_timestamp AS DATE
    ) AS order_date,
    COUNT(*) AS total_orders,
    COUNT(DISTINCT user_id) AS total_customers
FROM instacart_db.orders
GROUP BY
    CAST(
        synthetic_order_timestamp AS DATE
    )
ORDER BY order_date ASC
"""
