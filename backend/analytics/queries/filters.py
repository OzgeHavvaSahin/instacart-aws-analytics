DEPARTMENTS_FILTER_QUERY = """
SELECT
    department_id,
    department
FROM instacart_db.departments
ORDER BY department
"""


def build_aisles_filter_query(department_id=None):
    where_clause = ""

    if department_id is not None:
        where_clause = (
            f"WHERE p.department_id = {department_id}"
        )

    return f"""
    SELECT DISTINCT
        a.aisle_id,
        a.aisle
    FROM instacart_db.aisles a
    JOIN instacart_db.products p
        ON a.aisle_id = p.aisle_id
    {where_clause}
    ORDER BY a.aisle
    """


DATE_BOUNDS_QUERY = """
SELECT
    MIN(
        SUBSTR(
            CAST(synthetic_order_timestamp AS VARCHAR),
            1, 10
        )
    ) AS min_date,
    MAX(
        SUBSTR(
            CAST(synthetic_order_timestamp AS VARCHAR),
            1, 10
        )
    ) AS max_date
FROM instacart_db.orders
"""
