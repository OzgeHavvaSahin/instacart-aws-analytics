import logging
from io import BytesIO

from config import (
    s3,
    RAW_PREFIX,
    PROCESSED_PREFIX,
)

from validators import (
    validate_manifest,
    read_verified_csv,
    validate_dataframes,
)

logger = logging.getLogger(__name__)


def process_batch(bucket, batch_id, manifest):
    validate_manifest(manifest, batch_id)

    prefix = f"{RAW_PREFIX}{batch_id}/"

    orders = read_verified_csv(
        bucket,
        prefix + "orders.csv",
        manifest["files"]["orders.csv"],
    )

    items = read_verified_csv(
        bucket,
        prefix + "order_items.csv",
        manifest["files"]["order_items.csv"],
    )

    orders, items = validate_dataframes(
        orders,
        items,
        manifest,
    )

    orders["batch_id"] = batch_id
    items["batch_id"] = batch_id

    # Both Parquet payloads are generated
    # before starting the S3 uploads.

    outputs = []

    for table_name, dataframe in (
        ("orders", orders),
        ("order_items", items),
    ):
        buffer = BytesIO()

        dataframe.to_parquet(
            buffer,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        outputs.append((
            table_name,
            buffer.getvalue(),
        ))

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
            ContentType="application/octet-stream",
        )

        logger.info(
            "PARQUET CREATED: s3://%s/%s",
            bucket,
            output_key,
        )

        result[table_name] = output_key

    logger.info(
        "BATCH PROCESSED: %s | orders=%d items=%d",
        batch_id,
        len(orders),
        len(items),
    )

    return result
