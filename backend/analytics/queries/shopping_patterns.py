from queries.common import build_filtered_items_cte


def build_shopping_patterns_query(filters):
    cte = build_filtered_items_cte(filters)

    return f"""
    {cte},

    order_periods AS (
        SELECT DISTINCT
            order_id,
            DAY_OF_WEEK(order_timestamp) AS day_of_week,
            HOUR(order_timestamp) AS hour_of_day

        FROM filtered_items
    )

    SELECT
        day_of_week,
        hour_of_day,
        COUNT(*) AS total_orders

    FROM order_periods

    GROUP BY
        day_of_week,
        hour_of_day

    ORDER BY
        day_of_week ASC,
        hour_of_day ASC
    """
