
import json

from lambda_function import lambda_handler


event = {
    "version": "2.0",
    "rawPath": "/api/summary",
    "requestContext": {
        "http": {
            "method": "GET",
            "path": "/api/summary"
        }
    }
}

response = lambda_handler(event, None)

print("HTTP Status:", response["statusCode"])

body = json.loads(response["body"])

print(
    json.dumps(
        body,
        indent=2,
        ensure_ascii=False
    )
)

assert response["statusCode"] == 200
assert body["success"] is True
assert body["data"]["total_orders"] == 500000

print("SUMMARY ENDPOINT TEST PASSED")
