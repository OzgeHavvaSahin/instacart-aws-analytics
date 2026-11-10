from utils.responses import success_response, error_response


def route_request(event):
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})

    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    # Local / API Gateway HTTP API test
    if method == "GET" and path == "/api/health":
        return success_response({
            "service": "instacart-analytics-api",
            "status": "healthy",
            "version": "1.0.0"
        })

    return error_response(
        "Endpoint not found",
        status_code=404
    )
