
from queries.common import build_filtered_items_cte


ALLOWED_GRANULARITIES = {
    "day",
    "week",
    "month"
}


def build_revenue_trend_query(filters, granularity="day"):
    if granularity not in ALLOWED_GRANULARITIES:
        raise ValueError(
            "granularity must be day, week or month"
        )

    cte = build_filtered_items_cte(filters)

    return f"""
    {cte}

    SELECT
        CAST(
            DATE_TRUNC(
                '{granularity}',
                order_timestamp
            ) AS VARCHAR
        ) AS period,

        COUNT(DISTINCT order_id) AS total_orders,

        COUNT(*) AS total_items,

        ROUND(
            COALESCE(SUM(unit_price), 0),
            2
        ) AS estimated_revenue

    FROM filtered_items

    GROUP BY
        DATE_TRUNC(
            '{granularity}',
            order_timestamp
        )

    ORDER BY period ASC
    """
