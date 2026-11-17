import logging
from datetime import datetime, timezone
from uuid import uuid4

from config import (
    events_table,
    sns,
    ALERTS_TOPIC_ARN,
)

logger = logging.getLogger(__name__)


def save_system_event(
    status,
    batch_id,
    error_code=None,
    message=None,
    order_count=None,
    item_count=None,
    request_id=None,
):
    event_id = str(uuid4())

    timestamp = datetime.now(
        timezone.utc
    ).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")

    event = {
        "event_id": event_id,
        "timestamp": timestamp,
        "status": status,
        "status_day": f"{status}#{timestamp[:10]}",
        "time_event": f"{timestamp}#{event_id}",
        "service": "ingestion-lambda",
        "batch_id": batch_id,
    }

    if error_code:
        event["error_code"] = error_code

    if message:
        event["message"] = message[:500]

    if order_count is not None:
        event["order_count"] = order_count

    if item_count is not None:
        event["item_count"] = item_count

    if request_id:
        event["request_id"] = request_id

    events_table.put_item(Item=event)

    return event_id


def try_save_system_event(**kwargs):
    try:
        return save_system_event(**kwargs)
    except Exception:
        logger.exception(
            "Failed to write DynamoDB system event"
        )
        return None


def send_error_notification(
    batch_id,
    error_code,
    message,
):
    if not ALERTS_TOPIC_ARN:
        raise RuntimeError(
            "ALERTS_TOPIC_ARN is not configured"
        )

    sns.publish(
        TopicArn=ALERTS_TOPIC_ARN,
        Subject="Instacart Ingestion - ERROR",
        Message=(
            "Instacart Ingestion Failure\n\n"
            f"Batch: {batch_id}\n"
            f"Error: {error_code}\n"
            f"Details: {message[:500]}\n\n"
            "Check CloudWatch Logs for details."
        ),
    )


def try_send_error_notification(
    batch_id,
    error_code,
    message,
):
    try:
        send_error_notification(
            batch_id,
            error_code,
            message,
        )
    except Exception:
        logger.exception(
            "Failed to publish SNS notification"
        )
