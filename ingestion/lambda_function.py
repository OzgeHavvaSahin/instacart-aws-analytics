import json
import logging
import re

from urllib.parse import unquote_plus

from config import (
    s3,
    BUCKET,
)

from processor import process_batch

from monitoring import (
    try_save_system_event,
    try_send_error_notification,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    results = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]

        key = unquote_plus(
            record["s3"]["object"]["key"]
        )

        if bucket != BUCKET:
            raise ValueError("Unexpected bucket")

        match = re.fullmatch(
            r"raw/batches/(batch_\d{4,})/_READY\.json",
            key,
        )

        if not match:
            logger.warning("Ignored: %s", key)
            continue

        batch_id = match.group(1)

        request_id = getattr(
            context,
            "aws_request_id",
            None,
        )

        logger.info(
            "START BATCH: %s",
            batch_id,
        )

        try:
            response = s3.get_object(
                Bucket=bucket,
                Key=key,
            )

            try:
                manifest = json.loads(
                    response["Body"]
                    .read()
                    .decode("utf-8")
                )
            finally:
                response["Body"].close()

            output = process_batch(
                bucket,
                batch_id,
                manifest,
            )

            try_save_system_event(
                status="SUCCESS",
                batch_id=batch_id,
                order_count=manifest["order_count"],
                item_count=manifest["item_count"],
                request_id=request_id,
            )

            results.append({
                "batch_id": batch_id,
                "status": "PROCESSED",
                "files": output,
            })

        except Exception as error:
            logger.exception(
                "BATCH FAILED: %s",
                batch_id,
            )

            error_code = (
                "VALIDATION_ERROR"
                if isinstance(error, ValueError)
                else type(error).__name__
            )

            message = str(error)[:500]

            try_save_system_event(
                status="ERROR",
                batch_id=batch_id,
                error_code=error_code,
                message=message,
                request_id=request_id,
            )

            try_send_error_notification(
                batch_id=batch_id,
                error_code=error_code,
                message=message,
            )

            # Propagate the failure to Lambda.
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "results": results,
        }),
    }
