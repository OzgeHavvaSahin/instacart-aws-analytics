
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
   
   
    test_endpoint("/api/filters")

    test_endpoint(
        "/api/filters",
        {"department_id": "4"}
    )

    test_endpoint("/api/analytics/overview")

    test_endpoint(
        "/api/analytics/overview",
        {
            "department_id": "4",
        }
    )

    test_endpoint(
        "/api/analytics/overview",
        {
            "department_id": "4",
            "reordered": "true",
        }
    )
