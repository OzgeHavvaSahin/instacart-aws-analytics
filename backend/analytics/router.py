import logging

from services.athena_service import run_query
from queries.summary import SUMMARY_QUERY
from utils.responses import (
    success_response,
    error_response
)

logger = logging.getLogger(__name__)


def get_summary():
    # Athena sorgusunu calistir
    result = run_query(SUMMARY_QUERY, max_rows=1)

    rows = result["rows"]

    if not rows:
        raise RuntimeError(
            "Athena returned no summary data"
        )

    row = rows[0]

    # Athena sayilari string olarak dondurur.
    # JSON icin uygun tiplere ceviriyoruz.
    data = {
        "total_orders": int(row["total_orders"]),
        "total_customers": int(row["total_customers"]),
        "total_items": int(row["total_items"]),
        "estimated_revenue": float(
            row["estimated_revenue"]
        ),
        "currency": "USD",
        "revenue_type": "synthetic"
    }

    logger.info(
        "Summary query completed: %s",
        result["query_id"]
    )

    return success_response(data)


def route_request(event):
    request_context = event.get(
        "requestContext", {}
    )

    http = request_context.get("http", {})

    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    # Health endpoint
    if method == "GET" and path == "/api/health":
        return success_response({
            "service": "instacart-analytics-api",
            "status": "healthy",
            "version": "1.0.0"
        })

    # Summary endpoint
    if method == "GET" and path == "/api/summary":
        return get_summary()

    # Unknown endpoint
    return error_response(
        "Endpoint not found",
        status_code=404
    )
