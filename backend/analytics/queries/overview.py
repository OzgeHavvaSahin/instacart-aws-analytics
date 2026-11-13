def build_overview_query(filters):
    item_conditions = []

    if filters["department_id"] is not None:
        item_conditions.append(
            f"p.department_id = {filters['department_id']}"
        )

    if filters["aisle_id"] is not None:
        item_conditions.append(
            f"p.aisle_id = {filters['aisle_id']}"
        )

    if filters["reordered"] is not None:
        value = 1 if filters["reordered"] else 0
        item_conditions.append(
            f"oi.reordered = {value}"
        )

    item_where = (
        "WHERE " + " AND ".join(item_conditions)
        if item_conditions else ""
    )

    order_conditions = []

    if filters["date_from"]:
        order_conditions.append(
            "SUBSTR(CAST(o.synthetic_order_timestamp "
            "AS VARCHAR), 1, 10) >= "
            f"'{filters['date_from']}'"
        )

    if filters["date_to"]:
        order_conditions.append(
            "SUBSTR(CAST(o.synthetic_order_timestamp "
            "AS VARCHAR), 1, 10) <= "
            f"'{filters['date_to']}'"
        )

    if item_conditions:
        order_conditions.append(
            "EXISTS ("
            "SELECT 1 FROM selected_items si "
            "WHERE si.order_id = o.order_id"
            ")"
        )

    order_where = (
        "WHERE " + " AND ".join(order_conditions)
        if order_conditions else ""
    )

    return f"""
    WITH selected_items AS (
        SELECT
            oi.order_id,
            oi.reordered,
            p.unit_price
        FROM instacart_db.order_items oi
        JOIN instacart_db.products p
            ON oi.product_id = p.product_id
        {item_where}
    ),

    eligible_orders AS (
        SELECT
            o.order_id,
            o.user_id
        FROM instacart_db.orders o
        {order_where}
    ),

    order_stats AS (
        SELECT
            COUNT(*) AS total_orders,
            COUNT(DISTINCT user_id)
                AS total_customers
        FROM eligible_orders
    ),

    item_stats AS (
        SELECT
            COUNT(*) AS total_items,
            COALESCE(
                ROUND(SUM(si.unit_price), 2),
                0
            ) AS estimated_revenue,
            COALESCE(
                SUM(
                    CASE WHEN si.reordered = 1
                    THEN 1 ELSE 0 END
                ),
                0
            ) AS reordered_items
        FROM selected_items si
        JOIN eligible_orders eo
            ON si.order_id = eo.order_id
    )

    SELECT
        os.total_orders,
        os.total_customers,
        ist.total_items,
        ist.estimated_revenue,

        ROUND(
            CAST(ist.total_items AS DOUBLE)
            / NULLIF(os.total_orders, 0),
            2
        ) AS avg_basket_size,

        ROUND(
            100.0 * ist.reordered_items
            / NULLIF(ist.total_items, 0),
            2
        ) AS reorder_rate

    FROM order_stats os
    CROSS JOIN item_stats ist
    """
