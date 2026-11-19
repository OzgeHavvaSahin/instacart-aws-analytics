import os
import boto3

BUCKET = "instacart-ecom-data-raw"

RAW_PREFIX = "raw/batches/"
PROCESSED_PREFIX = "processed/"

EVENTS_TABLE_NAME = os.environ.get(
    "EVENTS_TABLE_NAME",
    "instacart-system-events",
)

ALERTS_TOPIC_ARN = os.environ.get(
    "ALERTS_TOPIC_ARN",
)

FILES = {
    "orders.csv": "orders",
    "order_items.csv": "order_items",
}

s3 = boto3.client("s3")
sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

events_table = dynamodb.Table(
    EVENTS_TABLE_NAME
)

STAGING_PREFIX = "staging/"
PROCESSED_V2_PREFIX = "processed_v2/"
COMMITS_PREFIX = "control/commits/"
