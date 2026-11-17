import hashlib
import re
from io import BytesIO

import pandas as pd

from config import FILES, s3


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
            raise ValueError(
                f"Invalid size: {filename}"
            )

        if not re.fullmatch(
            r"[0-9a-fA-F]{64}",
            str(info.get("sha256", ""))
        ):
            raise ValueError(
                f"Invalid SHA256: {filename}"
            )


def read_verified_csv(bucket, key, metadata):
    response = s3.get_object(
        Bucket=bucket,
        Key=key,
    )

    try:
        expected_size = metadata["bytes"]

        if response["ContentLength"] != expected_size:
            raise ValueError(f"Size mismatch: {key}")

        data = response["Body"].read()
    finally:
        response["Body"].close()

    if len(data) != expected_size:
        raise ValueError(f"Incomplete download: {key}")

    actual_hash = hashlib.sha256(
        data
    ).hexdigest()

    if (
        actual_hash.lower()
        != metadata["sha256"].lower()
    ):
        raise ValueError(f"SHA256 mismatch: {key}")

    return pd.read_csv(BytesIO(data))


def validate_dataframes(orders, items, manifest):
    required_orders = {
        "order_id",
        "user_id",
        "synthetic_order_timestamp",
    }

    required_items = {
        "order_id",
        "product_id",
        "add_to_cart_order",
        "reordered",
    }

    if not required_orders.issubset(orders.columns):
        raise ValueError("Missing order columns")

    if not required_items.issubset(items.columns):
        raise ValueError("Missing item columns")

    if len(orders) != manifest["order_count"]:
        raise ValueError("Order count mismatch")

    if len(items) != manifest["item_count"]:
        raise ValueError("Item count mismatch")

    if orders["order_id"].isna().any():
        raise ValueError("Missing order IDs")

    if orders["order_id"].duplicated().any():
        raise ValueError("Duplicate order IDs")

    if items[
        ["order_id", "product_id"]
    ].isna().any().any():
        raise ValueError("Missing item identifiers")

    if not items["order_id"].isin(
        orders["order_id"]
    ).all():
        raise ValueError("Orphan order items found")

    orders["synthetic_order_timestamp"] = (
        pd.to_datetime(
            orders["synthetic_order_timestamp"],
            errors="raise",
        )
    )

    if orders[
        "synthetic_order_timestamp"
    ].isna().any():
        raise ValueError("Missing timestamps")

    return orders, items
