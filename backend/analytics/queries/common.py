
def build_filtered_items_cte(filters):
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
        value = 1 if filters["reordered"] else 0
        conditions.append(f"oi.reordered = {value}")

    if filters["date_from"]:
        conditions.append(
            "CAST(o.synthetic_order_timestamp AS DATE) >= "
            f"DATE '{filters['date_from']}'"
        )

    if filters["date_to"]:
        conditions.append(
            "CAST(o.synthetic_order_timestamp AS DATE) <= "
            f"DATE '{filters['date_to']}'"
        )

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    return f"""
    WITH filtered_items AS (
        SELECT
            oi.order_id,
            o.user_id,
            oi.product_id,
            oi.reordered,
            p.department_id,
            p.aisle_id,
            p.unit_price,
            CAST(
                o.synthetic_order_timestamp AS TIMESTAMP
            ) AS order_timestamp

        FROM instacart_db.order_items oi

        JOIN instacart_db.products p
            ON oi.product_id = p.product_id

        JOIN instacart_db.orders o
            ON oi.order_id = o.order_id

        {where_clause}
    )
    """
