
import hashlib
import json
import logging

from datetime import datetime, timezone
from io import BytesIO

from botocore.exceptions import ClientError

from config import (
    s3,
    RAW_PREFIX,
    STAGING_PREFIX,
    PROCESSED_V2_PREFIX,
    COMMITS_PREFIX,
)

from validators import (
    validate_manifest,
    read_verified_csv,
    validate_dataframes,
)

logger = logging.getLogger(__name__)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def manifest_fingerprint(manifest):
    payload = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return sha256(payload)


def head_verified(bucket, key, expected):
    response = s3.head_object(
        Bucket=bucket,
        Key=key,
    )

    if response["ContentLength"] != expected["bytes"]:
        raise RuntimeError(
            f"Output size mismatch: {key}"
        )

    actual_sha = response.get(
        "Metadata", {}
    ).get("sha256")

    if actual_sha != expected["sha256"]:
        raise RuntimeError(
            f"Output metadata mismatch: {key}"
        )


def final_keys(batch_id):
    return {
        table_name: (
            f"{PROCESSED_V2_PREFIX}"
            f"{table_name}/{batch_id}.parquet"
        )
        for table_name in ("orders", "order_items")
    }


def read_existing_commit(bucket, batch_id):
    key = f"{COMMITS_PREFIX}{batch_id}.json"

    try:
        response = s3.get_object(
            Bucket=bucket,
            Key=key,
        )
    except ClientError as error:
        if (
            error.response["Error"]["Code"]
            in ("NoSuchKey", "404")
        ):
            return None
        raise

    try:
        return json.loads(
            response["Body"].read()
        )
    finally:
        response["Body"].close()


def verify_existing_commit(
    bucket,
    batch_id,
    manifest,
    commit,
):
    if commit.get("status") != "COMMITTED":
        raise RuntimeError("Invalid commit status")

    if commit.get("batch_id") != batch_id:
        raise RuntimeError("Commit batch mismatch")

    if (
        commit.get("manifest_sha256")
        != manifest_fingerprint(manifest)
    ):
        raise RuntimeError(
            "Committed manifest differs from source"
        )

    if (
        commit.get("order_count")
        != manifest["order_count"]
        or commit.get("item_count")
        != manifest["item_count"]
    ):
        raise RuntimeError(
            "Committed row counts mismatch"
        )

    expected = commit.get("outputs", {})
    paths = final_keys(batch_id)

    for table_name, key in paths.items():
        info = expected.get(table_name)

        if (
            not isinstance(info, dict)
            or info.get("key") != key
        ):
            raise RuntimeError(
                "Invalid committed output"
            )

        head_verified(
            bucket,
            key,
            info,
        )

    return paths


def process_batch(
    bucket,
    batch_id,
    manifest,
    attempt_id,
):
    validate_manifest(manifest, batch_id)

    # If the commit was created but DynamoDB
    # was not updated, recover without
    # overwriting published files.

    existing = read_existing_commit(
        bucket,
        batch_id,
    )

    if existing is not None:
        logger.warning(
            "EXISTING COMMIT FOUND: %s",
            batch_id,
        )

        return verify_existing_commit(
            bucket,
            batch_id,
            manifest,
            existing,
        )

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

    payloads = {}

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

        payload = buffer.getvalue()

        payloads[table_name] = {
            "data": payload,
            "bytes": len(payload),
            "sha256": sha256(payload),
        }

    # PHASE 1: upload both staging files.

    for table_name, info in payloads.items():
        staging_key = (
            f"{STAGING_PREFIX}"
            f"{batch_id}/{attempt_id}/"
            f"{table_name}.parquet"
        )

        s3.put_object(
            Bucket=bucket,
            Key=staging_key,
            Body=info["data"],
            ContentType="application/octet-stream",
            Metadata={
                "sha256": info["sha256"]
            },
        )

        info["staging_key"] = staging_key

        head_verified(
            bucket,
            staging_key,
            info,
        )

    logger.info(
        "STAGING VERIFIED: %s",
        batch_id,
    )

    # PHASE 2: copy to final locations.
    # These locations are not queried
    # through safe views until commit.

    paths = final_keys(batch_id)

    for table_name, info in payloads.items():
        final_key = paths[table_name]

        s3.copy_object(
            Bucket=bucket,
            Key=final_key,
            CopySource={
                "Bucket": bucket,
                "Key": info["staging_key"],
            },
            MetadataDirective="COPY",
        )

        head_verified(
            bucket,
            final_key,
            info,
        )

        logger.info(
            "FINAL VERIFIED: %s",
            final_key,
        )

    # PHASE 3: write one commit marker.
    # Only after BOTH final files exist.

    commit_key = (
        f"{COMMITS_PREFIX}{batch_id}.json"
    )

    commit = {
        "batch_id": batch_id,
        "status": "COMMITTED",
        "committed_at": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "order_count": len(orders),
        "item_count": len(items),
        "manifest_sha256": (
            manifest_fingerprint(manifest)
        ),
        "outputs": {
            name: {
                "key": paths[name],
                "bytes": payloads[name]["bytes"],
                "sha256": payloads[name]["sha256"],
            }
            for name in paths
        },
    }

    s3.put_object(
        Bucket=bucket,
        Key=commit_key,
        Body=(
            json.dumps(
                commit,
                separators=(",", ":"),
            ) + "\n"
        ).encode("utf-8"),
        ContentType="application/json",
        IfNoneMatch="*",
    )

    logger.info(
        "BATCH COMMITTED: %s",
        batch_id,
    )

    return paths
