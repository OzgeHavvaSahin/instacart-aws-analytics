def get_top_products_query(limit=10):
    return f"""
    SELECT
        p.product_id,
        p.product_name,
        d.department AS department_name,
        COUNT(*) AS units_sold,
        ROUND(
            SUM(p.unit_price), 2
        ) AS estimated_revenue
    FROM instacart_db.order_items oi
    JOIN instacart_db.products p
        ON oi.product_id = p.product_id
    LEFT JOIN instacart_db.departments d
        ON p.department_id = d.department_id
    GROUP BY
        p.product_id,
        p.product_name,
        d.department
    ORDER BY units_sold DESC
    LIMIT {limit}
    """
