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



PRODUCT_SORT_COLUMNS = {
    "units_sold": "units_sold",
    "estimated_revenue": "estimated_revenue",
    "reorder_rate": "reorder_rate",
    "product_name": "product_name",
}



def build_products_query(filters):
    conditions = []

    if filters["department_id"] is not None:
        conditions.append(
            f"p.department_id = {int(filters['department_id'])}"
        )

    if filters["aisle_id"] is not None:
        conditions.append(
            f"p.aisle_id = {int(filters['aisle_id'])}"
        )

    if filters["reordered"] is not None:
        reordered = 1 if filters["reordered"] else 0
        conditions.append(f"oi.reordered = {reordered}")

    if filters.get("date_from"):
        conditions.append(
            "CAST(o.synthetic_order_timestamp AS DATE) >= "
            f"DATE '{filters['date_from']}'"
        )

    if filters.get("date_to"):
        conditions.append(
            "CAST(o.synthetic_order_timestamp AS DATE) <= "
            f"DATE '{filters['date_to']}'"
        )

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    sort_column = PRODUCT_SORT_COLUMNS[
        filters["sort_by"]
    ]

    sort_order = filters["sort_order"].upper()
    limit = filters["limit"]

    return f"""
    SELECT
        p.product_id,
        p.product_name,
        p.department_id,
        p.aisle_id,
        COUNT(*) AS units_sold,
        COUNT(DISTINCT oi.order_id) AS order_count,
        ROUND(
            COALESCE(SUM(p.unit_price), 0), 2
        ) AS estimated_revenue,
        ROUND(
            100.0 *
            SUM(
                CASE WHEN oi.reordered = 1
                THEN 1 ELSE 0 END
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS reorder_rate

    FROM instacart_db.order_items oi

    JOIN instacart_db.products p
        ON oi.product_id = p.product_id

    JOIN instacart_db.orders o
        ON oi.order_id = o.order_id

    {where_clause}

    GROUP BY
        p.product_id,
        p.product_name,
        p.department_id,
        p.aisle_id

    ORDER BY
        {sort_column} {sort_order},
        p.product_id ASC

    LIMIT {limit}
    """
