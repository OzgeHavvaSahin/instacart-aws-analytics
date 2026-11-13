
import json

from lambda_function import lambda_handler


def test_endpoint(path, params=None):
    event = {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {
            "http": {
                "method": "GET",
                "path": path
            }
        },
        "queryStringParameters": params or {}
    }

    response = lambda_handler(event, None)

    print("\n" + "=" * 60)
    print("ENDPOINT:", path)
    print("STATUS:", response["statusCode"])

    body = json.loads(response["body"])

    print(json.dumps(
        body,
        indent=2,
        ensure_ascii=False
    ))

    assert response["statusCode"] == 200, body
    assert body["success"] is True


if __name__ == "__main__":
    test_endpoint("/api/health")
    test_endpoint("/api/summary")

    test_endpoint(
        "/api/top-products",
        {"limit": "5"}
    )

    test_endpoint("/api/departments")
    test_endpoint("/api/orders-trend")

    print("\nALL ENDPOINT TESTS PASSED")
