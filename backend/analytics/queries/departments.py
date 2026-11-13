DEPARTMENTS_QUERY = """
SELECT
    d.department_id,
    d.department AS department_name,
    COUNT(*) AS units_sold,
    ROUND(
        COALESCE(SUM(p.unit_price), 0),
        2
    ) AS estimated_revenue
FROM instacart_db.order_items oi
JOIN instacart_db.products p
    ON oi.product_id = p.product_id
JOIN instacart_db.departments d
    ON p.department_id = d.department_id
GROUP BY
    d.department_id,
    d.department
ORDER BY estimated_revenue DESC
"""
