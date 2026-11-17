import json
import logging
import re

from urllib.parse import unquote_plus

from config import s3, BUCKET

from processor import process_batch

from monitoring import (
    try_save_system_event,
    try_send_error_notification,
)

from batch_state import (
    claim_batch,
    mark_batch_success,
    mark_batch_failed,
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

        # =====================================
        # IDEMPOTENCY CHECK
        # =====================================

        claim_status, attempt_id = claim_batch(
            batch_id
        )

        if claim_status == "SUCCESS":
            logger.info(
                "SKIPPED ALREADY PROCESSED: %s",
                batch_id,
            )

            results.append({
                "batch_id": batch_id,
                "status": "SKIPPED",
                "reason": "ALREADY_PROCESSED",
            })
            continue

        if claim_status == "PROCESSING":
            logger.warning(
                "BATCH ALREADY IN PROGRESS: %s",
                batch_id,
            )

            results.append({
                "batch_id": batch_id,
                "status": "SKIPPED",
                "reason": "ALREADY_PROCESSING",
            })
            continue

        logger.info(
            "START BATCH: %s | attempt=%s",
            batch_id,
            attempt_id,
        )

        # =====================================
        # PROCESS BATCH
        # =====================================

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

            # Mark FAILED before raising.
            # Failure of this state update is
            # logged without masking the
            # original processing exception.

            try:
                mark_batch_failed(
                    batch_id,
                    attempt_id,
                    message,
                )
            except Exception:
                logger.exception(
                    "Could not mark batch FAILED"
                )

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

            raise

        # =====================================
        # COMMIT BATCH STATE
        # =====================================

        # This operation must succeed.
        # If it fails, do NOT falsely report
        # that the batch is complete.

        mark_batch_success(
            batch_id=batch_id,
            attempt_id=attempt_id,
            order_count=manifest["order_count"],
            item_count=manifest["item_count"],
        )

        # Monitoring is secondary to the
        # authoritative batch-state record.

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

    return {
        "statusCode": 200,
        "body": json.dumps({
            "results": results
        }),
    }
