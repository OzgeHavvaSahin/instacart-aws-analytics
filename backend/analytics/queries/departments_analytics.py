
from queries.common import build_filtered_items_cte


def build_departments_analytics_query(filters):
    cte = build_filtered_items_cte(filters)

    return f"""
    {cte}

    SELECT
        d.department_id,
        d.department AS department_name,

        COUNT(*) AS units_sold,

        COUNT(DISTINCT fi.order_id) AS total_orders,

        COUNT(DISTINCT fi.user_id) AS total_customers,

        ROUND(
            COALESCE(SUM(fi.unit_price), 0),
            2
        ) AS estimated_revenue,

        ROUND(
            100.0 *
            SUM(
                CASE WHEN fi.reordered = 1
                THEN 1 ELSE 0 END
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS reorder_rate

    FROM filtered_items fi

    JOIN instacart_db.departments d
        ON fi.department_id = d.department_id

    GROUP BY
        d.department_id,
        d.department

    ORDER BY
        estimated_revenue DESC,
        d.department_id ASC
    """
