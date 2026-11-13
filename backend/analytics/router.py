import logging

from services.athena_service import run_query

from queries.summary import SUMMARY_QUERY
from queries.products import get_top_products_query
from queries.departments import DEPARTMENTS_QUERY
from queries.trends import ORDERS_TREND_QUERY

from utils.responses import (
    success_response,
    error_response
)

from utils.validators import validate_limit

from queries.products import build_products_query
from utils.validators import validate_products_filters

logger = logging.getLogger(__name__)


from queries.filters import (
    DEPARTMENTS_FILTER_QUERY,
    DATE_BOUNDS_QUERY,
    build_aisles_filter_query,
)

from queries.overview import build_overview_query

from utils.validators import (
    parse_positive_int,
    validate_overview_filters,
)


# ======================================
# SUMMARY
# ======================================

def get_summary():
    result = run_query(
        SUMMARY_QUERY,
        max_rows=1
    )

    if not result["rows"]:
        raise RuntimeError("No summary data")

    row = result["rows"][0]

    return success_response({
        "total_orders": int(row["total_orders"]),
        "total_customers": int(row["total_customers"]),
        "total_items": int(row["total_items"]),
        "estimated_revenue": float(
            row["estimated_revenue"]
        ),
        "currency": "USD",
        "revenue_type": "synthetic"
    })


# ======================================
# TOP PRODUCTS
# ======================================

def get_top_products(params):
    limit = validate_limit(
        params.get("limit")
    )

    sql = get_top_products_query(limit)

    result = run_query(
        sql,
        max_rows=limit
    )

    products = []

    for row in result["rows"]:
        products.append({
            "product_id": int(row["product_id"]),
            "product_name": row["product_name"],
            "department_name": row["department_name"],
            "units_sold": int(row["units_sold"]),
            "estimated_revenue": float(
                row["estimated_revenue"]
            )
        })

    return success_response({
        "products": products,
        "count": len(products),
        "revenue_type": "synthetic"
    })


# ======================================
# DEPARTMENTS
# ======================================

def get_departments():
    result = run_query(
        DEPARTMENTS_QUERY,
        max_rows=100
    )

    departments = []

    for row in result["rows"]:
        departments.append({
            "department_id": int(row["department_id"]),
            "department_name": row["department_name"],
            "units_sold": int(row["units_sold"]),
            "estimated_revenue": float(
                row["estimated_revenue"]
            )
        })

    return success_response({
        "departments": departments,
        "count": len(departments),
        "revenue_type": "synthetic"
    })


# ======================================
# ORDERS TREND
# ======================================

def get_orders_trend():
    result = run_query(
        ORDERS_TREND_QUERY,
        max_rows=1000
    )

    trends = []

    for row in result["rows"]:
        trends.append({
            "date": row["order_date"],
            "total_orders": int(row["total_orders"]),
            "total_customers": int(
                row["total_customers"]
            )
        })

    return success_response({
        "trends": trends,
        "count": len(trends),
        "date_type": "synthetic"
    })

def get_filters(params):
    department_id = parse_positive_int(
        params.get("department_id"),
        "department_id"
    )

    departments_result = run_query(
        DEPARTMENTS_FILTER_QUERY,
        max_rows=100
    )

    aisles_result = run_query(
        build_aisles_filter_query(department_id),
        max_rows=200
    )

    dates_result = run_query(
        DATE_BOUNDS_QUERY,
        max_rows=1
    )

    departments = [
        {
            "id": int(row["department_id"]),
            "name": row["department"]
        }
        for row in departments_result["rows"]
    ]

    aisles = [
        {
            "id": int(row["aisle_id"]),
            "name": row["aisle"]
        }
        for row in aisles_result["rows"]
    ]

    date_row = (
        dates_result["rows"][0]
        if dates_result["rows"]
        else {}
    )

    return success_response({
        "departments": departments,
        "aisles": aisles,
        "date_range": {
            "min": date_row.get("min_date") or None,
            "max": date_row.get("max_date") or None
        },
        "selected_department_id": department_id,
        "date_type": "synthetic"
    })


def get_overview(params):
    filters = validate_overview_filters(params)

    result = run_query(
        build_overview_query(filters),
        max_rows=1
    )

    if not result["rows"]:
        raise RuntimeError(
            "Overview query returned no data"
        )

    row = result["rows"][0]

    return success_response({
        "total_orders": int(row["total_orders"] or 0),
        "total_customers": int(
            row["total_customers"] or 0
        ),
        "total_items": int(row["total_items"] or 0),
        "estimated_revenue": float(
            row["estimated_revenue"] or 0
        ),
        "avg_basket_size": float(
            row["avg_basket_size"] or 0
        ),
        "reorder_rate": float(
            row["reorder_rate"] or 0
        ),
        "currency": "USD",
        "revenue_type": "synthetic",
        "date_type": "synthetic",
        "applied_filters": filters
    })


# ======================================
# ROUTER
# ======================================

def route_request(event):
    http = event.get(
        "requestContext", {}
    ).get("http", {})

    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    params = event.get(
        "queryStringParameters"
    ) or {}

    if method != "GET":
        return error_response(
            "Method not allowed",
            status_code=405
        )

    if path == "/api/health":
        return success_response({
            "service": "instacart-analytics-api",
            "status": "healthy",
            "version": "1.0.0"
        })

    if path == "/api/summary":
        return get_summary()

    if path == "/api/top-products":
        try:
            return get_top_products(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400
            )

    if path == "/api/departments":
        return get_departments()

    if path == "/api/orders-trend":
        return get_orders_trend()

    if path == "/api/analytics/products":
        try:
            return get_filtered_products(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400
            )

    
    if path == "/api/filters":
        try:
            return get_filters(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400
            )

    if path == "/api/analytics/overview":
        try:
            return get_overview(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400
            )


    return error_response(
        "Endpoint not found",
        status_code=404
    )


def get_filtered_products(params):
    filters = validate_products_filters(params)

    sql = build_products_query(filters)

    result = run_query(
        sql,
        max_rows=filters["limit"]
    )

    products = []

    for row in result["rows"]:
        products.append({
            "product_id": int(row["product_id"]),
            "product_name": row["product_name"],
            "department_id": int(row["department_id"]),
            "aisle_id": int(row["aisle_id"]),
            "units_sold": int(row["units_sold"]),
            "order_count": int(row["order_count"]),
            "estimated_revenue": float(
                row["estimated_revenue"]
            ),
            "reorder_rate": float(
                row["reorder_rate"]
            ),
        })

    return success_response({
        "items": products,
        "count": len(products),
        "filters": filters,
        "metadata": {
            "revenue_type": "synthetic",
            "reorder_rate_unit": "percent",
        },
    })
