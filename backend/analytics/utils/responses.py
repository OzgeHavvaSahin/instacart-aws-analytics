import json


def success_response(data, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "success": True,
            "data": data
        })
    }


def error_response(message, status_code=400):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "success": False,
            "error": {
                "message": message
            }
        })
    }
