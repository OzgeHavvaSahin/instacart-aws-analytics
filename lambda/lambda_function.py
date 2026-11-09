
import json
import re
import hashlib
import logging
from io import BytesIO
from urllib.parse import unquote_plus

import boto3
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = "instacart-ecom-data-raw"
RAW_PREFIX = "raw/batches/"
PROCESSED_PREFIX = "processed/"

FILES = {
    "orders.csv": "orders",
    "order_items.csv": "order_items",
}


def validate_manifest(manifest, batch_id):
    if not isinstance(manifest, dict):
        raise ValueError("Invalid manifest")

    if manifest.get("schema_version") != 1:
        raise ValueError("Invalid schema version")

    if manifest.get("batch_id") != batch_id:
        raise ValueError("Batch ID mismatch")

    for field in ("order_count", "item_count"):
        value = manifest.get(field)

        if type(value) is not int or value <= 0:
            raise ValueError(f"Invalid {field}")

    metadata = manifest.get("files")

    if not isinstance(metadata, dict):
        raise ValueError("Missing file metadata")

    for filename in FILES:
        info = metadata.get(filename)

        if not isinstance(info, dict):
            raise ValueError(f"Missing {filename}")

        if (
            type(info.get("bytes")) is not int
            or info["bytes"] <= 0
        ):
            raise ValueError(f"Invalid size: {filename}")

        if not re.fullmatch(
            r"[0-9a-fA-F]{64}",
            str(info.get("sha256", ""))
        ):
            raise ValueError(f"Invalid SHA256: {filename}")


def read_verified_csv(bucket, key, metadata):
    logger.info("Reading and verifying: %s", key)

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    try:
        # First check object size.
        expected_size = metadata["bytes"]

        if response["ContentLength"] != expected_size:
            raise ValueError(
                f"Size mismatch: {key}"
            )

        # This batch is small enough to hold in memory.
        data = response["Body"].read()

    finally:
        response["Body"].close()

    if len(data) != expected_size:
        raise ValueError(
            f"Incomplete download: {key}"
        )

    actual_hash = hashlib.sha256(
        data
    ).hexdigest()

    if actual_hash.lower() != metadata["sha256"].lower():
        raise ValueError(
            f"SHA256 mismatch: {key}"
        )

    logger.info("SHA256 VERIFIED: %s", key)

    # Parse after integrity verification.
    return pd.read_csv(BytesIO(data))


def process_batch(bucket, batch_id, manifest):
    validate_manifest(manifest, batch_id)

    prefix = f"{RAW_PREFIX}{batch_id}/"

    orders = read_verified_csv(
        bucket,
        prefix + "orders.csv",
        manifest["files"]["orders.csv"]
    )

    items = read_verified_csv(
        bucket,
        prefix + "order_items.csv",
        manifest["files"]["order_items.csv"]
    )

    # Validate expected columns.
    required_orders = {
        "order_id",
        "user_id",
        "synthetic_order_timestamp"
    }

    required_items = {
        "order_id",
        "product_id",
        "add_to_cart_order",
        "reordered"
    }

    if not required_orders.issubset(orders.columns):
        raise ValueError("Missing order columns")

    if not required_items.issubset(items.columns):
        raise ValueError("Missing item columns")

    # Validate row counts.
    if len(orders) != manifest["order_count"]:
        raise ValueError("Order count mismatch")

    if len(items) != manifest["item_count"]:
        raise ValueError("Item count mismatch")

    if orders["order_id"].isna().any():
        raise ValueError("Missing order IDs")

    if orders["order_id"].duplicated().any():
        raise ValueError("Duplicate order IDs")

    if items[["order_id", "product_id"]].isna().any().any():
        raise ValueError("Missing item identifiers")

    # All order items must belong to this batch.
    if not items["order_id"].isin(
        orders["order_id"]
    ).all():
        raise ValueError("Orphan order items found")

    # Convert synthetic timestamps.
    orders["synthetic_order_timestamp"] = (
        pd.to_datetime(
            orders["synthetic_order_timestamp"],
            errors="raise"
        )
    )

    if orders["synthetic_order_timestamp"].isna().any():
        raise ValueError("Missing timestamps")

    # Explicitly document the batch source.
    orders["batch_id"] = batch_id
    items["batch_id"] = batch_id

    # Generate both Parquet files before upload.
    outputs = []

    for table_name, dataframe in (
        ("orders", orders),
        ("order_items", items)
    ):
        buffer = BytesIO()

        dataframe.to_parquet(
            buffer,
            engine="pyarrow",
            compression="snappy",
            index=False
        )

        outputs.append((
            table_name,
            buffer.getvalue()
        ))

    # Only start uploading after all checks pass.
    result = {}

    for table_name, payload in outputs:
        output_key = (
            f"{PROCESSED_PREFIX}"
            f"{table_name}/"
            f"{batch_id}.parquet"
        )

        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=payload,
            ContentType="application/octet-stream"
        )

        logger.info(
            "PARQUET CREATED: s3://%s/%s",
            bucket,
            output_key
        )

        result[table_name] = output_key

    logger.info(
        "BATCH PROCESSED: %s | orders=%d items=%d",
        batch_id,
        len(orders),
        len(items)
    )

    return result


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
            key
        )

        if not match:
            logger.warning("Ignored: %s", key)
            continue

        batch_id = match.group(1)

        logger.info("START BATCH: %s", batch_id)

        # Read the manifest.
        response = s3.get_object(
            Bucket=bucket,
            Key=key
        )

        try:
            manifest = json.loads(
                response["Body"].read().decode("utf-8")
            )
        finally:
            response["Body"].close()

        output = process_batch(
            bucket,
            batch_id,
            manifest
        )

        results.append({
            "batch_id": batch_id,
            "status": "PROCESSED",
            "files": output
        })

    return {
        "statusCode": 200,
        "body": json.dumps({
            "results": results
        })
    }
