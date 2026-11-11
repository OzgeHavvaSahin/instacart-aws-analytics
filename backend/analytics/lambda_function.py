import logging

from router import route_request
from utils.responses import error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        return route_request(event)

    except Exception:
        logger.exception("Unhandled API error")

        return error_response(
            "Internal server error",
            status_code=500
        )
