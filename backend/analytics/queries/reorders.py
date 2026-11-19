from queries.common import build_filtered_items_cte


def build_reorders_query(filters):
    cte = build_filtered_items_cte(filters)

    return f"""
    {cte}

    SELECT
        COUNT(*) AS total_items,

        COALESCE(
            SUM(
                CASE WHEN reordered = 1
                THEN 1 ELSE 0 END
            ),
            0
        ) AS reordered_items,

        COALESCE(
            SUM(
                CASE WHEN reordered = 0
                THEN 1 ELSE 0 END
            ),
            0
        ) AS first_time_items,

        COUNT(DISTINCT order_id) AS total_orders,

        ROUND(
            100.0 *
            SUM(
                CASE WHEN reordered = 1
                THEN 1 ELSE 0 END
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS reorder_rate

    FROM filtered_items
    """
