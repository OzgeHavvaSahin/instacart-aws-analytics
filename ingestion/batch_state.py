
import logging
import os

from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get(
    "BATCH_STATE_TABLE_NAME",
    "instacart-batch-state",
)

table = dynamodb.Table(TABLE_NAME)


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def is_conditional_failure(error):
    return (
        error.response["Error"]["Code"]
        == "ConditionalCheckFailedException"
    )


def get_batch_state(batch_id):
    response = table.get_item(
        Key={"batch_id": batch_id},
        ConsistentRead=True,
    )
    return response.get("Item")


def claim_batch(batch_id):
    """
    Returns:
        ("CLAIMED", attempt_id)
        ("SUCCESS", None)
        ("PROCESSING", None)
    """

    attempt_id = str(uuid4())
    timestamp = utc_now()

    new_item = {
        "batch_id": batch_id,
        "status": "PROCESSING",
        "attempt_id": attempt_id,
        "started_at": timestamp,
        "updated_at": timestamp,
    }

    # Try to create the batch state.
    # Only one concurrent caller can succeed.

    try:
        table.put_item(
            Item=new_item,
            ConditionExpression=(
                "attribute_not_exists(batch_id)"
            ),
        )

        logger.info(
            "BATCH CLAIMED: %s",
            batch_id,
        )

        return "CLAIMED", attempt_id

    except ClientError as error:
        if not is_conditional_failure(error):
            raise

    # A record already exists.
    state = get_batch_state(batch_id)

    if not state:
        raise RuntimeError(
            f"Batch state disappeared: {batch_id}"
        )

    status = state.get("status")

    if status == "SUCCESS":
        return "SUCCESS", None

    if status == "PROCESSING":
        return "PROCESSING", None

    if status != "FAILED":
        raise RuntimeError(
            f"Unexpected batch status: {status}"
        )

    # Previous attempt failed.
    # Allow only one caller to reclaim it.

    try:
        table.update_item(
            Key={"batch_id": batch_id},
            UpdateExpression=(
                "SET #status = :processing, "
                "attempt_id = :attempt, "
                "started_at = :now, "
                "updated_at = :now "
                "REMOVE completed_at, error_message"
            ),
            ConditionExpression=(
                "#status = :failed"
            ),
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":processing": "PROCESSING",
                ":failed": "FAILED",
                ":attempt": attempt_id,
                ":now": timestamp,
            },
        )

        logger.info(
            "FAILED BATCH RECLAIMED: %s",
            batch_id,
        )

        return "CLAIMED", attempt_id

    except ClientError as error:
        if not is_conditional_failure(error):
            raise

        # Another caller won the retry race.
        state = get_batch_state(batch_id)

        if not state:
            raise RuntimeError(
                f"Batch state unavailable: {batch_id}"
            )

        status = state.get("status")

        if status in ("SUCCESS", "PROCESSING"):
            return status, None

        raise RuntimeError(
            f"Unexpected retry state: {status}"
        )


def mark_batch_success(
    batch_id,
    attempt_id,
    order_count,
    item_count,
):
    table.update_item(
        Key={"batch_id": batch_id},
        UpdateExpression=(
            "SET #status = :success, "
            "completed_at = :now, "
            "updated_at = :now, "
            "order_count = :orders, "
            "item_count = :items"
        ),
        ConditionExpression=(
            "#status = :processing "
            "AND attempt_id = :attempt"
        ),
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":success": "SUCCESS",
            ":processing": "PROCESSING",
            ":attempt": attempt_id,
            ":now": utc_now(),
            ":orders": order_count,
            ":items": item_count,
        },
    )

    logger.info(
        "BATCH STATE SUCCESS: %s",
        batch_id,
    )


def mark_batch_failed(
    batch_id,
    attempt_id,
    error_message,
):
    table.update_item(
        Key={"batch_id": batch_id},
        UpdateExpression=(
            "SET #status = :failed, "
            "updated_at = :now, "
            "error_message = :message"
        ),
        ConditionExpression=(
            "#status = :processing "
            "AND attempt_id = :attempt"
        ),
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":failed": "FAILED",
            ":processing": "PROCESSING",
            ":attempt": attempt_id,
            ":now": utc_now(),
            ":message": error_message[:500],
        },
    )

    logger.info(
        "BATCH STATE FAILED: %s",
        batch_id,
    )
