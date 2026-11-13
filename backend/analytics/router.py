
import logging

from services.athena_service import run_query

from queries.summary import SUMMARY_QUERY
from queries.products import (
    get_top_products_query,
    build_products_query,
)
from queries.departments import DEPARTMENTS_QUERY
from queries.trends import ORDERS_TREND_QUERY

from queries.filters import (
    DEPARTMENTS_FILTER_QUERY,
    DATE_BOUNDS_QUERY,
    build_aisles_filter_query,
)

from queries.overview import build_overview_query

from queries.revenue import build_revenue_trend_query

from queries.departments_analytics import (
    build_departments_analytics_query,
)

from queries.reorders import build_reorders_query

from queries.shopping_patterns import (
    build_shopping_patterns_query,
)

from utils.responses import (
    success_response,
    error_response,
)

from utils.validators import (
    validate_limit,
    parse_positive_int,
    validate_products_filters,
    validate_overview_filters,
)

logger = logging.getLogger(__name__)


# ======================================
# SUMMARY
# ======================================

def get_summary():
    result = run_query(
        SUMMARY_QUERY,
        max_rows=1,
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
        "revenue_type": "synthetic",
    })


# ======================================
# TOP PRODUCTS (LEGACY)
# ======================================

def get_top_products(params):
    limit = validate_limit(
        params.get("limit")
    )

    sql = get_top_products_query(limit)

    result = run_query(
        sql,
        max_rows=limit,
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
            ),
        })

    return success_response({
        "products": products,
        "count": len(products),
        "revenue_type": "synthetic",
    })


# ======================================
# DEPARTMENTS (LEGACY)
# ======================================

def get_departments():
    result = run_query(
        DEPARTMENTS_QUERY,
        max_rows=100,
    )

    departments = []

    for row in result["rows"]:
        departments.append({
            "department_id": int(row["department_id"]),
            "department_name": row["department_name"],
            "units_sold": int(row["units_sold"]),
            "estimated_revenue": float(
                row["estimated_revenue"]
            ),
        })

    return success_response({
        "departments": departments,
        "count": len(departments),
        "revenue_type": "synthetic",
    })


# ======================================
# ORDERS TREND (LEGACY)
# ======================================

def get_orders_trend():
    result = run_query(
        ORDERS_TREND_QUERY,
        max_rows=1000,
    )

    trends = []

    for row in result["rows"]:
        trends.append({
            "date": row["order_date"],
            "total_orders": int(row["total_orders"]),
            "total_customers": int(
                row["total_customers"]
            ),
        })

    return success_response({
        "trends": trends,
        "count": len(trends),
        "date_type": "synthetic",
    })


# ======================================
# GLOBAL FILTERS
# ======================================

def get_filters(params):
    department_id = parse_positive_int(
        params.get("department_id"),
        "department_id",
    )

    departments_result = run_query(
        DEPARTMENTS_FILTER_QUERY,
        max_rows=100,
    )

    aisles_result = run_query(
        build_aisles_filter_query(department_id),
        max_rows=3000,
    )

    dates_result = run_query(
        DATE_BOUNDS_QUERY,
        max_rows=1,
    )

    departments = [
        {
            "id": int(row["department_id"]),
            "name": row["department"],
        }
        for row in departments_result["rows"]
    ]

    aisles = [
        {
            "id": int(row["aisle_id"]),
            "name": row["aisle"],
            "department_id": int(
                row["department_id"]
            ),
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
            "max": date_row.get("max_date") or None,
        },
        "selected_department_id": department_id,
        "date_type": "synthetic",
    })


# ======================================
# ANALYTICS OVERVIEW
# ======================================

def get_overview(params):
    filters = validate_overview_filters(params)

    result = run_query(
        build_overview_query(filters),
        max_rows=1,
    )

    if not result["rows"]:
        raise RuntimeError(
            "Overview query returned no data"
        )

    row = result["rows"][0]

    return success_response({
        "total_orders": int(
            row["total_orders"] or 0
        ),
        "total_customers": int(
            row["total_customers"] or 0
        ),
        "total_items": int(
            row["total_items"] or 0
        ),
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
        "applied_filters": filters,
    })


# ======================================
# ANALYTICS PRODUCTS
# ======================================

def get_filtered_products(params):
    filters = validate_products_filters(params)

    sql = build_products_query(filters)

    result = run_query(
        sql,
        max_rows=filters["limit"],
    )

    products = []

    for row in result["rows"]:
        products.append({
            "product_id": int(row["product_id"]),
            "product_name": row["product_name"],
            "department_id": int(
                row["department_id"]
            ),
            "aisle_id": int(row["aisle_id"]),
            "units_sold": int(row["units_sold"]),
            "order_count": int(row["order_count"]),
            "estimated_revenue": float(
                row["estimated_revenue"]
            ),
            "reorder_rate": float(
                row["reorder_rate"] or 0
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


# ======================================
# REVENUE TREND (NEW)
# ======================================

def get_revenue_trend(params):
    filters = validate_overview_filters(params)

    granularity = (
        params.get("granularity") or "day"
    )

    if granularity not in {
        "day",
        "week",
        "month",
    }:
        raise ValueError(
            "granularity must be day, week or month"
        )

    sql = build_revenue_trend_query(
        filters,
        granularity,
    )

    result = run_query(
        sql,
        max_rows=1500,
    )

    trends = []

    for row in result["rows"]:
        trends.append({
            "period": row["period"],
            "total_orders": int(
                row["total_orders"] or 0
            ),
            "total_items": int(
                row["total_items"] or 0
            ),
            "estimated_revenue": float(
                row["estimated_revenue"] or 0
            ),
        })

    return success_response({
        "trends": trends,
        "count": len(trends),
        "granularity": granularity,
        "currency": "USD",
        "revenue_type": "synthetic",
        "date_type": "synthetic",
        "applied_filters": filters,
    })


# ======================================
# DEPARTMENT ANALYTICS (NEW)
# ======================================

def get_analytics_departments(params):
    filters = validate_overview_filters(params)

    result = run_query(
        build_departments_analytics_query(filters),
        max_rows=100,
    )

    items = []

    for row in result["rows"]:
        items.append({
            "department_id": int(
                row["department_id"]
            ),
            "department_name": row["department_name"],
            "units_sold": int(row["units_sold"]),
            "total_orders": int(
                row["total_orders"]
            ),
            "total_customers": int(
                row["total_customers"]
            ),
            "estimated_revenue": float(
                row["estimated_revenue"] or 0
            ),
            "reorder_rate": float(
                row["reorder_rate"] or 0
            ),
        })

    return success_response({
        "items": items,
        "count": len(items),
        "currency": "USD",
        "revenue_type": "synthetic",
        "applied_filters": filters,
    })


# ======================================
# REORDER ANALYTICS (NEW)
# ======================================

def get_analytics_reorders(params):
    filters = validate_overview_filters(params)

    result = run_query(
        build_reorders_query(filters),
        max_rows=1,
    )

    if not result["rows"]:
        raise RuntimeError(
            "Reorders query returned no data"
        )

    row = result["rows"][0]

    return success_response({
        "total_items": int(
            row["total_items"] or 0
        ),
        "reordered_items": int(
            row["reordered_items"] or 0
        ),
        "first_time_items": int(
            row["first_time_items"] or 0
        ),
        "total_orders": int(
            row["total_orders"] or 0
        ),
        "reorder_rate": float(
            row["reorder_rate"] or 0
        ),
        "applied_filters": filters,
    })


# ======================================
# SHOPPING PATTERNS (NEW)
# ======================================

def get_analytics_shopping_patterns(params):
    filters = validate_overview_filters(params)

    result = run_query(
        build_shopping_patterns_query(filters),
        max_rows=200,
    )

    items = []

    for row in result["rows"]:
        items.append({
            "day_of_week": int(
                row["day_of_week"]
            ),
            "hour_of_day": int(
                row["hour_of_day"]
            ),
            "total_orders": int(
                row["total_orders"]
            ),
        })

    return success_response({
        "items": items,
        "count": len(items),
        "date_type": "synthetic",
        "applied_filters": filters,
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
            status_code=405,
        )

    # Health

    if path == "/api/health":
        return success_response({
            "service": "instacart-analytics-api",
            "status": "healthy",
            "version": "1.1.0",
        })

    # Legacy endpoints

    if path == "/api/summary":
        return get_summary()

    if path == "/api/top-products":
        try:
            return get_top_products(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    if path == "/api/departments":
        return get_departments()

    if path == "/api/orders-trend":
        return get_orders_trend()

    # Global filters

    if path == "/api/filters":
        try:
            return get_filters(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Overview analytics

    if path == "/api/analytics/overview":
        try:
            return get_overview(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Product analytics

    if path == "/api/analytics/products":
        try:
            return get_filtered_products(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Revenue analytics

    if path == "/api/analytics/revenue-trend":
        try:
            return get_revenue_trend(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Department analytics

    if path == "/api/analytics/departments":
        try:
            return get_analytics_departments(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Reorder analytics

    if path == "/api/analytics/reorders":
        try:
            return get_analytics_reorders(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    # Shopping patterns

    if path == "/api/analytics/shopping-patterns":
        try:
            return get_analytics_shopping_patterns(params)
        except ValueError as error:
            return error_response(
                str(error),
                status_code=400,
            )

    return error_response(
        "Endpoint not found",
        status_code=404,
    )
